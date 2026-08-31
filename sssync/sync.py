"""Sync engine — resolves tracks from a source playlist into a destination."""

from dataclasses import dataclass, field

from .clients.base import Client, Track
from .matcher import normalize


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
) -> tuple[list[Track], list[Track], list[str]]:
    """Map normalized tracks onto dest-native tracks via dest.search_track.

    Returns (resolved, unmatched, errors). Search errors are captured per
    track so one API failure doesn't kill the run.
    """
    resolved, unmatched, errors = [], [], []
    for track in tracks:
        try:
            hit = dest.search_track(track)
        except Exception as e:  # noqa: BLE001 — capture any client failure per track
            errors.append(f"{track}: {e}")
            unmatched.append(track)
            continue
        if hit is not None:
            resolved.append(hit)
        else:
            unmatched.append(track)
    return resolved, unmatched, errors


def sync_playlist(
    source: Client,
    dest: Client,
    playlist_ref: str,
    dest_name: str | None = None,
    dry_run: bool = False,
    is_id: bool = False,
) -> SyncReport:
    """Sync one playlist source → dest. Append-only at the destination."""
    report = SyncReport(source=source.name, dest=dest.name, playlist=playlist_ref)

    if is_id:
        src_id = playlist_ref
        report.playlist = playlist_ref
    else:
        src_pl = source.find_playlist_by_name(playlist_ref)
        if src_pl is None:
            src_id = playlist_ref  # fall back: might still be an id/url
            report.playlist = playlist_ref
        else:
            src_id = src_pl.source_id
            report.playlist = src_pl.name

    src_tracks = source.get_playlist_tracks(src_id)

    dest_name = dest_name or report.playlist
    target = dest.find_playlist_by_name(dest_name)
    existing = dest.get_playlist_tracks(target.source_id) if target else []

    # skip tracks already present (incremental, non-destructive)
    have = {(normalize(t.title), normalize(t.artist)) for t in existing}
    missing = [
        t for t in src_tracks
        if (normalize(t.title), normalize(t.artist)) not in have
    ]

    resolved, unmatched, errors = resolve_tracks(missing, dest)
    report.matched = len(resolved)
    report.unmatched = unmatched
    report.errors = errors

    if dry_run:
        return report

    new_id = target.source_id if target else dest.create_playlist(dest_name)
    if resolved:
        dest.add_tracks(new_id, resolved)
    return report
