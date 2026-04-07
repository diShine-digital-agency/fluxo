"""Project persistence service (save / load / autosave)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fluxo.models.project import Project

logger = logging.getLogger(__name__)

_AUTOSAVE_PREFIX = "autosave_"
_AUTOSAVE_EXT = ".fluxo"


class ProjectManager:
    """Manages saving, loading, and autosaving of Fluxo projects."""

    @staticmethod
    def save_project(project: Project, path: str) -> None:
        """Serialize *project* to a JSON file at *path*."""
        data = project.to_dict()
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        project.file_path = str(file_path)
        project.mark_saved()

    @staticmethod
    def load_project(path: str) -> Project:
        """Deserialize a project from a JSON file at *path*."""
        file_path = Path(path)
        data = json.loads(file_path.read_text(encoding="utf-8"))
        project = Project.from_dict(data)
        project.file_path = str(file_path)
        return project

    @staticmethod
    def create_autosave(project: Project, directory: str) -> str:
        """Save an autosave snapshot and return the file path."""
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        filename = f"{_AUTOSAVE_PREFIX}{timestamp}{_AUTOSAVE_EXT}"
        save_path = dir_path / filename

        data = project.to_dict()
        save_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        project.autosave_path = str(save_path)
        return str(save_path)

    @staticmethod
    def load_autosave(directory: str) -> Project | None:
        """Load the most recent autosave from *directory*, or ``None``."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return None

        autosaves = sorted(
            (f for f in dir_path.iterdir() if f.name.startswith(_AUTOSAVE_PREFIX)),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not autosaves:
            return None

        latest = autosaves[0]
        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
            project = Project.from_dict(data)
            project.autosave_path = str(latest)
            return project
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to load autosave %s", latest)
            return None

    @staticmethod
    def cleanup_autosaves(directory: str, keep: int = 5) -> None:
        """Remove old autosave files, keeping the *keep* most recent."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return

        autosaves = sorted(
            (f for f in dir_path.iterdir() if f.name.startswith(_AUTOSAVE_PREFIX)),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for old_file in autosaves[keep:]:
            try:
                old_file.unlink()
            except OSError:
                logger.warning("Could not remove autosave %s", old_file)
