"""Playlist statistics and analytics service."""

from __future__ import annotations

from dataclasses import dataclass, field

from fluxo.models.channel import Channel, HealthStatus
from fluxo.models.playlist import Playlist


@dataclass
class PlaylistStats:
    """Computed statistics for a playlist."""

    total_channels: int = 0
    total_groups: int = 0
    channels_per_group: dict[str, int] = field(default_factory=dict)
    health_summary: dict[str, int] = field(default_factory=dict)
    duplicate_url_count: int = 0
    channels_with_epg: int = 0
    channels_without_epg: int = 0
    channels_with_logo: int = 0
    channels_without_logo: int = 0
    favorite_count: int = 0

    def to_dict(self) -> dict:
        """Serialize statistics to a plain dictionary."""
        return {
            "total_channels": self.total_channels,
            "total_groups": self.total_groups,
            "channels_per_group": self.channels_per_group,
            "health_summary": self.health_summary,
            "duplicate_url_count": self.duplicate_url_count,
            "channels_with_epg": self.channels_with_epg,
            "channels_without_epg": self.channels_without_epg,
            "channels_with_logo": self.channels_with_logo,
            "channels_without_logo": self.channels_without_logo,
            "favorite_count": self.favorite_count,
        }


class StatisticsService:
    """Compute summary statistics for a playlist.

    All methods are stateless and operate on the supplied data.
    """

    @staticmethod
    def compute(playlist: Playlist) -> PlaylistStats:
        """Return a :class:`PlaylistStats` snapshot for *playlist*."""
        channels = playlist.channels
        stats = PlaylistStats(total_channels=len(channels))

        # Group counts
        group_counts: dict[str, int] = {}
        for ch in channels:
            group = ch.group_title or "Uncategorized"
            group_counts[group] = group_counts.get(group, 0) + 1
        stats.channels_per_group = dict(sorted(group_counts.items()))
        stats.total_groups = len(group_counts)

        # Health summary
        health_counts: dict[str, int] = {}
        for ch in channels:
            key = ch.health_status.name
            health_counts[key] = health_counts.get(key, 0) + 1
        stats.health_summary = health_counts

        # Duplicate URLs
        seen_urls: set[str] = set()
        dup_count = 0
        for ch in channels:
            if ch.url in seen_urls:
                dup_count += 1
            else:
                seen_urls.add(ch.url)
        stats.duplicate_url_count = dup_count

        # EPG coverage
        stats.channels_with_epg = sum(1 for ch in channels if ch.tvg_id)
        stats.channels_without_epg = stats.total_channels - stats.channels_with_epg

        # Logo coverage
        stats.channels_with_logo = sum(1 for ch in channels if ch.tvg_logo)
        stats.channels_without_logo = stats.total_channels - stats.channels_with_logo

        # Favorites
        stats.favorite_count = sum(1 for ch in channels if ch.is_favorite)

        return stats

    @staticmethod
    def health_score(channels: list[Channel]) -> float:
        """Return a 0–100 health score for a list of channels.

        Only channels that have been checked are counted.
        """
        checked = [ch for ch in channels if ch.health_status != HealthStatus.UNKNOWN]
        if not checked:
            return 0.0
        alive = sum(1 for ch in checked if ch.health_status == HealthStatus.ALIVE)
        return round(100.0 * alive / len(checked), 1)
