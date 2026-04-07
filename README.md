# Fluxo

A dedicated M3U/IPTV playlist manager for power users. Parse massive M3U lists from file or URL to visually edit channel orders, rename streams, fix broken EPG/XMLTV links, and assign custom logos. Save your optimized playlist locally or host it as a dynamic link for immediate streaming.

> **Fluxo is a neutral playlist-management tool for lawful personal and organizational use.**
> It does not bundle, provide, or facilitate access to copyrighted streams or pirate content.

## Features

### Core Playlist Management
- **Create** new playlists from scratch
- **Import** M3U from local files or remote URLs
- **Parse** large playlists robustly (100K+ channels)
- **Edit** channel names, URLs, groups, logos, and EPG IDs
- **Organize** with drag-and-drop reordering, groups, and categories
- **Export** clean M3U/M3U8 files preserving all metadata

### Metadata & EPG
- Full support for #EXTM3U, #EXTINF, tvg-id, tvg-name, tvg-logo, group-title, catchup attributes
- XMLTV/EPG import and management
- Intelligent EPG mapping assistant with fuzzy matching
- EPG mapping validation

### Power User Features
- **Duplicate detection** (exact and fuzzy)
- **Bulk operations**: rename, move, find-and-replace (regex supported)
- **Stream health checking** with background workers
- **Undo/redo** with full history
- **Project files** (.fluxo) for save/resume workflows
- **Autosave** and crash recovery
- **Keyboard shortcuts** for all major actions

### Hosting & Sharing
- **Self-hosted local playlist server** — serve playlists over HTTP on your LAN
- **Shareable links** with optional password protection (PBKDF2)
- **Link expiration** and access tracking
- **Group-filtered sharing** — share a subset of your playlist

### UX
- **Dark and light themes** (Catppuccin-inspired)
- Three-panel layout: Groups | Channels | Details
- Search, filter, and sort
- Multi-select with contextual actions
- Desktop-first native experience (PySide6/Qt)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/diShine-digital-agency/fluxo.git
cd fluxo

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install
pip install -e ".[dev]"

# Run
python -m fluxo
```

### Desktop Builds

Pre-built installers for macOS and Windows are available on the [Releases](https://github.com/diShine-digital-agency/fluxo/releases) page.

To build locally:
```bash
pip install pyinstaller
python scripts/build.py
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| UI Framework | PySide6 (Qt 6) |
| HTTP Client | httpx |
| XML Parsing | lxml |
| Encoding Detection | chardet |
| Packaging | PyInstaller |
| Testing | pytest + pytest-qt |

## Project Structure

```
src/fluxo/
├── models/          # Typed data models (Channel, Playlist, EPG, Project)
├── parsers/         # M3U and XMLTV parsers
├── services/        # Business logic (validation, dedup, export, EPG mapping, sharing)
├── server/          # Local HTTP playlist server and shared-link management
├── ui/              # PySide6 widgets and dialogs
│   └── widgets/     # Reusable UI components
├── persistence/     # Settings and autosave
├── app.py           # Application entry point
└── __main__.py      # Module entry point
```

## Testing

```bash
pytest
```

## Documentation

- [Product Discovery Report](docs/PRODUCT_DISCOVERY.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

## License

[MIT](LICENSE)
