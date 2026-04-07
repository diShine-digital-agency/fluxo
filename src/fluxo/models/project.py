"""Project model that wraps a playlist, EPG sources, and undo/redo history."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fluxo.models.epg import EpgData
from fluxo.models.playlist import Playlist

MAX_UNDO_HISTORY = 50


@dataclass
class _UndoEntry:
    """Internal container for a single undo/redo snapshot."""

    action_name: str
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"action_name": self.action_name, "snapshot": self.snapshot}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> _UndoEntry:
        return cls(action_name=data["action_name"], snapshot=data["snapshot"])


@dataclass
class Project:
    """Top-level model that ties together a playlist, EPG data, and project metadata.

    Provides undo/redo support via playlist-state snapshots.
    """

    name: str = "Untitled Project"
    file_path: str | None = None
    playlist: Playlist = field(default_factory=Playlist)
    epg_sources: list[EpgData] = field(default_factory=list)

    undo_stack: list[_UndoEntry] = field(default_factory=list)
    redo_stack: list[_UndoEntry] = field(default_factory=list)

    is_modified: bool = False
    autosave_path: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.modified_at, str):
            self.modified_at = datetime.fromisoformat(self.modified_at)

    # ------------------------------------------------------------------
    # Undo / redo
    # ------------------------------------------------------------------

    def push_undo(self, action_name: str, snapshot: dict[str, Any]) -> None:
        """Record a playlist snapshot before a mutating action.

        The *snapshot* should be the result of ``playlist.to_dict()``.
        Clears the redo stack and enforces :data:`MAX_UNDO_HISTORY`.
        """
        self.undo_stack.append(_UndoEntry(action_name=action_name, snapshot=snapshot))
        if len(self.undo_stack) > MAX_UNDO_HISTORY:
            self.undo_stack = self.undo_stack[-MAX_UNDO_HISTORY:]
        self.redo_stack.clear()
        self.is_modified = True
        self._touch()

    def undo(self) -> dict[str, Any] | None:
        """Pop the most recent undo entry and push current state onto redo.

        Returns the playlist snapshot to restore, or ``None`` if nothing to undo.
        """
        if not self.undo_stack:
            return None
        entry = self.undo_stack.pop()
        current_snapshot = self.playlist.to_dict()
        self.redo_stack.append(_UndoEntry(action_name=entry.action_name, snapshot=current_snapshot))
        self.is_modified = True
        self._touch()
        return entry.snapshot

    def redo(self) -> dict[str, Any] | None:
        """Pop the most recent redo entry and push current state onto undo.

        Returns the playlist snapshot to restore, or ``None`` if nothing to redo.
        """
        if not self.redo_stack:
            return None
        entry = self.redo_stack.pop()
        current_snapshot = self.playlist.to_dict()
        self.undo_stack.append(_UndoEntry(action_name=entry.action_name, snapshot=current_snapshot))
        self.is_modified = True
        self._touch()
        return entry.snapshot

    def mark_saved(self) -> None:
        """Mark the project as cleanly saved (not modified)."""
        self.is_modified = False
        self._touch()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation."""
        return {
            "name": self.name,
            "file_path": self.file_path,
            "playlist": self.playlist.to_dict(),
            "epg_sources": [epg.to_dict() for epg in self.epg_sources],
            "undo_stack": [e.to_dict() for e in self.undo_stack],
            "redo_stack": [e.to_dict() for e in self.redo_stack],
            "is_modified": self.is_modified,
            "autosave_path": self.autosave_path,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Project:
        """Create a :class:`Project` from a dictionary."""
        return cls(
            name=data.get("name", "Untitled Project"),
            file_path=data.get("file_path"),
            playlist=Playlist.from_dict(data.get("playlist", {})),
            epg_sources=[EpgData.from_dict(e) for e in data.get("epg_sources", [])],
            undo_stack=[_UndoEntry.from_dict(e) for e in data.get("undo_stack", [])],
            redo_stack=[_UndoEntry.from_dict(e) for e in data.get("redo_stack", [])],
            is_modified=data.get("is_modified", False),
            autosave_path=data.get("autosave_path"),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            modified_at=data.get("modified_at", datetime.now(timezone.utc)),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        self.modified_at = datetime.now(timezone.utc)
