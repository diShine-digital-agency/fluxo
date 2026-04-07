"""Bulk channel editing operations."""

from __future__ import annotations

import re

from fluxo.models.channel import Channel
from fluxo.models.epg import EpgData
from fluxo.services.epg_mapper import EpgMapper

_mapper = EpgMapper()


class BulkOperationService:
    """Perform bulk edits on lists of channels."""

    @staticmethod
    def bulk_rename(
        channels: list[Channel],
        find: str,
        replace: str,
        use_regex: bool = False,
    ) -> int:
        """Find-and-replace in channel names. Return the number of changes."""
        count = 0
        if use_regex:
            pattern = re.compile(find)
            for ch in channels:
                new_name, subs = pattern.subn(replace, ch.name)
                if subs:
                    ch.name = new_name
                    count += 1
        else:
            for ch in channels:
                if find in ch.name:
                    ch.name = ch.name.replace(find, replace)
                    count += 1
        return count

    @staticmethod
    def bulk_move_to_group(channels: list[Channel], target_group: str) -> int:
        """Move channels to *target_group*. Return the number of changes."""
        count = 0
        for ch in channels:
            if ch.group_title != target_group:
                ch.group_title = target_group
                count += 1
        return count

    @staticmethod
    def bulk_set_logo(channels: list[Channel], logo_url: str) -> int:
        """Set ``tvg_logo`` for all channels. Return the number of changes."""
        count = 0
        for ch in channels:
            if ch.tvg_logo != logo_url:
                ch.tvg_logo = logo_url
                count += 1
        return count

    @staticmethod
    def bulk_set_epg_id(channels: list[Channel], tvg_id: str) -> int:
        """Set ``tvg_id`` for all channels. Return the number of changes."""
        count = 0
        for ch in channels:
            if ch.tvg_id != tvg_id:
                ch.tvg_id = tvg_id
                count += 1
        return count

    @staticmethod
    def bulk_assign_epg_from_data(
        channels: list[Channel],
        epg_data: EpgData,
    ) -> int:
        """Auto-assign ``tvg_id`` to channels using fuzzy EPG matching.

        Only assigns when the best match confidence is ≥ 0.7.
        Return the number of channels assigned.
        """
        # Pre-normalise EPG display names once
        epg_entries: list[tuple[str, list[str]]] = []
        for epg_ch in epg_data.channels.values():
            normals = [_mapper.normalize_name(dn) for dn in epg_ch.display_names]
            epg_entries.append((epg_ch.id, normals))

        count = 0
        threshold = 0.7
        for ch in channels:
            if ch.tvg_id:
                continue
            norm_name = _mapper.normalize_name(ch.name)
            best_id: str | None = None
            best_score: float = 0.0

            for epg_id, normals in epg_entries:
                for norm_dn in normals:
                    score = _mapper.similarity(norm_name, norm_dn)
                    if score > best_score:
                        best_score = score
                        best_id = epg_id

            if best_id is not None and best_score >= threshold:
                ch.tvg_id = best_id
                count += 1

        return count
