
from conftest import FakeClient, make_track

from sssync.clients.base import Playlist
from sssync.sync import SyncReport, resolve_tracks, sync_playlist

# --- resolve_tracks ---

def test_resolve_tracks_searches_when_no_library_given():
    dest = FakeClient("dest")
    track = make_track("Song", "Artist")

    resolve_tracks([track], dest)

    assert dest.search_calls == [track]  # search is the only path now


def test_resolve_tracks_falls_back_to_search_when_not_in_library():
    hit = make_track("Song", "Artist", source_id="dest-1")
    dest = FakeClient("dest", search_results={("Song", "Artist"): hit})
    track = make_track("Song", "Artist")

    resolved, unmatched, _ = resolve_tracks([track], dest)

    assert resolved == [hit]
    assert unmatched == []
    assert dest.search_calls == [track]


def test_resolve_tracks_marks_unmatched_when_search_returns_none():
    dest = FakeClient("dest", search_results={("Song", "Artist"): None})
    track = make_track("Song", "Artist")

    resolved, unmatched, errors = resolve_tracks([track], dest)

    assert resolved == []
    assert unmatched == [track]
    assert errors == []


def test_resolve_tracks_captures_search_errors_without_raising():
    boom = RuntimeError("api down")
    dest = FakeClient("dest", search_results={("Song", "Artist"): boom})
    track = make_track("Song", "Artist")

    resolved, unmatched, errors = resolve_tracks([track], dest)

    assert resolved == []
    assert unmatched == [track]
    assert len(errors) == 1
    assert "api down" in errors[0]


def test_resolve_tracks_continues_after_one_track_errors():
    boom = RuntimeError("api down")
    ok_hit = make_track("Other", "Band", source_id="dest-2")
    dest = FakeClient(
        "dest",
        search_results={
            ("Song", "Artist"): boom,
            ("Other", "Band"): ok_hit,
        },
    )
    bad = make_track("Song", "Artist")
    good = make_track("Other", "Band")

    resolved, unmatched, errors = resolve_tracks([bad, good], dest)

    assert resolved == [ok_hit]
    assert unmatched == [bad]
    assert len(errors) == 1


# --- sync_playlist ---

def _source_with_playlist(name="qobuz", playlist_name="My Mix", tracks=None):
    pl = Playlist(name=playlist_name, source_id="src-pl-1", track_count=len(tracks or []))
    return FakeClient(name, playlists=[pl], tracks_by_playlist={"src-pl-1": tracks or []})


def test_sync_playlist_creates_new_dest_playlist_and_adds_resolved_tracks():
    tracks = [make_track("Song A", "Artist"), make_track("Song B", "Artist")]
    source = _source_with_playlist(tracks=tracks)
    hit_a = make_track("Song A", "Artist", source_id="d1")
    hit_b = make_track("Song B", "Artist", source_id="d2")
    dest = FakeClient(
        "dest",
        search_results={
            ("Song A", "Artist"): hit_a,
            ("Song B", "Artist"): hit_b,
        },
    )

    report = sync_playlist(source, dest, "My Mix")

    assert report.matched == 2
    assert report.unmatched == []
    assert report.errors == []
    assert len(dest.created_playlists) == 1
    new_id, name, _desc = dest.created_playlists[0]
    assert name == "My Mix"
    assert dest.added_tracks == [(new_id, [hit_a, hit_b])]


def test_sync_playlist_dry_run_does_not_write_anything():
    tracks = [make_track("Song A", "Artist")]
    source = _source_with_playlist(tracks=tracks)
    hit_a = make_track("Song A", "Artist", source_id="d1")
    dest = FakeClient("dest", search_results={("Song A", "Artist"): hit_a})

    report = sync_playlist(source, dest, "My Mix", dry_run=True)

    assert report.matched == 1
    assert dest.created_playlists == []
    assert dest.added_tracks == []


def test_sync_playlist_skips_tracks_already_present_regardless_of_punctuation():
    tracks = [make_track("Don't Stop Believin'", "Journey")]
    source = _source_with_playlist(tracks=tracks)
    existing_pl = Playlist(name="My Mix", source_id="dest-pl-1")
    already_there = make_track("Dont Stop Believin", "Journey", source_id="existing-1")
    dest = FakeClient(
        "dest",
        playlists=[existing_pl],
        tracks_by_playlist={"dest-pl-1": [already_there]},
    )

    report = sync_playlist(source, dest, "My Mix")

    assert report.matched == 0
    assert report.unmatched == []
    assert dest.search_calls == []  # never searched; treated as already synced
    assert dest.added_tracks == []  # nothing new to add


def test_sync_playlist_reuses_existing_dest_playlist_instead_of_creating_one():
    tracks = [make_track("New Song", "Artist")]
    source = _source_with_playlist(tracks=tracks)
    existing_pl = Playlist(name="My Mix", source_id="dest-pl-1")
    hit = make_track("New Song", "Artist", source_id="d1")
    dest = FakeClient(
        "dest",
        playlists=[existing_pl],
        tracks_by_playlist={"dest-pl-1": []},
        search_results={("New Song", "Artist"): hit},
    )

    report = sync_playlist(source, dest, "My Mix")

    assert dest.created_playlists == []
    assert dest.added_tracks == [("dest-pl-1", [hit])]
    assert report.matched == 1


def test_sync_playlist_records_search_errors_in_report():
    tracks = [make_track("Song A", "Artist")]
    source = _source_with_playlist(tracks=tracks)
    dest = FakeClient(
        "dest", search_results={("Song A", "Artist"): RuntimeError("timeout")}
    )

    report = sync_playlist(source, dest, "My Mix")

    assert report.matched == 0
    assert len(report.unmatched) == 1
    assert len(report.errors) == 1
    assert "timeout" in report.errors[0]


def test_sync_playlist_resolves_by_name_even_for_jellyfin_source():
    # Regression test: sync_playlist used to special-case source.name ==
    # "jellyfin" and skip find_playlist_by_name entirely, so a Jellyfin
    # source playlist could only ever be referenced by raw id, never name.
    tracks = [make_track("Song A", "Artist")]
    source = _source_with_playlist(name="jellyfin", playlist_name="Chill", tracks=tracks)
    hit = make_track("Song A", "Artist", source_id="d1")
    dest = FakeClient("dest", search_results={("Song A", "Artist"): hit})

    report = sync_playlist(source, dest, "Chill")

    assert report.playlist == "Chill"
    assert report.matched == 1


def test_sync_playlist_falls_back_to_raw_ref_when_name_not_found():
    tracks = [make_track("Song A", "Artist")]
    source = _source_with_playlist(playlist_name="My Mix", tracks=tracks)
    # look up an id directly, not a name -> find_playlist_by_name misses,
    # falls through to treating the ref as a literal playlist id
    source._tracks["12345"] = tracks
    dest = FakeClient("dest", search_results={("Song A", "Artist"): make_track("Song A", "Artist", source_id="d1")})

    report = sync_playlist(source, dest, "12345")

    assert report.playlist == "12345"
    assert report.matched == 1


def test_sync_report_summary_includes_errors():
    report = SyncReport(source="a", dest="b", playlist="p", matched=1, errors=["boom"])
    text = report.summary()
    assert "boom" in text
    assert "matched:   1" in text
