"""Local HTTP server for hosting M3U playlists."""

from __future__ import annotations

import logging
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from fluxo.server.shared_link import SharedLink
from fluxo.services.export_service import ExportService

if TYPE_CHECKING:
    from fluxo.models.playlist import Playlist

logger = logging.getLogger(__name__)


def _get_local_ip() -> str:
    """Best-effort detection of the local LAN IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Doesn't actually send traffic — used to discover the default route
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class _PlaylistHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves M3U playlists for valid shared-link tokens."""

    server: PlaylistHTTPServer  # type narrowing

    # Suppress default access-log lines; we log via Python logging instead.
    def log_message(self, fmt: str, *args: object) -> None:  # noqa: ARG002
        logger.debug(fmt, *args)

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Health endpoint: GET /health
        if path == "/health":
            self._respond_text(HTTPStatus.OK, "ok")
            return

        # Playlist endpoint: GET /playlist/<token>
        if path.startswith("/playlist/"):
            token = path[len("/playlist/"):]
            self._serve_playlist(token, parsed.query)
            return

        self._respond_text(HTTPStatus.NOT_FOUND, "Not found")

    # ------------------------------------------------------------------
    # HEAD (stream validators probe with HEAD)
    # ------------------------------------------------------------------

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if path.startswith("/playlist/"):
            token = path[len("/playlist/"):]
            link = self.server.playlist_server._get_link(token)
            if link is None or not link.is_valid:
                self._respond_text(HTTPStatus.NOT_FOUND, "")
            else:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "audio/mpegurl; charset=utf-8")
                self.end_headers()
        else:
            self._respond_text(HTTPStatus.NOT_FOUND, "")

    # ------------------------------------------------------------------
    # Serve playlist
    # ------------------------------------------------------------------

    def _serve_playlist(self, token: str, query_string: str) -> None:
        ps = self.server.playlist_server
        link = ps._get_link(token)

        if link is None or not link.is_valid:
            self._respond_text(HTTPStatus.NOT_FOUND, "Link not found or expired.")
            return

        # Password check (via ?password=… query param)
        if link.has_password:
            params = parse_qs(query_string)
            pw_list = params.get("password", [])
            pw = pw_list[0] if pw_list else ""
            if not link.check_password(pw):
                self._respond_text(HTTPStatus.FORBIDDEN, "Invalid password.")
                return

        # Generate M3U content from the stored playlist
        playlist = ps._playlist
        if playlist is None:
            self._respond_text(
                HTTPStatus.SERVICE_UNAVAILABLE, "No playlist available."
            )
            return

        m3u = ExportService.export_m3u_filtered(playlist, groups=link.groups_filter)
        link.record_access()

        body = m3u.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "audio/mpegurl; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Content-Disposition",
            f'inline; filename="{link.label or "playlist"}.m3u"',
        )
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _respond_text(self, status: HTTPStatus, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class PlaylistHTTPServer(HTTPServer):
    """``HTTPServer`` subclass that holds a back-reference to :class:`PlaylistServer`."""

    def __init__(
        self,
        server_address: tuple[str, int],
        playlist_server: PlaylistServer,
    ) -> None:
        self.playlist_server = playlist_server
        super().__init__(server_address, _PlaylistHandler)


class PlaylistServer:
    """Lightweight local HTTP server that hosts M3U playlists via shareable links.

    The server runs in a daemon thread so it does not block the application.
    It uses Python's built-in :mod:`http.server` — no external framework required.

    Usage::

        server = PlaylistServer()
        server.set_playlist(my_playlist)
        link = server.create_link(label="My list")
        server.start()
        print(f"Share: {server.get_url(link)}")
        # …
        server.stop()
    """

    DEFAULT_PORT = 7481

    def __init__(self, port: int = DEFAULT_PORT) -> None:
        self._port = port
        self._playlist: Playlist | None = None
        self._links: dict[str, SharedLink] = {}
        self._httpd: PlaylistHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Playlist binding
    # ------------------------------------------------------------------

    def set_playlist(self, playlist: Playlist) -> None:
        """Set (or update) the playlist served by this server."""
        self._playlist = playlist

    # ------------------------------------------------------------------
    # Link management
    # ------------------------------------------------------------------

    def create_link(
        self,
        *,
        label: str = "",
        password: str | None = None,
        expires_at: datetime | None = None,
        groups_filter: list[str] | None = None,
    ) -> SharedLink:
        """Create a new :class:`SharedLink` and return it."""
        link = SharedLink(label=label, groups_filter=groups_filter, expires_at=expires_at)
        if password:
            link.set_password(password)
        self._links[link.token] = link
        return link

    def revoke_link(self, token: str) -> bool:
        """Deactivate a link by its token. Returns ``True`` if found."""
        link = self._links.get(token)
        if link is None:
            return False
        link.is_active = False
        return True

    def list_links(self) -> list[SharedLink]:
        """Return all links (active and inactive)."""
        return list(self._links.values())

    def get_url(self, link: SharedLink) -> str:
        """Return the full URL for a shared link."""
        host = _get_local_ip()
        return f"http://{host}:{self._port}/playlist/{link.token}"

    def _get_link(self, token: str) -> SharedLink | None:
        return self._links.get(token)

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def port(self) -> int:
        return self._port

    @property
    def base_url(self) -> str:
        return f"http://{_get_local_ip()}:{self._port}"

    def start(self) -> None:
        """Start the server in a daemon thread."""
        if self.is_running:
            return
        self._httpd = PlaylistHTTPServer(("0.0.0.0", self._port), self)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Playlist server started on port %d", self._port)

    def stop(self) -> None:
        """Shutdown the server gracefully."""
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Playlist server stopped")
