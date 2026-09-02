"""Client.search_track's per-run cache (base class behavior, all clients get it)."""

from conftest import FakeClient, make_track


def test_search_track_caches_repeated_calls_for_the_same_track():
    hit = make_track("Song", "Artist", source_id="dest-1")
    client = FakeClient("dest", search_results={("Song", "Artist"): hit})
    track = make_track("Song", "Artist")

    first = client.search_track(track)
    second = client.search_track(track)

    assert first is hit
    assert second is hit
    assert client.search_calls == [track]  # only searched once


def test_search_track_cache_keys_on_isrc_title_and_artist_separately():
    hit_a = make_track("Song A", "Artist", source_id="a")
    hit_b = make_track("Song B", "Artist", source_id="b")
    client = FakeClient(
        "dest",
        search_results={("Song A", "Artist"): hit_a, ("Song B", "Artist"): hit_b},
    )

    client.search_track(make_track("Song A", "Artist"))
    client.search_track(make_track("Song B", "Artist"))
    client.search_track(make_track("Song A", "Artist"))  # repeat of the first

    assert len(client.search_calls) == 2  # each distinct track searched once


def test_search_track_caches_a_no_match_result_too():
    client = FakeClient("dest")  # no search_results configured -> every search misses
    track = make_track("Unknown", "Nobody")

    assert client.search_track(track) is None
    assert client.search_track(track) is None
    assert client.search_calls == [track]  # the miss itself was cached


def test_search_track_cache_is_scoped_to_the_client_instance():
    hit = make_track("Song", "Artist", source_id="dest-1")
    track = make_track("Song", "Artist")
    a = FakeClient("dest", search_results={("Song", "Artist"): hit})
    b = FakeClient("dest", search_results={("Song", "Artist"): hit})

    a.search_track(track)
    b.search_track(track)

    assert a.search_calls == [track]
    assert b.search_calls == [track]  # a fresh client has its own cache, not a.'s
