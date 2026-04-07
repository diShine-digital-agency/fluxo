"""Autosave manager using background threads (no Qt dependency)."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from fluxo.persistence.settings import Settings
from fluxo.services.project_manager import ProjectManager

if TYPE_CHECKING:
    from fluxo.models.project import Project

logger = logging.getLogger(__name__)


class AutosaveManager:
    """Periodically saves a project snapshot to the autosave directory.

    Uses :class:`threading.Timer` so it works without a Qt event loop.
    """

    def __init__(self, project: Project, interval: int = 60) -> None:
        self._project = project
        self._interval = max(10, interval)
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Timer control
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the periodic autosave timer."""
        with self._lock:
            self._cancel_timer()
            self._schedule()

    def stop(self) -> None:
        """Stop the autosave timer."""
        with self._lock:
            self._cancel_timer()

    def save_now(self) -> None:
        """Immediately create an autosave snapshot."""
        try:
            autosave_dir = str(self.get_autosave_dir())
            path = ProjectManager.create_autosave(self._project, autosave_dir)
            logger.info("Autosave created: %s", path)
        except OSError:
            logger.exception("Autosave failed")

    # ------------------------------------------------------------------
    # Autosave directory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_autosave_dir() -> Path:
        """Return the autosave directory inside the config directory."""
        autosave_dir = Settings.get_config_dir() / "autosave"
        autosave_dir.mkdir(parents=True, exist_ok=True)
        return autosave_dir

    def find_recovery_files(self) -> list[Path]:
        """Find autosave files that may need recovery."""
        autosave_dir = self.get_autosave_dir()
        if not autosave_dir.is_dir():
            return []
        return sorted(
            (f for f in autosave_dir.iterdir() if f.name.startswith("autosave_")),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

    def cleanup(self, keep: int = 5) -> None:
        """Remove old autosave files, keeping the *keep* most recent."""
        ProjectManager.cleanup_autosaves(str(self.get_autosave_dir()), keep=keep)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _schedule(self) -> None:
        self._timer = threading.Timer(self._interval, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        self.save_now()
        with self._lock:
            if self._timer is not None:
                self._schedule()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
