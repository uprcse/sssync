"""Client interface — every music service implements this.

Reading methods populate normalized `Track` objects. Writing is an
optional capability: Spotify is read-only by design (its OAuth scope
grants no playlist-modify), so write methods default to a clear
ReadOnlyError rather than being abstract. sssync never destructively
modifies a playlist — writes are append-only.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..exceptions import ReadOnlyError

if TYPE_CHECKING:
    from ..matcher import MatchConfig


@dataclass
class Track:
    """Normalized track identity shared across clients."""

    title: str
    artist: str
    album: str = ""
    duration_ms: int | None = None
    isrc: str | None = None
    source_id: str | None = None  # native track id at the client
    extra: dict = field(default_factory=dict)

    def __str__(self):
        return f"{self.artist} — {self.title}"


@dataclass
class Playlist:
    name: str
    source_id: str | None = None
    description: str = ""
    track_count: int = 0


class Client(ABC):
    name: str = "abstract"
    read_only: bool = False

    match_cfg: "MatchConfig"

    def __init__(self, config: dict):
        from ..matcher import DEFAULT  # lazy: matcher imports Track from here

        self.config = config
        self.match_cfg = DEFAULT
        # process-lifetime cache: the same track (e.g. one that appears in
        # several playlists) is looked up at most once per `sssync` run.
        # Cleared implicitly on exit — see search_track() for why it can't
        # grow unbounded within a run either.
        self._search_cache: dict[tuple, Track | None] = {}

    @abstractmethod
    def authenticate(self) -> None:
        """Validate credentials. Raise AuthError if they're missing/bad."""

    # --- reading (required) ---
    @abstractmethod
    def list_playlists(self) -> list[Playlist]: ...

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str) -> list[Track]: ...

    @abstractmethod
    def _search_track(self, track: Track) -> Track | None:
        """Find the closest native track for a normalized Track, or None.

        Implement this (not search_track) — the public search_track()
        wraps it with a per-run cache.
        """

    def search_track(self, track: Track) -> Track | None:
        """Cached lookup: at most one real search per unique track per run."""
        key = (track.isrc, track.title, track.artist)
        if key not in self._search_cache:
            self._search_cache[key] = self._search_track(track)
        return self._search_cache[key]

    def search_by_isrc(self, isrc: str) -> Track | None:
        """Direct ISRC lookup, for services whose search indexes it.

        Default: unsupported. `search_track` implementations that can query
        by ISRC should override this and try it before falling back to
        fuzzy title/artist search — a real ISRC match isn't guaranteed to
        rank in the top results of a plain-text search.
        """
        return None

    # --- writing (optional; read-only clients leave these) ---
    def find_playlist_by_name(self, name: str) -> Playlist | None:
        if self.read_only:
            raise ReadOnlyError(f"{self.name} is read-only")
        for p in self.list_playlists():
            if p.name == name:
                return p
        return None

    def create_playlist(self, name: str, description: str = "") -> str:
        raise ReadOnlyError(f"{self.name} does not support creating playlists")

    def add_tracks(self, playlist_id: str, tracks: list[Track]) -> int:
        raise ReadOnlyError(f"{self.name} does not support adding tracks")

    # --- favorites (optional) ---
    def get_favorite_tracks(self) -> list[Track]:
        raise NotImplementedError(f"{self.name} does not support favorites")

    def add_favorite_track(self, track: Track) -> bool:
        raise NotImplementedError(f"{self.name} does not support favorites")
