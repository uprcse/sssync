# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- ISRC-first matching now queries Qobuz and Spotify directly by ISRC before
  falling back to fuzzy title/artist search, instead of only checking ISRC
  against whatever a generic text search happened to return.
- Progress spinners and a live progress bar (via `rich`) for auth, playlist
  fetches, and track matching, with a silent fallback when output isn't a
  terminal.
- `search_track` results are now cached per client instance for the
  lifetime of a single run, so the same track appearing in multiple
  playlists (or in both a playlist and a favorites sync) is only looked up
  once.

### Fixed

- The `[sync]` config section (`title_threshold`, `artist_threshold`,
  `duration_tolerance_ms`, `min_score`) is now actually read and applied —
  previously it was documented and shipped in the default config but never
  wired into the matcher.
- `favorites` now dedups against the destination using the same
  normalized-identity check as `sync` (strips punctuation/diacritics)
  instead of raw `.lower()`, so titles like `"Don't Stop Believin'"` are no
  longer treated as new every run.
- `favorites` now captures per-track search/add failures and continues
  the run instead of aborting entirely on the first API error.

## [0.2.2] - 2026-08-31

### Fixed

- Spotify client updated for the current API response shape (tracks nested
  under `item`, playlists with a null track count).

### Added

- Persistent Spotify OAuth token cache, so re-running commands doesn't
  require re-authenticating in a browser each time.

## [0.2.1] - 2026-08-31

### Changed

- Genericized all CLI and README examples — no personal playlist data in
  the docs.
- Expanded the README: usage examples moved up top, a Safety section, and
  `MatchConfig` documentation.

## [0.2.0] - 2026-08-31

First published release on PyPI.

### Added

- Packaging metadata, `uv`-first install docs, and the tag-triggered
  PyPI release workflow (Trusted Publishing).
- Full test suite covering the matcher and sync engine.

### Fixed

- Dedup identity, error reporting, and a favorites id-space bug where
  source and destination track ids were compared directly even though
  they come from different services' id spaces.

### Changed

- Split `Client` into required read methods and optional write methods
  (read-only clients, like Spotify, raise a clear error instead of
  silently no-op-ing); introduced `MatchConfig` and the `SssyncError`
  exception hierarchy; batched playlist writes; added pagination to
  playlist/library reads.
