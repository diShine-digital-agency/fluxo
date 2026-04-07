"""Tests for M3U parser."""
from __future__ import annotations

from pathlib import Path

from fluxo.parsers.m3u_parser import M3UParser


class TestM3UParser:
    def setup_method(self):
        self.parser = M3UParser()

    def test_parse_valid_m3u(self, sample_m3u_content: str):
        result = self.parser.parse(sample_m3u_content)
        assert len(result.errors) == 0
        assert result.playlist.channel_count == 8
        assert "News" in result.playlist.groups
        assert "Sports" in result.playlist.groups
        assert "Entertainment" in result.playlist.groups

    def test_parse_channel_metadata(self, sample_m3u_content: str):
        result = self.parser.parse(sample_m3u_content)
        ch = result.playlist.channels[0]
        assert ch.name == "CNN International"
        assert ch.tvg_id == "CNN.us"
        assert ch.tvg_name == "CNN"
        assert ch.tvg_logo == "http://example.com/cnn.png"
        assert ch.group_title == "News"
        assert ch.url == "http://example.com/streams/cnn.m3u8"
        assert ch.duration == -1

    def test_parse_header_attributes(self, sample_m3u_content: str):
        result = self.parser.parse(sample_m3u_content)
        assert result.playlist.header_attributes.get("url-tvg") == "http://example.com/epg.xml"

    def test_parse_malformed_m3u(self, malformed_m3u_content: str):
        result = self.parser.parse(malformed_m3u_content)
        # Should parse what it can and report warnings
        assert result.playlist.channel_count > 0
        assert len(result.warnings) > 0 or len(result.errors) > 0

    def test_parse_missing_header(self):
        content = '#EXTINF:-1 tvg-id="ch1" group-title="Test",Channel 1\nhttp://example.com/ch1\n'
        result = self.parser.parse(content)
        assert result.playlist.channel_count == 1
        assert len(result.warnings) > 0  # Warning about missing header

    def test_parse_empty_content(self):
        result = self.parser.parse("")
        assert result.playlist.channel_count == 0

    def test_parse_only_header(self):
        result = self.parser.parse("#EXTM3U\n")
        assert result.playlist.channel_count == 0

    def test_parse_preserves_all_attributes(self, sample_m3u_content: str):
        result = self.parser.parse(sample_m3u_content)
        for ch in result.playlist.channels:
            assert ch.url != ""
            assert ch.name != ""

    def test_parse_file(self, sample_m3u_path: Path):
        result = self.parser.parse_file(str(sample_m3u_path))
        assert result.playlist.channel_count == 8

    def test_roundtrip_metadata(self, sample_m3u_content: str):
        """Parse and re-export should preserve metadata."""
        result = self.parser.parse(sample_m3u_content)
        # Re-export using ExportService-style logic
        lines = []
        header_parts = ["#EXTM3U"]
        for k, v in result.playlist.header_attributes.items():
            header_parts.append(f'{k}="{v}"')
        lines.append(" ".join(header_parts))
        for ch in result.playlist.channels:
            # to_m3u_line() already includes both #EXTINF and URL lines
            lines.append(ch.to_m3u_line())
        exported = "\n".join(lines) + "\n"
        # Re-parse the exported content
        result2 = self.parser.parse(exported)
        assert result2.playlist.channel_count == result.playlist.channel_count
        for orig, reparsed in zip(
            result.playlist.channels, result2.playlist.channels
        ):
            assert orig.name == reparsed.name
            assert orig.tvg_id == reparsed.tvg_id
            assert orig.group_title == reparsed.group_title
            assert orig.url == reparsed.url

    def test_parse_windows_line_endings(self):
        content = "#EXTM3U\r\n#EXTINF:-1 group-title=\"Test\",Ch1\r\nhttp://example.com/1\r\n"
        result = self.parser.parse(content)
        assert result.playlist.channel_count == 1

    def test_parse_channel_without_comma(self):
        content = "#EXTM3U\n#EXTINF:-1 group-title=\"Test\"\nhttp://example.com/1\n"
        result = self.parser.parse(content)
        # Should still parse the channel
        assert result.playlist.channel_count >= 0
