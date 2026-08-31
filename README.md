# sssync

A scriptable playlist sync tool for Qobuz, Spotify, and Jellyfin.

## Features

- Sync playlists in any direction between Qobuz, Spotify, and Jellyfin
- ISRC-based track matching (exact) with fuzzy title/artist/duration fallback
- Incremental, append-only syncs — existing playlist contents are never touched
- Favorites sync between services that support them
- Simple TOML config, streamrip-style CLI

## Installation

```bash
pip install git+https://github.com/uprcse/sssync.git
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
# or: api_key_path = "~/jellyfin_key.txt"
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
   tolerance. Thresholds are tunable in `[sync]` in the config.

Unmatched tracks are reported, never silently dropped.

## License

MIT
