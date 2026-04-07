"""Tests for v0.2.0 features: column visibility, column widths, favorites, drag-and-drop."""

from __future__ import annotations

import json

import pytest
from PySide6.QtCore import QMimeData, QModelIndex, Qt, QUrl

from fluxo.models import Channel, Playlist
from fluxo.persistence.settings import Settings
from fluxo.ui.widgets.channel_table import (
    ChannelFilterProxyModel,
    ChannelTableModel,
    ChannelTableWidget,
    _COL_FAVORITE,
    _COL_GROUP,
    _COL_NAME,
    _COLUMNS_FULL,
    _STAR_EMPTY,
    _STAR_FILLED,
)
from fluxo.ui.widgets.search_bar import SearchBar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_playlist(*names: str) -> Playlist:
    p = Playlist()
    for n in names:
        p.add_channel(Channel(name=n, url=f"http://example.com/{n}"))
    return p


# ---------------------------------------------------------------------------
# Settings persistence
# ---------------------------------------------------------------------------


class TestSettingsColumnPersistence:
    """Settings should persist column_widths and column_visibility."""

    def test_defaults(self):
        s = Settings()
        assert s.column_widths == {}
        assert s.column_visibility == {}

    def test_save_load_roundtrip(self, tmp_path):
        path = str(tmp_path / "settings.json")
        s = Settings(
            column_widths={"Name": 300, "URL": 400},
            column_visibility={"URL": False, "Health": True},
        )
        s._config_path = path
        s.save()

        loaded = Settings.load(path)
        assert loaded.column_widths == {"Name": 300, "URL": 400}
        assert loaded.column_visibility == {"URL": False, "Health": True}

    def test_load_missing_keys_uses_defaults(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"theme": "light"}), encoding="utf-8")
        loaded = Settings.load(str(path))
        assert loaded.column_widths == {}
        assert loaded.column_visibility == {}


# ---------------------------------------------------------------------------
# Channel table model – Favorite column
# ---------------------------------------------------------------------------


class TestChannelTableModelFavorite:
    """The model should expose and toggle the Favorite column."""

    @pytest.fixture()
    def model(self, qtbot):
        m = ChannelTableModel()
        p = _make_playlist("A", "B")
        m.set_playlist(p)
        return m

    def test_column_count_includes_favorite(self, model):
        assert model.columnCount() == len(_COLUMNS_FULL)

    def test_display_data_star(self, model):
        idx = model.index(0, _COL_FAVORITE)
        assert model.data(idx, Qt.ItemDataRole.DisplayRole) == _STAR_EMPTY

        model.playlist.channels[0].is_favorite = True
        assert model.data(idx, Qt.ItemDataRole.DisplayRole) == _STAR_FILLED

    def test_set_data_toggles_favorite(self, model):
        idx = model.index(0, _COL_FAVORITE)
        assert not model.playlist.channels[0].is_favorite

        result = model.setData(idx, None, Qt.ItemDataRole.EditRole)
        assert result is True
        assert model.playlist.channels[0].is_favorite is True

        result = model.setData(idx, None, Qt.ItemDataRole.EditRole)
        assert result is True
        assert model.playlist.channels[0].is_favorite is False

    def test_header_data_fav(self, model):
        hdr = model.headerData(_COL_FAVORITE, Qt.Orientation.Horizontal)
        assert hdr == "Fav"


# ---------------------------------------------------------------------------
# Filter proxy – favorites only
# ---------------------------------------------------------------------------


class TestFilterProxyFavorites:
    """The proxy model should be able to filter by favorites."""

    @pytest.fixture()
    def setup(self, qtbot):
        model = ChannelTableModel()
        p = _make_playlist("Fav1", "Normal", "Fav2")
        p.channels[0].is_favorite = True
        p.channels[2].is_favorite = True
        model.set_playlist(p)

        proxy = ChannelFilterProxyModel()
        proxy.setSourceModel(model)
        return model, proxy

    def test_no_filter_shows_all(self, setup):
        _model, proxy = setup
        assert proxy.rowCount() == 3

    def test_favorites_only(self, setup):
        _model, proxy = setup
        proxy.set_favorites_only(True)
        assert proxy.rowCount() == 2

    def test_favorites_off_shows_all(self, setup):
        _model, proxy = setup
        proxy.set_favorites_only(True)
        proxy.set_favorites_only(False)
        assert proxy.rowCount() == 3


# ---------------------------------------------------------------------------
# ChannelTableWidget – column visibility
# ---------------------------------------------------------------------------


class TestChannelTableWidgetColumnVisibility:
    """Column visibility methods on ChannelTableWidget."""

    @pytest.fixture()
    def widget(self, qtbot):
        w = ChannelTableWidget()
        qtbot.addWidget(w)
        w.set_playlist(_make_playlist("Ch1"))
        return w

    def test_set_column_visibility_hides(self, widget):
        widget.set_column_visibility(_COL_GROUP, False)
        assert widget.view.isColumnHidden(_COL_GROUP)

    def test_set_column_visibility_shows(self, widget):
        widget.set_column_visibility(_COL_GROUP, False)
        widget.set_column_visibility(_COL_GROUP, True)
        assert not widget.view.isColumnHidden(_COL_GROUP)

    def test_get_column_visibility(self, widget):
        widget.set_column_visibility(_COL_GROUP, False)
        state = widget.get_column_visibility()
        assert state["Group"] is False
        assert state["Name"] is True

    def test_restore_column_visibility(self, widget):
        saved = {"Group": False, "URL": False}
        widget.restore_column_visibility(saved)
        assert widget.view.isColumnHidden(_COL_GROUP)
        assert not widget.view.isColumnHidden(_COL_NAME)

    def test_visibility_changed_signal(self, widget, qtbot):
        with qtbot.waitSignal(widget.column_visibility_changed, timeout=1000):
            widget.set_column_visibility(_COL_GROUP, False)


# ---------------------------------------------------------------------------
# ChannelTableWidget – column widths
# ---------------------------------------------------------------------------


class TestChannelTableWidgetColumnWidths:
    """Column width save/restore on ChannelTableWidget."""

    @pytest.fixture()
    def widget(self, qtbot):
        w = ChannelTableWidget()
        qtbot.addWidget(w)
        w.set_playlist(_make_playlist("Ch1"))
        return w

    def test_get_column_widths_returns_dict(self, widget):
        widths = widget.get_column_widths()
        assert isinstance(widths, dict)
        assert "Name" in widths
        assert all(isinstance(v, int) for v in widths.values())

    def test_restore_column_widths(self, widget):
        widget.restore_column_widths({"#": 80})
        widths = widget.get_column_widths()
        assert widths["#"] == 80


# ---------------------------------------------------------------------------
# ChannelTableWidget – toggle favorite
# ---------------------------------------------------------------------------


class TestChannelTableWidgetFavorite:
    """Favorite toggle via ChannelTableWidget."""

    @pytest.fixture()
    def widget(self, qtbot):
        w = ChannelTableWidget()
        qtbot.addWidget(w)
        w.set_playlist(_make_playlist("A", "B"))
        return w

    def test_toggle_favorite(self, widget):
        ch = widget.model.playlist.channels[0]
        assert not ch.is_favorite
        widget.toggle_favorite(ch)
        assert ch.is_favorite
        widget.toggle_favorite(ch)
        assert not ch.is_favorite


# ---------------------------------------------------------------------------
# SearchBar – favorites filter
# ---------------------------------------------------------------------------


class TestSearchBarFavorites:
    """SearchBar should expose a favorites_filter_changed signal."""

    @pytest.fixture()
    def bar(self, qtbot):
        b = SearchBar()
        qtbot.addWidget(b)
        return b

    def test_favorites_signal_emitted(self, bar, qtbot):
        with qtbot.waitSignal(bar.favorites_filter_changed, timeout=1000):
            bar._favorites_check.setChecked(True)

    def test_clear_filters_unchecks_favorites(self, bar):
        bar._favorites_check.setChecked(True)
        bar.clear_filters()
        assert not bar._favorites_check.isChecked()


# ---------------------------------------------------------------------------
# MainWindow – drag-and-drop acceptance
# ---------------------------------------------------------------------------


class TestMainWindowDragDrop:
    """MainWindow should accept .m3u/.m3u8 files via drag-and-drop."""

    def test_accepts_m3u_extension(self):
        from fluxo.ui.main_window import MainWindow

        assert ".m3u" in MainWindow._M3U_EXTENSIONS
        assert ".m3u8" in MainWindow._M3U_EXTENSIONS
