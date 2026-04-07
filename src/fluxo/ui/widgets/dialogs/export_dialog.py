"""Export M3U dialog — save playlists to file with filtering options."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from fluxo.models import HealthStatus, Playlist
from fluxo.services import ExportService

logger = logging.getLogger(__name__)

_ENCODINGS = ["UTF-8", "Latin-1", "Windows-1252", "ISO-8859-1", "ASCII"]


class ExportDialog(QDialog):
    """Dialog for exporting a playlist to an M3U file."""

    _MIN_WIDTH = 520
    _MIN_HEIGHT = 460

    def __init__(
        self,
        playlist: Playlist,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export M3U Playlist")
        self.setMinimumSize(self._MIN_WIDTH, self._MIN_HEIGHT)
        self.resize(self._MIN_WIDTH, self._MIN_HEIGHT)

        self._playlist = playlist

        self._build_ui()
        self._connect_signals()
        self._refresh_preview()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # File path
        layout.addWidget(self._build_path_group())

        # Options
        layout.addWidget(self._build_options_group())

        # Groups filter
        layout.addWidget(self._build_groups_group())

        # Preview
        layout.addWidget(self._build_preview_group())

        # Buttons
        self._button_box = QDialogButtonBox()
        self._export_btn = self._button_box.addButton(
            "Export", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._export_btn.setEnabled(False)
        layout.addWidget(self._button_box)

    def _build_path_group(self) -> QGroupBox:
        group = QGroupBox("Destination")
        row = QHBoxLayout(group)

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Choose output file…")
        self._browse_btn = QPushButton("Browse…")
        row.addWidget(self._path_edit, 1)
        row.addWidget(self._browse_btn)

        return group

    def _build_options_group(self) -> QGroupBox:
        group = QGroupBox("Options")
        form = QFormLayout(group)

        self._encoding_combo = QComboBox()
        self._encoding_combo.addItems(_ENCODINGS)
        form.addRow("Encoding:", self._encoding_combo)

        self._healthy_only_check = QCheckBox("Include only healthy streams")
        form.addRow("", self._healthy_only_check)

        return group

    def _build_groups_group(self) -> QGroupBox:
        group = QGroupBox("Groups")
        layout = QVBoxLayout(group)

        self._group_checkboxes: list[QCheckBox] = []
        groups = sorted(self._playlist.groups)

        if groups:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(120)
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(4, 4, 4, 4)

            for g in groups:
                cb = QCheckBox(g or "(No group)")
                cb.setChecked(True)
                self._group_checkboxes.append(cb)
                container_layout.addWidget(cb)

            scroll.setWidget(container)
            layout.addWidget(scroll)

            btn_row = QHBoxLayout()
            self._select_all_btn = QPushButton("Select All")
            self._deselect_all_btn = QPushButton("Deselect All")
            btn_row.addWidget(self._select_all_btn)
            btn_row.addWidget(self._deselect_all_btn)
            btn_row.addStretch()
            layout.addLayout(btn_row)
        else:
            layout.addWidget(QLabel("No groups in playlist."))

        return group

    def _build_preview_group(self) -> QGroupBox:
        group = QGroupBox("Preview")
        layout = QVBoxLayout(group)

        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setMaximumHeight(120)
        layout.addWidget(self._preview_text)

        return group

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._browse_btn.clicked.connect(self._on_browse)
        self._path_edit.textChanged.connect(self._on_path_changed)
        self._encoding_combo.currentIndexChanged.connect(
            lambda _: self._refresh_preview()
        )
        self._healthy_only_check.toggled.connect(lambda _: self._refresh_preview())

        for cb in self._group_checkboxes:
            cb.toggled.connect(lambda _: self._refresh_preview())

        if self._group_checkboxes:
            self._select_all_btn.clicked.connect(self._select_all_groups)
            self._deselect_all_btn.clicked.connect(self._deselect_all_groups)

        self._button_box.accepted.connect(self._on_export)
        self._button_box.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save M3U Playlist",
            "",
            "M3U Files (*.m3u *.m3u8);;All Files (*)",
        )
        if path:
            self._path_edit.setText(path)

    def _on_path_changed(self, path: str) -> None:
        self._export_btn.setEnabled(bool(path.strip()))

    def _on_export(self) -> None:
        path = self._path_edit.text().strip()
        if not path:
            return

        content = self._generate_content()
        encoding = self._encoding_combo.currentText()

        try:
            with open(path, "w", encoding=encoding) as fh:
                fh.write(content)
            self.accept()
        except Exception as exc:  # noqa: BLE001
            self._preview_text.setPlainText(f"Export error: {exc}")

    def _select_all_groups(self) -> None:
        for cb in self._group_checkboxes:
            cb.setChecked(True)

    def _deselect_all_groups(self) -> None:
        for cb in self._group_checkboxes:
            cb.setChecked(False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _selected_groups(self) -> list[str] | None:
        if not self._group_checkboxes:
            return None
        selected = []
        for cb in self._group_checkboxes:
            if cb.isChecked():
                text = cb.text()
                selected.append("" if text == "(No group)" else text)
        if len(selected) == len(self._group_checkboxes):
            return None  # all selected → no filter
        return selected

    def _generate_content(self) -> str:
        groups = self._selected_groups()
        health_filter = HealthStatus.ALIVE if self._healthy_only_check.isChecked() else None
        return ExportService.export_m3u_filtered(
            self._playlist, groups=groups, health_filter=health_filter
        )

    def _refresh_preview(self) -> None:
        content = self._generate_content()
        lines = content.splitlines()[:8]
        preview = "\n".join(lines)
        if len(content.splitlines()) > 8:
            preview += "\n…"
        self._preview_text.setPlainText(preview)
