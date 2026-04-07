"""Reusable UI widgets for Fluxo."""

from fluxo.ui.widgets.channel_table import (
    ChannelFilterProxyModel,
    ChannelTableModel,
    ChannelTableWidget,
)
from fluxo.ui.widgets.detail_panel import DetailPanel
from fluxo.ui.widgets.group_panel import GroupPanel
from fluxo.ui.widgets.search_bar import SearchBar
from fluxo.ui.widgets.status_bar import FluxoStatusBar

__all__ = [
    "ChannelFilterProxyModel",
    "ChannelTableModel",
    "ChannelTableWidget",
    "DetailPanel",
    "FluxoStatusBar",
    "GroupPanel",
    "SearchBar",
]
