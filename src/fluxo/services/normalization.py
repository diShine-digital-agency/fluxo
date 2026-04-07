"""Metadata normalization rules engine for channels."""

from __future__ import annotations

import logging
import re

from fluxo.models.channel import Channel

logger = logging.getLogger(__name__)

# Regex matching common quality suffixes (case-insensitive, with optional surrounding whitespace)
_QUALITY_SUFFIX_RE = re.compile(
    r"\s*\b(UHD|4K|FHD|HD|SD|H\.265|H\.264|HEVC)\b\.?\s*",
    re.IGNORECASE,
)


class NormalizationService:
    """Apply normalization rules to clean up channel metadata.

    All public methods operate **in-place** on the supplied channel list
    and return the number of channels that were modified.
    """

    @staticmethod
    def normalize_group_names(channels: list[Channel]) -> int:
        """Title-case group names and trim whitespace."""
        count = 0
        for ch in channels:
            original = ch.group_title
            normalized = ch.group_title.strip().title()
            if normalized != original:
                ch.group_title = normalized
                count += 1
        return count

    @staticmethod
    def clean_channel_names(channels: list[Channel]) -> int:
        """Remove common quality suffixes (HD, FHD, 4K, etc.) and trim whitespace."""
        count = 0
        for ch in channels:
            original = ch.name
            cleaned = _QUALITY_SUFFIX_RE.sub(" ", ch.name).strip()
            if cleaned != original:
                ch.name = cleaned
                count += 1
        return count

    @staticmethod
    def fix_urls(channels: list[Channel]) -> int:
        """Trim whitespace from URLs and upgrade ``http://`` to ``https://``."""
        count = 0
        for ch in channels:
            original = ch.url
            url = ch.url.strip()
            if url.startswith("http://"):
                url = "https://" + url[len("http://"):]
            if url != original:
                ch.url = url
                count += 1
        return count

    @staticmethod
    def remove_empty_groups(channels: list[Channel]) -> int:
        """Assign ``"Uncategorized"`` to channels with an empty group title."""
        count = 0
        for ch in channels:
            if not ch.group_title.strip():
                ch.group_title = "Uncategorized"
                count += 1
        return count

    @classmethod
    def apply_all(cls, channels: list[Channel]) -> int:
        """Apply every built-in normalization rule and return total modifications."""
        total = 0
        total += cls.normalize_group_names(channels)
        total += cls.clean_channel_names(channels)
        total += cls.fix_urls(channels)
        total += cls.remove_empty_groups(channels)
        return total
