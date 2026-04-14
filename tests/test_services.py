"""Tests for validation and deduplication services."""

from __future__ import annotations

from fluxo.models.channel import Channel
from fluxo.models.epg import EpgChannel, EpgData
from fluxo.models.playlist import Playlist
from fluxo.services.deduplication import DeduplicationService
from fluxo.services.epg_mapper import EpgMapper


class TestDeduplication:
    def test_find_exact_duplicates(self):
        channels = [
            Channel(name="Ch1", url="http://example.com/same"),
            Channel(name="Ch2", url="http://example.com/same"),
            Channel(name="Ch3", url="http://example.com/other"),
        ]
        service = DeduplicationService()
        dupes = service.find_exact_duplicates(channels)
        assert len(dupes) == 1
        assert len(dupes[0]) == 2

    def test_find_no_duplicates(self):
        channels = [
            Channel(name="Ch1", url="http://example.com/1"),
            Channel(name="Ch2", url="http://example.com/2"),
        ]
        service = DeduplicationService()
        dupes = service.find_exact_duplicates(channels)
        assert len(dupes) == 0

    def test_remove_duplicates(self):
        pl = Playlist(name="Test")
        pl.add_channel(Channel(name="Ch1", url="http://example.com/same"))
        pl.add_channel(Channel(name="Ch2", url="http://example.com/same"))
        pl.add_channel(Channel(name="Ch3", url="http://example.com/other"))
        service = DeduplicationService()
        removed = service.remove_duplicates(pl, keep="first")
        assert len(removed) == 1
        assert pl.channel_count == 2


class TestEpgMapper:
    def test_normalize_name(self):
        mapper = EpgMapper()
        assert mapper.normalize_name("CNN HD") == "cnn"
        assert mapper.normalize_name("BBC One FHD") == "bbc one"
        assert mapper.normalize_name("  ESPN  ") == "espn"

    def test_auto_map(self):
        pl = Playlist(name="Test")
        pl.add_channel(Channel(name="CNN", url="http://example.com/1"))
        pl.add_channel(Channel(name="BBC One", url="http://example.com/2"))
        epg = EpgData(
            channels={
                "CNN.us": EpgChannel(id="CNN.us", display_names=["CNN International"]),
                "BBC1.uk": EpgChannel(id="BBC1.uk", display_names=["BBC One"]),
            },
            programmes={},
        )
        mapper = EpgMapper()
        results = mapper.auto_map(pl, epg)
        assert len(results) == 2
        # BBC One should have a high confidence match
        bbc_result = [r for r in results if r[0].name == "BBC One"][0]
        assert bbc_result[1] is not None  # Has a match
        assert bbc_result[2] > 0.5  # Reasonable confidence
