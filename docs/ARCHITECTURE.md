# Fluxo Architecture

## Overview

Fluxo follows a clean layered architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────┐
│                  UI Layer                    │
│         (PySide6 Widgets + Dialogs)         │
├─────────────────────────────────────────────┤
│               Service Layer                  │
│  (Validation, Dedup, Bulk Ops, Export, EPG, │
│   Sharing, Templates, Normalization,       │
│   Statistics)                              │
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

## Data Flow: Import → Edit → Export

```
  ┌────────────┐      ┌────────────┐      ┌─────────────┐
  │  M3U File  │─────▸│  M3UParser │─────▸│  Playlist   │
  │  or URL    │      │            │      │  (model)    │
  └────────────┘      └────────────┘      └──────┬──────┘
                                                 │
                      ┌────────────┐             │
                      │  XMLTV     │─────▸ EpgData ──▸ EpgMapper
                      │  Parser    │             │
                      └────────────┘             │
                                                 ▼
                                          ┌─────────────┐
                                          │   Project   │
                                          │ (undo stack │
                                          │  + metadata)│
                                          └──────┬──────┘
                                                 │
              ┌──────────────────────────────────┼──────────────────┐
              ▼                                  ▼                  ▼
     ┌─────────────────┐               ┌──────────────┐   ┌──────────────┐
     │ ExportService   │               │ ProjectMgr   │   │ SharingService│
     │ (clean M3U out) │               │ (.fluxo save)│   │ (HTTP share) │
     └─────────────────┘               └──────────────┘   └──────────────┘
```

## Sharing: Request Lifecycle

```
  Client (IPTV Player)                     PlaylistServer
         │                                       │
         │  GET /playlist/<token>?password=...    │
         │──────────────────────────────────────▸│
         │                                       │
         │                    ┌──────────────────┤
         │                    │ 1. Lookup token  │
         │                    │ 2. Check active  │
         │                    │ 3. Check expiry  │
         │                    │ 4. Verify pwd    │
         │                    │ 5. Filter groups │
         │                    │ 6. Export M3U    │
         │                    └──────────────────┤
         │                                       │
         │  200 OK  (audio/x-mpegurl)            │
         │◂──────────────────────────────────────│
         │  #EXTM3U                              │
         │  #EXTINF:-1, Channel One              │
         │  http://...                           │
```

## Layers

### Model Layer (`src/fluxo/models/`)
- Typed dataclasses for all domain entities
- `Channel` — a single IPTV channel with all M3U metadata fields
- `Playlist` — ordered collection of channels with header metadata
- `EpgData` / `EpgChannel` / `EpgProgramme` — XMLTV EPG structures
- `Project` — wraps a playlist with undo history, EPG links, and project metadata
- `Collection` — user-defined grouping of channels (independent of M3U groups)
- `ChannelTemplate` — reusable metadata preset for applying to channels

### Parser Layer (`src/fluxo/parsers/`)
- `M3UParser` — robust M3U/M3U8 parser handling edge cases (bad encoding, malformed entries, huge files)
- `XmltvParser` — XMLTV/EPG parser extracting channel and programme data

### Service Layer (`src/fluxo/services/`)
- `ValidationService` — stream health checking, EPG mapping validation
- `DeduplicationService` — exact and fuzzy duplicate detection
- `BulkOperationService` — mass rename, move, replace, logo/EPG assignment
- `ExportService` — clean M3U/M3U8 export with metadata preservation, playlist merging with deduplication
- `ProjectManager` — save/load project files, autosave integration
- `EpgMapper` — intelligent EPG-to-channel mapping with fuzzy matching
- `TemplateService` — channel templates/profiles for reusable metadata presets
- `NormalizationService` — metadata cleanup rules (group names, channel names, URLs)
- `SharingService` — manages hosted playlist links and the local server lifecycle
- `StatisticsService` — playlist analytics (channel/group counts, health score, EPG/logo coverage, duplicate detection, favorites)

### Server Layer (`src/fluxo/server/`)
- `PlaylistServer` — lightweight local HTTP server serving M3U playlists via shareable link tokens (stdlib `http.server`, daemon thread, default port 7481)
- `SharedLink` — data model for shareable links with PBKDF2-HMAC-SHA256 password protection, expiry, access tracking, and group filtering

### UI Layer (`src/fluxo/ui/`)

```
┌──────────────────────────────────────────────────────────┐
│ MainWindow                                               │
│ ┌──────────┬──────────────────────────┬─────────────────┐│
│ │GroupPanel │  ChannelTableWidget      │  DetailPanel    ││
│ │          │  (model/view + proxy)    │                 ││
│ │          │  ┌────────────────────┐  │                 ││
│ │          │  │  SearchBar         │  │                 ││
│ │          │  ├────────────────────┤  │                 ││
│ │          │  │  QTableView        │  │                 ││
│ │          │  │  (ChannelModel)    │  │                 ││
│ │          │  └────────────────────┘  │                 ││
│ └──────────┴──────────────────────────┴─────────────────┘│
│ StatusBar                                                │
└──────────────────────────────────────────────────────────┘
```

- `MainWindow` — primary application window with menu bar and status bar
- `ChannelTableWidget` — virtualized table for channel list display with inline editing
- `GroupPanel` — sidebar for group/category navigation
- `DetailPanel` — sidebar for editing selected channel details
- `SearchBar` — search and filter controls with favorites toggle
- `StatusBar` — channel count, group count, server status
- **Dialogs:** Import, Export, Bulk Edit, EPG, Settings, Sharing

### Persistence Layer (`src/fluxo/persistence/`)
- `Settings` — application preferences (theme, recent files, column widths, etc.)
- `AutosaveManager` — periodic project state snapshots for crash recovery

## Key Design Decisions

1. **Qt Model/View** — Channel table uses Qt's model/view architecture for virtualized rendering of large lists
2. **Background Workers** — Parsing, stream checking, and import use QThread workers to keep the UI responsive
3. **Signal/Slot** — Loose coupling between components via Qt signals
4. **Dataclasses** — Clean, typed domain models without ORM overhead
5. **JSON project files** — Human-readable, versionable project format (.fluxo)
6. **Lazy imports** — `SharingService` uses a lazy import for `PlaylistServer` to avoid circular dependencies via `services/__init__.py`
7. **Localhost by default** — `PlaylistServer` binds to `127.0.0.1`; `SharingService` opts in to `0.0.0.0` for LAN sharing

---

*Part of [Fluxo](../README.md) by [diShine Digital Agency](https://dishine.it).*
