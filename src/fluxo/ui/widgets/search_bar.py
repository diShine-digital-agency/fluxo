"""Search and filter toolbar for the channel table."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

_DEBOUNCE_MS = 300

_ALL_GROUPS = "All Groups"
_ALL_HEALTH = "All Statuses"
_HEALTH_OPTIONS = ("All Statuses", "Alive", "Dead", "Timeout", "Unknown")


class SearchBar(QWidget):
    """Toolbar with search input and group/health filter dropdowns."""

    # Signals
    search_changed = Signal(str)
    group_filter_changed = Signal(object)  # str | None
    health_filter_changed = Signal(object)  # str | None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Search input
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search channels…")
        self._search.setClearButtonEnabled(True)

        # Debounce timer
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._emit_search)
        self._search.textChanged.connect(self._on_text_changed)

        # Group filter
        self._group_filter = QComboBox(self)
        self._group_filter.addItem(_ALL_GROUPS)
        self._group_filter.currentTextChanged.connect(self._on_group_changed)

        # Health filter
        self._health_filter = QComboBox(self)
        for opt in _HEALTH_OPTIONS:
            self._health_filter.addItem(opt)
        self._health_filter.currentTextChanged.connect(self._on_health_changed)

        # Clear button
        self._clear_btn = QPushButton("Clear Filters", self)
        self._clear_btn.clicked.connect(self.clear_filters)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._search, stretch=2)
        layout.addWidget(self._group_filter, stretch=1)
        layout.addWidget(self._health_filter, stretch=1)
        layout.addWidget(self._clear_btn)

    # -- public API --------------------------------------------------------

    def update_groups(self, groups: list[str]) -> None:
        """Refresh the group filter dropdown items."""
        current = self._group_filter.currentText()
        self._group_filter.blockSignals(True)
        self._group_filter.clear()
        self._group_filter.addItem(_ALL_GROUPS)
        for g in groups:
            self._group_filter.addItem(g)
        # Restore selection if still valid
        idx = self._group_filter.findText(current)
        self._group_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self._group_filter.blockSignals(False)

    def clear_filters(self) -> None:
        """Reset all filters to their defaults."""
        self._search.clear()
        self._group_filter.setCurrentIndex(0)
        self._health_filter.setCurrentIndex(0)

    # -- private -----------------------------------------------------------

    def _on_text_changed(self, _text: str) -> None:
        self._debounce.start()

    def _emit_search(self) -> None:
        self.search_changed.emit(self._search.text())

    def _on_group_changed(self, text: str) -> None:
        self.group_filter_changed.emit(None if text == _ALL_GROUPS else text)

    def _on_health_changed(self, text: str) -> None:
        self.health_filter_changed.emit(None if text == _ALL_HEALTH else text.lower())
