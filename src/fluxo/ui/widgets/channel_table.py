"""Channel table widget using Qt Model/View architecture."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from PySide6.QtCore import (
    QAbstractTableModel,
    QMimeData,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QAction, QColor, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from fluxo.models import Channel, HealthStatus, Playlist

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COLUMNS = ("#", "Name", "Group", "TVG-ID", "URL", "Health")
_COL_ROW = 0
_COL_NAME = 1
_COL_GROUP = 2
_COL_TVG_ID = 3
_COL_URL = 4
_COL_HEALTH = 5

_EDITABLE_COLUMNS = {_COL_NAME, _COL_GROUP, _COL_TVG_ID}

MIME_TYPE = "application/x-fluxo-channel-rows"

# Health-status colours (Catppuccin palette)
_HEALTH_COLORS: dict[HealthStatus, QColor] = {
    HealthStatus.ALIVE: QColor("#a6e3a1"),  # green
    HealthStatus.DEAD: QColor("#f38ba8"),  # red
    HealthStatus.TIMEOUT: QColor("#f9e2af"),  # yellow
    HealthStatus.UNKNOWN: QColor("#6c7086"),  # overlay0 / gray
}

_DOT_SIZE = 12


def _health_dot(status: HealthStatus) -> QPixmap:
    """Return a small coloured circle pixmap for *status*."""
    pixmap = QPixmap(_DOT_SIZE, _DOT_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    from PySide6.QtGui import QPainter

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(_HEALTH_COLORS[status])
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, _DOT_SIZE - 2, _DOT_SIZE - 2)
    painter.end()
    return pixmap


# ---------------------------------------------------------------------------
# Table model
# ---------------------------------------------------------------------------


class ChannelTableModel(QAbstractTableModel):
    """Qt table model backed by a :class:`Playlist`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._playlist: Playlist = Playlist()

    # -- public API --------------------------------------------------------

    @property
    def playlist(self) -> Playlist:
        return self._playlist

    def set_playlist(self, playlist: Playlist) -> None:
        """Replace the underlying playlist and reset the view."""
        self.beginResetModel()
        self._playlist = playlist
        self.endResetModel()

    def channel_at(self, row: int) -> Channel | None:
        """Return the channel at *row*, or ``None`` if out of range."""
        if 0 <= row < len(self._playlist.channels):
            return self._playlist.channels[row]
        return None

    def row_of(self, channel: Channel) -> int | None:
        """Return the row index of *channel*, or ``None``."""
        for i, ch in enumerate(self._playlist.channels):
            if ch.id == channel.id:
                return i
        return None

    def remove_rows_by_ids(self, ids: set[UUID]) -> list[Channel]:
        """Remove channels by their IDs and return the removed list."""
        rows = sorted(
            (i for i, ch in enumerate(self._playlist.channels) if ch.id in ids),
            reverse=True,
        )
        removed: list[Channel] = []
        for row in rows:
            self.beginRemoveRows(QModelIndex(), row, row)
            removed.append(self._playlist.channels.pop(row))
            self.endRemoveRows()
        self._playlist._touch()
        return removed

    def move_rows(self, source_rows: list[int], dest_row: int) -> None:
        """Move *source_rows* so they end up contiguously at *dest_row*."""
        source_rows = sorted(source_rows)
        channels = [self._playlist.channels[r] for r in source_rows]

        # Remove from bottom-up to keep indices stable
        for r in reversed(source_rows):
            self.beginRemoveRows(QModelIndex(), r, r)
            self._playlist.channels.pop(r)
            self.endRemoveRows()

        # Adjust destination for removed rows above it
        adjusted = dest_row - sum(1 for r in source_rows if r < dest_row)
        adjusted = max(0, min(adjusted, len(self._playlist.channels)))

        for offset, ch in enumerate(channels):
            insert_at = adjusted + offset
            self.beginInsertRows(QModelIndex(), insert_at, insert_at)
            self._playlist.channels.insert(insert_at, ch)
            self.endInsertRows()

        self._playlist._touch()

    # -- QAbstractTableModel overrides -------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._playlist.channels)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(_COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row < 0 or row >= len(self._playlist.channels):
            return None
        channel = self._playlist.channels[row]

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_data(row, col, channel)
        if role == Qt.ItemDataRole.EditRole:
            return self._edit_data(col, channel)
        if role == Qt.ItemDataRole.DecorationRole and col == _COL_HEALTH:
            return _health_dot(channel.health_status)
        if role == Qt.ItemDataRole.BackgroundRole:
            if channel.health_status == HealthStatus.DEAD:
                c = QColor(_HEALTH_COLORS[HealthStatus.DEAD])
                c.setAlpha(30)
                return c
        if role == Qt.ItemDataRole.ToolTipRole and col == _COL_HEALTH:
            return channel.health_status.value.capitalize()
        return None

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal and 0 <= section < len(_COLUMNS):
                return _COLUMNS[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        base = super().flags(index)
        if not index.isValid():
            return base | Qt.ItemFlag.ItemIsDropEnabled

        base |= Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        if index.column() in _EDITABLE_COLUMNS:
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def setData(  # noqa: N802
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        row, col = index.row(), index.column()
        if row < 0 or row >= len(self._playlist.channels):
            return False

        channel = self._playlist.channels[row]
        text = str(value).strip()
        changed = False

        if col == _COL_NAME and text and text != channel.name:
            channel.name = text
            changed = True
        elif col == _COL_GROUP and text != channel.group_title:
            channel.group_title = text
            changed = True
        elif col == _COL_TVG_ID and text != channel.tvg_id:
            channel.tvg_id = text
            changed = True

        if changed:
            self._playlist._touch()
            self.dataChanged.emit(index, index, [role])
        return changed

    # -- Drag & drop -------------------------------------------------------

    def supportedDropActions(self) -> Qt.DropAction:  # noqa: N802
        return Qt.DropAction.MoveAction

    def supportedDragActions(self) -> Qt.DropAction:  # noqa: N802
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:  # noqa: N802
        return [MIME_TYPE]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:  # noqa: N802
        rows = sorted({idx.row() for idx in indexes if idx.isValid()})
        mime = QMimeData()
        mime.setData(MIME_TYPE, json.dumps(rows).encode())
        return mime

    def canDropMimeData(  # noqa: N802
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        return data.hasFormat(MIME_TYPE)

    def dropMimeData(  # noqa: N802
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if not data.hasFormat(MIME_TYPE):
            return False
        source_rows: list[int] = json.loads(bytes(data.data(MIME_TYPE)).decode())
        dest = row if row >= 0 else self.rowCount()
        self.move_rows(source_rows, dest)
        return True

    # -- private helpers ---------------------------------------------------

    @staticmethod
    def _display_data(row: int, col: int, channel: Channel) -> str | None:
        if col == _COL_ROW:
            return str(row + 1)
        if col == _COL_NAME:
            return channel.name
        if col == _COL_GROUP:
            return channel.group_title
        if col == _COL_TVG_ID:
            return channel.tvg_id
        if col == _COL_URL:
            return channel.url
        if col == _COL_HEALTH:
            return channel.health_status.value.capitalize()
        return None

    @staticmethod
    def _edit_data(col: int, channel: Channel) -> str | None:
        if col == _COL_NAME:
            return channel.name
        if col == _COL_GROUP:
            return channel.group_title
        if col == _COL_TVG_ID:
            return channel.tvg_id
        return None


# ---------------------------------------------------------------------------
# Filter proxy model
# ---------------------------------------------------------------------------


class ChannelFilterProxyModel(QSortFilterProxyModel):
    """Proxy that filters channels by a search string."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(-1)  # search all columns

    def set_filter_text(self, text: str) -> None:
        """Apply a simple substring filter across all columns."""
        self.setFilterFixedString(text)


# ---------------------------------------------------------------------------
# Channel table widget
# ---------------------------------------------------------------------------


class ChannelTableWidget(QWidget):
    """Top-level widget containing the channel table view, model, and proxy."""

    # Signals
    selection_changed = Signal(list)  # list[Channel]
    channel_double_clicked = Signal(object)  # Channel
    context_menu_requested = Signal(list, object)  # list[Channel], QPoint

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Models
        self._model = ChannelTableModel(self)
        self._proxy = ChannelFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.ItemDataRole.DisplayRole)

        # View
        self._view = QTableView(self)
        self._view.setModel(self._proxy)
        self._configure_view()

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        # Connections
        self._view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._view.doubleClicked.connect(self._on_double_clicked)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._on_context_menu)

    # -- public API --------------------------------------------------------

    @property
    def model(self) -> ChannelTableModel:
        return self._model

    @property
    def proxy(self) -> ChannelFilterProxyModel:
        return self._proxy

    @property
    def view(self) -> QTableView:
        return self._view

    def set_playlist(self, playlist: Playlist) -> None:
        """Load a new playlist into the table."""
        self._model.set_playlist(playlist)
        self._resize_columns()

    def get_selected_channels(self) -> list[Channel]:
        """Return the list of currently selected channels."""
        rows = self._selected_source_rows()
        return [
            ch
            for r in rows
            if (ch := self._model.channel_at(r)) is not None
        ]

    def select_all(self) -> None:
        """Select all visible rows."""
        self._view.selectAll()

    def deselect_all(self) -> None:
        """Clear the selection."""
        self._view.clearSelection()

    def scroll_to_channel(self, channel: Channel) -> None:
        """Scroll the view so that *channel* is visible."""
        source_row = self._model.row_of(channel)
        if source_row is None:
            return
        source_index = self._model.index(source_row, 0)
        proxy_index = self._proxy.mapFromSource(source_index)
        if proxy_index.isValid():
            self._view.scrollTo(proxy_index, QAbstractItemView.ScrollHint.PositionAtCenter)

    def set_filter(self, text: str) -> None:
        """Filter visible channels by *text*."""
        self._proxy.set_filter_text(text)

    # -- event handling ----------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Delete:
            selected = self.get_selected_channels()
            if selected:
                ids = {ch.id for ch in selected}
                self._model.remove_rows_by_ids(ids)
                return
        super().keyPressEvent(event)

    # -- private -----------------------------------------------------------

    def _configure_view(self) -> None:
        view = self._view
        view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setSortingEnabled(True)
        view.setAlternatingRowColors(True)
        view.setShowGrid(False)
        view.verticalHeader().setVisible(False)
        view.horizontalHeader().setStretchLastSection(True)
        view.horizontalHeader().setSectionsMovable(True)
        view.horizontalHeader().setSortIndicatorShown(True)

        # Drag & drop
        view.setDragEnabled(True)
        view.setAcceptDrops(True)
        view.setDropIndicatorShown(True)
        view.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        view.setDefaultDropAction(Qt.DropAction.MoveAction)

    def _resize_columns(self) -> None:
        header = self._view.horizontalHeader()
        header.resizeSection(_COL_ROW, 50)
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(_COL_GROUP, 150)
        header.resizeSection(_COL_TVG_ID, 120)
        header.resizeSection(_COL_URL, 250)
        header.resizeSection(_COL_HEALTH, 80)

    def _selected_source_rows(self) -> list[int]:
        """Return sorted source-model row indices for the current selection."""
        proxy_indexes = self._view.selectionModel().selectedRows()
        return sorted(self._proxy.mapToSource(idx).row() for idx in proxy_indexes)

    # -- slots -------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        self.selection_changed.emit(self.get_selected_channels())

    def _on_double_clicked(self, proxy_index: QModelIndex) -> None:
        source_index = self._proxy.mapToSource(proxy_index)
        channel = self._model.channel_at(source_index.row())
        if channel is not None:
            self.channel_double_clicked.emit(channel)

    def _on_context_menu(self, pos: object) -> None:
        selected = self.get_selected_channels()
        if not selected:
            return

        menu = QMenu(self)

        edit_action = QAction("Edit", self)
        delete_action = QAction("Delete", self)
        move_group_action = QAction("Move to Group…", self)
        check_stream_action = QAction("Check Stream", self)
        copy_url_action = QAction("Copy URL", self)
        duplicate_action = QAction("Duplicate", self)

        menu.addAction(edit_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(move_group_action)
        menu.addAction(check_stream_action)
        menu.addSeparator()
        menu.addAction(copy_url_action)
        menu.addAction(duplicate_action)

        # Let upstream consumers connect to the signal for custom handling
        global_pos = self._view.viewport().mapToGlobal(pos)
        self.context_menu_requested.emit(selected, global_pos)

        # Built-in actions
        copy_url_action.triggered.connect(lambda: self._copy_urls(selected))
        delete_action.triggered.connect(
            lambda: self._model.remove_rows_by_ids({ch.id for ch in selected})
        )
        duplicate_action.triggered.connect(lambda: self._duplicate_channels(selected))

        menu.exec(global_pos)

    def _copy_urls(self, channels: list[Channel]) -> None:
        from PySide6.QtWidgets import QApplication

        urls = "\n".join(ch.url for ch in channels)
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(urls)

    def _duplicate_channels(self, channels: list[Channel]) -> None:
        for ch in channels:
            source_row = self._model.row_of(ch)
            if source_row is None:
                continue
            clone = ch.clone()
            insert_at = source_row + 1
            self._model.beginInsertRows(QModelIndex(), insert_at, insert_at)
            self._model.playlist.channels.insert(insert_at, clone)
            self._model.endInsertRows()
        self._model.playlist._touch()
