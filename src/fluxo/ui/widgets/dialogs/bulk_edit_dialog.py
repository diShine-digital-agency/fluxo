"""Bulk Edit dialog — find-and-replace, bulk move, and bulk assign operations."""

from __future__ import annotations

import logging
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from fluxo.models import Channel, EpgData
from fluxo.services import BulkOperationService

logger = logging.getLogger(__name__)

_SCOPES = ["Name", "Group", "TVG-ID", "All"]
_SCOPE_FIELDS: dict[str, list[str]] = {
    "Name": ["name"],
    "Group": ["group_title"],
    "TVG-ID": ["tvg_id"],
    "All": ["name", "group_title", "tvg_id"],
}


class BulkEditDialog(QDialog):
    """Dialog for performing bulk edits on selected channels."""

    channels_modified = Signal()

    _MIN_WIDTH = 540
    _MIN_HEIGHT = 420

    def __init__(
        self,
        channels: list[Channel],
        available_groups: list[str] | None = None,
        epg_data: EpgData | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bulk Edit Channels")
        self.setMinimumSize(self._MIN_WIDTH, self._MIN_HEIGHT)
        self.resize(self._MIN_WIDTH, self._MIN_HEIGHT)

        self._channels = channels
        self._available_groups = sorted(available_groups or [])
        self._epg_data = epg_data

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        info = QLabel(f"{len(self._channels)} channel(s) selected")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_find_replace_tab(), "Find && Replace")
        self._tabs.addTab(self._build_bulk_move_tab(), "Bulk Move")
        self._tabs.addTab(self._build_bulk_assign_tab(), "Bulk Assign")
        layout.addWidget(self._tabs)

        # Buttons
        self._button_box = QDialogButtonBox()
        self._apply_btn = self._button_box.addButton(
            "Apply", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self._button_box)

    # -- Find & Replace -----------------------------------------------

    def _build_find_replace_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()
        self._find_edit = QLineEdit()
        self._find_edit.setPlaceholderText("Text to find…")
        form.addRow("Find:", self._find_edit)

        self._replace_edit = QLineEdit()
        self._replace_edit.setPlaceholderText("Replacement text…")
        form.addRow("Replace:", self._replace_edit)

        self._regex_check = QCheckBox("Use regular expression")
        form.addRow("", self._regex_check)

        self._scope_combo = QComboBox()
        self._scope_combo.addItems(_SCOPES)
        form.addRow("Scope:", self._scope_combo)
        layout.addLayout(form)

        # Preview
        preview_group = QGroupBox("Match preview")
        preview_layout = QVBoxLayout(preview_group)
        self._fr_preview = QTextEdit()
        self._fr_preview.setReadOnly(True)
        self._fr_preview.setMaximumHeight(120)
        preview_layout.addWidget(self._fr_preview)

        self._preview_btn = QPushButton("Preview matches")
        preview_layout.addWidget(self._preview_btn)
        layout.addWidget(preview_group)

        return tab

    # -- Bulk Move -----------------------------------------------------

    def _build_bulk_move_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()
        self._move_group_combo = QComboBox()
        self._move_group_combo.setEditable(True)
        self._move_group_combo.addItems(self._available_groups)
        form.addRow("Target group:", self._move_group_combo)
        layout.addLayout(form)

        self._move_info = QLabel(
            f"{len(self._channels)} channel(s) will be moved to the selected group."
        )
        self._move_info.setWordWrap(True)
        layout.addWidget(self._move_info)
        layout.addStretch()

        return tab

    # -- Bulk Assign ---------------------------------------------------

    def _build_bulk_assign_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()
        self._logo_edit = QLineEdit()
        self._logo_edit.setPlaceholderText("https://example.com/logo.png")
        form.addRow("Logo URL:", self._logo_edit)

        self._epg_id_edit = QLineEdit()
        self._epg_id_edit.setPlaceholderText("channel.epg.id")
        form.addRow("EPG ID:", self._epg_id_edit)
        layout.addLayout(form)

        self._auto_epg_btn = QPushButton("Auto-assign EPG IDs")
        self._auto_epg_btn.setEnabled(self._epg_data is not None)
        layout.addWidget(self._auto_epg_btn)

        self._assign_info = QLabel("")
        self._assign_info.setWordWrap(True)
        layout.addWidget(self._assign_info)
        layout.addStretch()

        return tab

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._preview_btn.clicked.connect(self._on_preview)
        self._auto_epg_btn.clicked.connect(self._on_auto_epg)
        self._button_box.accepted.connect(self._on_apply)
        self._button_box.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_preview(self) -> None:
        pattern = self._find_edit.text()
        if not pattern:
            self._fr_preview.setPlainText("Enter a search term.")
            return

        use_regex = self._regex_check.isChecked()
        scope_fields = _SCOPE_FIELDS[self._scope_combo.currentText()]

        if use_regex:
            try:
                compiled = re.compile(pattern)
            except re.error as err:
                self._fr_preview.setPlainText(f"Invalid regex: {err}")
                return
        else:
            compiled = None

        matches: list[str] = []
        for ch in self._channels:
            for field_name in scope_fields:
                value = getattr(ch, field_name, "")
                if compiled:
                    if compiled.search(value):
                        matches.append(f"  {ch.name}  →  {field_name}: {value!r}")
                elif pattern.lower() in value.lower():
                    matches.append(f"  {ch.name}  →  {field_name}: {value!r}")

        if matches:
            text = f"{len(matches)} match(es):\n" + "\n".join(matches[:20])
            if len(matches) > 20:
                text += f"\n… and {len(matches) - 20} more"
        else:
            text = "No matches found."
        self._fr_preview.setPlainText(text)

    def _on_auto_epg(self) -> None:
        if self._epg_data is None:
            return

        count = BulkOperationService.bulk_assign_epg_from_data(
            self._channels, self._epg_data
        )
        self._assign_info.setText(f"Auto-assigned EPG IDs to {count} channel(s).")

    def _on_apply(self) -> None:
        current_tab = self._tabs.currentIndex()
        modified = False

        if current_tab == 0:
            modified = self._apply_find_replace()
        elif current_tab == 1:
            modified = self._apply_bulk_move()
        elif current_tab == 2:
            modified = self._apply_bulk_assign()

        if modified:
            self.channels_modified.emit()
        self.accept()

    # ------------------------------------------------------------------
    # Apply helpers
    # ------------------------------------------------------------------

    def _apply_find_replace(self) -> bool:
        find_text = self._find_edit.text()
        replace_text = self._replace_edit.text()
        if not find_text:
            return False

        use_regex = self._regex_check.isChecked()
        scope = self._scope_combo.currentText()
        scope_fields = _SCOPE_FIELDS[scope]

        total = 0
        for field_name in scope_fields:
            if field_name == "name":
                total += BulkOperationService.bulk_rename(
                    self._channels, find_text, replace_text, use_regex=use_regex
                )
            else:
                # Apply find/replace to other fields manually
                for ch in self._channels:
                    old_val = getattr(ch, field_name, "")
                    if use_regex:
                        new_val = re.sub(find_text, replace_text, old_val)
                    else:
                        new_val = old_val.replace(find_text, replace_text)
                    if new_val != old_val:
                        setattr(ch, field_name, new_val)
                        total += 1

        return total > 0

    def _apply_bulk_move(self) -> bool:
        target = self._move_group_combo.currentText().strip()
        if not target:
            return False
        count = BulkOperationService.bulk_move_to_group(self._channels, target)
        return count > 0

    def _apply_bulk_assign(self) -> bool:
        changed = False

        logo_url = self._logo_edit.text().strip()
        if logo_url:
            BulkOperationService.bulk_set_logo(self._channels, logo_url)
            changed = True

        epg_id = self._epg_id_edit.text().strip()
        if epg_id:
            BulkOperationService.bulk_set_epg_id(self._channels, epg_id)
            changed = True

        return changed
