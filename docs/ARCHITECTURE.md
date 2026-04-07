# Fluxo Architecture

## Overview

Fluxo follows a clean layered architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────┐
│                  UI Layer                    │
│         (PySide6 Widgets + Dialogs)         │
├─────────────────────────────────────────────┤
│               Service Layer                  │
│  (Validation, Dedup, Bulk Ops, Export, EPG) │
├─────────────────────────────────────────────┤
│               Parser Layer                   │
│        (M3U Parser, XMLTV Parser)           │
├─────────────────────────────────────────────┤
│               Model Layer                    │
│    (Channel, Playlist, EPG, Project)        │
├─────────────────────────────────────────────┤
│            Persistence Layer                 │
│    (Settings, Autosave, Project Files)      │
└─────────────────────────────────────────────┘
```

## Layers

### Model Layer (`src/fluxo/models/`)
- Typed dataclasses for all domain entities
- `Channel` — represents a single IPTV channel entry with all metadata
- `Playlist` — collection of channels with header metadata
- `EpgData` / `EpgChannel` / `EpgProgramme` — XMLTV EPG structures
- `Project` — wraps a playlist with undo history, EPG links, and project metadata

### Parser Layer (`src/fluxo/parsers/`)
- `M3UParser` — robust M3U/M3U8 parser handling edge cases (bad encoding, malformed entries, huge files)
- `XmltvParser` — XMLTV/EPG parser extracting channel and programme data

### Service Layer (`src/fluxo/services/`)
- `ValidationService` — stream health checking, EPG mapping validation
- `DeduplicationService` — exact and fuzzy duplicate detection
- `BulkOperationService` — mass rename, move, replace, logo/EPG assignment
- `ExportService` — clean M3U/M3U8 export with metadata preservation
- `ProjectManager` — save/load project files, autosave
- `EpgMapper` — intelligent EPG-to-channel mapping with fuzzy matching

### UI Layer (`src/fluxo/ui/`)
- `MainWindow` — primary application window with menu bar and status bar
- `ChannelTableWidget` — virtualized table for channel list display
- `GroupPanel` — sidebar for group/category navigation
- `DetailPanel` — sidebar for editing selected channel details
- `SearchBar` — search and filter controls
- Various dialogs for import, export, bulk edit, EPG management, settings

### Persistence Layer (`src/fluxo/persistence/`)
- `Settings` — application preferences (theme, recent files, etc.)
- `Autosave` — periodic project state snapshots for crash recovery

## Key Design Decisions

1. **Qt Model/View** — Channel table uses Qt's model/view architecture for virtualized rendering of large lists
2. **Background Workers** — Parsing, stream checking, and import use QThread workers to keep the UI responsive
3. **Signal/Slot** — Loose coupling between components via Qt signals
4. **Dataclasses** — Clean, typed domain models without ORM overhead
5. **JSON project files** — Human-readable, versionable project format
