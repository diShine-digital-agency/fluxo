# Fluxo — Product Discovery Report

## What is Fluxo?

Fluxo is a dedicated M3U / IPTV playlist manager designed for power users who need full control over their IPTV playlists. It is a native desktop application (macOS + Windows) built with Python and PySide6 (Qt), providing a fast, polished, local-first experience for creating, editing, importing, validating, organizing, optimizing, and exporting IPTV playlists and related metadata.

## Who is it for?

- **IPTV enthusiasts** who manage large personal playlists
- **Content curators** who organize channel collections for lawful distribution
- **System administrators** who maintain IPTV infrastructure for hotels, hospitals, or educational institutions
- **Developers and testers** who build or test IPTV-related software
- **Small IPTV service operators** who need playlist management tooling

## Core Playlist Management Workflows

1. **Import** — Load M3U from local files or remote URLs, parse robustly with metadata preservation
2. **Create** — Build playlists from scratch with guided channel entry
3. **Edit** — Modify channel names, URLs, groups, logos, EPG IDs, and all metadata fields
4. **Organize** — Group, sort, filter, search, tag, and reorder channels
5. **Validate** — Check stream health, detect broken links, validate EPG mappings
6. **Deduplicate** — Find and merge duplicate entries intelligently
7. **Bulk Operations** — Mass rename, move, reassign logos/EPG, find-and-replace
8. **Export** — Output clean M3U/M3U8 files preserving all metadata
9. **Save/Resume** — Project files for interrupted work, autosave, undo/redo

## Must-Have Features (MVP)

- Create new playlist from scratch
- Import M3U from local file or remote URL
- Robust parser handling large files (100K+ channels)
- Full metadata preservation (#EXTM3U, #EXTINF, tvg-id, tvg-name, tvg-logo, group-title, catchup attributes)
- Visual channel list with table/grid view
- Drag-and-drop reordering
- Channel editing (name, URL, group, logo, EPG ID)
- Group/category management
- XMLTV / EPG link management and validation
- Search, filter, sort
- Duplicate detection
- Bulk edit operations (rename, move, replace, logo/EPG assignment)
- Stream status / broken link checking
- Clean M3U export
- Project file save/load
- Undo / redo
- Autosave / recovery
- Dark and light themes
- Keyboard shortcuts
- Local-first, privacy-friendly operation

## Advanced / Killer Features

- Smart cleanup suggestions for malformed playlists
- EPG mapping assistant with fuzzy matching
- Logo finder / fallback manager
- Merge multiple playlists with conflict resolution
- Intelligent deduplication (fuzzy name + URL matching)
- Favorites / tags / custom collections
- Stream health dashboard with history
- Metadata normalization rules engine
- Channel templates / profiles
- Compare two playlists and merge differences
- Regex-powered find and replace

## Weaknesses / Gaps in Existing Tools

| Tool | Key Weakness |
|------|-------------|
| m3ue/m3u-editor | Requires Docker, complex setup, web-only |
| kamalsoft/m3u-editor | Depends on external binaries (FFmpeg, VLC), overwhelming UI |
| bugsfreeweb/m3ueditor | No EPG support, basic features only |
| arazgholami/awesome-m3u-editor | Minimal features, no diagnostics |
| Coolerm690/m3u_editor | Basic editing only, no EPG/validation |
| Isayso/PlaylistEditorTV | Windows-only, outdated .NET, basic |
| shinigami-playlist | Web-only, no desktop version, limited undo |
| ezIPTV | CLI-focused, steep learning curve |
| m3uedit.online | Web-only, CORS limitations, no project save |
| m3uedit.com | Limited features, no bulk operations |

**Common gaps across all tools:**
- No polished cross-platform native desktop app
- Poor handling of very large playlists (>50K channels)
- Limited or no undo/redo support
- No project file concept (save work in progress)
- Weak EPG mapping assistance
- No smart cleanup or normalization
- Poor onboarding for new users
- No autosave/recovery

## 3–5 Killer Differentiators for Fluxo

1. **True Native Desktop Experience** — PySide6/Qt delivers real native performance and feel on macOS and Windows. No browser, no Docker, no dev server. Just install and run.

2. **Power-User Workflow Engine** — Regex find-and-replace, bulk operations, smart deduplication, metadata normalization rules, and keyboard-driven workflows make Fluxo the fastest tool for heavy playlist editing.

3. **Intelligent EPG Mapping Assistant** — Fuzzy matching between channel names and XMLTV channel IDs, with visual mapping review and one-click fixes. No other tool does this well.

4. **Project-Based Workflow with Undo/Redo** — Save your work as a project file. Full undo/redo stack. Autosave and crash recovery. Work on playlists over days without losing progress.

5. **Scalable Performance** — Virtualized table rendering, background parsing, non-blocking stream checks, and efficient data structures handle 100K+ channel playlists smoothly.

## Recommended Technical Stack

### Language: Python 3.11+
- Strong file-processing ergonomics
- Rich ecosystem for HTTP, XML, text parsing
- Mature typing support for clean architecture
- Excellent packaging options

### UI Framework: PySide6 (Qt 6)
- **Why PySide6 over alternatives:**
  - True native widgets on macOS and Windows (not Chromium/Electron)
  - Mature, stable, well-documented
  - Built-in support for tables, drag-and-drop, themes, keyboard shortcuts
  - QThread and signals for non-blocking UI
  - Virtual scrolling support via model/view architecture
  - LGPL-licensed (compatible with commercial use)
- **Why not Electron/Tauri:** Problem statement explicitly excludes Chromium-based approaches
- **Why not Tkinter:** Lacks modern widgets, theming, and performance for complex UIs
- **Why not wxPython:** Smaller community, less polished than Qt

### Packaging: PyInstaller
- Most mature and reliable Python packaging tool
- Produces standalone executables for macOS (.app) and Windows (.exe)
- Handles PySide6 dependencies well with proper configuration
- Alternative: cx_Freeze for slimmer builds if needed

### Key Libraries
- `PySide6` — UI framework
- `httpx` — HTTP client for stream checking and URL imports
- `lxml` — Fast XML parsing for XMLTV/EPG
- `chardet` — Character encoding detection
- `pytest` / `pytest-qt` — Testing framework

## Recommended Architecture

```
┌─────────────────────────────────────────────┐
│                  UI Layer                    │
│         (PySide6 Widgets + Dialogs)         │
├─────────────────────────────────────────────┤
│               Service Layer                  │
│  (Validation, Dedup, Bulk Ops, Export, EPG, │
│   Sharing, Templates, Normalization)        │
├─────────────────────────────────────────────┤
│               Server Layer                   │
│    (Playlist HTTP Server, Shared Links)     │
├─────────────────────────────────────────────┤
│               Parser Layer                   │
│        (M3U Parser, XMLTV Parser)           │
├─────────────────────────────────────────────┤
│               Model Layer                    │
│  (Channel, Playlist, EPG, Project,          │
│   Collection, ChannelTemplate)              │
├─────────────────────────────────────────────┤
│            Persistence Layer                 │
│    (Settings, Autosave, Project Files)      │
└─────────────────────────────────────────────┘
```

**Key architectural decisions:**
- **Model/View separation** — Qt's model/view architecture for the channel table
- **Background workers** — QThread-based workers for parsing, stream checking, import
- **Signal/slot communication** — Loose coupling between UI and services
- **Typed models** — Pydantic or dataclasses for all data entities
- **Plugin-ready** — Clean interfaces for future extensibility

## Legal / Ethical Constraints

- Fluxo is a **neutral playlist-management tool** for lawful personal and organizational use
- **No bundled streams** — no copyrighted content, pirate streams, or illegal IPTV sources
- **No piracy features** — no circumvention tools, no stream scraping, no provider-specific hacks
- **User-provided data only** — all playlist data comes from the user
- **Privacy-first** — local-only processing, no telemetry, no cloud dependency
- **Clear positioning** — README and docs explicitly state lawful-use-only intent
- **LGPL compliance** — PySide6 is LGPL, which is compatible with commercial/open-source use
- **Safe defaults** — no features that encourage or facilitate infringement

---

*Part of [Fluxo](../README.md) by [diShine Digital Agency](https://dishine.it).*
