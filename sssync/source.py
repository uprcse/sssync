"""Source interface — every music service implements this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Track:
    """Normalized track identity shared across sources."""
    title: str
    artist: str
    album: str = ""
    duration_ms: int | None = None
    isrc: str | None = None
    source_id: str | None = None  # native track id at the source
    extra: dict = field(default_factory=dict)


@dataclass
class Playlist:
    name: str
    source_id: str | None = None
    description: str = ""
    track_count: int = 0


class Source(ABC):
    """A music service that can hold playlists/favorites and accept tracks."""

    name: str = "abstract"

    def __init__(self, config: dict):
        self.config = config

    # --- reading ---
    @abstractmethod
    def list_playlists(self) -> list[Playlist]: ...

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str) -> list[Track]: ...

    @abstractmethod
    def search_track(self, track: Track) -> Track | None:
        """Find the closest native track for a normalized Track, or None."""

    # --- writing ---
    @abstractmethod
    def create_playlist(self, name: str, description: str = "") -> str: ...

    @abstractmethod
    def add_tracks(self, playlist_id: str, tracks: list[Track]) -> int:
        """Append native tracks; returns count added. Never destructive."""

    @abstractmethod
    def find_playlist_by_name(self, name: str) -> Playlist | None: ...

    # --- favorites (optional) ---
    def get_favorite_tracks(self) -> list[Track]:
        raise NotImplementedError(f"{self.name} does not support favorites")

    def add_favorite_track(self, track: Track) -> bool:
        raise NotImplementedError(f"{self.name} does not support favorites")
