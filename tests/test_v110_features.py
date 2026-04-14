"""Tests for v1.1.0 features: statistics service and playlist merge."""

from __future__ import annotations

from fluxo.models.channel import Channel, HealthStatus
from fluxo.models.playlist import Playlist
from fluxo.services.statistics import PlaylistStats, StatisticsService

# ---------------------------------------------------------------------------
# StatisticsService
# ---------------------------------------------------------------------------


class TestPlaylistStats:
    """Tests for PlaylistStats dataclass."""

    def test_defaults(self):
        stats = PlaylistStats()
        assert stats.total_channels == 0
        assert stats.total_groups == 0
        assert stats.channels_per_group == {}
        assert stats.health_summary == {}

    def test_to_dict(self):
        stats = PlaylistStats(total_channels=5, total_groups=2)
        d = stats.to_dict()
        assert d["total_channels"] == 5
        assert d["total_groups"] == 2
        assert isinstance(d, dict)


class TestStatisticsService:
    """Tests for StatisticsService.compute()."""

    def test_empty_playlist(self):
        pl = Playlist(name="empty")
        stats = StatisticsService.compute(pl)
        assert stats.total_channels == 0
        assert stats.total_groups == 0
        assert stats.duplicate_url_count == 0

    def test_basic_stats(self):
        channels = [
            Channel(name="CNN", url="http://cnn.com/live", group_title="News", tvg_id="cnn.us"),
            Channel(name="BBC", url="http://bbc.com/live", group_title="News", tvg_logo="logo.png"),
            Channel(name="ESPN", url="http://espn.com/live", group_title="Sports"),
        ]
        pl = Playlist(name="test", channels=channels)
        stats = StatisticsService.compute(pl)

        assert stats.total_channels == 3
        assert stats.total_groups == 2
        assert stats.channels_per_group["News"] == 2
        assert stats.channels_per_group["Sports"] == 1

    def test_duplicate_count(self):
        channels = [
            Channel(name="A", url="http://a.com/1"),
            Channel(name="B", url="http://a.com/1"),
            Channel(name="C", url="http://c.com/1"),
        ]
        pl = Playlist(name="test", channels=channels)
        stats = StatisticsService.compute(pl)
        assert stats.duplicate_url_count == 1

    def test_epg_coverage(self):
        channels = [
            Channel(name="A", url="http://a.com", tvg_id="a.id"),
            Channel(name="B", url="http://b.com"),
            Channel(name="C", url="http://c.com", tvg_id="c.id"),
        ]
        pl = Playlist(name="test", channels=channels)
        stats = StatisticsService.compute(pl)
        assert stats.channels_with_epg == 2
        assert stats.channels_without_epg == 1

    def test_logo_coverage(self):
        channels = [
            Channel(name="A", url="http://a.com", tvg_logo="http://logo.com/a.png"),
            Channel(name="B", url="http://b.com"),
        ]
        pl = Playlist(name="test", channels=channels)
        stats = StatisticsService.compute(pl)
        assert stats.channels_with_logo == 1
        assert stats.channels_without_logo == 1

    def test_health_summary(self):
        ch1 = Channel(name="A", url="http://a.com")
        ch1.health_status = HealthStatus.ALIVE
        ch2 = Channel(name="B", url="http://b.com")
        ch2.health_status = HealthStatus.DEAD
        ch3 = Channel(name="C", url="http://c.com")
        # default is UNKNOWN
        pl = Playlist(name="test", channels=[ch1, ch2, ch3])
        stats = StatisticsService.compute(pl)
        assert stats.health_summary["ALIVE"] == 1
        assert stats.health_summary["DEAD"] == 1
        assert stats.health_summary["UNKNOWN"] == 1

    def test_favorites_count(self):
        ch1 = Channel(name="A", url="http://a.com", is_favorite=True)
        ch2 = Channel(name="B", url="http://b.com")
        ch3 = Channel(name="C", url="http://c.com", is_favorite=True)
        pl = Playlist(name="test", channels=[ch1, ch2, ch3])
        stats = StatisticsService.compute(pl)
        assert stats.favorite_count == 2

    def test_groups_sorted_alphabetically(self):
        channels = [
            Channel(name="Z", url="http://z.com", group_title="Zzz"),
            Channel(name="A", url="http://a.com", group_title="Aaa"),
        ]
        pl = Playlist(name="test", channels=channels)
        stats = StatisticsService.compute(pl)
        keys = list(stats.channels_per_group.keys())
        assert keys == ["Aaa", "Zzz"]

    def test_uncategorized_group(self):
        channels = [
            Channel(name="A", url="http://a.com", group_title=""),
            Channel(name="B", url="http://b.com"),  # default group_title=""
        ]
        pl = Playlist(name="test", channels=channels)
        stats = StatisticsService.compute(pl)
        assert "Uncategorized" in stats.channels_per_group


class TestHealthScore:
    """Tests for StatisticsService.health_score()."""

    def test_no_checked_channels(self):
        channels = [Channel(name="A", url="http://a.com")]
        assert StatisticsService.health_score(channels) == 0.0

    def test_all_alive(self):
        ch1 = Channel(name="A", url="http://a.com")
        ch1.health_status = HealthStatus.ALIVE
        ch2 = Channel(name="B", url="http://b.com")
        ch2.health_status = HealthStatus.ALIVE
        assert StatisticsService.health_score([ch1, ch2]) == 100.0

    def test_mixed(self):
        ch1 = Channel(name="A", url="http://a.com")
        ch1.health_status = HealthStatus.ALIVE
        ch2 = Channel(name="B", url="http://b.com")
        ch2.health_status = HealthStatus.DEAD
        assert StatisticsService.health_score([ch1, ch2]) == 50.0

    def test_empty_list(self):
        assert StatisticsService.health_score([]) == 0.0


# ---------------------------------------------------------------------------
# Playlist Merge
# ---------------------------------------------------------------------------


class TestPlaylistMerge:
    """Tests for ExportService.merge_playlists()."""

    def test_merge_two_playlists(self):
        from fluxo.services.export_service import ExportService

        pl1 = Playlist(
            name="A",
            channels=[Channel(name="CNN", url="http://cnn.com/live", group_title="News")],
        )
        pl2 = Playlist(
            name="B",
            channels=[Channel(name="ESPN", url="http://espn.com/live", group_title="Sports")],
        )
        merged = ExportService.merge_playlists([pl1, pl2])
        assert merged.name == "Merged Playlist"
        assert len(merged.channels) == 2

    def test_merge_deduplicates_by_url(self):
        from fluxo.services.export_service import ExportService

        pl1 = Playlist(
            name="A",
            channels=[Channel(name="CNN", url="http://cnn.com/live")],
        )
        pl2 = Playlist(
            name="B",
            channels=[Channel(name="CNN Copy", url="http://cnn.com/live")],
        )
        merged = ExportService.merge_playlists([pl1, pl2], deduplicate=True)
        assert len(merged.channels) == 1

    def test_merge_without_dedup(self):
        from fluxo.services.export_service import ExportService

        pl1 = Playlist(
            name="A",
            channels=[Channel(name="CNN", url="http://cnn.com/live")],
        )
        pl2 = Playlist(
            name="B",
            channels=[Channel(name="CNN Copy", url="http://cnn.com/live")],
        )
        merged = ExportService.merge_playlists([pl1, pl2], deduplicate=False)
        assert len(merged.channels) == 2

    def test_merge_preserves_epg_urls(self):
        from fluxo.services.export_service import ExportService

        epg_url_1 = "http://example.com/epg1.xml"
        epg_url_2 = "http://example.com/epg2.xml"
        pl1 = Playlist(name="A", channels=[], epg_urls=[epg_url_1])
        pl2 = Playlist(name="B", channels=[], epg_urls=[epg_url_2])
        merged = ExportService.merge_playlists([pl1, pl2])
        assert epg_url_1 in merged.epg_urls
        assert epg_url_2 in merged.epg_urls

    def test_merge_empty_list(self):
        from fluxo.services.export_service import ExportService

        merged = ExportService.merge_playlists([])
        assert len(merged.channels) == 0

    def test_merge_single_playlist(self):
        from fluxo.services.export_service import ExportService

        pl = Playlist(
            name="Only",
            channels=[Channel(name="A", url="http://a.com")],
        )
        merged = ExportService.merge_playlists([pl])
        assert len(merged.channels) == 1

    def test_merge_custom_name(self):
        from fluxo.services.export_service import ExportService

        pl1 = Playlist(name="A", channels=[])
        merged = ExportService.merge_playlists([pl1], name="My Merged")
        assert merged.name == "My Merged"
