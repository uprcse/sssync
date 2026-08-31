"""Spotify client — OAuth via spotipy, read-only on playlists/favorites."""

import re

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from ..exceptions import ConfigError
from .base import Client, Playlist, Track

SCOPE = "playlist-read-private playlist-read-collaborative user-library-read"


class SpotifyClient(Client):
    name = "spotify"
    read_only = True  # no playlist-modify scope; Spotify is a source only

    def __init__(self, config: dict):
        super().__init__(config)
        self.sp: spotipy.Spotify | None = None

    def authenticate(self):
        missing = [k for k in ("client_id", "client_secret") if not self.config.get(k)]
        if missing:
            raise ConfigError(
                f"[spotify] missing {', '.join(missing)} in ~/.config/sssync/config.toml. "
                "Create an app at https://developer.spotify.com/dashboard and add "
                "redirect URI http://127.0.0.1:8888/callback"
            )
        auth = SpotifyOAuth(
            client_id=self.config["client_id"],
            client_secret=self.config["client_secret"],
            redirect_uri=self.config.get("redirect_uri", "http://127.0.0.1:8888/callback"),
            scope=SCOPE,
            open_browser=True,
        )
        self.sp = spotipy.Spotify(auth_manager=auth)
        self.sp.current_user()  # fail fast on bad credentials

    # --- helpers ---
    @staticmethod
    def _playlist_id(ref: str) -> str:
        """Accept a bare ID or an open.spotify.com URL."""
        m = re.search(r"playlist/([A-Za-z0-9]+)", ref)
        return m.group(1) if m else ref

    @staticmethod
    def _to_track(item: dict) -> Track | None:
        t = item.get("track") or {}
        if not t or t.get("is_local"):
            return None  # local files have no searchable identity
        artists = t.get("artists") or [{}]
        isrc = (t.get("external_ids") or {}).get("isrc")
        return Track(
            title=t.get("name", ""),
            artist=", ".join(a.get("name", "") for a in artists if a.get("name")) or "Unknown",
            album=(t.get("album") or {}).get("name", ""),
            duration_ms=t.get("duration_ms"),
            isrc=isrc,
            source_id=t.get("id"),
        )

    # --- reading ---
    def list_playlists(self):
        out, offset = [], 0
        while True:
            page = self.sp.current_user_playlists(limit=50, offset=offset)
            for p in page["items"]:
                out.append(Playlist(
                    name=p["name"],
                    source_id=p["id"],
                    description=p.get("description", ""),
                    track_count=p["tracks"]["total"],
                ))
            if not page.get("next"):
                break
            offset += 50
        return out

    def get_playlist_tracks(self, playlist_id):
        pid = self._playlist_id(playlist_id)
        out, offset = [], 0
        while True:
            page = self.sp.playlist_items(pid, limit=100, offset=offset)
            for item in page["items"]:
                tr = self._to_track(item)
                if tr:
                    out.append(tr)
            if not page.get("next"):
                break
            offset += 100
        return out

    def search_track(self, track):
        # field queries break on colons/quotes and multi-artist strings —
        # use a plain query with the primary artist only
        primary = track.artist.split(",")[0].strip()
        q = f"{track.title} {primary}"
        res = self.sp.search(q=q, type="track", limit=10)
        from ..matcher import best_match
        cands = [
            Track(
                title=t["name"],
                artist=", ".join(a["name"] for a in t["artists"]),
                album=t.get("album", {}).get("name", ""),
                duration_ms=t.get("duration_ms"),
                isrc=t.get("external_ids", {}).get("isrc"),
                source_id=t["id"],
            )
            for t in res["tracks"]["items"]
        ]
        return best_match(track, cands)

    # --- favorites (read) ---
    def get_favorite_tracks(self):
        out, offset = [], 0
        while True:
            page = self.sp.current_user_saved_tracks(limit=50, offset=offset)
            for item in page["items"]:
                tr = self._to_track(item)
                if tr:
                    out.append(tr)
            if not page.get("next"):
                break
            offset += 50
        return out
