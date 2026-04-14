"""Status bar widget showing playlist statistics."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar, QWidget

from fluxo.models import HealthStatus, Playlist


class FluxoStatusBar(QStatusBar):
    """Application status bar displaying channel/group/health stats."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._channels_label = QLabel("Channels: 0")
        self._groups_label = QLabel("Groups: 0")
        self._selected_label = QLabel("")
        self._health_label = QLabel("")

        self.addPermanentWidget(self._channels_label)
        self.addPermanentWidget(self._groups_label)
        self.addPermanentWidget(self._selected_label)
        self.addPermanentWidget(self._health_label)

    # -- public API --------------------------------------------------------

    def update_stats(self, playlist: Playlist, selected_count: int = 0) -> None:
        """Refresh all statistics from *playlist*."""
        self._channels_label.setText(f"Channels: {playlist.channel_count}")
        self._groups_label.setText(f"Groups: {len(playlist.groups)}")

        if selected_count:
            self._selected_label.setText(f"Selected: {selected_count}")
            self._selected_label.show()
        else:
            self._selected_label.setText("")
            self._selected_label.hide()

        # Health summary
        alive = dead = unknown = 0
        for ch in playlist.channels:
            if ch.health_status == HealthStatus.ALIVE:
                alive += 1
            elif ch.health_status == HealthStatus.DEAD:
                dead += 1
            else:
                unknown += 1

        self._health_label.setText(f"Health: {alive} alive · {dead} dead · {unknown} unknown")
