"""Client interface — every music service implements this.

Reading methods populate normalized `Track` objects. Writing is an
optional capability: Spotify is read-only by design (its OAuth scope
grants no playlist-modify), so write methods default to a clear
ReadOnlyError rather than being abstract. sssync never destructively
modifies a playlist — writes are append-only.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..exceptions import ReadOnlyError


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

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def authenticate(self) -> None:
        """Validate credentials. Raise AuthError if they're missing/bad."""

    # --- reading (required) ---
    @abstractmethod
    def list_playlists(self) -> list[Playlist]: ...

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str) -> list[Track]: ...

    @abstractmethod
    def search_track(self, track: Track) -> Track | None:
        """Find the closest native track for a normalized Track, or None."""

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
