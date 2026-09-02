"""Spotify client — OAuth via spotipy, read-only on playlists/favorites."""

import re

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from ..exceptions import ConfigError
from ..matcher import best_match, match_isrc
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
        import os

        from spotipy.cache_handler import CacheFileHandler

        cache_path = self.config.get(
            "token_cache", os.path.expanduser("~/.config/sssync/spotify_token.cache")
        )
        auth = SpotifyOAuth(
            client_id=self.config["client_id"],
            client_secret=self.config["client_secret"],
            redirect_uri=self.config.get("redirect_uri", "http://127.0.0.1:8888/callback"),
            scope=SCOPE,
            open_browser=True,
            cache_handler=CacheFileHandler(cache_path=cache_path),
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
        # current API wraps the track under "item"; legacy responses use
        # "track". The inner object also has a "track" boolean — never read
        # the track data from that flag.
        t = item.get("item") or {}
        if not t and isinstance(item.get("track"), dict):
            t = item["track"]
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
                # some items (local-files playlists, audiobooks) lack a
                # tracks object — treat as zero and keep going
                tracks = p.get("tracks") or {}
                out.append(Playlist(
                    name=p.get("name") or p["id"],
                    source_id=p["id"],
                    description=p.get("description", ""),
                    track_count=tracks.get("total", 0),
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

    @staticmethod
    def _to_tracks(items) -> list[Track]:
        return [
            Track(
                title=t["name"],
                artist=", ".join(a["name"] for a in t["artists"]),
                album=t.get("album", {}).get("name", ""),
                duration_ms=t.get("duration_ms"),
                isrc=t.get("external_ids", {}).get("isrc"),
                source_id=t["id"],
            )
            for t in items
        ]

    def search_by_isrc(self, isrc):
        # the search API supports a dedicated isrc: field filter — an exact,
        # single-call lookup instead of hoping a text search surfaces it.
        res = self.sp.search(q=f"isrc:{isrc}", type="track", limit=10)
        return match_isrc(isrc, self._to_tracks(res["tracks"]["items"]))

    def search_track(self, track):
        if track.isrc:
            hit = self.search_by_isrc(track.isrc)
            if hit is not None:
                return hit
        # field queries break on colons/quotes and multi-artist strings —
        # use a plain query with the primary artist only
        primary = track.artist.split(",")[0].strip()
        q = f"{track.title} {primary}"
        res = self.sp.search(q=q, type="track", limit=10)
        return best_match(track, self._to_tracks(res["tracks"]["items"]))

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
