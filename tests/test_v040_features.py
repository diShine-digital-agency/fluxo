"""Tests for v0.4.0 features — Hosting & Sharing."""

from __future__ import annotations

import time
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

from fluxo.models.channel import Channel
from fluxo.models.playlist import Playlist
from fluxo.server.playlist_server import PlaylistServer
from fluxo.server.shared_link import SharedLink, _hash_password, verify_password
from fluxo.services.sharing_service import SharingService

# -----------------------------------------------------------------------
# SharedLink model
# -----------------------------------------------------------------------


class TestSharedLink:
    """Unit tests for SharedLink dataclass."""

    def test_create_default_link(self):
        link = SharedLink()
        assert link.token  # auto-generated
        assert link.is_active
        assert link.is_valid
        assert not link.has_password
        assert not link.is_expired
        assert link.access_count == 0

    def test_set_and_check_password(self):
        link = SharedLink()
        link.set_password("secret123")
        assert link.has_password
        assert link.check_password("secret123")
        assert not link.check_password("wrong")

    def test_no_password_always_passes(self):
        link = SharedLink()
        assert link.check_password("")
        assert link.check_password("anything")

    def test_expiry_not_expired(self):
        link = SharedLink(expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
        assert not link.is_expired
        assert link.is_valid

    def test_expiry_expired(self):
        link = SharedLink(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        assert link.is_expired
        assert not link.is_valid

    def test_no_expiry_never_expires(self):
        link = SharedLink(expires_at=None)
        assert not link.is_expired
        assert link.is_valid

    def test_revoked_link_invalid(self):
        link = SharedLink(is_active=False)
        assert not link.is_valid

    def test_record_access(self):
        link = SharedLink()
        assert link.access_count == 0
        assert link.last_accessed_at is None
        link.record_access()
        assert link.access_count == 1
        assert link.last_accessed_at is not None
        link.record_access()
        assert link.access_count == 2

    def test_serialization_roundtrip(self):
        link = SharedLink(label="Test Link", groups_filter=["Sports", "News"])
        link.set_password("pw")
        link.record_access()
        data = link.to_dict()
        restored = SharedLink.from_dict(data)
        assert restored.token == link.token
        assert restored.label == "Test Link"
        assert restored.has_password
        assert restored.check_password("pw")
        assert restored.access_count == 1
        assert restored.groups_filter == ["Sports", "News"]

    def test_serialization_with_expiry(self):
        future = datetime.now(timezone.utc) + timedelta(days=7)
        link = SharedLink(expires_at=future)
        data = link.to_dict()
        restored = SharedLink.from_dict(data)
        assert restored.expires_at is not None
        assert not restored.is_expired

    def test_serialization_no_expiry(self):
        link = SharedLink(expires_at=None)
        data = link.to_dict()
        assert data["expires_at"] is None
        restored = SharedLink.from_dict(data)
        assert restored.expires_at is None

    def test_string_datetime_coercion(self):
        """__post_init__ should parse ISO strings into datetime objects."""
        now = datetime.now(timezone.utc)
        link = SharedLink(created_at=now.isoformat())  # type: ignore[arg-type]
        assert isinstance(link.created_at, datetime)


# -----------------------------------------------------------------------
# Password hashing functions
# -----------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h, s = _hash_password("test")
        assert verify_password("test", h, s)
        assert not verify_password("wrong", h, s)

    def test_deterministic_with_same_salt(self):
        import os

        salt = os.urandom(16)
        h1, s1 = _hash_password("abc", salt)
        h2, s2 = _hash_password("abc", salt)
        assert h1 == h2
        assert s1 == s2


# -----------------------------------------------------------------------
# PlaylistServer
# -----------------------------------------------------------------------


def _make_playlist(n: int = 3) -> Playlist:
    channels = [
        Channel(name=f"Ch {i}", url=f"http://example.com/stream{i}", group_title="Group A")
        for i in range(n)
    ]
    return Playlist(name="Test", channels=channels)


class TestPlaylistServer:
    """Integration tests for the local HTTP playlist server."""

    @pytest.fixture()
    def server(self):
        """Provide a running PlaylistServer on an ephemeral port."""
        srv = PlaylistServer(port=0)  # port 0 = OS picks a free port
        srv.set_playlist(_make_playlist())
        srv.start()
        # Wait briefly for the server thread to be ready
        time.sleep(0.15)
        yield srv
        srv.stop()

    def _url(self, server: PlaylistServer, path: str) -> str:
        port = server._httpd.server_address[1]  # actual bound port
        return f"http://127.0.0.1:{port}{path}"

    def test_health_endpoint(self, server):
        url = self._url(server, "/health")
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            assert resp.read() == b"ok"

    def test_not_found(self, server):
        url = self._url(server, "/nonexistent")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404

    def test_serve_playlist_valid_token(self, server):
        link = server.create_link(label="pub")
        url = self._url(server, f"/playlist/{link.token}")
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            body = resp.read().decode()
            assert body.startswith("#EXTM3U")
            assert "Ch 0" in body
        # Access count incremented
        assert link.access_count == 1

    def test_serve_playlist_invalid_token(self, server):
        url = self._url(server, "/playlist/bogus-token")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404

    def test_password_protected_link(self, server):
        link = server.create_link(label="priv", password="s3cret")
        base = self._url(server, f"/playlist/{link.token}")

        # No password → 403
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(base)
        assert exc_info.value.code == 403

        # Wrong password → 403
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{base}?password=wrong")
        assert exc_info.value.code == 403

        # Correct password → 200
        with urllib.request.urlopen(f"{base}?password=s3cret") as resp:
            assert resp.status == 200

    def test_revoked_link_returns_404(self, server):
        link = server.create_link(label="rev")
        server.revoke_link(link.token)
        url = self._url(server, f"/playlist/{link.token}")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404

    def test_expired_link_returns_404(self, server):
        link = server.create_link(
            label="exp",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        url = self._url(server, f"/playlist/{link.token}")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404

    def test_start_idempotent(self, server):
        """Calling start() on an already-running server is a no-op."""
        server.start()
        assert server.is_running

    def test_stop_and_restart(self):
        srv = PlaylistServer(port=0)
        srv.set_playlist(_make_playlist())
        srv.start()
        time.sleep(0.1)
        assert srv.is_running
        srv.stop()
        assert not srv.is_running

    def test_create_link_properties(self):
        srv = PlaylistServer(port=9999)
        link = srv.create_link(label="demo", groups_filter=["News"])
        assert link.label == "demo"
        assert link.groups_filter == ["News"]
        assert link in srv.list_links()

    def test_get_url_contains_token(self):
        srv = PlaylistServer(port=9999)
        link = srv.create_link(label="x")
        url = srv.get_url(link)
        assert link.token in url
        assert ":9999" in url


# -----------------------------------------------------------------------
# SharingService
# -----------------------------------------------------------------------


class TestSharingService:
    """Tests for the SharingService facade."""

    def test_create_and_list(self):
        svc = SharingService(port=0)
        link = svc.create_link(label="L1")
        assert link.label == "L1"
        assert len(svc.list_links()) == 1

    def test_revoke(self):
        svc = SharingService(port=0)
        link = svc.create_link(label="L2")
        assert svc.revoke_link(link.token)
        assert not link.is_active

    def test_revoke_nonexistent(self):
        svc = SharingService(port=0)
        assert not svc.revoke_link("fake-token")

    def test_get_url(self):
        svc = SharingService(port=0)
        link = svc.create_link(label="L3")
        url = svc.get_url(link)
        assert link.token in url

    def test_start_and_stop(self):
        svc = SharingService(port=0)
        pl = _make_playlist()
        assert not svc.is_running
        svc.start(pl)
        time.sleep(0.1)
        assert svc.is_running
        svc.stop()
        assert not svc.is_running

    def test_persist_and_load_links(self, tmp_path, monkeypatch):
        """Links should survive a save/load cycle."""
        monkeypatch.setattr(
            "fluxo.services.sharing_service.Settings.get_config_dir",
            staticmethod(lambda: tmp_path),
        )
        svc = SharingService(port=0)
        svc.create_link(label="persisted", password="pw")
        svc.create_link(label="other")

        # New service instance loads them back
        svc2 = SharingService(port=0)
        svc2.load_links()
        loaded = svc2.list_links()
        assert len(loaded) == 2
        labels = {ln.label for ln in loaded}
        assert "persisted" in labels
        assert "other" in labels
        # Password survives
        pw_link = next(ln for ln in loaded if ln.label == "persisted")
        assert pw_link.check_password("pw")


# -----------------------------------------------------------------------
# SharingDialog (smoke test — requires Qt)
# -----------------------------------------------------------------------


class TestSharingDialog:
    """Smoke-test for the SharingDialog widget."""

    def test_dialog_creates_and_shows(self, qtbot):
        from fluxo.ui.widgets.dialogs.sharing_dialog import SharingDialog

        pl = _make_playlist()
        svc = SharingService(port=0)
        dlg = SharingDialog(pl, svc)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "Host & Share Playlist"
