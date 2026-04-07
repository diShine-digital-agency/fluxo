"""Import M3U dialog — load playlists from file or URL."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QThread
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
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from fluxo.models import Playlist
from fluxo.parsers import M3UParser, ParseResult

logger = logging.getLogger(__name__)

_ENCODINGS = ["Auto-detect", "UTF-8", "Latin-1", "Windows-1252", "ISO-8859-1", "ASCII"]


class _DownloadWorker(QThread):
    """Background worker that downloads and parses an M3U URL."""

    finished = Signal(object)  # ParseResult | Exception
    progress = Signal(int)

    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url

    def run(self) -> None:
        try:
            self.progress.emit(50)
            parser = M3UParser()
            result = parser.parse_url(self._url)
            self.progress.emit(100)
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.finished.emit(exc)


class ImportDialog(QDialog):
    """Dialog for importing an M3U playlist from a local file or URL."""

    import_completed = Signal(object, list)  # Playlist, list[str]

    _MIN_WIDTH = 560
    _MIN_HEIGHT = 440

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import M3U Playlist")
        self.setMinimumSize(self._MIN_WIDTH, self._MIN_HEIGHT)
        self.resize(self._MIN_WIDTH, self._MIN_HEIGHT)

        self._result: ParseResult | None = None
        self._worker: _DownloadWorker | None = None

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_file_tab(), "From File")
        self._tabs.addTab(self._build_url_tab(), "From URL")
        layout.addWidget(self._tabs)

        # Options
        layout.addWidget(self._build_options_group())

        # Preview
        layout.addWidget(self._build_preview_group())

        # Buttons
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        layout.addWidget(self._button_box)

    def _build_file_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)

        path_row = QHBoxLayout()
        self._file_path_edit = QLineEdit()
        self._file_path_edit.setPlaceholderText("Select an M3U file…")
        self._browse_btn = QPushButton("Browse…")
        path_row.addWidget(self._file_path_edit, 1)
        path_row.addWidget(self._browse_btn)
        form.addRow("File:", path_row)

        self._file_info_label = QLabel("")
        self._file_info_label.setWordWrap(True)
        form.addRow("Info:", self._file_info_label)

        return tab

    def _build_url_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://example.com/playlist.m3u")
        form.addRow("URL:", self._url_edit)

        progress_row = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._download_btn = QPushButton("Download")
        progress_row.addWidget(self._progress_bar, 1)
        progress_row.addWidget(self._download_btn)
        form.addRow("", progress_row)

        return tab

    def _build_options_group(self) -> QGroupBox:
        group = QGroupBox("Options")
        form = QFormLayout(group)

        self._encoding_combo = QComboBox()
        self._encoding_combo.addItems(_ENCODINGS)
        form.addRow("Encoding:", self._encoding_combo)

        return group

    def _build_preview_group(self) -> QGroupBox:
        group = QGroupBox("Preview")
        layout = QVBoxLayout(group)

        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setMaximumHeight(140)
        layout.addWidget(self._preview_text)

        return group

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._browse_btn.clicked.connect(self._on_browse)
        self._file_path_edit.textChanged.connect(self._on_file_path_changed)
        self._download_btn.clicked.connect(self._on_download)
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open M3U Playlist",
            "",
            "M3U Files (*.m3u *.m3u8);;All Files (*)",
        )
        if path:
            self._file_path_edit.setText(path)

    def _on_file_path_changed(self, path: str) -> None:
        if not path:
            self._file_info_label.setText("")
            return
        p = Path(path)
        if not p.is_file():
            self._file_info_label.setText("File not found.")
            self._clear_result()
            return

        size_kb = p.stat().st_size / 1024
        self._file_info_label.setText(f"{p.name}  —  {size_kb:.1f} KB")
        self._parse_file(path)

    def _on_download(self) -> None:
        url = self._url_edit.text().strip()
        if not url:
            return

        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._download_btn.setEnabled(False)

        self._worker = _DownloadWorker(url, self)
        self._worker.progress.connect(self._progress_bar.setValue)
        self._worker.finished.connect(self._on_download_finished)
        self._worker.start()

    def _on_download_finished(self, result: ParseResult | Exception) -> None:
        self._download_btn.setEnabled(True)
        if isinstance(result, Exception):
            self._progress_bar.setVisible(False)
            self._preview_text.setPlainText(f"Download error: {result}")
            self._clear_result()
        else:
            self._apply_result(result)

    def _on_accept(self) -> None:
        if self._result is not None:
            self.import_completed.emit(self._result.playlist, self._result.warnings)
            self.accept()

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_file(self, path: str) -> None:
        encoding = self._selected_encoding()
        try:
            if encoding:
                raw = Path(path).read_bytes()
                content = raw.decode(encoding)
                result = M3UParser().parse(content)
                result.playlist.name = Path(path).stem
            else:
                result = M3UParser().parse_file(path)
            self._apply_result(result)
        except Exception as exc:  # noqa: BLE001
            self._preview_text.setPlainText(f"Parse error: {exc}")
            self._clear_result()

    def _selected_encoding(self) -> str | None:
        text = self._encoding_combo.currentText()
        if text == "Auto-detect":
            return None
        return text

    def _apply_result(self, result: ParseResult) -> None:
        self._result = result
        lines: list[str] = []
        channels = result.playlist.channels[:10]
        for i, ch in enumerate(channels, 1):
            lines.append(f"{i}. {ch.name}  [{ch.group_title or 'No group'}]")

        total = len(result.playlist.channels)
        header = f"Parsed {total} channel(s)"
        if result.warnings:
            header += f" with {len(result.warnings)} warning(s)"
        lines.insert(0, header)
        if result.warnings:
            lines.append("")
            lines.extend(f"⚠ {w}" for w in result.warnings[:5])

        self._preview_text.setPlainText("\n".join(lines))
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def _clear_result(self) -> None:
        self._result = None
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
