"""Sharing service — manages hosted playlist links and the local server."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fluxo.models.playlist import Playlist
from fluxo.persistence.settings import Settings
from fluxo.server.playlist_server import PlaylistServer
from fluxo.server.shared_link import SharedLink

logger = logging.getLogger(__name__)


class SharingService:
    """High-level facade for creating, listing, and revoking shared links.

    Wraps :class:`PlaylistServer` and persists link metadata to the Fluxo
    configuration directory so links survive application restarts.
    """

    _LINKS_FILE = "shared_links.json"

    def __init__(self, *, port: int = PlaylistServer.DEFAULT_PORT) -> None:
        self._server = PlaylistServer(port=port)

    # ------------------------------------------------------------------
    # Server lifecycle (delegated)
    # ------------------------------------------------------------------

    @property
    def server(self) -> PlaylistServer:
        return self._server

    def start(self, playlist: Playlist) -> None:
        """Start hosting *playlist*."""
        self._server.set_playlist(playlist)
        self._server.start()

    def stop(self) -> None:
        self._server.stop()

    @property
    def is_running(self) -> bool:
        return self._server.is_running

    # ------------------------------------------------------------------
    # Link CRUD
    # ------------------------------------------------------------------

    def create_link(
        self,
        *,
        label: str = "",
        password: str | None = None,
        expires_at: datetime | None = None,
        groups_filter: list[str] | None = None,
    ) -> SharedLink:
        """Create a new shared link and persist it."""
        link = self._server.create_link(
            label=label,
            password=password,
            expires_at=expires_at,
            groups_filter=groups_filter,
        )
        self._save_links()
        return link

    def revoke_link(self, token: str) -> bool:
        ok = self._server.revoke_link(token)
        if ok:
            self._save_links()
        return ok

    def list_links(self) -> list[SharedLink]:
        return self._server.list_links()

    def get_url(self, link: SharedLink) -> str:
        return self._server.get_url(link)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _links_path(self) -> Path:
        return Settings.get_config_dir() / self._LINKS_FILE

    def _save_links(self) -> None:
        path = self._links_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data: list[dict[str, Any]] = [ln.to_dict() for ln in self._server.list_links()]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_links(self) -> None:
        """Load previously-persisted links from disk."""
        path = self._links_path()
        if not path.is_file():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            for item in raw:
                link = SharedLink.from_dict(item)
                self._server._links[link.token] = link
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load shared links: %s", exc)
