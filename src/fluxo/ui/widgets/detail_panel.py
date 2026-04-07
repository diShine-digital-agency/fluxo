"""Channel detail editor sidebar panel."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from fluxo.models import Channel

# Fields that can be edited when multiple channels are selected
_BULK_FIELDS = {"group", "favorite"}

_LOGO_PREVIEW_SIZE = 48


class DetailPanel(QWidget):
    """Sidebar panel for viewing and editing channel metadata."""

    # Signals
    channel_updated = Signal(object)  # Channel
    channels_bulk_updated = Signal(list)  # list[Channel]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._channel: Channel | None = None
        self._channels: list[Channel] = []
        self._original: dict[str, Any] | None = None

        self._network = QNetworkAccessManager(self)

        # Placeholder label shown when nothing is selected
        self._placeholder = QLabel("No selection")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Scrollable form area
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._form_widget = QWidget()
        self._form_layout = QFormLayout(self._form_widget)
        self._form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        self._scroll.setWidget(self._form_widget)

        # --- form fields ---
        self._name_edit = QLineEdit()
        self._url_edit = QLineEdit()
        self._group_combo = QComboBox()
        self._group_combo.setEditable(True)

        self._tvg_id_edit = QLineEdit()
        self._tvg_name_edit = QLineEdit()
        self._tvg_logo_edit = QLineEdit()
        self._logo_preview = QLabel()
        self._logo_preview.setFixedSize(_LOGO_PREVIEW_SIZE, _LOGO_PREVIEW_SIZE)
        self._logo_preview.setScaledContents(True)

        self._channel_number_spin = QSpinBox()
        self._channel_number_spin.setRange(0, 99999)
        self._channel_number_spin.setSpecialValueText("")

        self._catchup_edit = QLineEdit()
        self._catchup_days_spin = QSpinBox()
        self._catchup_days_spin.setRange(0, 365)
        self._catchup_days_spin.setSpecialValueText("")
        self._catchup_source_edit = QLineEdit()

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("tag1, tag2, …")
        self._favorite_check = QCheckBox("Favorite")

        # Logo row with preview
        logo_layout = QHBoxLayout()
        logo_layout.addWidget(self._tvg_logo_edit)
        logo_layout.addWidget(self._logo_preview)

        self._form_layout.addRow("Name", self._name_edit)
        self._form_layout.addRow("URL", self._url_edit)
        self._form_layout.addRow("Group", self._group_combo)
        self._form_layout.addRow("TVG-ID", self._tvg_id_edit)
        self._form_layout.addRow("TVG-Name", self._tvg_name_edit)
        self._form_layout.addRow("TVG-Logo", logo_layout)
        self._form_layout.addRow("Channel #", self._channel_number_spin)
        self._form_layout.addRow("Catchup", self._catchup_edit)
        self._form_layout.addRow("Catchup Days", self._catchup_days_spin)
        self._form_layout.addRow("Catchup Source", self._catchup_source_edit)
        self._form_layout.addRow("Tags", self._tags_edit)
        self._form_layout.addRow("", self._favorite_check)

        # Buttons
        self._apply_btn = QPushButton("Apply")
        self._revert_btn = QPushButton("Revert")
        self._apply_btn.clicked.connect(self._on_apply)
        self._revert_btn.clicked.connect(self._on_revert)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self._apply_btn)
        btn_layout.addWidget(self._revert_btn)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._placeholder)
        layout.addWidget(self._scroll)
        layout.addLayout(btn_layout)

        # Load logo preview when TVG-Logo field changes
        self._tvg_logo_edit.editingFinished.connect(self._load_logo_preview)

        self._show_placeholder()

    # -- public API --------------------------------------------------------

    def set_channel(self, channel: Channel | None) -> None:
        """Display a single channel for editing, or clear the panel."""
        self._channels = []
        self._channel = channel
        if channel is None:
            self._show_placeholder()
            return
        self._show_form()
        self._enable_all_fields(True)
        self._populate_from_channel(channel)
        self._snapshot_original()

    def set_channels(self, channels: list[Channel]) -> None:
        """Display bulk-edit mode for multiple channels."""
        self._channel = None
        self._channels = list(channels)
        if not channels:
            self._show_placeholder()
            return
        if len(channels) == 1:
            self.set_channel(channels[0])
            return
        self._show_form()
        self._enable_bulk_mode(len(channels))

    def set_available_groups(self, groups: list[str]) -> None:
        """Update the group combo box with available groups."""
        current = self._group_combo.currentText()
        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        self._group_combo.addItem("")  # allow empty / no group
        self._group_combo.addItems(groups)
        self._group_combo.setCurrentText(current)
        self._group_combo.blockSignals(False)

    # -- private helpers ---------------------------------------------------

    def _show_placeholder(self) -> None:
        self._scroll.hide()
        self._apply_btn.hide()
        self._revert_btn.hide()
        self._placeholder.show()

    def _show_form(self) -> None:
        self._placeholder.hide()
        self._scroll.show()
        self._apply_btn.show()
        self._revert_btn.show()

    def _enable_all_fields(self, enabled: bool) -> None:
        """Enable or disable all form fields."""
        for widget in (
            self._name_edit,
            self._url_edit,
            self._group_combo,
            self._tvg_id_edit,
            self._tvg_name_edit,
            self._tvg_logo_edit,
            self._channel_number_spin,
            self._catchup_edit,
            self._catchup_days_spin,
            self._catchup_source_edit,
            self._tags_edit,
            self._favorite_check,
        ):
            widget.setEnabled(enabled)

    def _enable_bulk_mode(self, count: int) -> None:
        """Configure the panel for bulk editing."""
        self._placeholder.setText(f"Multiple selected ({count})")
        self._placeholder.hide()  # still show the form, not placeholder

        # Clear all fields
        self._name_edit.clear()
        self._url_edit.clear()
        self._group_combo.setCurrentText("")
        self._tvg_id_edit.clear()
        self._tvg_name_edit.clear()
        self._tvg_logo_edit.clear()
        self._logo_preview.clear()
        self._channel_number_spin.setValue(0)
        self._catchup_edit.clear()
        self._catchup_days_spin.setValue(0)
        self._catchup_source_edit.clear()
        self._tags_edit.clear()
        self._favorite_check.setChecked(False)

        # Disable non-bulk fields
        self._name_edit.setEnabled(False)
        self._url_edit.setEnabled(False)
        self._tvg_id_edit.setEnabled(False)
        self._tvg_name_edit.setEnabled(False)
        self._tvg_logo_edit.setEnabled(False)
        self._channel_number_spin.setEnabled(False)
        self._catchup_edit.setEnabled(False)
        self._catchup_days_spin.setEnabled(False)
        self._catchup_source_edit.setEnabled(False)
        self._tags_edit.setEnabled(False)

        # Enable bulk-editable fields
        self._group_combo.setEnabled(True)
        self._favorite_check.setEnabled(True)

        self._name_edit.setPlaceholderText(f"({count} channels)")
        self._url_edit.setPlaceholderText(f"({count} channels)")
        self._original = None

    def _populate_from_channel(self, ch: Channel) -> None:
        """Fill form fields from a Channel instance."""
        self._name_edit.setText(ch.name)
        self._name_edit.setPlaceholderText("")
        self._url_edit.setText(ch.url)
        self._url_edit.setPlaceholderText("")
        self._group_combo.setCurrentText(ch.group_title)
        self._tvg_id_edit.setText(ch.tvg_id)
        self._tvg_name_edit.setText(ch.tvg_name)
        self._tvg_logo_edit.setText(ch.tvg_logo)
        ch_num = int(ch.channel_number) if ch.channel_number.isdigit() else 0
        self._channel_number_spin.setValue(ch_num)
        self._catchup_edit.setText(ch.catchup)
        self._catchup_days_spin.setValue(int(ch.catchup_days) if ch.catchup_days.isdigit() else 0)
        self._catchup_source_edit.setText(ch.catchup_source)
        self._tags_edit.setText(", ".join(ch.tags))
        self._favorite_check.setChecked(ch.is_favorite)
        self._load_logo_preview()

    def _snapshot_original(self) -> None:
        """Save current form state for revert."""
        self._original = {
            "name": self._name_edit.text(),
            "url": self._url_edit.text(),
            "group": self._group_combo.currentText(),
            "tvg_id": self._tvg_id_edit.text(),
            "tvg_name": self._tvg_name_edit.text(),
            "tvg_logo": self._tvg_logo_edit.text(),
            "channel_number": self._channel_number_spin.value(),
            "catchup": self._catchup_edit.text(),
            "catchup_days": self._catchup_days_spin.value(),
            "catchup_source": self._catchup_source_edit.text(),
            "tags": self._tags_edit.text(),
            "favorite": self._favorite_check.isChecked(),
        }

    def _load_logo_preview(self) -> None:
        """Attempt to load and show a thumbnail from the TVG-Logo URL."""
        url_text = self._tvg_logo_edit.text().strip()
        self._logo_preview.clear()
        if not url_text:
            return

        from PySide6.QtCore import QUrl

        url = QUrl(url_text)
        if not url.isValid() or url.scheme() not in ("http", "https"):
            return

        request = QNetworkRequest(url)
        reply = self._network.get(request)
        reply.finished.connect(lambda: self._on_logo_loaded(reply))

    def _on_logo_loaded(self, reply: QNetworkReply) -> None:
        """Handle the network reply for logo preview."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self._logo_preview.setPixmap(
                    pixmap.scaled(
                        _LOGO_PREVIEW_SIZE,
                        _LOGO_PREVIEW_SIZE,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        reply.deleteLater()

    # -- slots -------------------------------------------------------------

    def _on_apply(self) -> None:
        """Commit form changes back to the channel(s)."""
        if self._channels and len(self._channels) > 1:
            self._apply_bulk()
            return
        if self._channel is None:
            return
        self._apply_single()

    def _apply_single(self) -> None:
        """Apply form values to the single selected channel."""
        ch = self._channel
        if ch is None:
            return
        ch.name = self._name_edit.text().strip() or ch.name
        ch.url = self._url_edit.text().strip() or ch.url
        ch.group_title = self._group_combo.currentText().strip()
        ch.tvg_id = self._tvg_id_edit.text().strip()
        ch.tvg_name = self._tvg_name_edit.text().strip()
        ch.tvg_logo = self._tvg_logo_edit.text().strip()
        num = self._channel_number_spin.value()
        ch.channel_number = str(num) if num > 0 else ""
        ch.catchup = self._catchup_edit.text().strip()
        days = self._catchup_days_spin.value()
        ch.catchup_days = str(days) if days > 0 else ""
        ch.catchup_source = self._catchup_source_edit.text().strip()
        raw_tags = self._tags_edit.text()
        ch.tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        ch.is_favorite = self._favorite_check.isChecked()

        self._snapshot_original()
        self.channel_updated.emit(ch)

    def _apply_bulk(self) -> None:
        """Apply bulk-editable fields to all selected channels."""
        group = self._group_combo.currentText().strip()
        favorite = self._favorite_check.isChecked()

        updated: list[Channel] = []
        for ch in self._channels:
            changed = False
            if group and ch.group_title != group:
                ch.group_title = group
                changed = True
            if ch.is_favorite != favorite:
                ch.is_favorite = favorite
                changed = True
            if changed:
                updated.append(ch)

        if updated:
            self.channels_bulk_updated.emit(updated)

    def _on_revert(self) -> None:
        """Revert form fields to the last snapshot."""
        if self._original is not None:
            self._name_edit.setText(self._original["name"])
            self._url_edit.setText(self._original["url"])
            self._group_combo.setCurrentText(self._original["group"])
            self._tvg_id_edit.setText(self._original["tvg_id"])
            self._tvg_name_edit.setText(self._original["tvg_name"])
            self._tvg_logo_edit.setText(self._original["tvg_logo"])
            self._channel_number_spin.setValue(self._original["channel_number"])
            self._catchup_edit.setText(self._original["catchup"])
            self._catchup_days_spin.setValue(self._original["catchup_days"])
            self._catchup_source_edit.setText(self._original["catchup_source"])
            self._tags_edit.setText(self._original["tags"])
            self._favorite_check.setChecked(self._original["favorite"])
        elif self._channel is not None:
            self._populate_from_channel(self._channel)
