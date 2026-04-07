"""Sharing dialog for managing hosted playlist links."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fluxo.models.playlist import Playlist
from fluxo.services.sharing_service import SharingService


class SharingDialog(QDialog):
    """Dialog for hosting a playlist and managing shared links."""

    server_started = Signal()
    server_stopped = Signal()

    def __init__(
        self,
        playlist: Playlist,
        sharing_service: SharingService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Host & Share Playlist")
        self.resize(700, 500)

        self._playlist = playlist
        self._svc = sharing_service
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Server control section
        server_box = QGroupBox("Local Server")
        srv_layout = QHBoxLayout(server_box)
        self._status_label = QLabel("Stopped")
        self._url_label = QLabel("")
        self._start_btn = QPushButton("Start Server")
        self._stop_btn = QPushButton("Stop Server")
        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn.clicked.connect(self._on_stop)
        srv_layout.addWidget(self._status_label)
        srv_layout.addWidget(self._url_label)
        srv_layout.addStretch()
        srv_layout.addWidget(self._start_btn)
        srv_layout.addWidget(self._stop_btn)
        root.addWidget(server_box)

        # New-link form
        link_box = QGroupBox("Create Sharing Link")
        form = QFormLayout(link_box)

        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("e.g. Family, Travel")
        form.addRow("Label:", self._label_edit)

        self._pw_edit = QLineEdit()
        self._pw_edit.setPlaceholderText("Leave empty for no password")
        self._pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self._pw_edit)

        self._expiry_combo = QComboBox()
        self._expiry_combo.addItems(["Never", "1 hour", "24 hours", "7 days", "30 days"])
        form.addRow("Expires:", self._expiry_combo)

        self._groups_check = QCheckBox("All groups")
        self._groups_check.setChecked(True)
        form.addRow("Groups:", self._groups_check)

        create_btn = QPushButton("Create Link")
        create_btn.clicked.connect(self._on_create_link)
        form.addRow("", create_btn)

        root.addWidget(link_box)

        # Links table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Label", "URL", "Accesses", "Status", "Actions"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        root.addWidget(self._table, 1)

        # Close
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._svc.start(self._playlist)
        self.server_started.emit()
        self._refresh()

    def _on_stop(self) -> None:
        self._svc.stop()
        self.server_stopped.emit()
        self._refresh()

    def _on_create_link(self) -> None:
        label = self._label_edit.text().strip() or "Untitled"
        password = self._pw_edit.text() or None
        groups_filter = None if self._groups_check.isChecked() else []

        # Expiry
        expires_at = None
        idx = self._expiry_combo.currentIndex()
        if idx == 1:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        elif idx == 2:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        elif idx == 3:
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        elif idx == 4:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        self._svc.create_link(
            label=label,
            password=password,
            expires_at=expires_at,
            groups_filter=groups_filter,
        )
        self._label_edit.clear()
        self._pw_edit.clear()
        self._refresh()

    # ------------------------------------------------------------------
    # Table refresh
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        # Server status
        running = self._svc.is_running
        self._status_label.setText("● Running" if running else "○ Stopped")
        self._url_label.setText(self._svc.server.base_url if running else "")
        self._start_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)

        # Links
        links = self._svc.list_links()
        self._table.setRowCount(len(links))
        for row, link in enumerate(links):
            self._table.setItem(row, 0, QTableWidgetItem(link.label or "(no label)"))

            url = self._svc.get_url(link)
            url_item = QTableWidgetItem(url)
            url_item.setFlags(url_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, url_item)

            self._table.setItem(row, 2, QTableWidgetItem(str(link.access_count)))

            status = "Active" if link.is_valid else ("Expired" if link.is_expired else "Revoked")
            self._table.setItem(row, 3, QTableWidgetItem(status))

            # Actions cell
            actions = QWidget()
            h = QHBoxLayout(actions)
            h.setContentsMargins(2, 2, 2, 2)

            copy_btn = QPushButton("Copy URL")
            copy_btn.clicked.connect(lambda _checked=False, u=url: self._copy_url(u))
            h.addWidget(copy_btn)

            if link.is_active:
                revoke_btn = QPushButton("Revoke")
                revoke_btn.clicked.connect(
                    lambda _checked=False, t=link.token: self._revoke(t)
                )
                h.addWidget(revoke_btn)

            self._table.setCellWidget(row, 4, actions)

    @staticmethod
    def _copy_url(url: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(url)

    def _revoke(self, token: str) -> None:
        self._svc.revoke_link(token)
        self._refresh()
