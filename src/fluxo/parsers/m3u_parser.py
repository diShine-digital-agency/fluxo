"""Robust M3U/EXTINF playlist parser."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import chardet
import httpx

from fluxo.models.channel import Channel
from fluxo.models.playlist import Playlist

logger = logging.getLogger(__name__)

# Regex for quoted attributes: key="value"
_RE_ATTR_QUOTED = re.compile(r'([a-zA-Z_][\w-]*)="([^"]*)"')
# Regex for single-quoted attributes: key='value'
_RE_ATTR_SINGLE_QUOTED = re.compile(r"([a-zA-Z_][\w-]*)='([^']*)'")
# Regex for unquoted attributes: key=value (no spaces, quotes, or commas in value)
_RE_ATTR_UNQUOTED = re.compile(r'([a-zA-Z_][\w-]*)=([^\s"\',]+)')
# Regex for the duration at the start of an #EXTINF line
_RE_DURATION = re.compile(r"^#EXTINF:\s*(-?\d+)")

# Known Channel field attributes (M3U attr name -> Channel field name)
_KNOWN_ATTRS: dict[str, str] = {
    "tvg-id": "tvg_id",
    "tvg-name": "tvg_name",
    "tvg-logo": "tvg_logo",
    "group-title": "group_title",
    "tvg-language": "tvg_language",
    "tvg-country": "tvg_country",
    "tvg-shift": "tvg_shift",
    "catchup": "catchup",
    "catchup-days": "catchup_days",
    "catchup-source": "catchup_source",
    "channel-number": "channel_number",
}

# Header attributes that contain EPG URLs
_EPG_URL_ATTRS = {"url-tvg", "x-tvg-url"}


@dataclass
class ParseResult:
    """Result container for M3U parsing, including warnings and errors."""

    playlist: Playlist
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class M3UParser:
    """Parser for M3U/EXTINF playlist files.

    Handles standard and extended M3U formats with robust error recovery.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, content: str) -> ParseResult:
        """Parse M3U text content into a :class:`ParseResult`."""
        warnings: list[str] = []
        errors: list[str] = []

        lines = _normalize_lines(content)
        header_attrs: dict[str, str] = {}
        epg_urls: list[str] = []
        channels: list[Channel] = []

        idx = 0
        total = len(lines)

        # --- Parse optional #EXTM3U header ---
        if total > 0 and lines[0].upper().startswith("#EXTM3U"):
            header_attrs = _parse_attributes(lines[0][len("#EXTM3U"):])
            for attr_name in _EPG_URL_ATTRS:
                url = header_attrs.get(attr_name, "").strip()
                if url:
                    epg_urls.append(url)
            idx = 1
        elif total > 0:
            warnings.append("Missing #EXTM3U header; treating as valid M3U content.")

        # --- Process remaining lines ---
        pending_extinf: str | None = None
        pending_extra: list[str] = []
        line_num_extinf = 0

        while idx < total:
            line = lines[idx]
            idx += 1

            if not line:
                continue

            if line.upper().startswith("#EXTINF:"):
                # If there was a previous unmatched #EXTINF, warn and discard
                if pending_extinf is not None:
                    warnings.append(
                        f"Line {line_num_extinf}: #EXTINF without a URL, skipping."
                    )
                pending_extinf = line
                pending_extra = []
                line_num_extinf = idx  # 1-based

            elif line.startswith("#"):
                # Other comment / directive lines — collect as extra
                if pending_extinf is not None:
                    pending_extra.append(line)

            else:
                # Non-comment, non-empty → this is a URL line
                if pending_extinf is not None:
                    channel = self._build_channel(
                        pending_extinf, line, pending_extra, line_num_extinf, warnings
                    )
                    if channel is not None:
                        channels.append(channel)
                    pending_extinf = None
                    pending_extra = []
                else:
                    # Bare URL without #EXTINF
                    channels.append(Channel(name=line, url=line))

        # Handle trailing #EXTINF with no URL
        if pending_extinf is not None:
            warnings.append(
                f"Line {line_num_extinf}: #EXTINF at end of file without a URL, skipping."
            )

        playlist = Playlist(
            channels=channels,
            header_attributes=header_attrs,
            epg_urls=epg_urls,
        )
        return ParseResult(playlist=playlist, warnings=warnings, errors=errors)

    def parse_file(self, path: str) -> ParseResult:
        """Read a file with encoding detection and parse it as M3U."""
        file_path = Path(path)
        raw = file_path.read_bytes()

        detected = chardet.detect(raw)
        encoding = detected.get("encoding") or "utf-8"
        try:
            content = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            content = raw.decode("utf-8", errors="replace")

        result = self.parse(content)
        result.playlist.name = file_path.stem
        return result

    def parse_url(self, url: str) -> ParseResult:
        """Download from *url* using httpx and parse as M3U."""
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()

        content = response.text
        result = self.parse(content)
        result.playlist.name = _name_from_url(url)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_channel(
        self,
        extinf_line: str,
        url: str,
        extra_lines: list[str],
        line_num: int,
        warnings: list[str],
    ) -> Channel | None:
        """Parse a single #EXTINF line + URL into a Channel."""
        # Duration
        dur_match = _RE_DURATION.match(extinf_line)
        if dur_match:
            duration = int(dur_match.group(1))
        else:
            duration = -1
            warnings.append(
                f"Line {line_num}: Could not parse duration from #EXTINF, defaulting to -1."
            )

        # Attributes from the part after duration up to the last comma
        attrs = _parse_attributes(extinf_line)

        # Display name — text after the last comma
        comma_pos = extinf_line.rfind(",")
        if comma_pos != -1:
            display_name = extinf_line[comma_pos + 1:].strip()
        else:
            # No comma — use the remainder after attributes as name
            display_name = ""
            warnings.append(
                f"Line {line_num}: No comma separator in #EXTINF line."
            )

        # Split attributes into known fields and extras
        known_kwargs: dict[str, str] = {}
        extra_attrs: dict[str, str] = {}

        for key, value in attrs.items():
            field_name = _KNOWN_ATTRS.get(key)
            if field_name:
                known_kwargs[field_name] = value
            else:
                extra_attrs[key] = value

        # Collect extra comment lines (e.g. #EXTVLCOPT)
        for extra_line in extra_lines:
            # Try to parse as key:value or key=value
            if ":" in extra_line[1:]:
                tag_body = extra_line[1:]  # strip leading #
                colon_pos = tag_body.index(":")
                tag_key = tag_body[:colon_pos].strip()
                tag_val = tag_body[colon_pos + 1:].strip()
                extra_attrs[tag_key] = tag_val
            else:
                extra_attrs[extra_line] = ""

        return Channel(
            name=display_name or url,
            url=url,
            duration=duration,
            extra_attributes=extra_attrs,
            **known_kwargs,
        )


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------


def _normalize_lines(content: str) -> list[str]:
    """Split content into lines, handling mixed line endings."""
    # Normalize all line endings to \n then split
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    return [line.strip() for line in content.split("\n")]


def _parse_attributes(text: str) -> dict[str, str]:
    """Extract key=value attributes from a text fragment.

    Supports double-quoted, single-quoted, and unquoted values.
    Double-quoted attributes take priority to avoid false positives.
    """
    attrs: dict[str, str] = {}

    # 1. Double-quoted  key="value"
    for m in _RE_ATTR_QUOTED.finditer(text):
        attrs[m.group(1)] = m.group(2)

    # 2. Single-quoted  key='value'  (only if not already captured)
    for m in _RE_ATTR_SINGLE_QUOTED.finditer(text):
        if m.group(1) not in attrs:
            attrs[m.group(1)] = m.group(2)

    # 3. Unquoted  key=value  (only if not already captured)
    for m in _RE_ATTR_UNQUOTED.finditer(text):
        if m.group(1) not in attrs:
            attrs[m.group(1)] = m.group(2)

    return attrs


def _name_from_url(url: str) -> str:
    """Derive a playlist name from a URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if path:
        name = path.rsplit("/", 1)[-1]
        # Strip common extensions
        for ext in (".m3u", ".m3u8", ".txt"):
            if name.lower().endswith(ext):
                name = name[: -len(ext)]
                break
        if name:
            return name
    return parsed.hostname or "Untitled"
