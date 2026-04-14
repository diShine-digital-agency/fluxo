"""Settings dialog — application-wide preferences."""

from __future__ import annotations

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

_THEMES = ["Dark", "Light"]
_ENCODINGS = ["UTF-8", "Latin-1", "Windows-1252", "ISO-8859-1", "ASCII"]


class SettingsDialog(QDialog):
    """Application settings dialog."""

    settings_applied = Signal(dict)

    _MIN_WIDTH = 400
    _MIN_HEIGHT = 320

    def __init__(
        self,
        current_settings: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(self._MIN_WIDTH, self._MIN_HEIGHT)
        self.resize(self._MIN_WIDTH, self._MIN_HEIGHT)

        self._settings = current_settings or {}

        self._build_ui()
        self._load_current()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(self._build_appearance_group())
        layout.addWidget(self._build_general_group())
        layout.addWidget(self._build_stream_group())
        layout.addStretch()

        # Buttons: OK / Cancel / Apply
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        layout.addWidget(self._button_box)

    def _build_appearance_group(self) -> QGroupBox:
        group = QGroupBox("Appearance")
        form = QFormLayout(group)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(_THEMES)
        form.addRow("Theme:", self._theme_combo)

        return group

    def _build_general_group(self) -> QGroupBox:
        group = QGroupBox("General")
        form = QFormLayout(group)

        self._autosave_check = QCheckBox("Enable autosave")
        form.addRow("", self._autosave_check)

        self._autosave_interval_spin = QSpinBox()
        self._autosave_interval_spin.setRange(1, 60)
        self._autosave_interval_spin.setSuffix(" min")
        self._autosave_interval_spin.setValue(5)
        form.addRow("Autosave interval:", self._autosave_interval_spin)

        self._encoding_combo = QComboBox()
        self._encoding_combo.addItems(_ENCODINGS)
        form.addRow("Default encoding:", self._encoding_combo)

        return group

    def _build_stream_group(self) -> QGroupBox:
        group = QGroupBox("Stream Checking")
        form = QFormLayout(group)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 60)
        self._timeout_spin.setSuffix(" s")
        self._timeout_spin.setValue(5)
        form.addRow("Check timeout:", self._timeout_spin)

        return group

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._autosave_check.toggled.connect(self._on_autosave_toggled)
        self._button_box.accepted.connect(self._on_ok)
        self._button_box.rejected.connect(self.reject)
        apply_btn = self._button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_btn:
            apply_btn.clicked.connect(self._on_apply)

    # ------------------------------------------------------------------
    # Load / collect
    # ------------------------------------------------------------------

    def _load_current(self) -> None:
        theme = self._settings.get("theme", "dark")
        idx = next((i for i, t in enumerate(_THEMES) if t.lower() == theme.lower()), 0)
        self._theme_combo.setCurrentIndex(idx)

        self._autosave_check.setChecked(self._settings.get("autosave_enabled", True))
        self._autosave_interval_spin.setValue(self._settings.get("autosave_interval", 5))
        self._autosave_interval_spin.setEnabled(self._autosave_check.isChecked())

        encoding = self._settings.get("default_encoding", "UTF-8")
        enc_idx = next((i for i, e in enumerate(_ENCODINGS) if e == encoding), 0)
        self._encoding_combo.setCurrentIndex(enc_idx)

        self._timeout_spin.setValue(self._settings.get("stream_check_timeout", 5))

    def _collect_settings(self) -> dict:
        return {
            "theme": self._theme_combo.currentText().lower(),
            "autosave_enabled": self._autosave_check.isChecked(),
            "autosave_interval": self._autosave_interval_spin.value(),
            "default_encoding": self._encoding_combo.currentText(),
            "stream_check_timeout": self._timeout_spin.value(),
        }

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_autosave_toggled(self, checked: bool) -> None:
        self._autosave_interval_spin.setEnabled(checked)

    def _on_ok(self) -> None:
        self.settings_applied.emit(self._collect_settings())
        self.accept()

    def _on_apply(self) -> None:
        self.settings_applied.emit(self._collect_settings())
