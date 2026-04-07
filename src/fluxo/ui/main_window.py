"""Main application window for Fluxo."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSettings, QSize, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fluxo.models import Channel, EpgData, HealthStatus, Playlist, Project
from fluxo.parsers import M3UParser, XmltvParser
from fluxo.persistence import AutosaveManager, Settings
from fluxo.services import (
    BulkOperationService,
    DeduplicationService,
    EpgMapper,
    ExportService,
    ProjectManager,
    ValidationService,
)
from fluxo.ui.shortcuts import ShortcutManager
from fluxo.ui.theme import ThemeManager
from fluxo.ui.widgets import (
    ChannelTableWidget,
    DetailPanel,
    FluxoStatusBar,
    GroupPanel,
    SearchBar,
)
from fluxo.ui.widgets.dialogs import (
    BulkEditDialog,
    EpgDialog,
    ExportDialog,
    ImportDialog,
    SettingsDialog,
)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class _Worker(QThread):
    """Generic background worker for long-running tasks."""

    progress = pyqtSignal(int, int)  # current, total
    finished_result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished_result.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

_APP_NAME = "Fluxo"
_DEFAULT_SIZE = QSize(1200, 800)
_MAX_RECENT = 10


class MainWindow(QMainWindow):
    """Primary application window that ties every Fluxo component together."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # -- state -----------------------------------------------------------
        self._project: Project = Project(name="Untitled")
        self._current_path: Optional[str] = None
        self._settings = Settings()
        self._autosave = AutosaveManager()
        self._worker: Optional[_Worker] = None
        self._theme = "dark"

        # -- ui setup --------------------------------------------------------
        self._build_widgets()
        self._build_menu_bar()
        self._build_layout()
        self._connect_signals()
        self._setup_shortcuts()
        self._restore_state()
        self._apply_initial_state()

    # ------------------------------------------------------------------ build
    def _build_widgets(self) -> None:
        self._search_bar = SearchBar(self)
        self._group_panel = GroupPanel(self)
        self._channel_table = ChannelTableWidget(self)
        self._detail_panel = DetailPanel(self)
        self._status_bar = FluxoStatusBar(self)
        self.setStatusBar(self._status_bar)

    def _build_layout(self) -> None:
        # Splitter: group | table | detail
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.addWidget(self._group_panel)
        self._splitter.addWidget(self._channel_table)
        self._splitter.addWidget(self._detail_panel)
        self._splitter.setSizes([200, 700, 300])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._search_bar)
        layout.addWidget(self._splitter, 1)
        self.setCentralWidget(container)

    # ------------------------------------------------------------- menu bar
    def _build_menu_bar(self) -> None:
        mb = self.menuBar()

        # -- File ------------------------------------------------------------
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "&New Playlist", self.new_playlist, QKeySequence.StandardKey.New)
        self._add_action(file_menu, "&Open Project…", self.open_project, QKeySequence.StandardKey.Open)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Save Project", self.save_project, QKeySequence.StandardKey.Save)
        self._add_action(file_menu, "Save &As…", self.save_project_as, QKeySequence("Ctrl+Shift+S"))
        file_menu.addSeparator()
        self._add_action(file_menu, "&Import M3U…", self.import_m3u, QKeySequence("Ctrl+I"))
        self._add_action(file_menu, "&Export M3U…", self.export_m3u, QKeySequence("Ctrl+E"))
        file_menu.addSeparator()
        self._recent_menu = file_menu.addMenu("Recent Files")
        self._rebuild_recent_menu()
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", self.close, QKeySequence("Ctrl+Q"))

        # -- Edit ------------------------------------------------------------
        edit_menu = mb.addMenu("&Edit")
        self._undo_action = self._add_action(edit_menu, "&Undo", self.undo, QKeySequence.StandardKey.Undo)
        self._redo_action = self._add_action(edit_menu, "&Redo", self.redo, QKeySequence("Ctrl+Shift+Z"))
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Select &All", self._channel_table.select_all, QKeySequence.StandardKey.SelectAll)
        self._add_action(edit_menu, "&Delete Selected", self.delete_selected, QKeySequence(Qt.Key.Key_Delete))
        edit_menu.addSeparator()
        self._add_action(edit_menu, "&Find && Replace", self._focus_search, QKeySequence.StandardKey.Find)
        self._add_action(edit_menu, "&Preferences…", self._open_preferences)

        # -- Playlist --------------------------------------------------------
        playlist_menu = mb.addMenu("&Playlist")
        self._add_action(playlist_menu, "&Add Channel", self.add_channel)
        self._add_action(playlist_menu, "&Duplicate Detection", self.find_duplicates, QKeySequence("Ctrl+D"))
        self._add_action(playlist_menu, "&Bulk Edit…", self.bulk_edit)
        self._add_action(playlist_menu, "&Check Stream Health", self.check_streams, QKeySequence(Qt.Key.Key_F5))
        self._add_action(playlist_menu, "&Merge Playlist…", self._merge_playlist)

        # -- EPG -------------------------------------------------------------
        epg_menu = mb.addMenu("E&PG")
        self._add_action(epg_menu, "&Manage EPG Sources…", self.manage_epg)
        self._add_action(epg_menu, "&Auto-Map EPG", self._auto_map_epg)
        self._add_action(epg_menu, "&Validate EPG Mapping", self._validate_epg)

        # -- View ------------------------------------------------------------
        view_menu = mb.addMenu("&View")
        self._add_action(view_menu, "Toggle &Dark/Light Theme", self.toggle_theme)
        self._toggle_group_action = self._add_action(view_menu, "Toggle &Group Panel", self._toggle_group_panel)
        self._toggle_detail_action = self._add_action(view_menu, "Toggle D&etail Panel", self._toggle_detail_panel)

        # -- Help ------------------------------------------------------------
        help_menu = mb.addMenu("&Help")
        self._add_action(help_menu, "&About", self._show_about)
        self._add_action(help_menu, "&Keyboard Shortcuts", self._show_shortcuts)

    @staticmethod
    def _add_action(menu, text, slot, shortcut=None) -> QAction:
        action = menu.addAction(text)
        action.triggered.connect(slot)
        if shortcut is not None:
            action.setShortcut(shortcut)
        return action

    # ------------------------------------------------------------ shortcuts
    def _setup_shortcuts(self) -> None:
        self._shortcut_mgr = ShortcutManager(self)
        self._shortcut_mgr.register_defaults({
            "new_playlist": self.new_playlist,
            "open_file": self.open_project,
            "save_project": self.save_project,
            "save_as": self.save_project_as,
            "export_m3u": self.export_m3u,
            "import_m3u": self.import_m3u,
            "undo": self.undo,
            "redo": self.redo,
            "search": self._focus_search,
            "select_all": self._channel_table.select_all,
            "duplicate_detection": self.find_duplicates,
            "delete_selected": self.delete_selected,
            "refresh_streams": self.check_streams,
        })

    # -------------------------------------------------------------- signals
    def _connect_signals(self) -> None:
        # Group panel -> table filter
        self._group_panel.group_selected.connect(self._on_group_selected)

        # Search bar -> table filter
        self._search_bar.search_changed.connect(self._on_search_changed)

        # Table -> detail panel
        self._channel_table.channel_selected.connect(self._detail_panel.set_channel)
        self._channel_table.channels_deleted.connect(self._on_channels_deleted)

        # Detail panel -> refresh
        self._detail_panel.channel_updated.connect(self._on_channel_updated)

    # ============================================================ actions ===

    # -- File ----------------------------------------------------------------

    @pyqtSlot()
    def new_playlist(self) -> None:
        if not self._confirm_discard():
            return
        self._project = Project(name="Untitled")
        self._current_path = None
        self._refresh_all()

    @pyqtSlot()
    def open_project(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "Fluxo Projects (*.fluxo);;All Files (*)"
        )
        if not path:
            return
        try:
            self._project = ProjectManager.load_project(path)
            self._current_path = path
            self._push_recent(path)
            self._refresh_all()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to open project:\n{exc}")

    @pyqtSlot()
    def save_project(self) -> None:
        if self._current_path:
            self._do_save(self._current_path)
        else:
            self.save_project_as()

    @pyqtSlot()
    def save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "Fluxo Projects (*.fluxo);;All Files (*)"
        )
        if not path:
            return
        self._do_save(path)

    def _do_save(self, path: str) -> None:
        try:
            ProjectManager.save_project(self._project, path)
            self._current_path = path
            self._project.mark_saved()
            self._push_recent(path)
            self.update_title()
            self._status_bar.showMessage("Project saved.", 3000)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to save project:\n{exc}")

    @pyqtSlot()
    def import_m3u(self) -> None:
        dlg = ImportDialog(self)
        if dlg.exec():
            result = dlg.get_result()
            if result and result.playlist:
                self._project.playlist = result.playlist
                self._refresh_all()
                if result.warnings:
                    self._status_bar.showMessage(
                        f"Imported with {len(result.warnings)} warning(s).", 5000
                    )
                else:
                    self._status_bar.showMessage("Import complete.", 3000)

    @pyqtSlot()
    def export_m3u(self) -> None:
        dlg = ExportDialog(self._project.playlist, self)
        dlg.exec()

    def _merge_playlist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Merge Playlist", "", "M3U Files (*.m3u *.m3u8);;All Files (*)"
        )
        if not path:
            return
        try:
            result = M3UParser.parse_file(path)
            if result.playlist:
                for ch in result.playlist.channels:
                    self._project.playlist.add_channel(ch)
                self._refresh_all()
                self._status_bar.showMessage("Playlist merged.", 3000)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to merge playlist:\n{exc}")

    # -- Edit ----------------------------------------------------------------

    @pyqtSlot()
    def undo(self) -> None:
        self._project.undo()
        self._refresh_all()

    @pyqtSlot()
    def redo(self) -> None:
        self._project.redo()
        self._refresh_all()

    @pyqtSlot()
    def delete_selected(self) -> None:
        self._channel_table.delete_selected()

    def _focus_search(self) -> None:
        self._search_bar.setFocus()

    def _open_preferences(self) -> None:
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec():
            new_settings = dlg.get_settings()
            for k, v in new_settings.items():
                self._settings.set(k, v)
            self._settings.save()

    # -- Playlist ------------------------------------------------------------

    @pyqtSlot()
    def add_channel(self) -> None:
        ch = Channel(name="New Channel", url="")
        self._project.playlist.add_channel(ch)
        self._refresh_all()

    @pyqtSlot()
    def find_duplicates(self) -> None:
        dupes = DeduplicationService.find_duplicates(self._project.playlist)
        count = sum(len(g) for g in dupes.values()) if isinstance(dupes, dict) else len(dupes)
        self._status_bar.showMessage(f"Found {count} potential duplicate(s).", 5000)

    @pyqtSlot()
    def bulk_edit(self) -> None:
        selected = self._channel_table.selected_channels()
        if not selected:
            QMessageBox.information(self, "Bulk Edit", "No channels selected.")
            return
        epg_data = self._project.epg_sources if hasattr(self._project, "epg_sources") else None
        dlg = BulkEditDialog(selected, epg_data, self)
        if dlg.exec():
            self._refresh_all()

    @pyqtSlot()
    def check_streams(self) -> None:
        channels = self._channel_table.selected_channels()
        if not channels:
            channels = list(self._project.playlist.channels)
        if not channels:
            return
        self._status_bar.showMessage(f"Checking {len(channels)} stream(s)…")
        self._run_worker(self._check_streams_work, channels, callback=self._on_streams_checked)

    @staticmethod
    def _check_streams_work(channels):
        for ch in channels:
            try:
                ch.health = ValidationService.validate_url(ch.url)
            except Exception:  # noqa: BLE001
                ch.health = HealthStatus.DEAD
        return channels

    def _on_streams_checked(self, _result) -> None:
        self._refresh_all()
        self._status_bar.showMessage("Stream health check complete.", 5000)

    # -- EPG -----------------------------------------------------------------

    @pyqtSlot()
    def manage_epg(self) -> None:
        epg_sources = getattr(self._project, "epg_sources", [])
        dlg = EpgDialog(self._project.playlist, epg_sources, self)
        if dlg.exec():
            self._project.epg_sources = dlg.get_epg_sources()
            self._refresh_all()

    def _auto_map_epg(self) -> None:
        epg_sources = getattr(self._project, "epg_sources", [])
        if not epg_sources:
            QMessageBox.information(self, "EPG", "No EPG sources configured.")
            return
        try:
            EpgMapper.map_channels_to_epg(self._project.playlist, epg_sources)
            self._refresh_all()
            self._status_bar.showMessage("EPG auto-mapping complete.", 5000)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"EPG mapping failed:\n{exc}")

    def _validate_epg(self) -> None:
        unmapped = [
            ch for ch in self._project.playlist.channels
            if not getattr(ch, "tvg_id", None)
        ]
        if unmapped:
            QMessageBox.information(
                self, "EPG Validation",
                f"{len(unmapped)} channel(s) have no EPG mapping.",
            )
        else:
            QMessageBox.information(self, "EPG Validation", "All channels are mapped.")

    # -- View ----------------------------------------------------------------

    @pyqtSlot()
    def toggle_theme(self) -> None:
        self._theme = "light" if self._theme == "dark" else "dark"
        app = QApplication.instance()
        if app:
            ThemeManager.apply_theme(app, self._theme)
        self._settings.set("theme", self._theme)
        self._settings.save()

    def _toggle_group_panel(self) -> None:
        self._group_panel.setVisible(not self._group_panel.isVisible())

    def _toggle_detail_panel(self) -> None:
        self._detail_panel.setVisible(not self._detail_panel.isVisible())

    # -- Help ----------------------------------------------------------------

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {_APP_NAME}",
            f"<h3>{_APP_NAME}</h3>"
            "<p>A professional IPTV playlist editor.</p>"
            "<p>Manage M3U playlists, EPG data, and stream health.</p>",
        )

    def _show_shortcuts(self) -> None:
        shortcuts = (
            "Ctrl+N  New Playlist\n"
            "Ctrl+O  Open Project\n"
            "Ctrl+S  Save Project\n"
            "Ctrl+Shift+S  Save As\n"
            "Ctrl+I  Import M3U\n"
            "Ctrl+E  Export M3U\n"
            "Ctrl+Z  Undo\n"
            "Ctrl+Shift+Z  Redo\n"
            "Ctrl+F  Find\n"
            "Ctrl+A  Select All\n"
            "Delete  Delete Selected\n"
            "Ctrl+D  Duplicate Detection\n"
            "F5  Check Streams\n"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts)

    # ========================================================== internal ===

    def _on_group_selected(self, group: str) -> None:
        self._channel_table._proxy_model.set_group_filter(group if group != "All" else "")

    def _on_search_changed(self, text: str) -> None:
        self._channel_table._proxy_model.set_filter_text(text)

    def _on_channels_deleted(self) -> None:
        self._detail_panel.clear()
        self._refresh_groups()
        self._update_status()

    def _on_channel_updated(self, channel) -> None:
        self._refresh_groups()
        self._update_status()

    # -- refresh helpers -----------------------------------------------------

    def _refresh_all(self) -> None:
        self._channel_table.set_playlist(self._project.playlist)
        self._refresh_groups()
        self._detail_panel.clear()
        self._update_status()
        self.update_title()

    def _refresh_groups(self) -> None:
        groups = list(self._project.playlist.get_channels_by_group().keys())
        self._group_panel.update_groups(groups)
        self._search_bar.update_groups(groups)

    def _update_status(self) -> None:
        self._status_bar.update_stats(self._project.playlist)

    def update_title(self) -> None:
        modified = "*" if getattr(self._project, "_modified", False) else ""
        name = self._project.name or "Untitled"
        self.setWindowTitle(f"{modified}{name} — {_APP_NAME}")

    # -- recent files --------------------------------------------------------

    def _push_recent(self, path: str) -> None:
        recents = self._settings.get("recent_files", [])
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        self._settings.set("recent_files", recents[:_MAX_RECENT])
        self._settings.save()
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        recents = self._settings.get("recent_files", [])
        if not recents:
            no_action = self._recent_menu.addAction("(none)")
            no_action.setEnabled(False)
            return
        for path in recents:
            action = self._recent_menu.addAction(os.path.basename(path))
            action.setData(path)
            action.triggered.connect(lambda checked, p=path: self._open_recent(p))

    def _open_recent(self, path: str) -> None:
        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found", f"{path} no longer exists.")
            return
        if not self._confirm_discard():
            return
        try:
            self._project = ProjectManager.load_project(path)
            self._current_path = path
            self._refresh_all()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to open project:\n{exc}")

    # -- worker --------------------------------------------------------------

    def _run_worker(self, fn, *args, callback=None) -> None:
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Busy", "A background task is already running.")
            return
        self._worker = _Worker(fn, *args)
        if callback:
            self._worker.finished_result.connect(callback)
        self._worker.error.connect(
            lambda msg: QMessageBox.critical(self, "Error", msg)
        )
        self._worker.finished.connect(lambda: self._status_bar.showMessage("Ready."))
        self._worker.start()

    # -- confirm discard -----------------------------------------------------

    def _confirm_discard(self) -> bool:
        if not getattr(self._project, "_modified", False):
            return True
        result = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if result == QMessageBox.StandardButton.Save:
            self.save_project()
            return True
        return result == QMessageBox.StandardButton.Discard

    # -- state persistence ---------------------------------------------------

    def _restore_state(self) -> None:
        self._settings.load()
        self._theme = self._settings.get("theme", "dark")
        geo = self._settings.get("geometry", None)
        if geo:
            try:
                self.restoreGeometry(bytes.fromhex(geo))
            except Exception:  # noqa: BLE001
                self._set_default_geometry()
        else:
            self._set_default_geometry()

    def _set_default_geometry(self) -> None:
        self.resize(_DEFAULT_SIZE)
        screen = self.screen()
        if screen:
            fg = self.frameGeometry()
            fg.moveCenter(screen.availableGeometry().center())
            self.move(fg.topLeft())

    def _apply_initial_state(self) -> None:
        app = QApplication.instance()
        if app:
            ThemeManager.apply_theme(app, self._theme)
        self.update_title()
        self._update_status()

        # Check for autosave recovery
        try:
            recovery = self._autosave.load_last()
            if recovery:
                result = QMessageBox.question(
                    self,
                    "Recovery",
                    "An autosave file was found. Restore it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if result == QMessageBox.StandardButton.Yes:
                    self._project = recovery
                    self._refresh_all()
        except Exception:  # noqa: BLE001
            pass

    def _save_state(self) -> None:
        self._settings.set("geometry", self.saveGeometry().toHex().data().decode())
        self._settings.set("theme", self._theme)
        self._settings.save()

    # -- close ---------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._confirm_discard():
            event.ignore()
            return
        self._save_state()
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(3000)
        super().closeEvent(event)
