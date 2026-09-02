"""Shared fixtures for the sssync test suite.

FakeClient is an in-memory stand-in for a real Client implementation
(Qobuz/Spotify/Jellyfin) so matcher/sync logic can be exercised without
ever touching the network.
"""

from sssync.clients.base import Client, Playlist, Track


class FakeClient(Client):
    """Scriptable in-memory Client — no network calls, ever."""

    def __init__(
        self,
        name,
        playlists=None,
        tracks_by_playlist=None,
        search_results=None,
        favorite_tracks=None,
    ):
        super().__init__({})
        self.name = name
        self._playlists = list(playlists or [])
        self._tracks = dict(tracks_by_playlist or {})  # playlist_id -> list[Track]
        # keyed by (title, artist) -> Track | Exception | None
        self._search_results = dict(search_results or {})
        self._favorite_tracks = list(favorite_tracks or [])
        self.created_playlists = []  # (id, name, description)
        self.added_tracks = []  # (playlist_id, [Track, ...])
        self.search_calls = []  # tracks passed to search_track, in order
        self.added_favorites = []  # tracks passed to add_favorite_track, in order

    def authenticate(self):
        pass

    def list_playlists(self):
        return list(self._playlists)

    def get_playlist_tracks(self, playlist_id):
        return list(self._tracks.get(playlist_id, []))

    def search_track(self, track):
        self.search_calls.append(track)
        result = self._search_results.get((track.title, track.artist))
        if isinstance(result, Exception):
            raise result
        return result

    def find_playlist_by_name(self, name):
        for p in self._playlists:
            if p.name == name:
                return p
        return None

    def create_playlist(self, name, description=""):
        new_id = f"new-{len(self.created_playlists)}"
        self.created_playlists.append((new_id, name, description))
        self._playlists.append(Playlist(name=name, source_id=new_id))
        self._tracks[new_id] = []
        return new_id

    def add_tracks(self, playlist_id, tracks):
        self.added_tracks.append((playlist_id, list(tracks)))
        self._tracks.setdefault(playlist_id, []).extend(tracks)
        return len(tracks)

    def get_favorite_tracks(self):
        return list(self._favorite_tracks)

    def add_favorite_track(self, track):
        self.added_favorites.append(track)
        return True


def make_track(title="Song", artist="Artist", **kwargs):
    return Track(title=title, artist=artist, **kwargs)
