"""Playlist model representing an M3U/IPTV playlist."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fluxo.models.channel import Channel


@dataclass
class Playlist:
    """Represents an M3U playlist with its channels and metadata.

    The ``header_attributes`` dict stores key/value pairs from the ``#EXTM3U``
    line (e.g. ``url-tvg``, ``x-tvg-url``).
    """

    name: str = "Untitled"
    channels: list[Channel] = field(default_factory=list)
    epg_urls: list[str] = field(default_factory=list)
    header_attributes: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.modified_at, str):
            self.modified_at = datetime.fromisoformat(self.modified_at)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def channel_count(self) -> int:
        """Return the total number of channels."""
        return len(self.channels)

    @property
    def groups(self) -> list[str]:
        """Return a sorted list of unique, non-empty group names."""
        return sorted({ch.group_title for ch in self.channels if ch.group_title})

    @property
    def group_counts(self) -> dict[str, int]:
        """Return a mapping of group name → channel count."""
        return dict(Counter(ch.group_title for ch in self.channels if ch.group_title))

    # ------------------------------------------------------------------
    # Channel management
    # ------------------------------------------------------------------

    def add_channel(self, channel: Channel, index: int | None = None) -> None:
        """Add a channel, optionally at a specific *index*."""
        if index is None:
            self.channels.append(channel)
        else:
            self.channels.insert(index, channel)
        self._touch()

    def remove_channel(self, channel_id: UUID) -> Channel | None:
        """Remove and return the channel with *channel_id*, or ``None``."""
        for i, ch in enumerate(self.channels):
            if ch.id == channel_id:
                self._touch()
                return self.channels.pop(i)
        return None

    def remove_channels(self, channel_ids: set[UUID]) -> list[Channel]:
        """Remove multiple channels by their IDs. Returns the removed channels."""
        removed: list[Channel] = []
        kept: list[Channel] = []
        for ch in self.channels:
            if ch.id in channel_ids:
                removed.append(ch)
            else:
                kept.append(ch)
        if removed:
            self.channels = kept
            self._touch()
        return removed

    def move_channel(self, channel_id: UUID, new_index: int) -> bool:
        """Move a channel to *new_index*. Returns ``True`` on success."""
        for i, ch in enumerate(self.channels):
            if ch.id == channel_id:
                self.channels.pop(i)
                self.channels.insert(new_index, ch)
                self._touch()
                return True
        return False

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_channels_by_group(self, group: str) -> list[Channel]:
        """Return channels belonging to *group*."""
        return [ch for ch in self.channels if ch.group_title == group]

    def get_duplicates(self, *, by: str = "name") -> dict[str, list[Channel]]:
        """Find duplicate channels grouped by *by* (``"name"`` or ``"url"``).

        Returns only groups with more than one entry.
        """
        buckets: dict[str, list[Channel]] = {}
        for ch in self.channels:
            key = ch.name if by == "name" else ch.url
            buckets.setdefault(key, []).append(ch)
        return {k: v for k, v in buckets.items() if len(v) > 1}

    def search(self, text: str) -> list[Channel]:
        """Return channels matching *text* (case-insensitive substring search)."""
        return [ch for ch in self.channels if ch.matches_filter(text)]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation."""
        return {
            "name": self.name,
            "channels": [ch.to_dict() for ch in self.channels],
            "epg_urls": list(self.epg_urls),
            "header_attributes": dict(self.header_attributes),
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Playlist:
        """Create a :class:`Playlist` from a dictionary."""
        return cls(
            name=data.get("name", "Untitled"),
            channels=[Channel.from_dict(ch) for ch in data.get("channels", [])],
            epg_urls=data.get("epg_urls", []),
            header_attributes=data.get("header_attributes", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            modified_at=data.get("modified_at", datetime.now(timezone.utc)),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        """Update *modified_at* to the current time."""
        self.modified_at = datetime.now(timezone.utc)
