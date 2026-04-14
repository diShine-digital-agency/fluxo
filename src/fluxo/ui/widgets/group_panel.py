"""Group/category sidebar panel for filtering channels by group."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fluxo.models import HealthStatus, Playlist

# Badge colours (Catppuccin palette)
_WARN_COLOR = QColor("#f9e2af")  # yellow
_DOT_SIZE = 10

_ALL_CHANNELS = "All Channels"


def _warning_badge() -> QPixmap:
    """Return a small warning-dot pixmap for groups with health issues."""
    from PySide6.QtGui import QPainter

    pixmap = QPixmap(_DOT_SIZE, _DOT_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(_WARN_COLOR)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, _DOT_SIZE - 2, _DOT_SIZE - 2)
    painter.end()
    return pixmap


class GroupPanel(QWidget):
    """Sidebar panel listing playlist groups with channel counts."""

    # Signals
    group_selected = Signal(object)  # str | None
    group_renamed = Signal(str, str)  # old_name, new_name
    group_deleted = Signal(str)  # group_name

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._playlist: Playlist = Playlist()

        self._list = QListWidget(self)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.currentItemChanged.connect(self._on_item_changed)

        self._add_btn = QPushButton("Add Group", self)
        self._add_btn.clicked.connect(self._on_add_group)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self._add_btn)
        layout.addLayout(btn_layout)

    # -- public API --------------------------------------------------------

    def update_groups(self, playlist: Playlist) -> None:
        """Refresh the group list from *playlist*."""
        self._playlist = playlist
        current_text = self._selected_group_name()

        self._list.blockSignals(True)
        self._list.clear()

        # "All Channels" entry
        all_item = QListWidgetItem(f"{_ALL_CHANNELS} ({playlist.channel_count})")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self._list.addItem(all_item)

        group_counts = playlist.group_counts
        groups_with_issues = self._groups_with_health_issues()
        badge = _warning_badge() if groups_with_issues else None

        for group in playlist.groups:
            count = group_counts.get(group, 0)
            item = QListWidgetItem(f"{group} ({count})")
            item.setData(Qt.ItemDataRole.UserRole, group)
            if badge and group in groups_with_issues:
                item.setIcon(badge)
            self._list.addItem(item)

        # Restore previous selection
        self._select_group(current_text)
        self._list.blockSignals(False)

    # -- private helpers ---------------------------------------------------

    def _groups_with_health_issues(self) -> set[str]:
        """Return group names that contain at least one DEAD or TIMEOUT channel."""
        bad = set()
        for ch in self._playlist.channels:
            if ch.health_status in (HealthStatus.DEAD, HealthStatus.TIMEOUT):
                if ch.group_title:
                    bad.add(ch.group_title)
        return bad

    def _selected_group_name(self) -> str | None:
        """Return the currently-selected group name (None for 'All')."""
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _select_group(self, group: str | None) -> None:
        """Select the list item matching *group*."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == group:
                self._list.setCurrentItem(item)
                return
        # Default to "All Channels"
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    # -- slots -------------------------------------------------------------

    def _on_item_changed(
        self,
        current: QListWidgetItem | None,
        _prev: QListWidgetItem | None,
    ) -> None:
        if current is None:
            return
        group = current.data(Qt.ItemDataRole.UserRole)
        self.group_selected.emit(group)

    def _on_context_menu(self, pos: object) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        group = item.data(Qt.ItemDataRole.UserRole)
        if group is None:
            return  # no context menu for "All Channels"

        menu = QMenu(self)

        rename_action = QAction("Rename Group", self)
        delete_action = QAction("Delete Group", self)
        merge_action = QAction("Merge with Another Group…", self)

        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(merge_action)

        rename_action.triggered.connect(lambda: self._rename_group(group))
        delete_action.triggered.connect(lambda: self._delete_group(group))
        merge_action.triggered.connect(lambda: self._merge_group(group))

        menu.exec(self._list.viewport().mapToGlobal(pos))

    def _on_add_group(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Group", "Group name:")
        if ok and name.strip():
            name = name.strip()
            # Emit rename signal with empty old_name to indicate a new group
            self.group_renamed.emit("", name)

    def _rename_group(self, old_name: str) -> None:
        new_name, ok = QInputDialog.getText(self, "Rename Group", "New name:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            self.group_renamed.emit(old_name, new_name.strip())

    def _delete_group(self, group: str) -> None:
        self.group_deleted.emit(group)

    def _merge_group(self, source_group: str) -> None:
        other_groups = [g for g in self._playlist.groups if g != source_group]
        if not other_groups:
            return
        target, ok = QInputDialog.getItem(
            self,
            "Merge Group",
            f'Merge "{source_group}" into:',
            other_groups,
            editable=False,
        )
        if ok and target:
            self.group_renamed.emit(source_group, target)
