"""Channel deduplication service."""

from __future__ import annotations

from fluxo.models.channel import Channel
from fluxo.models.playlist import Playlist


def _string_similarity(a: str, b: str) -> float:
    """Compute a simple character-level similarity ratio (0-1).

    Uses the formula ``2 * M / T`` where *M* is the number of matching
    characters (longest common subsequence length) and *T* is the total
    number of characters in both strings.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    len_a, len_b = len(a), len(b)
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


class DeduplicationService:
    """Finds and removes duplicate channels from playlists."""

    @staticmethod
    def find_exact_duplicates(channels: list[Channel]) -> list[list[Channel]]:
        """Group channels with identical URLs.

        Returns only groups that contain more than one channel.
        """
        buckets: dict[str, list[Channel]] = {}
        for ch in channels:
            buckets.setdefault(ch.url, []).append(ch)
        return [group for group in buckets.values() if len(group) > 1]

    @staticmethod
    def find_fuzzy_duplicates(
        channels: list[Channel],
        threshold: float = 0.8,
    ) -> list[list[Channel]]:
        """Group channels with similar names above *threshold*.

        Uses a simple string similarity ratio.  Returns only groups with
        more than one member.
        """
        n = len(channels)
        visited: list[bool] = [False] * n
        groups: list[list[Channel]] = []

        for i in range(n):
            if visited[i]:
                continue
            group = [channels[i]]
            name_i = channels[i].name.lower()
            for j in range(i + 1, n):
                if visited[j]:
                    continue
                name_j = channels[j].name.lower()
                if _string_similarity(name_i, name_j) >= threshold:
                    group.append(channels[j])
                    visited[j] = True
            if len(group) > 1:
                groups.append(group)
                visited[i] = True

        return groups

    @staticmethod
    def remove_duplicates(
        playlist: Playlist,
        keep: str = "first",
    ) -> list[Channel]:
        """Remove URL-based duplicates from *playlist* in place.

        *keep* controls which duplicate to retain (``'first'`` or ``'last'``).
        Returns the list of removed channels.
        """
        seen: dict[str, int] = {}
        for idx, ch in enumerate(playlist.channels):
            if ch.url in seen:
                if keep == "last":
                    seen[ch.url] = idx
            else:
                seen[ch.url] = idx

        keep_indices = set(seen.values())
        removed: list[Channel] = []
        kept: list[Channel] = []
        for idx, ch in enumerate(playlist.channels):
            if idx in keep_indices:
                kept.append(ch)
            else:
                removed.append(ch)

        if removed:
            playlist.channels = kept
        return removed
