"""Channel model representing a single IPTV channel entry."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class HealthStatus(Enum):
    """Health check status for a channel stream."""

    UNKNOWN = "unknown"
    ALIVE = "alive"
    DEAD = "dead"
    TIMEOUT = "timeout"


@dataclass
class Channel:
    """Represents a single IPTV channel entry from an M3U playlist.

    Stores all standard M3U/EXTINF attributes plus extra attributes for
    non-standard or provider-specific tags.
    """

    name: str
    url: str
    duration: int = -1
    id: UUID = field(default_factory=uuid4)

    # TVG (TV Guide) attributes
    tvg_id: str = ""
    tvg_name: str = ""
    tvg_logo: str = ""
    group_title: str = ""
    tvg_language: str = ""
    tvg_country: str = ""
    tvg_shift: str = ""

    # Catchup / timeshift attributes
    catchup: str = ""
    catchup_days: str = ""
    catchup_source: str = ""

    # Channel ordering
    channel_number: str = ""

    # Catch-all for any other attributes
    extra_attributes: dict[str, str] = field(default_factory=dict)

    # User-defined metadata
    is_favorite: bool = False
    tags: list[str] = field(default_factory=list)

    # Stream health tracking
    health_status: HealthStatus = HealthStatus.UNKNOWN
    health_checked_at: datetime | None = None

    def __post_init__(self) -> None:
        if isinstance(self.id, str):
            self.id = UUID(self.id)
        if isinstance(self.health_status, str):
            self.health_status = HealthStatus(self.health_status)
        if isinstance(self.health_checked_at, str):
            self.health_checked_at = datetime.fromisoformat(self.health_checked_at)

    # ------------------------------------------------------------------
    # M3U serialization
    # ------------------------------------------------------------------

    def to_m3u_line(self) -> str:
        """Serialize this channel to M3U ``#EXTINF`` + URL lines."""
        attrs = self._build_attribute_string()
        extinf = f"#EXTINF:{self.duration}"
        if attrs:
            extinf += f" {attrs}"
        extinf += f",{self.name}"
        return f"{extinf}\n{self.url}"

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def clone(self) -> Channel:
        """Return a deep copy with a new UUID."""
        cloned = copy.deepcopy(self)
        cloned.id = uuid4()
        return cloned

    def matches_filter(self, text: str) -> bool:
        """Return ``True`` if *text* matches name, group, URL, or TVG fields (case-insensitive)."""
        needle = text.lower()
        searchable = (
            self.name,
            self.url,
            self.group_title,
            self.tvg_id,
            self.tvg_name,
            self.tvg_language,
            self.tvg_country,
        )
        return any(needle in val.lower() for val in searchable if val)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "url": self.url,
            "duration": self.duration,
            "tvg_id": self.tvg_id,
            "tvg_name": self.tvg_name,
            "tvg_logo": self.tvg_logo,
            "group_title": self.group_title,
            "tvg_language": self.tvg_language,
            "tvg_country": self.tvg_country,
            "tvg_shift": self.tvg_shift,
            "catchup": self.catchup,
            "catchup_days": self.catchup_days,
            "catchup_source": self.catchup_source,
            "channel_number": self.channel_number,
            "extra_attributes": dict(self.extra_attributes),
            "is_favorite": self.is_favorite,
            "tags": list(self.tags),
            "health_status": self.health_status.value,
            "health_checked_at": (
                self.health_checked_at.isoformat() if self.health_checked_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Channel:
        """Create a :class:`Channel` from a dictionary (e.g. JSON-loaded)."""
        return cls(
            id=data.get("id", uuid4()),
            name=data["name"],
            url=data["url"],
            duration=data.get("duration", -1),
            tvg_id=data.get("tvg_id", ""),
            tvg_name=data.get("tvg_name", ""),
            tvg_logo=data.get("tvg_logo", ""),
            group_title=data.get("group_title", ""),
            tvg_language=data.get("tvg_language", ""),
            tvg_country=data.get("tvg_country", ""),
            tvg_shift=data.get("tvg_shift", ""),
            catchup=data.get("catchup", ""),
            catchup_days=data.get("catchup_days", ""),
            catchup_source=data.get("catchup_source", ""),
            channel_number=data.get("channel_number", ""),
            extra_attributes=data.get("extra_attributes", {}),
            is_favorite=data.get("is_favorite", False),
            tags=data.get("tags", []),
            health_status=data.get("health_status", HealthStatus.UNKNOWN),
            health_checked_at=data.get("health_checked_at"),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_attribute_string(self) -> str:
        """Build the key="value" attribute portion of the ``#EXTINF`` line."""
        known_attrs: list[tuple[str, str, str]] = [
            ("tvg-id", "tvg_id", self.tvg_id),
            ("tvg-name", "tvg_name", self.tvg_name),
            ("tvg-logo", "tvg_logo", self.tvg_logo),
            ("group-title", "group_title", self.group_title),
            ("tvg-language", "tvg_language", self.tvg_language),
            ("tvg-country", "tvg_country", self.tvg_country),
            ("tvg-shift", "tvg_shift", self.tvg_shift),
            ("catchup", "catchup", self.catchup),
            ("catchup-days", "catchup_days", self.catchup_days),
            ("catchup-source", "catchup_source", self.catchup_source),
            ("channel-number", "channel_number", self.channel_number),
        ]
        parts: list[str] = []
        for attr_name, _, value in known_attrs:
            if value:
                parts.append(f'{attr_name}="{value}"')
        for key, value in self.extra_attributes.items():
            parts.append(f'{key}="{value}"')
        return " ".join(parts)
