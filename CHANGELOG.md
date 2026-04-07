# Changelog

All notable changes to Fluxo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-07

### Changed
- Bumped to production-ready v1.0.0
- Development Status classifier updated to Beta

## [0.4.0] - 2026-04-07

### Added
- Self-hosted local playlist server (`src/fluxo/server/`)
- Dynamic hosted playlist link generation with shareable URLs
- Secure private sharing links with PBKDF2-HMAC-SHA256 password protection
- Link expiration and access tracking
- Group-filtered sharing (share subsets of a playlist)
- Sharing management dialog in the UI
- `SharingService` facade for link CRUD and persistence
- Health endpoint (`/health`) on the local server

## [0.3.0] - 2026-04-07

### Added
- Channel templates/profiles — save, apply, and persist reusable metadata presets
- Metadata normalization rules engine (group names, channel names, URL cleanup)
- Custom collections — user-defined channel groupings independent of M3U groups

## [0.2.0] - 2026-04-07

### Added
- Recent files menu
- Drag-and-drop file import (.m3u/.m3u8)
- Column visibility customization via header context menu
- Table column resizing persistence across sessions
- Favorites toggle and filter

## [0.1.0] - 2026-04-07

### Added
- Initial release
- M3U parser with full metadata support
- XMLTV/EPG parser
- Create, import, edit, and export playlists
- Visual channel list with drag-and-drop reordering
- Group/category management
- Channel metadata editing (name, URL, group, logo, EPG ID)
- Search, filter, and sort
- Duplicate detection
- Bulk edit operations
- Stream health checking
- Project file save/load
- Undo/redo support
- Autosave and recovery
- Dark and light themes
- Keyboard shortcuts
- EPG mapping assistant
