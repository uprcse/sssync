# sssync

A scriptable playlist sync tool for Qobuz, Spotify, and Jellyfin.

## Features

- Sync playlists from Spotify or Qobuz into Qobuz or Jellyfin (Spotify is read-only, so it's a source only)
- ISRC-based track matching (exact) with fuzzy title/artist/duration fallback
- Incremental, append-only syncs — existing playlist contents are never touched
- Favorites sync between services that support them
- Simple TOML config, streamrip-style CLI

## Installation

Requires Python 3.11+.

Install as an isolated tool (recommended):

```bash
uv tool install sssync
# or
pipx install sssync
```

Try it without installing anything:

```bash
uvx sssync playlists qobuz
```

Or with pip in a virtualenv:

```bash
pip install sssync
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

## Usage

List playlists on a source:

```bash
sssync playlists qobuz
sssync playlists jellyfin
```

Sync a playlist (accepts a name, id, or URL):

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

1. **ISRC** — if both services expose the track's ISRC, it's an exact match.
2. **Fuzzy** — normalized title/artist similarity (rapidfuzz) with a duration
   tolerance. Thresholds are tunable in the `[sync]` section of the config.

Unmatched tracks are reported, never silently dropped.

## Development

```bash
git clone https://github.com/uprcse/sssync.git
cd sssync
pip install -e ".[dev]"
pytest tests/
ruff check sssync tests
```

CI runs pytest + ruff on Python 3.11–3.13.

## License

MIT — see [LICENSE](LICENSE).
