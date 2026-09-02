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

- Syncs playlists from Spotify or Qobuz into Qobuz or Jellyfin. Spotify is read only, so it can only be a source.
- Matches tracks by ISRC first, with fuzzy title, artist, and duration matching as a fallback.
- Syncs are incremental and append only. Existing playlist contents are never touched, and re-running only adds what's missing.
- Syncs favorites between services that support them.
- Dry run mode previews matches without writing anything.
- Simple TOML config. CLI modeled on streamrip.

## Installation

Requires Python 3.11 or greater.

```bash
pip install sssync
```

That's it. It works with any standard Python install.

If you'd rather keep sssync out of your global environment, install it as an isolated CLI tool with [uv](https://docs.astral.sh/uv/) or [pipx](https://pipx.pypa.io/) instead. Either one manages its own venv for you.

```bash
uv tool install sssync
# or
pipx install sssync
```

Or skip installing entirely and run it once with uv.

```bash
uvx sssync playlists qobuz
```

## Configuration

```bash
sssync config
```

This creates and opens `~/.config/sssync/config.toml`.

```toml
[qobuz]
# Session token: log into https://play.qobuz.com, open DevTools,
# then Application > Cookies > qobuz.com > user_auth_token
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

Only the sections you use need to be filled in. Sources are loaded lazily per command.

## Usage

List playlists on a source.

```bash
sssync playlists qobuz
sssync playlists jellyfin
```

Sync a playlist. Accepts a name, an id, or a URL.

```bash
sssync sync spotify qobuz "My Playlist"
sssync sync qobuz jellyfin <playlist-id>
sssync sync qobuz jellyfin <playlist-id> "My Playlist"
```

Sync everything.

```bash
sssync sync spotify qobuz --all
```

Preview without writing.

```bash
sssync sync qobuz jellyfin <playlist-id> --dry-run
```

Sync favorites.

```bash
sssync favorites spotify qobuz
```

## How matching works

1. **ISRC.** If the source track has an ISRC, services that support looking one up directly (Qobuz, Spotify) are queried by ISRC first. This gives an exact match without depending on text search ranking. Jellyfin has no dedicated ISRC field to query, so it relies on step 2.
2. **Fuzzy.** Normalized title, artist, and duration similarity (via rapidfuzz), run against a plain text search. If a candidate happens to carry a matching ISRC it still wins outright. Otherwise the highest scoring candidate above the thresholds is used. Thresholds are tunable in the `[sync]` section of the config:

```toml
[sync]
title_threshold = 80
artist_threshold = 75
duration_tolerance_ms = 5000
min_score = 75
```

Unmatched tracks are reported, never silently dropped. API errors during matching are captured per track and included in the sync report.

## Safety

Writes are append only by design. sssync never removes or reorders tracks in an existing destination playlist, and dry run makes no changes at all. Destination playlists keep their cover art and metadata.

## Development

```bash
git clone https://github.com/uprcse/sssync.git
cd sssync
pip install -e ".[dev]"
pytest tests/
ruff check sssync tests
```

CI runs pytest and ruff on Python 3.11 through 3.13. Releases are published to PyPI automatically on tag push via Trusted Publishing.

## Contributing

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), and releases are versioned and tagged with [commitizen](https://commitizen-tools.github.io/commitizen/). See [CONTRIBUTING.md](CONTRIBUTING.md).

## Disclaimer

I will not be responsible for how you use sssync. By using it, you agree to the terms and conditions of the Qobuz, Spotify, and Jellyfin APIs.

## License

MIT. See [LICENSE](LICENSE).
