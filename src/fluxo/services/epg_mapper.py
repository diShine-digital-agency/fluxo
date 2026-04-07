"""EPG mapping service for matching channels to EPG data."""

from __future__ import annotations

import re
import unicodedata

from fluxo.models.channel import Channel
from fluxo.models.epg import EpgChannel, EpgData
from fluxo.models.playlist import Playlist

# Suffixes commonly appended to channel names that should be ignored during matching
_SUFFIX_PATTERN = re.compile(
    r"\b(hd|sd|fhd|uhd|4k|hevc|h\.?265|plus|\+)\b",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


class EpgMapper:
    """Maps playlist channels to EPG channel entries using fuzzy name matching."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize a channel name for matching.

        Lowercase, strip accents, remove HD/SD/FHD/4K suffixes,
        strip punctuation, and collapse whitespace.
        """
        text = name.lower()
        # Strip unicode accents
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
        # Remove known quality/format suffixes
        text = _SUFFIX_PATTERN.sub("", text)
        # Remove punctuation
        text = _PUNCTUATION.sub(" ", text)
        # Collapse whitespace
        text = _WHITESPACE.sub(" ", text).strip()
        return text

    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Compute a simple ratio similarity between two strings (0-1).

        Uses the longest common subsequence ratio as a lightweight metric.
        """
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0

        # Sequence matcher–style ratio: 2 * matches / total length
        len_a, len_b = len(a), len(b)
        # Build simple LCS length via DP (space-optimised to two rows)
        prev = [0] * (len_b + 1)
        for i in range(1, len_a + 1):
            curr = [0] * (len_b + 1)
            for j in range(1, len_b + 1):
                if a[i - 1] == b[j - 1]:
                    curr[j] = prev[j - 1] + 1
                else:
                    curr[j] = max(prev[j], curr[j - 1])
            prev = curr
        lcs_len = prev[len_b]
        return 2.0 * lcs_len / (len_a + len_b)

    def auto_map(
        self,
        playlist: Playlist,
        epg_data: EpgData,
    ) -> list[tuple[Channel, EpgChannel | None, float]]:
        """For each channel find the best EPG match with a confidence score.

        Returns a list of ``(channel, best_match_or_None, confidence)`` tuples.
        """
        # Pre-normalise EPG display names for fast comparison
        epg_entries: list[tuple[EpgChannel, list[str]]] = []
        for epg_ch in epg_data.channels.values():
            normals = [self.normalize_name(dn) for dn in epg_ch.display_names]
            epg_entries.append((epg_ch, normals))

        results: list[tuple[Channel, EpgChannel | None, float]] = []
        for channel in playlist.channels:
            # Direct tvg_id match takes priority
            if channel.tvg_id and channel.tvg_id in epg_data.channels:
                results.append((channel, epg_data.channels[channel.tvg_id], 1.0))
                continue

            norm_name = self.normalize_name(channel.name)
            best_match: EpgChannel | None = None
            best_score: float = 0.0

            for epg_ch, normals in epg_entries:
                for norm_dn in normals:
                    score = self.similarity(norm_name, norm_dn)
                    if score > best_score:
                        best_score = score
                        best_match = epg_ch

            results.append((channel, best_match, best_score))

        return results

    @staticmethod
    def apply_mapping(channel: Channel, epg_channel: EpgChannel) -> None:
        """Apply an EPG mapping to a channel.

        Sets ``tvg_id`` and optionally updates ``tvg_name`` and ``tvg_logo``
        from the EPG channel data.
        """
        channel.tvg_id = epg_channel.id
        if epg_channel.display_names:
            channel.tvg_name = epg_channel.display_names[0]
        if epg_channel.icon_url:
            channel.tvg_logo = epg_channel.icon_url
