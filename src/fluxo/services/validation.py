"""Stream validation and EPG mapping verification service."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

from fluxo.models.channel import Channel, HealthStatus
from fluxo.models.epg import EpgChannel, EpgData
from fluxo.models.playlist import Playlist
from fluxo.services.epg_mapper import EpgMapper

logger = logging.getLogger(__name__)

_mapper = EpgMapper()


class ValidationService:
    """Validates stream URLs and EPG mappings."""

    @staticmethod
    def check_stream(
        url: str,
        timeout: float = 5.0,
        verify_ssl: bool = True,
    ) -> tuple[HealthStatus, str]:
        """Send a HEAD request to *url* and return ``(status, message)``.

        Falls back to a range-limited GET when the server rejects HEAD.
        Set *verify_ssl* to ``False`` to skip certificate verification
        (useful for self-signed IPTV servers).
        """
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=timeout,
                verify=verify_ssl,
            ) as client:
                response = client.head(url)  # noqa: S501
                # Some servers reject HEAD – retry with GET
                if response.status_code == 405:
                    response = client.get(url, headers={"Range": "bytes=0-0"})  # noqa: S501
                if response.status_code < 400:
                    return HealthStatus.ALIVE, f"OK ({response.status_code})"
                return HealthStatus.DEAD, f"HTTP {response.status_code}"
        except httpx.TimeoutException:
            return HealthStatus.TIMEOUT, "Connection timed out"
        except httpx.HTTPError as exc:
            return HealthStatus.DEAD, str(exc)

    @classmethod
    def check_streams(
        cls,
        channels: list[Channel],
        callback: Callable[[Channel, HealthStatus, str], None] | None = None,
    ) -> list[tuple[Channel, HealthStatus, str]]:
        """Check multiple channels sequentially.

        After each check the channel's ``health_status`` and
        ``health_checked_at`` fields are updated in place.
        If *callback* is provided it is called after each check.
        """
        results: list[tuple[Channel, HealthStatus, str]] = []
        for channel in channels:
            status, msg = cls.check_stream(channel.url)
            channel.health_status = status
            channel.health_checked_at = datetime.now(timezone.utc)
            results.append((channel, status, msg))
            if callback is not None:
                callback(channel, status, msg)
        return results

    @staticmethod
    def validate_epg_mapping(
        playlist: Playlist,
        epg_data: EpgData,
    ) -> list[dict]:
        """Check each channel's ``tvg_id`` against *epg_data*.

        Returns a list of dicts with keys ``channel``, ``status``
        (``'mapped'`` | ``'unmapped'`` | ``'missing'``), and ``suggestion``.
        """
        results: list[dict] = []
        for channel in playlist.channels:
            if not channel.tvg_id:
                suggestions = ValidationService.find_epg_suggestions(
                    channel, epg_data, max_results=1
                )
                suggestion = suggestions[0].id if suggestions else None
                results.append({"channel": channel, "status": "unmapped", "suggestion": suggestion})
            elif channel.tvg_id in epg_data.channels:
                results.append({"channel": channel, "status": "mapped", "suggestion": None})
            else:
                suggestions = ValidationService.find_epg_suggestions(
                    channel, epg_data, max_results=1
                )
                suggestion = suggestions[0].id if suggestions else None
                results.append({"channel": channel, "status": "missing", "suggestion": suggestion})
        return results

    @staticmethod
    def find_epg_suggestions(
        channel: Channel,
        epg_data: EpgData,
        max_results: int = 5,
    ) -> list[EpgChannel]:
        """Fuzzy-match a channel name against EPG display names.

        Returns up to *max_results* :class:`EpgChannel` objects sorted by
        descending similarity.
        """
        norm_name = _mapper.normalize_name(channel.name)
        scored: list[tuple[float, EpgChannel]] = []

        for epg_ch in epg_data.channels.values():
            best = 0.0
            for dn in epg_ch.display_names:
                score = _mapper.similarity(norm_name, _mapper.normalize_name(dn))
                if score > best:
                    best = score
            if best > 0:
                scored.append((best, epg_ch))

        scored.sort(key=lambda t: t[0], reverse=True)
        return [epg_ch for _, epg_ch in scored[:max_results]]
