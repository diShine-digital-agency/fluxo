"""Keyboard shortcut definitions and manager for Fluxo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtGui import QKeySequence, QShortcut

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtWidgets import QMainWindow


@dataclass(frozen=True, slots=True)
class ShortcutDef:
    """Immutable definition of a single keyboard shortcut."""

    action: str
    key_sequence: str
    description: str


DEFAULT_SHORTCUTS: tuple[ShortcutDef, ...] = (
    ShortcutDef("new_playlist", "Ctrl+N", "New playlist"),
    ShortcutDef("open_file", "Ctrl+O", "Open file"),
    ShortcutDef("save_project", "Ctrl+S", "Save project"),
    ShortcutDef("save_as", "Ctrl+Shift+S", "Save as"),
    ShortcutDef("export_m3u", "Ctrl+E", "Export M3U"),
    ShortcutDef("import_m3u", "Ctrl+I", "Import M3U"),
    ShortcutDef("undo", "Ctrl+Z", "Undo"),
    ShortcutDef("redo", "Ctrl+Shift+Z", "Redo"),
    ShortcutDef("search", "Ctrl+F", "Search / find"),
    ShortcutDef("select_all", "Ctrl+A", "Select all"),
    ShortcutDef("duplicate_detection", "Ctrl+D", "Duplicate detection"),
    ShortcutDef("delete_selected", "Delete", "Delete selected"),
    ShortcutDef("refresh_streams", "F5", "Refresh / check streams"),
    ShortcutDef("find_replace", "Ctrl+H", "Find and replace"),
    ShortcutDef("go_to_group", "Ctrl+G", "Go to group"),
)


class ShortcutManager:
    """Register and manage keyboard shortcuts on a main window."""

    def __init__(self, window: QMainWindow) -> None:
        self._window = window
        self._shortcuts: dict[str, QShortcut] = {}

    def register(
        self,
        action: str,
        key_sequence: str,
        callback: Callable[[], object],
    ) -> QShortcut:
        """Register a single shortcut and return the QShortcut instance."""
        shortcut = QShortcut(QKeySequence(key_sequence), self._window)
        shortcut.activated.connect(callback)
        self._shortcuts[action] = shortcut
        return shortcut

    def register_defaults(
        self,
        handlers: dict[str, Callable[[], object]],
    ) -> None:
        """Register all default shortcuts whose action has a handler.

        *handlers* maps action names (e.g. ``"new_playlist"``) to callables.
        Shortcuts without a matching handler are silently skipped.
        """
        for defn in DEFAULT_SHORTCUTS:
            callback = handlers.get(defn.action)
            if callback is not None:
                self.register(defn.action, defn.key_sequence, callback)

    def unregister(self, action: str) -> None:
        """Remove a previously registered shortcut."""
        shortcut = self._shortcuts.pop(action, None)
        if shortcut is not None:
            shortcut.setEnabled(False)
            shortcut.deleteLater()

    def unregister_all(self) -> None:
        """Remove every registered shortcut."""
        for action in list(self._shortcuts):
            self.unregister(action)

    @property
    def registered(self) -> dict[str, QShortcut]:
        """Return a read-only view of currently registered shortcuts."""
        return dict(self._shortcuts)
