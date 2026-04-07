"""Playlist export service."""

from __future__ import annotations

from pathlib import Path

from fluxo.models.channel import HealthStatus
from fluxo.models.playlist import Playlist


class ExportService:
    """Exports playlists to M3U format."""

    @staticmethod
    def export_m3u(playlist: Playlist, path: str | None = None) -> str:
        """Generate an M3U string from *playlist*.

        If *path* is provided the string is also written to disk.
        All header attributes and channel metadata are preserved.
        """
        lines: list[str] = []

        # Build #EXTM3U header
        header = "#EXTM3U"
        if playlist.header_attributes:
            parts = [f'{k}="{v}"' for k, v in playlist.header_attributes.items()]
            header += " " + " ".join(parts)
        lines.append(header)

        # Channel lines
        for channel in playlist.channels:
            lines.append(channel.to_m3u_line())

        content = "\n".join(lines) + "\n"

        if path is not None:
            Path(path).write_text(content, encoding="utf-8")

        return content

    @staticmethod
    def export_m3u_filtered(
        playlist: Playlist,
        groups: list[str] | None = None,
        health_filter: HealthStatus | None = None,
    ) -> str:
        """Export a filtered subset of the playlist as M3U.

        *groups*: if provided, only channels whose ``group_title`` is in
        the list are exported.
        *health_filter*: if provided, only channels with that
        ``health_status`` are exported.
        """
        filtered_channels = playlist.channels

        if groups is not None:
            group_set = set(groups)
            filtered_channels = [ch for ch in filtered_channels if ch.group_title in group_set]

        if health_filter is not None:
            filtered_channels = [
                ch for ch in filtered_channels if ch.health_status == health_filter
            ]

        # Build a temporary playlist to reuse export_m3u
        temp = Playlist(
            name=playlist.name,
            channels=filtered_channels,
            header_attributes=playlist.header_attributes,
            epg_urls=playlist.epg_urls,
        )
        return ExportService.export_m3u(temp)
