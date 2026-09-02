# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

Everything in this file so far, including `[Unreleased]`, is hand-written
history predating [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
adoption. From the next release on, `cz bump` generates new entries from
commit history instead, grouped by commit type rather than Keep a Changelog's
Added/Changed/Fixed sections. See [CONTRIBUTING.md](CONTRIBUTING.md).


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

## v0.2.3 (2026-09-02)

### Fix

- **qobuz**: skip re-authenticating when already authenticated

## v0.2.2 (2026-08-31)

## v0.2.1 (2026-08-31)

## v0.2.0 (2026-08-31)
