# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

This project uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
and [commitizen](https://commitizen-tools.github.io/commitizen/) to generate
new entries here on every release. See [CONTRIBUTING.md](CONTRIBUTING.md).

Version headers below must stay in the `## v<version> (<date>)` form
commitizen recognizes (`tag_format` in `pyproject.toml`). Anything else
breaks its incremental changelog generation: it can't find the last
documented version, so it silently regenerates the whole file from scratch
instead of prepending the new release, which is exactly what happened the
first time this project tried it. Only include a version header here once
that version is actually tagged; commitizen generates the entry for the
next release itself from commit messages, it isn't something to pre-write
by hand.

Work merged between the `v0.2.2` tag and the adoption of Conventional
Commits predates commit-driven changelog generation and isn't repeated
here; see the individual commit messages on `master` for that detail.

## v0.2.3 (2026-09-02)

### Fix

- **changelog**: use commitizen-recognized version headers
- **qobuz**: skip re-authenticating when already authenticated

## v0.2.2 (2026-08-31)

### Fixed

- Spotify client updated for the current API response shape (tracks nested
  under `item`, playlists with a null track count).

### Added

- Persistent Spotify OAuth token cache, so re-running commands doesn't
  require re-authenticating in a browser each time.

## v0.2.1 (2026-08-31)

### Changed

- Genericized all CLI and README examples. No personal playlist data in
  the docs.
- Expanded the README: usage examples moved up top, a Safety section, and
  `MatchConfig` documentation.

## v0.2.0 (2026-08-31)

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
