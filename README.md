# sssync

[![PyPI](https://img.shields.io/pypi/v/sssync)](https://pypi.org/project/sssync/)
[![Downloads](https://img.shields.io/pypi/dm/sssync)](https://pypistats.org/packages/sssync)
[![Python versions](https://img.shields.io/pypi/pyversions/sssync)](https://pypi.org/project/sssync/)
[![Tests](https://img.shields.io/github/actions/workflow/status/uprcse/sssync/tests.yml?branch=master&label=tests)](https://github.com/uprcse/sssync/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A scriptable playlist sync tool for Qobuz, Spotify, and Jellyfin.

```
sssync sync spotify qobuz --all
sssync sync qobuz jellyfin <playlist-id> "My Playlist"
sssync sync qobuz jellyfin --dry-run
```

## Features

- **Sync playlists** from Spotify or Qobuz into Qobuz or Jellyfin (Spotify is read-only, so it's a source only)
- **ISRC-first matching** — exact track identification via ISRC, with fuzzy title/artist/duration fallback
- **Incremental, append-only syncs** — existing playlist contents are never touched; re-running adds only what's missing
- **Favorites sync** between services that support them
- **Dry-run mode** — preview matches without writing anything
- Simple TOML config, streamrip-style CLI

## Installation

Requires Python 3.11+.

```bash
pip install sssync
```

That's it — works with any standard Python install. If you'd rather keep
`sssync` out of your global environment, install it as an isolated CLI tool
with [`uv`](https://docs.astral.sh/uv/) or [`pipx`](https://pipx.pypa.io/)
instead (either one manages its own venv for you, so `sssync` stays
isolated from your other Python packages):

```bash
uv tool install sssync
# or
pipx install sssync
```

Or skip installing entirely and run it once with `uv`:

```bash
uvx sssync playlists qobuz
```

## Configuration

```bash
sssync config
```

Creates and opens `~/.config/sssync/config.toml`:

```toml
[qobuz]
# Session token: log into https://play.qobuz.com → DevTools →
# Application → Cookies → qobuz.com → user_auth_token
token = ""

[spotify]
client_id = ""
client_secret = ""
redirect_uri = "http://127.0.0.1:8888/callback"

[jellyfin]
url = "http://your-server/jellyfin"
api_key = ""
# or: api_key_path = "~/jellyfin_api_key.txt"
```

Only the sections you use need to be filled in — sources are loaded lazily per command.

## Usage

List playlists on a source:

```bash
sssync playlists qobuz
sssync playlists jellyfin
```

Sync a playlist (accepts a name, an id, or a URL):

```bash
sssync sync spotify qobuz "My Playlist"
sssync sync qobuz jellyfin <playlist-id>
sssync sync qobuz jellyfin <playlist-id> "My Playlist"
```

Sync everything:

```bash
sssync sync spotify qobuz --all
```

Preview without writing:

```bash
sssync sync qobuz jellyfin <playlist-id> --dry-run
```

Sync favorites:

```bash
sssync favorites spotify qobuz
```

## How matching works

1. **ISRC** — if the source track has an ISRC, services that support looking one up directly (Qobuz, Spotify) are queried by ISRC first, for an exact match without depending on text search ranking. Jellyfin has no dedicated ISRC field to query, so it relies on step 2.
2. **Fuzzy** — normalized title/artist similarity (rapidfuzz) with a duration tolerance, run against a plain text search. If any candidate happens to carry a matching ISRC it still wins outright; otherwise the highest-scoring candidate above the thresholds is used. Thresholds are tunable in the `[sync]` section of the config:

```toml
[sync]
title_threshold = 80
artist_threshold = 75
duration_tolerance_ms = 5000
min_score = 75
```

Unmatched tracks are reported, never silently dropped. API errors during matching are captured per track and included in the sync report.

## Safety

Writes are append-only by design. `sssync` never removes or reorders tracks in an existing destination playlist, and dry-run makes no changes at all. Destination playlists keep their cover art and metadata.

## Development

```bash
git clone https://github.com/uprcse/sssync.git
cd sssync
pip install -e ".[dev]"
pytest tests/
ruff check sssync tests
```

CI runs pytest + ruff on Python 3.11–3.13. Releases are published to PyPI automatically on tag push via Trusted Publishing.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## License

MIT — see [LICENSE](LICENSE).
