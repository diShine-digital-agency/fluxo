"""EPG Management dialog — manage EPG sources and channel-to-EPG mapping."""

from __future__ import annotations

import logging
from enum import Enum

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fluxo.models import Channel, EpgData, Playlist
from fluxo.services import EpgMapper

logger = logging.getLogger(__name__)


class _MapStatus(Enum):
    MAPPED = "mapped"
    UNMAPPED = "unmapped"
    MISSING = "missing"


_STATUS_COLORS: dict[_MapStatus, QColor] = {
    _MapStatus.MAPPED: QColor("#a6e3a1"),  # green
    _MapStatus.UNMAPPED: QColor("#f9e2af"),  # yellow
    _MapStatus.MISSING: QColor("#f38ba8"),  # red
}


class EpgDialog(QDialog):
    """Dialog for managing EPG sources and mapping channels to EPG data."""

    mapping_applied = Signal()

    _MIN_WIDTH = 720
    _MIN_HEIGHT = 520

    def __init__(
        self,
        playlist: Playlist,
        epg_data: EpgData | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("EPG Management")
        self.setMinimumSize(self._MIN_WIDTH, self._MIN_HEIGHT)
        self.resize(self._MIN_WIDTH, self._MIN_HEIGHT)

        self._playlist = playlist
        self._epg_data = epg_data or EpgData()
        self._mapper = EpgMapper()

        self._build_ui()
        self._connect_signals()
        self._refresh_mapping_table()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_sources_group())
        splitter.addWidget(self._build_mapping_group())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        # Manual mapping
        layout.addWidget(self._build_manual_group())

        # Buttons
        self._button_box = QDialogButtonBox()
        self._apply_btn = self._button_box.addButton(
            "Apply", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self._button_box)

    def _build_sources_group(self) -> QGroupBox:
        group = QGroupBox("EPG Sources")
        layout = QVBoxLayout(group)

        self._source_list = QListWidget()
        for url in self._playlist.epg_urls:
            self._source_list.addItem(url)
        layout.addWidget(self._source_list)

        btn_row = QHBoxLayout()
        self._add_url_edit = QLineEdit()
        self._add_url_edit.setPlaceholderText("https://example.com/epg.xml")
        btn_row.addWidget(self._add_url_edit, 1)

        self._add_btn = QPushButton("Add")
        self._remove_btn = QPushButton("Remove")
        self._import_btn = QPushButton("Import EPG")
        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._remove_btn)
        btn_row.addWidget(self._import_btn)
        layout.addLayout(btn_row)

        return group

    def _build_mapping_group(self) -> QGroupBox:
        group = QGroupBox("EPG Mapping")
        layout = QVBoxLayout(group)

        toolbar = QHBoxLayout()
        self._auto_map_btn = QPushButton("Auto-Map")
        self._status_label = QLabel("")
        toolbar.addWidget(self._auto_map_btn)
        toolbar.addStretch()
        toolbar.addWidget(self._status_label)
        layout.addLayout(toolbar)

        self._mapping_table = QTableWidget()
        self._mapping_table.setColumnCount(4)
        self._mapping_table.setHorizontalHeaderLabels(["Channel", "TVG-ID", "EPG Match", "Status"])
        self._mapping_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._mapping_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._mapping_table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._mapping_table)

        return group

    def _build_manual_group(self) -> QGroupBox:
        group = QGroupBox("Manual Mapping")
        layout = QHBoxLayout(group)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search EPG channels…")
        layout.addWidget(self._search_edit)

        self._epg_combo = QComboBox()
        self._epg_combo.setMinimumWidth(200)
        layout.addWidget(self._epg_combo)

        self._assign_btn = QPushButton("Assign to Selected")
        layout.addWidget(self._assign_btn)

        return group

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._add_btn.clicked.connect(self._on_add_source)
        self._remove_btn.clicked.connect(self._on_remove_source)
        self._import_btn.clicked.connect(self._on_import_epg)
        self._auto_map_btn.clicked.connect(self._on_auto_map)
        self._search_edit.textChanged.connect(self._on_search_epg)
        self._assign_btn.clicked.connect(self._on_manual_assign)
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_add_source(self) -> None:
        url = self._add_url_edit.text().strip()
        if url and url not in self._current_urls():
            self._source_list.addItem(url)
            self._add_url_edit.clear()

    def _on_remove_source(self) -> None:
        row = self._source_list.currentRow()
        if row >= 0:
            self._source_list.takeItem(row)

    def _on_import_epg(self) -> None:
        # Importing EPG XML is a potentially long operation.
        # This stub updates the status label; real implementation would use
        # XmltvParser in a background thread.
        self._status_label.setText("EPG import is handled by the main application.")

    def _on_auto_map(self) -> None:
        results = self._mapper.auto_map(self._playlist, self._epg_data)
        applied = 0
        for channel, epg_channel, score in results:
            if epg_channel is not None and score > 0.6:
                EpgMapper.apply_mapping(channel, epg_channel)
                applied += 1

        self._status_label.setText(f"Auto-mapped {applied} channel(s).")
        self._refresh_mapping_table()

    def _on_search_epg(self, text: str) -> None:
        self._epg_combo.clear()
        if not text:
            return
        matches = self._epg_data.find_channel_by_name(text)
        for epg_ch in matches[:30]:
            display = epg_ch.display_names[0] if epg_ch.display_names else epg_ch.id
            self._epg_combo.addItem(f"{display}  ({epg_ch.id})", epg_ch.id)

    def _on_manual_assign(self) -> None:
        selected_rows = self._mapping_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        epg_id = self._epg_combo.currentData()
        if not epg_id:
            return

        epg_channel = self._epg_data.channels.get(epg_id)
        if not epg_channel:
            return

        for idx in selected_rows:
            row = idx.row()
            if row < len(self._playlist.channels):
                channel = self._playlist.channels[row]
                EpgMapper.apply_mapping(channel, epg_channel)

        self._refresh_mapping_table()

    def _on_accept(self) -> None:
        # Sync EPG source list back to the playlist
        self._playlist.epg_urls = self._current_urls()
        self.mapping_applied.emit()
        self.accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_urls(self) -> list[str]:
        return [self._source_list.item(i).text() for i in range(self._source_list.count())]

    def _refresh_mapping_table(self) -> None:
        channels = self._playlist.channels
        self._mapping_table.setRowCount(len(channels))

        mapped_count = 0
        unmapped_count = 0
        missing_count = 0

        for row, ch in enumerate(channels):
            status = self._channel_map_status(ch)
            if status == _MapStatus.MAPPED:
                mapped_count += 1
            elif status == _MapStatus.UNMAPPED:
                unmapped_count += 1
            else:
                missing_count += 1

            color = _STATUS_COLORS[status]

            name_item = QTableWidgetItem(ch.name)
            tvg_item = QTableWidgetItem(ch.tvg_id)

            epg_match = ""
            if ch.tvg_id and ch.tvg_id in self._epg_data.channels:
                epg_ch = self._epg_data.channels[ch.tvg_id]
                epg_match = epg_ch.display_names[0] if epg_ch.display_names else epg_ch.id
            match_item = QTableWidgetItem(epg_match)

            status_item = QTableWidgetItem(status.value.capitalize())
            status_item.setForeground(QBrush(color))

            for item in (name_item, tvg_item, match_item, status_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self._mapping_table.setItem(row, 0, name_item)
            self._mapping_table.setItem(row, 1, tvg_item)
            self._mapping_table.setItem(row, 2, match_item)
            self._mapping_table.setItem(row, 3, status_item)

        self._status_label.setText(
            f"Mapped: {mapped_count}  |  Unmapped: {unmapped_count}  |  Missing: {missing_count}"
        )

    def _channel_map_status(self, channel: Channel) -> _MapStatus:
        if not channel.tvg_id:
            return _MapStatus.UNMAPPED
        if channel.tvg_id in self._epg_data.channels:
            return _MapStatus.MAPPED
        return _MapStatus.MISSING
