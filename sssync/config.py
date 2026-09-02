"""Config handling for sssync — TOML at ~/.config/sssync/config.toml."""

import os
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib  # type: ignore

from .exceptions import ConfigError

DEFAULT_CONFIG = """\
# sssync configuration
# Sources are enabled lazily — a section only needs to be present and
# complete for the commands that use it.

[qobuz]
# Session token from https://play.qobuz.com (DevTools → Application →
# Cookies → qobuz.com → user_auth_token).
token = ""

[spotify]
client_id = ""
client_secret = ""
redirect_uri = "http://127.0.0.1:8888/callback"

[jellyfin]
url = "http://your-server/jellyfin"
api_key = ""
# Or point at a file containing the key instead:
# api_key_path = "~/jellyfin_api_key.txt"
# On a multi-user server, pin one explicitly:
# user_id = "..."

[sync]
# Fuzzy matching thresholds (read by the matcher)
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
    p = ensure_config()
    with open(p, "rb") as f:
        return tomllib.load(f)


def section(cfg: dict, name: str) -> dict:
    """Get a source's config section, erroring clearly if missing."""
    s = cfg.get(name)
    if s is None:
        raise ConfigError(
            f"No [{name}] section in {config_path()}. "
            f"Run `sssync config` to edit it."
        )
    return s


def make_source(cfg: dict, name: str):
    """Instantiate a client for `name` from config, with auth applied."""
    from .clients.jellyfin import JellyfinClient
    from .clients.qobuz import QobuzClient
    from .clients.spotify import SpotifyClient
    from .matcher import config_from

    registry = {
        "qobuz": QobuzClient,
        "spotify": SpotifyClient,
        "jellyfin": JellyfinClient,
    }
    try:
        cls = registry[name]
    except KeyError:
        raise ConfigError(
            f"Unknown source '{name}'. Available: {', '.join(registry)}"
        )
    client = cls(section(cfg, name))
    client.match_cfg = config_from(cfg.get("sync"))
    client.authenticate()
    return client
