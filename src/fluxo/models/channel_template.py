"""Channel template model for reusable channel metadata profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChannelTemplate:
    """A reusable template that captures channel metadata for quick application.

    Templates let users save common attribute combinations (e.g. "Sports Channel",
    "News Channel") and apply them to channels in bulk.
    """

    name: str
    group_title: str = ""
    tvg_logo: str = ""
    catchup: str = ""
    catchup_days: str = ""
    extra_attributes: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation."""
        return {
            "name": self.name,
            "group_title": self.group_title,
            "tvg_logo": self.tvg_logo,
            "catchup": self.catchup,
            "catchup_days": self.catchup_days,
            "extra_attributes": dict(self.extra_attributes),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelTemplate:
        """Create a :class:`ChannelTemplate` from a dictionary."""
        return cls(
            name=data["name"],
            group_title=data.get("group_title", ""),
            tvg_logo=data.get("tvg_logo", ""),
            catchup=data.get("catchup", ""),
            catchup_days=data.get("catchup_days", ""),
            extra_attributes=data.get("extra_attributes", {}),
            tags=data.get("tags", []),
        )
