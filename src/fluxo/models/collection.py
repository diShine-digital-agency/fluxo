"""Collection model for user-defined channel groupings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass
class Collection:
    """A named collection of channels, like a playlist within a playlist.

    Users can organise channels into custom collections independently of the
    group-title hierarchy.
    """

    name: str
    channel_ids: list[UUID] = field(default_factory=list)
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.channel_ids = [UUID(cid) if isinstance(cid, str) else cid for cid in self.channel_ids]
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation."""
        return {
            "name": self.name,
            "channel_ids": [str(cid) for cid in self.channel_ids],
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Collection:
        """Create a :class:`Collection` from a dictionary."""
        return cls(
            name=data["name"],
            channel_ids=data.get("channel_ids", []),
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
        )
