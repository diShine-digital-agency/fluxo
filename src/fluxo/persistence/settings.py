"""Application settings management with platform-specific config storage."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MAX_RECENT_FILES = 10

_VALID_THEMES = ("dark", "light")


@dataclass
class Settings:
    """User preferences stored as JSON in a platform-specific config directory."""

    theme: str = "dark"
    recent_files: list[str] = field(default_factory=list)
    window_geometry: dict[str, int] = field(
        default_factory=lambda: {"x": 100, "y": 100, "width": 1280, "height": 720}
    )
    last_open_directory: str = ""
    autosave_enabled: bool = True
    autosave_interval: int = 60
    check_streams_on_import: bool = False
    default_export_encoding: str = "utf-8"
    column_widths: dict[str, int] = field(default_factory=dict)
    column_visibility: dict[str, bool] = field(default_factory=dict)

    _config_path: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.theme not in _VALID_THEMES:
            self.theme = "dark"
        self.recent_files = self.recent_files[:_MAX_RECENT_FILES]
        self.autosave_interval = max(10, self.autosave_interval)

    # ------------------------------------------------------------------
    # Platform-specific config directory
    # ------------------------------------------------------------------

    @staticmethod
    def get_config_dir() -> Path:
        """Return the platform-specific configuration directory for Fluxo."""
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "Fluxo"
        elif sys.platform == "win32":
            appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            base = appdata / "Fluxo"
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME", "")
            base = Path(xdg) / "fluxo" if xdg else Path.home() / ".config" / "fluxo"
        return base

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | None = None) -> Settings:
        """Load settings from *path* or the default config location.

        Returns default settings when the file does not exist or is invalid.
        """
        config_path = Path(path) if path else cls.get_config_dir() / "settings.json"

        if not config_path.is_file():
            settings = cls()
            settings._config_path = str(config_path)
            return settings

        try:
            data: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read settings from %s: %s", config_path, exc)
            settings = cls()
            settings._config_path = str(config_path)
            return settings

        settings = cls(
            theme=data.get("theme", "dark"),
            recent_files=data.get("recent_files", []),
            window_geometry=data.get(
                "window_geometry", {"x": 100, "y": 100, "width": 1280, "height": 720}
            ),
            last_open_directory=data.get("last_open_directory", ""),
            autosave_enabled=data.get("autosave_enabled", True),
            autosave_interval=data.get("autosave_interval", 60),
            check_streams_on_import=data.get("check_streams_on_import", False),
            default_export_encoding=data.get("default_export_encoding", "utf-8"),
            column_widths=data.get("column_widths", {}),
            column_visibility=data.get("column_visibility", {}),
        )
        settings._config_path = str(config_path)
        return settings

    def save(self) -> None:
        """Write settings to the config file."""
        config_path = (
            Path(self._config_path)
            if self._config_path
            else (self.get_config_dir() / "settings.json")
        )
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(self)
        data.pop("_config_path", None)
        config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self._config_path = str(config_path)

    # ------------------------------------------------------------------
    # Recent files
    # ------------------------------------------------------------------

    def add_recent_file(self, path: str) -> None:
        """Add *path* to the recent files list, deduplicating and capping at 10."""
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:_MAX_RECENT_FILES]
