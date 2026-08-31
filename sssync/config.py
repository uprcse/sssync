"""Config handling for sssync — TOML at ~/.config/sssync/config.toml."""

import os
from pathlib import Path
from functools import lru_cache

DEFAULT_CONFIG = """\
# sssync configuration
# Sources are enabled lazily — a section only needs to be present and
# complete for the commands that use it.

[qobuz]
# Session token from https://play.qobuz.com (DevTools → Application → Cookies
# → user_auth_token). See `sssync config --docs qobuz` for a walkthrough.
token = ""

[spotify]
client_id = ""
client_secret = ""
redirect_uri = "http://127.0.0.1:8888/callback"

[jellyfin]
url = "http://your-server/jellyfin"
api_key = ""
# Or point at a file containing the key instead:
# api_key_path = "~/JELLYFIN_API_KEY.txt"

[sync]
# Fuzzy matching thresholds
title_threshold = 80
artist_threshold = 75
duration_tolerance_ms = 5000
min_score = 75
"""


def config_dir() -> Path:
    if (env := os.environ.get("SSSYNC_CONFIG_DIR")):
        return Path(env).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME", "~/.config")
    return Path(xdg).expanduser() / "sssync"


def config_path() -> Path:
    return config_dir() / "config.toml"


def ensure_config() -> Path:
    p = config_path()
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(DEFAULT_CONFIG)
    return p


def load() -> dict:
    import tomllib

    p = ensure_config()
    with open(p, "rb") as f:
        cfg = tomllib.load(f)
    return cfg


def section(cfg: dict, name: str) -> dict:
    """Get a source's config section, erroring clearly if missing/empty."""
    s = cfg.get(name)
    if s is None:
        raise SystemExit(
            f"No [{name}] section in {config_path()}. "
            f"Run `sssync config` to edit it."
        )
    return s


@lru_cache(maxsize=None)
def sources_registry():
    from .clients.qobuz import QobuzClient
    from .clients.spotify import SpotifyClient
    from .clients.jellyfin import JellyfinClient

    return {
        "qobuz": QobuzClient,
        "spotify": SpotifyClient,
        "jellyfin": JellyfinClient,
    }


def make_source(cfg: dict, name: str):
    """Instantiate a client for `name` from config, with auth applied."""
    try:
        cls = sources_registry()[name]
    except KeyError:
        raise SystemExit(
            f"Unknown source '{name}'. Available: {', '.join(sources_registry())}"
        )
    client = cls(section(cfg, name))
    client.authenticate()
    return client
