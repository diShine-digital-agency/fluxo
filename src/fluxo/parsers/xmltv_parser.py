"""XMLTV / EPG parser using lxml for fast XML processing."""

from __future__ import annotations

import gzip
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from lxml import etree

from fluxo.models.epg import EpgChannel, EpgData, EpgProgramme

logger = logging.getLogger(__name__)

# Default HTTP timeout in seconds for downloading EPG data
DEFAULT_TIMEOUT = 30.0


class XmltvParser:
    """Parser for XMLTV-format EPG (Electronic Programme Guide) data.

    Uses ``lxml.etree.iterparse`` for memory-efficient processing of large files.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, content: bytes) -> EpgData:
        """Parse XML *content* bytes into an :class:`EpgData` object."""
        channels: dict[str, EpgChannel] = {}
        programmes: dict[str, list[EpgProgramme]] = {}

        context = etree.iterparse(
            _bytes_source(content),
            events=("end",),
            tag=("channel", "programme"),
        )

        for _event, elem in context:
            if elem.tag == "channel":
                channel = self._parse_channel(elem)
                if channel is not None:
                    channels[channel.id] = channel
            elif elem.tag == "programme":
                programme = self._parse_programme(elem)
                if programme is not None:
                    programmes.setdefault(programme.channel_id, []).append(programme)

            # Free memory for processed elements
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

        return EpgData(channels=channels, programmes=programmes)

    def parse_file(self, path: str) -> EpgData:
        """Read a file (optionally .gz compressed) and parse as XMLTV."""
        file_path = Path(path)
        if file_path.suffix.lower() == ".gz":
            with gzip.open(file_path, "rb") as f:
                raw = f.read()
        else:
            raw = file_path.read_bytes()

        epg = self.parse(raw)
        epg.source_url = str(file_path)
        return epg

    def parse_url(self, url: str) -> EpgData:
        """Download from *url* (handles .gz) and parse as XMLTV."""
        with httpx.Client(follow_redirects=True, timeout=DEFAULT_TIMEOUT) as client:
            response = client.get(url)
            response.raise_for_status()

        raw = response.content
        # Decompress if gzip (check magic bytes or URL suffix)
        if raw[:2] == b"\x1f\x8b" or url.lower().endswith(".gz"):
            raw = gzip.decompress(raw)

        epg = self.parse(raw)
        epg.source_url = url
        return epg

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_channel(elem: etree._Element) -> EpgChannel | None:
        """Parse a <channel> element into an :class:`EpgChannel`."""
        channel_id = elem.get("id", "").strip()
        if not channel_id:
            return None

        display_names = [
            dn.text.strip() for dn in elem.findall("display-name") if dn.text and dn.text.strip()
        ]

        icon_elem = elem.find("icon")
        icon_url = icon_elem.get("src", "") if icon_elem is not None else ""

        urls = [u.text.strip() for u in elem.findall("url") if u.text and u.text.strip()]

        return EpgChannel(
            id=channel_id,
            display_names=display_names,
            icon_url=icon_url,
            urls=urls,
        )

    @staticmethod
    def _parse_programme(elem: etree._Element) -> EpgProgramme | None:
        """Parse a <programme> element into an :class:`EpgProgramme`."""
        channel_id = elem.get("channel", "").strip()
        start_str = elem.get("start", "").strip()
        stop_str = elem.get("stop", "").strip()

        if not channel_id or not start_str or not stop_str:
            return None

        start = _parse_xmltv_datetime(start_str)
        stop = _parse_xmltv_datetime(stop_str)
        if start is None or stop is None:
            return None

        title_elem = elem.find("title")
        title = (title_elem.text or "").strip() if title_elem is not None else ""
        if not title:
            return None

        desc_elem = elem.find("desc")
        description = (desc_elem.text or "").strip() if desc_elem is not None else ""

        cat_elem = elem.find("category")
        category = (cat_elem.text or "").strip() if cat_elem is not None else ""

        icon_elem = elem.find("icon")
        icon_url = icon_elem.get("src", "") if icon_elem is not None else ""

        return EpgProgramme(
            channel_id=channel_id,
            title=title,
            start=start,
            stop=stop,
            description=description,
            category=category,
            icon_url=icon_url,
        )


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------


def _bytes_source(data: bytes):
    """Wrap bytes into a file-like object for lxml iterparse."""
    from io import BytesIO

    return BytesIO(data)


def _parse_xmltv_datetime(dt_str: str) -> datetime | None:
    """Parse an XMLTV datetime string.

    Supported formats:
        ``YYYYMMDDHHmmss +HHMM``
        ``YYYYMMDDHHmmss``
        ``YYYYMMDDHHmm``
        ``YYYYMMDD``
    """
    dt_str = dt_str.strip()
    if not dt_str:
        return None

    # Split off timezone offset if present
    tz_offset: timezone | None = None
    parts = dt_str.split(None, 1)
    core = parts[0]

    if len(parts) == 2:
        tz_offset = _parse_tz_offset(parts[1])

    try:
        if len(core) >= 14:
            dt = datetime(
                year=int(core[0:4]),
                month=int(core[4:6]),
                day=int(core[6:8]),
                hour=int(core[8:10]),
                minute=int(core[10:12]),
                second=int(core[12:14]),
                tzinfo=tz_offset,
            )
        elif len(core) >= 12:
            dt = datetime(
                year=int(core[0:4]),
                month=int(core[4:6]),
                day=int(core[6:8]),
                hour=int(core[8:10]),
                minute=int(core[10:12]),
                tzinfo=tz_offset,
            )
        elif len(core) >= 8:
            dt = datetime(
                year=int(core[0:4]),
                month=int(core[4:6]),
                day=int(core[6:8]),
                tzinfo=tz_offset,
            )
        else:
            return None
    except (ValueError, IndexError):
        return None

    return dt


def _parse_tz_offset(offset_str: str) -> timezone | None:
    """Parse a timezone offset like ``+0530`` or ``-0100``."""
    offset_str = offset_str.strip()
    if not offset_str:
        return None

    sign = 1
    if offset_str.startswith("-"):
        sign = -1
        offset_str = offset_str[1:]
    elif offset_str.startswith("+"):
        offset_str = offset_str[1:]

    # Remove optional colon
    offset_str = offset_str.replace(":", "")

    try:
        if len(offset_str) >= 4:
            hours = int(offset_str[0:2])
            minutes = int(offset_str[2:4])
        elif len(offset_str) >= 2:
            hours = int(offset_str[0:2])
            minutes = 0
        else:
            return None
    except ValueError:
        return None

    total_minutes = sign * (hours * 60 + minutes)
    return timezone(timedelta(minutes=total_minutes))
