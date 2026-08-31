"""Jellyfin client — playlists + library search over the REST API."""

from pathlib import Path

import requests

from ..exceptions import AuthError, ConfigError
from ..matcher import best_match
from .base import Client, Playlist, Track


def _jf_isrc(item: dict) -> str | None:
    """Jellyfin stores external ids in ProviderIds; ISRC may appear there."""
    pids = item.get("ProviderIds") or {}
    for v in pids.values():
        if isinstance(v, str) and len(v) == 12 and v[:2].isalpha() and v.isalnum():
            return v
    return None


class JellyfinClient(Client):
    name = "jellyfin"

    def __init__(self, config: dict):
        super().__init__(config)
        self.base = config["url"].rstrip("/")
        key = config.get("api_key")
        if not key and config.get("api_key_path"):
            key = Path(
                config["api_key_path"].replace("~", str(Path.home()), 1)
            ).read_text().strip()
        if not key:
            raise ConfigError(
                "[jellyfin] no api_key in ~/.config/sssync/config.toml "
                "(or api_key_path pointing at a key file)"
            )
        self.s = requests.Session()
        self.s.headers.update({"X-Emby-Token": key})
        self.s.timeout = 15
        self._user_id = config.get("user_id")  # explicit override for multi-user servers

    def authenticate(self):
        try:
            self.user_id()
        except Exception as e:
            raise AuthError(f"[jellyfin] auth failed: {e}") from e

    def _req(self, path, method="GET", body=None, **params):
        r = self.s.request(
            method, f"{self.base}{path}",
            json=body, params=params or None, timeout=15,
        )
        r.raise_for_status()
        raw = r.text
        import json
        return json.loads(raw) if raw else {}

    def user_id(self):
        if self._user_id is None:
            users = self._req("/Users")
            if not users:
                raise AuthError("[jellyfin] no users found")
            self._user_id = users[0]["Id"]
        return self._user_id

    # --- reading ---
    def list_playlists(self):
        data = self._req(
            "/Items", IncludeItemTypes="Playlist", Recursive="true",
            UserId=self.user_id(),
        )
        return [
            Playlist(
                name=it["Name"], source_id=it["Id"],
                track_count=it.get("ChildCount", 0),
            )
            for it in data.get("Items", [])
        ]

    def get_playlist_tracks(self, playlist_id):
        out, offset = [], 0
        while True:
            data = self._req(
                f"/Playlists/{playlist_id}/Items",
                UserId=self.user_id(),
                Fields="AlbumArtist,Artists,Album,RunTimeTicks",
                Limit=500, StartIndex=offset,
            )
            items = data.get("Items", [])
            for it in items:
                dur = it.get("RunTimeTicks")
                out.append(Track(
                    title=it.get("Name", ""),
                    artist=it.get("AlbumArtist")
                    or (it.get("Artists") or [""])[0] or "Unknown",
                    album=it.get("Album", ""),
                    duration_ms=int(dur / 10000) if dur else None,
                    source_id=it["Id"],
                ))
            offset += len(items)
            if offset >= data.get("TotalRecordCount", len(items)) or not items:
                break
        return out

    def search_track(self, track):
        # include artist in the search so common titles don't push the
        # right result past the limit
        q = f"{track.artist.split(',')[0].strip()} {track.title}"
        data = self._req(
            "/Items", SearchTerm=q, IncludeItemTypes="Audio",
            Recursive="true", Limit=15,
            Fields="AlbumArtist,Artists,RunTimeTicks,ProviderIds",
        )
        cands = []
        for it in data.get("Items", []):
            dur = it.get("RunTimeTicks")
            cands.append(Track(
                title=it.get("Name", ""),
                artist=it.get("AlbumArtist")
                or (it.get("Artists") or [""])[0] or "Unknown",
                duration_ms=int(dur / 10000) if dur else None,
                isrc=_jf_isrc(it),
                source_id=it["Id"],
            ))
        return best_match(track, cands)

    # --- writing ---
    def find_playlist_by_name(self, name):
        for p in self.list_playlists():
            if p.name == name:
                return p
        return None

    def create_playlist(self, name, description=""):
        body = {
            "Name": name, "Ids": [],
            "UserId": self.user_id(), "MediaType": "Audio",
        }
        return self._req("/Playlists", method="POST", body=body)["Id"]

    def add_tracks(self, playlist_id, tracks):
        # chunk — a few hundred ids in one query string exceeds URL limits
        ids = [t.source_id for t in tracks if t.source_id]
        for i in range(0, len(ids), 100):
            batch = ids[i:i + 100]
            self._req(
                f"/Playlists/{playlist_id}/Items",
                method="POST", Ids=",".join(batch), UserId=self.user_id(),
            )
        return len(ids)
