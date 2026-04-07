"""EPG / XMLTV data models for electronic programme guide information."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EpgChannel:
    """Represents a channel entry in an XMLTV EPG source."""

    id: str
    display_names: list[str] = field(default_factory=list)
    icon_url: str = ""
    urls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_names": list(self.display_names),
            "icon_url": self.icon_url,
            "urls": list(self.urls),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpgChannel:
        return cls(
            id=data["id"],
            display_names=data.get("display_names", []),
            icon_url=data.get("icon_url", ""),
            urls=data.get("urls", []),
        )


@dataclass
class EpgProgramme:
    """Represents a single programme/show in an XMLTV EPG source."""

    channel_id: str
    title: str
    start: datetime
    stop: datetime
    description: str = ""
    category: str = ""
    icon_url: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.start, str):
            self.start = datetime.fromisoformat(self.start)
        if isinstance(self.stop, str):
            self.stop = datetime.fromisoformat(self.stop)

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "title": self.title,
            "start": self.start.isoformat(),
            "stop": self.stop.isoformat(),
            "description": self.description,
            "category": self.category,
            "icon_url": self.icon_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpgProgramme:
        return cls(
            channel_id=data["channel_id"],
            title=data["title"],
            start=data["start"],
            stop=data["stop"],
            description=data.get("description", ""),
            category=data.get("category", ""),
            icon_url=data.get("icon_url", ""),
        )


@dataclass
class EpgData:
    """Container for all EPG data from a single XMLTV source.

    ``channels`` maps channel ID → :class:`EpgChannel`.
    ``programmes`` maps channel ID → list of :class:`EpgProgramme`.
    """

    channels: dict[str, EpgChannel] = field(default_factory=dict)
    programmes: dict[str, list[EpgProgramme]] = field(default_factory=dict)
    source_url: str = ""

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def find_channel_by_name(self, name: str) -> list[EpgChannel]:
        """Return EPG channels whose display names contain *name* (case-insensitive)."""
        needle = name.lower()
        return [
            ch
            for ch in self.channels.values()
            if any(needle in dn.lower() for dn in ch.display_names)
        ]

    def get_programmes_for_channel(self, channel_id: str) -> list[EpgProgramme]:
        """Return all programmes for *channel_id*, sorted by start time."""
        progs = self.programmes.get(channel_id, [])
        return sorted(progs, key=lambda p: p.start)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "channels": {cid: ch.to_dict() for cid, ch in self.channels.items()},
            "programmes": {
                cid: [p.to_dict() for p in progs] for cid, progs in self.programmes.items()
            },
            "source_url": self.source_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpgData:
        channels = {cid: EpgChannel.from_dict(ch) for cid, ch in data.get("channels", {}).items()}
        programmes = {
            cid: [EpgProgramme.from_dict(p) for p in progs]
            for cid, progs in data.get("programmes", {}).items()
        }
        return cls(
            channels=channels,
            programmes=programmes,
            source_url=data.get("source_url", ""),
        )
