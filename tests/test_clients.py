"""ISRC-first search behavior for clients that support a direct lookup.

No network calls: QobuzClient._get and SpotifyClient.sp.search are stubbed.
"""

from sssync.clients.base import Track
from sssync.clients.qobuz import QobuzClient
from sssync.clients.spotify import SpotifyClient


def qobuz_search_response(items):
    return {"tracks": {"items": items}}


def qobuz_item(title="Song", artist="Artist", isrc=None, track_id="1", duration=200):
    return {
        "title": title,
        "performer": {"name": artist},
        "album": {"title": ""},
        "duration": duration,
        "isrc": isrc,
        "id": track_id,
    }


def make_qobuz_client():
    return QobuzClient({"token": "fake"})


# --- QobuzClient ---

def test_qobuz_authenticate_is_idempotent(monkeypatch):
    client = make_qobuz_client()
    calls = []

    def fake_get(endpoint, **params):
        calls.append(endpoint)
        return {"user": {"id": 42}}

    monkeypatch.setattr(client, "_get", fake_get)
    client.authenticate()
    client.authenticate()
    assert client.user_id == 42
    assert calls == ["favorite/getUserFavorites"]  # second call was skipped


def test_qobuz_list_playlists_does_not_reauthenticate(monkeypatch):
    # mirrors config.make_source: authenticate() once up front, then call
    # a method that used to call authenticate() again internally
    client = make_qobuz_client()
    calls = []

    def fake_get(endpoint, **params):
        calls.append(endpoint)
        if endpoint == "favorite/getUserFavorites":
            return {"user": {"id": 42}}
        return {"playlists": {"items": [], "total": 0}}

    monkeypatch.setattr(client, "_get", fake_get)
    client.authenticate()
    client.list_playlists()
    assert calls == ["favorite/getUserFavorites", "playlist/getUserPlaylists"]



def test_qobuz_search_by_isrc_returns_exact_hit(monkeypatch):
    client = make_qobuz_client()
    calls = []

    def fake_get(endpoint, **params):
        calls.append((endpoint, params))
        return qobuz_search_response([qobuz_item(isrc="USABC1234567", track_id="42")])

    monkeypatch.setattr(client, "_get", fake_get)
    hit = client.search_by_isrc("usabc1234567")
    assert hit is not None
    assert hit.source_id == "42"
    assert calls[0] == ("catalog/search", {"query": "usabc1234567", "limit": 10})


def test_qobuz_search_by_isrc_returns_none_when_absent(monkeypatch):
    client = make_qobuz_client()
    monkeypatch.setattr(client, "_get", lambda *a, **k: qobuz_search_response([]))
    assert client.search_by_isrc("USABC1234567") is None


def test_qobuz_search_track_tries_isrc_before_text_search(monkeypatch):
    client = make_qobuz_client()
    calls = []

    def fake_get(endpoint, **params):
        calls.append(params.get("query"))
        if params["query"] == "USABC1234567":
            return qobuz_search_response([qobuz_item(isrc="USABC1234567", track_id="42")])
        raise AssertionError("text search should not run when ISRC search hits")

    monkeypatch.setattr(client, "_get", fake_get)
    track = Track(title="Song", artist="Artist", isrc="USABC1234567")
    hit = client.search_track(track)
    assert hit.source_id == "42"
    assert calls == ["USABC1234567"]  # only the ISRC query ran


def test_qobuz_search_track_falls_back_to_text_search_when_isrc_misses(monkeypatch):
    client = make_qobuz_client()

    def fake_get(endpoint, **params):
        if params["query"] == "USABC1234567":
            return qobuz_search_response([])  # no ISRC hit
        return qobuz_search_response([qobuz_item(title="Song", artist="Artist", track_id="7")])

    monkeypatch.setattr(client, "_get", fake_get)
    track = Track(title="Song", artist="Artist", isrc="USABC1234567", duration_ms=200_000)
    hit = client.search_track(track)
    assert hit.source_id == "7"


def test_qobuz_search_track_skips_isrc_search_when_track_has_none(monkeypatch):
    client = make_qobuz_client()
    calls = []

    def fake_get(endpoint, **params):
        calls.append(params.get("query"))
        return qobuz_search_response([qobuz_item(title="Song", artist="Artist", track_id="7")])

    monkeypatch.setattr(client, "_get", fake_get)
    track = Track(title="Song", artist="Artist")
    client.search_track(track)
    assert calls == ["Artist Song"]  # straight to the text search


# --- SpotifyClient ---

def spotify_item(title="Song", artists=("Artist",), isrc=None, track_id="1", duration_ms=200_000):
    return {
        "name": title,
        "artists": [{"name": a} for a in artists],
        "album": {"name": ""},
        "duration_ms": duration_ms,
        "external_ids": {"isrc": isrc} if isrc else {},
        "id": track_id,
    }


class FakeSpotipy:
    def __init__(self, responses):
        self.responses = responses  # query -> list[item]
        self.queries = []

    def search(self, q, type, limit):
        self.queries.append(q)
        return {"tracks": {"items": self.responses.get(q, [])}}


def make_spotify_client(responses):
    client = SpotifyClient({})
    client.sp = FakeSpotipy(responses)
    return client


def test_spotify_search_by_isrc_returns_exact_hit():
    client = make_spotify_client({
        "isrc:USABC1234567": [spotify_item(isrc="USABC1234567", track_id="42")],
    })
    hit = client.search_by_isrc("USABC1234567")
    assert hit is not None
    assert hit.source_id == "42"


def test_spotify_search_by_isrc_returns_none_when_absent():
    client = make_spotify_client({"isrc:USABC1234567": []})
    assert client.search_by_isrc("USABC1234567") is None


def test_spotify_search_track_tries_isrc_before_text_search():
    client = make_spotify_client({
        "isrc:USABC1234567": [spotify_item(isrc="USABC1234567", track_id="42")],
        "Song Artist": [spotify_item(title="Song", artists=("Artist",), track_id="99")],
    })
    track = Track(title="Song", artist="Artist", isrc="USABC1234567")
    hit = client.search_track(track)
    assert hit.source_id == "42"
    assert client.sp.queries == ["isrc:USABC1234567"]  # text search never ran


def test_spotify_search_track_falls_back_to_text_search_when_isrc_misses():
    client = make_spotify_client({
        "isrc:USABC1234567": [],
        "Song Artist": [spotify_item(title="Song", artists=("Artist",), track_id="99", duration_ms=200_000)],
    })
    track = Track(title="Song", artist="Artist", isrc="USABC1234567", duration_ms=200_000)
    hit = client.search_track(track)
    assert hit.source_id == "99"
