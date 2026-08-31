"""Jellyfin client — playlists + library search over the REST API."""

import json
from pathlib import Path
import urllib.parse
import urllib.request

from ..clients.base import Client, Playlist, Track
from ..matcher import best_match


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
            key = open(
                config["api_key_path"].replace("~", str(Path.home()), 1)
            ).read().strip()
        if not key:
            raise SystemExit(
                "[jellyfin] no api_key in ~/.config/sssync/config.toml "
                "(or api_key_path pointing at a key file)"
            )
        self.key = key
        self._user_id = None

    def authenticate(self):
        """Verify the API key against the live server."""
        try:
            self.user_id()
        except Exception as e:
            raise SystemExit(f"[jellyfin] auth failed: {e}")

    def _req(self, path, method="GET", body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.base}{path}", data=data, method=method,
            headers={"X-Emby-Token": self.key, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}

    def user_id(self):
        if self._user_id is None:
            users = self._req("/Users")
            if not users:
                raise SystemExit("[jellyfin] no users found")
            self._user_id = users[0]["Id"]
        return self._user_id

    # --- reading ---
    def list_playlists(self):
        data = self._req(
            f"/Items?IncludeItemTypes=Playlist&Recursive=true&UserId={self.user_id()}"
        )
        return [
            Playlist(
                name=it["Name"], source_id=it["Id"],
                track_count=it.get("ChildCount", 0),
            )
            for it in data.get("Items", [])
        ]

    def get_playlist_tracks(self, playlist_id):
        data = self._req(
            f"/Playlists/{playlist_id}/Items?UserId={self.user_id()}"
            "&Fields=AlbumArtist,Artists,Album,RunTimeTicks&Limit=10000"
        )
        out = []
        for it in data.get("Items", []):
            dur = it.get("RunTimeTicks")
            out.append(Track(
                title=it.get("Name", ""),
                artist=it.get("AlbumArtist")
                or (it.get("Artists") or [""])[0] or "Unknown",
                album=it.get("Album", ""),
                duration_ms=int(dur / 10000) if dur else None,
                source_id=it["Id"],
            ))
        return out

    def search_track(self, track):
        q = urllib.parse.quote(track.title)
        data = self._req(
            f"/Items?SearchTerm={q}&IncludeItemTypes=Audio&Recursive=true"
            "&Limit=15&Fields=AlbumArtist,Artists,RunTimeTicks,ProviderIds"
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
        ids = [t.source_id for t in tracks if t.source_id]
        if not ids:
            return 0
        self._req(
            f"/Playlists/{playlist_id}/Items?Ids={','.join(ids)}"
            f"&UserId={self.user_id()}",
            method="POST",
        )
        return len(ids)
