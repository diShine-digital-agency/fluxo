"""Tests for data models."""
from __future__ import annotations

from fluxo.models.channel import Channel, HealthStatus
from fluxo.models.playlist import Playlist
from fluxo.models.project import Project


class TestChannel:
    def test_create_channel(self):
        ch = Channel(name="Test", url="http://example.com/test")
        assert ch.name == "Test"
        assert ch.url == "http://example.com/test"
        assert ch.id != ""
        assert ch.health_status == HealthStatus.UNKNOWN

    def test_channel_to_m3u_line(self):
        ch = Channel(
            name="CNN",
            url="http://example.com/cnn",
            tvg_id="CNN.us",
            tvg_name="CNN",
            tvg_logo="http://example.com/cnn.png",
            group_title="News",
        )
        line = ch.to_m3u_line()
        # to_m3u_line returns "#EXTINF:...,CNN\nURL"
        extinf_line = line.split("\n")[0]
        assert extinf_line.startswith("#EXTINF:")
        assert 'tvg-id="CNN.us"' in extinf_line
        assert 'tvg-name="CNN"' in extinf_line
        assert 'group-title="News"' in extinf_line
        assert extinf_line.endswith(",CNN")

    def test_channel_clone(self):
        ch = Channel(name="Test", url="http://example.com/test", group_title="A")
        clone = ch.clone()
        assert clone.name == ch.name
        assert clone.url == ch.url
        assert clone.id != ch.id  # New ID

    def test_channel_matches_filter(self):
        ch = Channel(name="CNN International", url="http://example.com/cnn", group_title="News")
        assert ch.matches_filter("cnn")
        assert ch.matches_filter("news")
        assert ch.matches_filter("international")
        assert not ch.matches_filter("xyz")

    def test_channel_serialization(self):
        ch = Channel(
            name="Test",
            url="http://example.com/test",
            tvg_id="test.id",
            group_title="Group",
        )
        data = ch.to_dict()
        restored = Channel.from_dict(data)
        assert restored.name == ch.name
        assert restored.url == ch.url
        assert restored.tvg_id == ch.tvg_id
        assert restored.group_title == ch.group_title


class TestPlaylist:
    def test_create_empty_playlist(self):
        pl = Playlist(name="Test")
        assert pl.channel_count == 0
        assert pl.groups == []

    def test_add_channel(self):
        pl = Playlist(name="Test")
        ch = Channel(name="Ch1", url="http://example.com/1", group_title="A")
        pl.add_channel(ch)
        assert pl.channel_count == 1
        assert "A" in pl.groups

    def test_remove_channel(self):
        pl = Playlist(name="Test")
        ch = Channel(name="Ch1", url="http://example.com/1")
        pl.add_channel(ch)
        pl.remove_channel(ch.id)
        assert pl.channel_count == 0

    def test_move_channel(self):
        pl = Playlist(name="Test")
        ch1 = Channel(name="Ch1", url="http://example.com/1")
        ch2 = Channel(name="Ch2", url="http://example.com/2")
        ch3 = Channel(name="Ch3", url="http://example.com/3")
        pl.add_channel(ch1)
        pl.add_channel(ch2)
        pl.add_channel(ch3)
        pl.move_channel(ch3.id, 0)
        assert pl.channels[0].name == "Ch3"

    def test_get_duplicates_by_url(self):
        pl = Playlist(name="Test")
        pl.add_channel(Channel(name="Ch1", url="http://example.com/same"))
        pl.add_channel(Channel(name="Ch2", url="http://example.com/same"))
        pl.add_channel(Channel(name="Ch3", url="http://example.com/other"))
        dupes = pl.get_duplicates(by="url")
        # get_duplicates returns dict[str, list[Channel]], keyed by URL
        assert len(dupes) == 1  # One group of duplicates
        dup_group = list(dupes.values())[0]
        assert len(dup_group) == 2

    def test_search(self):
        pl = Playlist(name="Test")
        pl.add_channel(Channel(name="CNN", url="http://example.com/1", group_title="News"))
        pl.add_channel(Channel(name="ESPN", url="http://example.com/2", group_title="Sports"))
        results = pl.search("cnn")
        assert len(results) == 1
        assert results[0].name == "CNN"

    def test_serialization(self):
        pl = Playlist(name="Test")
        pl.add_channel(Channel(name="Ch1", url="http://example.com/1", group_title="A"))
        data = pl.to_dict()
        restored = Playlist.from_dict(data)
        assert restored.name == pl.name
        assert restored.channel_count == pl.channel_count


class TestProject:
    def test_create_project(self):
        proj = Project(name="Test Project")
        assert proj.name == "Test Project"
        assert not proj.is_modified

    def test_undo_redo(self):
        proj = Project(name="Test")
        proj.playlist.add_channel(
            Channel(name="Ch1", url="http://example.com/1")
        )
        # Push undo state
        snapshot = proj.playlist.to_dict()
        proj.push_undo("add channel", snapshot)
        assert proj.is_modified
        # Should be able to undo
        result = proj.undo()
        assert result is not None

    def test_serialization(self):
        proj = Project(name="Test")
        proj.playlist.add_channel(
            Channel(name="Ch1", url="http://example.com/1", group_title="G")
        )
        data = proj.to_dict()
        restored = Project.from_dict(data)
        assert restored.name == proj.name
        assert restored.playlist.channel_count == 1
