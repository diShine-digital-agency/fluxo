"""Tests for XMLTV parser."""

from __future__ import annotations

from pathlib import Path

from fluxo.parsers.xmltv_parser import XmltvParser


class TestXmltvParser:
    def setup_method(self):
        self.parser = XmltvParser()

    def test_parse_valid_epg(self, sample_epg_bytes: bytes):
        epg = self.parser.parse(sample_epg_bytes)
        assert len(epg.channels) == 3
        assert "CNN.us" in epg.channels
        assert "BBC1.uk" in epg.channels
        assert "ESPN.us" in epg.channels

    def test_parse_channel_details(self, sample_epg_bytes: bytes):
        epg = self.parser.parse(sample_epg_bytes)
        cnn = epg.channels["CNN.us"]
        assert "CNN International" in cnn.display_names
        assert "CNN" in cnn.display_names
        assert cnn.icon_url == "http://example.com/cnn.png"

    def test_parse_programmes(self, sample_epg_bytes: bytes):
        epg = self.parser.parse(sample_epg_bytes)
        progs = epg.get_programmes_for_channel("CNN.us")
        assert len(progs) == 2
        assert progs[0].title == "CNN Newsroom"

    def test_parse_file(self, sample_epg_path: Path):
        epg = self.parser.parse_file(str(sample_epg_path))
        assert len(epg.channels) == 3

    def test_find_channel_by_name(self, sample_epg_bytes: bytes):
        epg = self.parser.parse(sample_epg_bytes)
        matches = epg.find_channel_by_name("CNN")
        assert len(matches) >= 1

    def test_parse_empty_xml(self):
        content = b'<?xml version="1.0"?><tv></tv>'
        epg = self.parser.parse(content)
        assert len(epg.channels) == 0
        assert len(epg.programmes) == 0
