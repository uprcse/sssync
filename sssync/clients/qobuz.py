"""Qobuz client — token auth, same scheme as the web player / streamrip."""

from pathlib import Path

import requests

from ..exceptions import AuthError, ConfigError
from ..matcher import best_match, match_isrc
from .base import Client, Playlist, Track

BASE_URL = "https://www.qobuz.com/api.json/0.2"
DEFAULT_APP_ID = "798273057"


class QobuzClient(Client):
    name = "qobuz"

    def __init__(self, config: dict):
        super().__init__(config)
        token = config.get("token")
        if not token and config.get("token_path"):
            token = Path(
                config["token_path"].replace("~", str(Path.home()), 1)
            ).read_text().strip()
        if not token:
            raise ConfigError(
                "[qobuz] no token in ~/.config/sssync/config.toml.\n"
                "Get it: log into https://play.qobuz.com → DevTools (F12) → "
                "Application → Cookies → qobuz.com → user_auth_token"
            )
        self.app_id = config.get("app_id", DEFAULT_APP_ID)
        self.s = requests.Session()
        self.s.headers.update({
            "X-App-Id": self.app_id,
            "X-User-Auth-Token": token,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://play.qobuz.com",
            "Referer": "https://play.qobuz.com/",
        })
        self.user_id = None

    def authenticate(self):
        if self.user_id:
            return  # already authenticated this run, no need to re-check
        data = self._get("favorite/getUserFavorites", type="albums", limit=1)
        if "user" in data and "id" in data["user"]:
            self.user_id = data["user"]["id"]
        if not self.user_id:
            raise AuthError(
                "[qobuz] could not determine user id, token may be invalid"
            )

    def _get(self, endpoint, **params):
        r = self.s.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
        if r.status_code in (400, 401):
            raise AuthError(
                "[qobuz] token rejected — grab a fresh user_auth_token from "
                "play.qobuz.com cookies"
            )
        r.raise_for_status()
        return r.json()

    def _post(self, endpoint, **params):
        r = self.s.post(f"{BASE_URL}/{endpoint}", data=params, timeout=15)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _playlist_id(ref: str) -> str:
        return ref.rstrip("/").split("/")[-1]

    # --- reading ---
    def list_playlists(self):
        self.authenticate()
        out, limit, offset = [], 100, 0
        while True:
            data = self._get(
                "playlist/getUserPlaylists",
                user_id=self.user_id, limit=limit, offset=offset,
            )
            items = (data.get("playlists") or {}).get("items", [])
            for p in items:
                out.append(Playlist(
                    name=p.get("name", ""),
                    source_id=str(p["id"]),
                    track_count=p.get("tracks_count", 0),
                ))
            total = (data.get("playlists") or {}).get("total", 0)
            offset += limit
            if offset >= total or len(items) < limit:
                break
        return out

    def get_playlist_tracks(self, playlist_id):
        pid = self._playlist_id(playlist_id)
        out, limit, offset = [], 100, 0
        while True:
            data = self._get(
                "playlist/get", playlist_id=pid,
                limit=limit, offset=offset, extra="tracks",
            )
            items = data.get("tracks", {}).get("items", [])
            for t in items:
                album = t.get("album") or {}
                artist = (
                    (t.get("performer") or {}).get("name")
                    or (album.get("artist") or {}).get("name")
                    or "Unknown"
                )
                out.append(Track(
                    title=t.get("title", ""),
                    artist=artist,
                    album=album.get("title", ""),
                    duration_ms=t.get("duration") * 1000 if t.get("duration") else None,
                    isrc=t.get("isrc"),
                    source_id=str(t["id"]),
                ))
            if len(items) < limit:
                break
            offset += limit
        return out

    @staticmethod
    def _to_tracks(data) -> list[Track]:
        return [
            Track(
                title=t.get("title", ""),
                artist=(t.get("performer") or {}).get("name", "Unknown"),
                album=(t.get("album") or {}).get("title", ""),
                duration_ms=t.get("duration") * 1000 if t.get("duration") else None,
                isrc=t.get("isrc"),
                source_id=str(t["id"]),
            )
            for t in (data.get("tracks") or {}).get("items", [])
        ]

    def search_by_isrc(self, isrc):
        # catalog/search indexes ISRC as searchable text — querying the raw
        # ISRC reliably surfaces the exact track without a title/artist guess.
        data = self._get("catalog/search", query=isrc, limit=10)
        return match_isrc(isrc, self._to_tracks(data))

    def _search_track(self, track):
        if track.isrc:
            hit = self.search_by_isrc(track.isrc)
            if hit is not None:
                return hit
        data = self._get("catalog/search", query=f"{track.artist} {track.title}", limit=10)
        return best_match(track, self._to_tracks(data), self.match_cfg)

    # --- writing ---
    def find_playlist_by_name(self, name):
        for p in self.list_playlists():
            if p.name == name:
                return p
        return None

    def create_playlist(self, name, description=""):
        data = self._post(
            "playlist/create", name=name, description=description, is_public=1,
        )
        return str(data["id"])

    def add_tracks(self, playlist_id, tracks):
        # Qobuz accepts comma-joined ids — batch instead of one POST per track
        ids = [t.source_id for t in tracks if t.source_id]
        added = 0
        for i in range(0, len(ids), 100):
            batch = ",".join(ids[i:i + 100])
            self._post(
                "playlist/addTracks", playlist_id=playlist_id, track_ids=batch,
            )
            added += len(batch.split(","))
        return added

    # --- favorites ---
    def get_favorite_tracks(self):
        self.authenticate()
        out, limit, offset = [], 500, 0
        while True:
            data = self._get(
                "favorite/getUserFavorites", type="tracks",
                limit=limit, offset=offset,
            )
            items = data.get("tracks", {}).get("items", [])
            for t in items:
                out.append(Track(
                    title=t.get("title", ""),
                    artist=(t.get("performer") or {}).get("name", "Unknown"),
                    duration_ms=t.get("duration") * 1000 if t.get("duration") else None,
                    isrc=t.get("isrc"),
                    source_id=str(t["id"]),
                ))
            if len(items) < limit:
                break
            offset += limit
        return out

    def add_favorite_track(self, track):
        if not track.source_id:
            return False
        self._post("favorite/add", track_ids=track.source_id)
        return True
