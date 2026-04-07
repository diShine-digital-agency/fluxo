"""Theme manager for the Fluxo application."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication


class ThemeManager:
    """Manages dark and light application themes via Qt stylesheets."""

    DARK_STYLE: str = """
    /* ── Base ─────────────────────────────────────────────────── */
    QMainWindow, QDialog {
        background-color: #1e1e2e;
        color: #cdd6f4;
    }

    QWidget {
        background-color: #1e1e2e;
        color: #cdd6f4;
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }

    /* ── Labels ────────────────────────────────────────────────── */
    QLabel {
        background-color: transparent;
        color: #cdd6f4;
        padding: 1px;
    }

    /* ── Table / Tree views ────────────────────────────────────── */
    QTableView, QTreeWidget {
        background-color: #1e1e2e;
        alternate-background-color: #262637;
        color: #cdd6f4;
        border: 1px solid #585b70;
        border-radius: 4px;
        gridline-color: #45475a;
        selection-background-color: #45475a;
        selection-color: #cdd6f4;
        outline: none;
    }

    QTableView::item:hover, QTreeWidget::item:hover {
        background-color: #313244;
    }

    QTableView::item:selected, QTreeWidget::item:selected {
        background-color: #45475a;
        color: #cdd6f4;
    }

    QHeaderView {
        background-color: #2d2d3f;
        border: none;
    }

    QHeaderView::section {
        background-color: #2d2d3f;
        color: #bac2de;
        border: none;
        border-right: 1px solid #45475a;
        border-bottom: 1px solid #45475a;
        padding: 6px 8px;
        font-weight: bold;
    }

    QHeaderView::section:hover {
        background-color: #45475a;
    }

    /* ── Buttons ───────────────────────────────────────────────── */
    QPushButton {
        background-color: #2d2d3f;
        color: #cdd6f4;
        border: 1px solid #585b70;
        border-radius: 6px;
        padding: 6px 16px;
        min-height: 20px;
    }

    QPushButton:hover {
        background-color: #45475a;
        border-color: #89b4fa;
    }

    QPushButton:pressed {
        background-color: #585b70;
    }

    QPushButton:disabled {
        background-color: #262637;
        color: #6c7086;
        border-color: #45475a;
    }

    QPushButton:focus {
        border-color: #89b4fa;
        outline: none;
    }

    /* ── Line edits / inputs ──────────────────────────────────── */
    QLineEdit {
        background-color: #2d2d3f;
        color: #cdd6f4;
        border: 1px solid #585b70;
        border-radius: 6px;
        padding: 6px 10px;
        selection-background-color: #45475a;
        selection-color: #cdd6f4;
    }

    QLineEdit:focus {
        border-color: #89b4fa;
    }

    QLineEdit:disabled {
        background-color: #262637;
        color: #6c7086;
    }

    /* ── Combo boxes ──────────────────────────────────────────── */
    QComboBox {
        background-color: #2d2d3f;
        color: #cdd6f4;
        border: 1px solid #585b70;
        border-radius: 6px;
        padding: 6px 10px;
        min-height: 20px;
    }

    QComboBox:hover {
        border-color: #89b4fa;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }

    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #cdd6f4;
        margin-right: 8px;
    }

    QComboBox QAbstractItemView {
        background-color: #2d2d3f;
        color: #cdd6f4;
        border: 1px solid #585b70;
        selection-background-color: #45475a;
        selection-color: #cdd6f4;
        outline: none;
    }

    /* ── Menu bar ─────────────────────────────────────────────── */
    QMenuBar {
        background-color: #2d2d3f;
        color: #cdd6f4;
        border-bottom: 1px solid #45475a;
        padding: 2px;
    }

    QMenuBar::item {
        background-color: transparent;
        padding: 6px 12px;
        border-radius: 4px;
    }

    QMenuBar::item:selected {
        background-color: #45475a;
    }

    /* ── Menus ────────────────────────────────────────────────── */
    QMenu {
        background-color: #2d2d3f;
        color: #cdd6f4;
        border: 1px solid #585b70;
        border-radius: 8px;
        padding: 4px;
    }

    QMenu::item {
        padding: 6px 28px 6px 12px;
        border-radius: 4px;
    }

    QMenu::item:selected {
        background-color: #45475a;
    }

    QMenu::separator {
        height: 1px;
        background-color: #45475a;
        margin: 4px 8px;
    }

    QMenu::item:disabled {
        color: #6c7086;
    }

    /* ── Toolbar ──────────────────────────────────────────────── */
    QToolBar {
        background-color: #2d2d3f;
        border-bottom: 1px solid #45475a;
        padding: 3px;
        spacing: 4px;
    }

    QToolBar::separator {
        width: 1px;
        background-color: #45475a;
        margin: 4px 6px;
    }

    QToolButton {
        background-color: transparent;
        color: #cdd6f4;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 5px;
    }

    QToolButton:hover {
        background-color: #45475a;
        border-color: #585b70;
    }

    QToolButton:pressed {
        background-color: #585b70;
    }

    /* ── Splitter ─────────────────────────────────────────────── */
    QSplitter::handle {
        background-color: #45475a;
    }

    QSplitter::handle:horizontal {
        width: 2px;
    }

    QSplitter::handle:vertical {
        height: 2px;
    }

    QSplitter::handle:hover {
        background-color: #89b4fa;
    }

    /* ── Scroll bars ──────────────────────────────────────────── */
    QScrollBar:vertical {
        background-color: #1e1e2e;
        width: 10px;
        margin: 0;
        border: none;
    }

    QScrollBar::handle:vertical {
        background-color: #45475a;
        min-height: 30px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #585b70;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }

    QScrollBar:horizontal {
        background-color: #1e1e2e;
        height: 10px;
        margin: 0;
        border: none;
    }

    QScrollBar::handle:horizontal {
        background-color: #45475a;
        min-width: 30px;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #585b70;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }

    /* ── Group box ────────────────────────────────────────────── */
    QGroupBox {
        background-color: #2d2d3f;
        border: 1px solid #585b70;
        border-radius: 8px;
        margin-top: 14px;
        padding: 16px 8px 8px 8px;
        font-weight: bold;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 10px;
        color: #89b4fa;
    }

    /* ── Tabs ─────────────────────────────────────────────────── */
    QTabWidget::pane {
        background-color: #1e1e2e;
        border: 1px solid #585b70;
        border-radius: 4px;
        top: -1px;
    }

    QTabBar::tab {
        background-color: #2d2d3f;
        color: #bac2de;
        border: 1px solid #585b70;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 16px;
        margin-right: 2px;
    }

    QTabBar::tab:selected {
        background-color: #1e1e2e;
        color: #cdd6f4;
        border-bottom: 2px solid #89b4fa;
    }

    QTabBar::tab:hover:!selected {
        background-color: #45475a;
    }

    /* ── Status bar ───────────────────────────────────────────── */
    QStatusBar {
        background-color: #2d2d3f;
        color: #bac2de;
        border-top: 1px solid #45475a;
        padding: 2px;
    }

    QStatusBar::item {
        border: none;
    }
    """

    LIGHT_STYLE: str = """
    /* ── Base ─────────────────────────────────────────────────── */
    QMainWindow, QDialog {
        background-color: #ffffff;
        color: #1e1e2e;
    }

    QWidget {
        background-color: #ffffff;
        color: #1e1e2e;
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }

    /* ── Labels ────────────────────────────────────────────────── */
    QLabel {
        background-color: transparent;
        color: #1e1e2e;
        padding: 1px;
    }

    /* ── Table / Tree views ────────────────────────────────────── */
    QTableView, QTreeWidget {
        background-color: #ffffff;
        alternate-background-color: #f5f5f9;
        color: #1e1e2e;
        border: 1px solid #d0d0d8;
        border-radius: 4px;
        gridline-color: #e0e0e6;
        selection-background-color: #cce5ff;
        selection-color: #1e1e2e;
        outline: none;
    }

    QTableView::item:hover, QTreeWidget::item:hover {
        background-color: #eef2f8;
    }

    QTableView::item:selected, QTreeWidget::item:selected {
        background-color: #cce5ff;
        color: #1e1e2e;
    }

    QHeaderView {
        background-color: #f0f0f5;
        border: none;
    }

    QHeaderView::section {
        background-color: #f0f0f5;
        color: #444466;
        border: none;
        border-right: 1px solid #d0d0d8;
        border-bottom: 1px solid #d0d0d8;
        padding: 6px 8px;
        font-weight: bold;
    }

    QHeaderView::section:hover {
        background-color: #e0e0ea;
    }

    /* ── Buttons ───────────────────────────────────────────────── */
    QPushButton {
        background-color: #f0f0f5;
        color: #1e1e2e;
        border: 1px solid #d0d0d8;
        border-radius: 6px;
        padding: 6px 16px;
        min-height: 20px;
    }

    QPushButton:hover {
        background-color: #e0e0ea;
        border-color: #3574e0;
    }

    QPushButton:pressed {
        background-color: #d0d0d8;
    }

    QPushButton:disabled {
        background-color: #f5f5f9;
        color: #a0a0b0;
        border-color: #e0e0e6;
    }

    QPushButton:focus {
        border-color: #3574e0;
        outline: none;
    }

    /* ── Line edits / inputs ──────────────────────────────────── */
    QLineEdit {
        background-color: #ffffff;
        color: #1e1e2e;
        border: 1px solid #d0d0d8;
        border-radius: 6px;
        padding: 6px 10px;
        selection-background-color: #cce5ff;
        selection-color: #1e1e2e;
    }

    QLineEdit:focus {
        border-color: #3574e0;
    }

    QLineEdit:disabled {
        background-color: #f5f5f9;
        color: #a0a0b0;
    }

    /* ── Combo boxes ──────────────────────────────────────────── */
    QComboBox {
        background-color: #ffffff;
        color: #1e1e2e;
        border: 1px solid #d0d0d8;
        border-radius: 6px;
        padding: 6px 10px;
        min-height: 20px;
    }

    QComboBox:hover {
        border-color: #3574e0;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }

    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #444466;
        margin-right: 8px;
    }

    QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #1e1e2e;
        border: 1px solid #d0d0d8;
        selection-background-color: #cce5ff;
        selection-color: #1e1e2e;
        outline: none;
    }

    /* ── Menu bar ─────────────────────────────────────────────── */
    QMenuBar {
        background-color: #f0f0f5;
        color: #1e1e2e;
        border-bottom: 1px solid #d0d0d8;
        padding: 2px;
    }

    QMenuBar::item {
        background-color: transparent;
        padding: 6px 12px;
        border-radius: 4px;
    }

    QMenuBar::item:selected {
        background-color: #e0e0ea;
    }

    /* ── Menus ────────────────────────────────────────────────── */
    QMenu {
        background-color: #ffffff;
        color: #1e1e2e;
        border: 1px solid #d0d0d8;
        border-radius: 8px;
        padding: 4px;
    }

    QMenu::item {
        padding: 6px 28px 6px 12px;
        border-radius: 4px;
    }

    QMenu::item:selected {
        background-color: #cce5ff;
    }

    QMenu::separator {
        height: 1px;
        background-color: #e0e0e6;
        margin: 4px 8px;
    }

    QMenu::item:disabled {
        color: #a0a0b0;
    }

    /* ── Toolbar ──────────────────────────────────────────────── */
    QToolBar {
        background-color: #f0f0f5;
        border-bottom: 1px solid #d0d0d8;
        padding: 3px;
        spacing: 4px;
    }

    QToolBar::separator {
        width: 1px;
        background-color: #d0d0d8;
        margin: 4px 6px;
    }

    QToolButton {
        background-color: transparent;
        color: #1e1e2e;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 5px;
    }

    QToolButton:hover {
        background-color: #e0e0ea;
        border-color: #d0d0d8;
    }

    QToolButton:pressed {
        background-color: #d0d0d8;
    }

    /* ── Splitter ─────────────────────────────────────────────── */
    QSplitter::handle {
        background-color: #d0d0d8;
    }

    QSplitter::handle:horizontal {
        width: 2px;
    }

    QSplitter::handle:vertical {
        height: 2px;
    }

    QSplitter::handle:hover {
        background-color: #3574e0;
    }

    /* ── Scroll bars ──────────────────────────────────────────── */
    QScrollBar:vertical {
        background-color: #ffffff;
        width: 10px;
        margin: 0;
        border: none;
    }

    QScrollBar::handle:vertical {
        background-color: #d0d0d8;
        min-height: 30px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #b0b0c0;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }

    QScrollBar:horizontal {
        background-color: #ffffff;
        height: 10px;
        margin: 0;
        border: none;
    }

    QScrollBar::handle:horizontal {
        background-color: #d0d0d8;
        min-width: 30px;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #b0b0c0;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }

    /* ── Group box ────────────────────────────────────────────── */
    QGroupBox {
        background-color: #f5f5f9;
        border: 1px solid #d0d0d8;
        border-radius: 8px;
        margin-top: 14px;
        padding: 16px 8px 8px 8px;
        font-weight: bold;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 10px;
        color: #3574e0;
    }

    /* ── Tabs ─────────────────────────────────────────────────── */
    QTabWidget::pane {
        background-color: #ffffff;
        border: 1px solid #d0d0d8;
        border-radius: 4px;
        top: -1px;
    }

    QTabBar::tab {
        background-color: #f0f0f5;
        color: #444466;
        border: 1px solid #d0d0d8;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 16px;
        margin-right: 2px;
    }

    QTabBar::tab:selected {
        background-color: #ffffff;
        color: #1e1e2e;
        border-bottom: 2px solid #3574e0;
    }

    QTabBar::tab:hover:!selected {
        background-color: #e0e0ea;
    }

    /* ── Status bar ───────────────────────────────────────────── */
    QStatusBar {
        background-color: #f0f0f5;
        color: #444466;
        border-top: 1px solid #d0d0d8;
        padding: 2px;
    }

    QStatusBar::item {
        border: none;
    }
    """

    _STYLES = {
        "dark": DARK_STYLE,
        "light": LIGHT_STYLE,
    }

    @staticmethod
    def apply_theme(app: QApplication, theme: str) -> None:
        """Apply *dark* or *light* theme stylesheet to the application."""
        style = ThemeManager._STYLES.get(theme, ThemeManager.DARK_STYLE)
        app.setStyleSheet(style)

    @staticmethod
    def get_icon_color(theme: str) -> str:
        """Return a suitable icon color string for the given theme."""
        if theme == "light":
            return "#1e1e2e"
        return "#cdd6f4"
