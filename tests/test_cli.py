"""CLI-level tests for `favorites` — dedup identity, error resilience, dry-run."""

from click.testing import CliRunner
from conftest import FakeClient, make_track

from sssync import config as config_mod
from sssync.cli import main


def run_favorites(monkeypatch, src, dst, extra_args=()):
    monkeypatch.setattr(config_mod, "load", dict)
    clients = {"src": src, "dst": dst}
    monkeypatch.setattr(config_mod, "make_source", lambda cfg, name: clients[name])
    runner = CliRunner()
    return runner.invoke(main, ["favorites", "src", "dst", *extra_args])


def test_favorites_dedup_ignores_punctuation_and_diacritics(monkeypatch):
    # already present at dest, just spelled without the apostrophe
    existing = make_track("Dont Stop Believin", "Journey")
    src = FakeClient("src", favorite_tracks=[make_track("Don't Stop Believin'", "Journey")])
    dst = FakeClient("dst", favorite_tracks=[existing])

    result = run_favorites(monkeypatch, src, dst)

    assert result.exit_code == 0
    assert "0 of 1 favorites not in dst" in result.output
    assert dst.added_favorites == []  # never re-searched or re-added


def test_favorites_one_search_failure_does_not_abort_the_run(monkeypatch):
    ok = make_track("Song A", "Artist A")
    bad = make_track("Song B", "Artist B")
    hit = make_track("Song A", "Artist A", source_id="dst-1")
    src = FakeClient("src", favorite_tracks=[ok, bad])
    dst = FakeClient(
        "dst",
        search_results={
            ("Song A", "Artist A"): hit,
            ("Song B", "Artist B"): RuntimeError("rate limited"),
        },
    )

    result = run_favorites(monkeypatch, src, dst)

    assert result.exit_code == 0
    assert dst.added_favorites == [hit]  # the good track still got added
    assert "Added 1 favorites to dst" in result.output
    assert "error: " in result.output  # the failure was reported, not swallowed


def test_favorites_dry_run_makes_no_writes(monkeypatch):
    src = FakeClient("src", favorite_tracks=[make_track("Song", "Artist")])
    dst = FakeClient("dst", search_results={("Song", "Artist"): make_track("Song", "Artist")})

    result = run_favorites(monkeypatch, src, dst, extra_args=["--dry-run"])

    assert result.exit_code == 0
    assert dst.search_calls == []  # dry-run never even searches
    assert dst.added_favorites == []
