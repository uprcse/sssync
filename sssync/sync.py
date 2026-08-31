"""Sync engine — resolves tracks from a source playlist into a destination."""

from dataclasses import dataclass, field

from .clients.base import Client, Track
from .matcher import best_match


@dataclass
class SyncReport:
    source: str
    dest: str
    playlist: str
    matched: int = 0
    unmatched: list[Track] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"{self.source} → {self.dest}: {self.playlist}",
            f"  matched:   {self.matched}",
            f"  unmatched: {len(self.unmatched)}",
        ]
        for t in self.unmatched:
            lines.append(f"    - {t}")
        for e in self.errors:
            lines.append(f"  error: {e}")
        return "\n".join(lines)


def resolve_tracks(
    tracks: list[Track],
    dest: Client,
    dest_library: list[Track] | None = None,
) -> tuple[list[Track], list[Track]]:
    """Map normalized tracks onto dest-native tracks.

    Strategy:
      1. If the dest playlist/library already contains the track (matched by
         identity), reuse its native id — no API search needed.
      2. Otherwise search the dest service.

    Returns (resolved, unmatched).
    """
    from .matcher import normalize

    resolved, unmatched = [], []
    # index the dest library once for cheap identity lookup
    index: dict[tuple, Track] = {}
    if dest_library:
        for t in dest_library:
            index[(normalize(t.title), normalize(t.artist))] = t

    for track in tracks:
        hit = index.get((normalize(track.title), normalize(track.artist)))
        if hit is None:
            try:
                hit = dest.search_track(track)
            except Exception as e:
                unmatched.append(track)
                continue
        if hit is not None:
            resolved.append(hit)
        else:
            unmatched.append(track)
    return resolved, unmatched


def sync_playlist(
    source: Client,
    dest: Client,
    playlist_ref: str,
    dest_name: str | None = None,
    dry_run: bool = False,
) -> SyncReport:
    """Sync one playlist source → dest. Append-only at the destination."""
    report = SyncReport(source=source.name, dest=dest.name, playlist=playlist_ref)

    # accept a playlist id/url or a name
    src_pl = None
    if source.name != "jellyfin":
        src_pl = source.find_playlist_by_name(playlist_ref)
    if src_pl is None:
        src_pl = f"ref:{playlist_ref}"  # fall through; id/url still works

    src_tracks = source.get_playlist_tracks(
        src_pl.source_id if not isinstance(src_pl, str) else playlist_ref
    )
    report.playlist = (
        src_pl.name if not isinstance(src_pl, str) else playlist_ref
    )

    dest_name = dest_name or report.playlist
    target = dest.find_playlist_by_name(dest_name)

    if target is not None:
        existing = dest.get_playlist_tracks(target.source_id)
    else:
        existing = []

    # skip tracks already present (incremental, non-destructive)
    have = {(t.title.lower(), t.artist.lower()) for t in existing}
    missing = [
        t for t in src_tracks
        if (t.title.lower(), t.artist.lower()) not in have
    ]

    resolved, unmatched = resolve_tracks(missing, dest)
    report.matched = len(resolved)
    report.unmatched = unmatched

    if dry_run:
        return report

    if target is None:
        new_id = dest.create_playlist(dest_name)
    else:
        new_id = target.source_id

    if resolved:
        dest.add_tracks(new_id, resolved)
    return report
