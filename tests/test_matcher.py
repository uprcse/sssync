from sssync.clients.base import Track
from sssync.matcher import (
    DEFAULT as MATCH_DEFAULT,
)
from sssync.matcher import (
    best_match,
    is_match,
    match_score,
    normalize,
)

# --- normalize ---

def test_normalize_lowercases_and_strips_punctuation():
    assert normalize("Don't Stop, Believin'!") == "dontstopbelievin"


def test_normalize_strips_diacritics():
    assert normalize("Café del Mar") == "cafedelmar"


def test_normalize_handles_none_and_empty():
    assert normalize("") == ""
    assert normalize(None) == ""


# --- match_score ---

def test_match_score_identical_tracks_is_100():
    a = Track(title="Song", artist="Artist", duration_ms=200_000)
    b = Track(title="Song", artist="Artist", duration_ms=200_000)
    assert match_score(a, b) == 100.0


def test_match_score_penalizes_duration_beyond_tolerance():
    a = Track(title="Song", artist="Artist", duration_ms=200_000)
    close = Track(title="Song", artist="Artist", duration_ms=200_000 + MATCH_DEFAULT.duration_tolerance_ms)
    far = Track(title="Song", artist="Artist", duration_ms=200_000 + MATCH_DEFAULT.duration_tolerance_ms + 60_000)
    assert match_score(a, close) == 100.0
    assert match_score(a, far) < 100.0


def test_match_score_ignores_duration_when_missing():
    a = Track(title="Song", artist="Artist", duration_ms=None)
    b = Track(title="Song", artist="Artist", duration_ms=None)
    assert match_score(a, b) == 100.0


# --- is_match ---

def test_is_match_true_for_close_title_and_artist():
    a = Track(title="Bohemian Rhapsody", artist="Queen")
    b = Track(title="Bohemian Rhapsody", artist="Queen")
    assert is_match(a, b) is True


def test_is_match_false_for_different_title():
    a = Track(title="Bohemian Rhapsody", artist="Queen")
    b = Track(title="Radio Ga Ga", artist="Queen")
    assert is_match(a, b) is False


def test_is_match_false_for_different_artist():
    a = Track(title="Song", artist="Artist A")
    b = Track(title="Song", artist="Totally Unrelated Band")
    assert is_match(a, b) is False


def test_is_match_tolerates_minor_title_punctuation_differences():
    a = Track(title="Don't Stop Believin'", artist="Journey")
    b = Track(title="Dont Stop Believin", artist="Journey")
    assert is_match(a, b) is True


def test_is_match_rejects_large_duration_mismatch_unless_title_near_exact():
    # "Yesterday" vs "Yesterday Live" scores ~82: clears TITLE_THRESHOLD (80)
    # but stays below the 90 near-exact bar used by the duration escape hatch.
    a = Track(title="Yesterday", artist="Artist", duration_ms=200_000)
    b = Track(title="Yesterday Live", artist="Artist", duration_ms=400_000)
    assert is_match(a, b) is False


def test_is_match_allows_duration_mismatch_when_title_near_exact():
    a = Track(title="Song", artist="Artist", duration_ms=200_000)
    b = Track(title="Song", artist="Artist", duration_ms=400_000)
    assert is_match(a, b) is True


# --- best_match ---

def test_best_match_prefers_exact_isrc_over_fuzzy_candidates():
    track = Track(title="Song", artist="Artist", isrc="USABC1234567")
    isrc_hit = Track(title="Totally Different Title", artist="Someone Else", isrc="USABC1234567")
    fuzzy_hit = Track(title="Song", artist="Artist")
    result = best_match(track, [fuzzy_hit, isrc_hit])
    assert result is isrc_hit


def test_best_match_isrc_comparison_is_case_insensitive():
    track = Track(title="Song", artist="Artist", isrc="usabc1234567")
    isrc_hit = Track(title="Song", artist="Artist", isrc="USABC1234567")
    assert best_match(track, [isrc_hit]) is isrc_hit


def test_best_match_falls_back_to_fuzzy_when_no_isrc_hit():
    track = Track(title="Song", artist="Artist", isrc="USABC1234567")
    candidate = Track(title="Song", artist="Artist", isrc="DEXYZ7654321")
    assert best_match(track, [candidate]) is candidate


def test_best_match_returns_none_when_no_candidate_clears_threshold():
    track = Track(title="Song", artist="Artist")
    candidates = [Track(title="Completely Unrelated", artist="Nobody")]
    assert best_match(track, candidates) is None


def test_best_match_returns_none_for_empty_candidates():
    track = Track(title="Song", artist="Artist")
    assert best_match(track, []) is None


def test_best_match_picks_highest_scoring_candidate():
    track = Track(title="Song Title", artist="Artist", duration_ms=200_000)
    weaker = Track(title="Song Titl", artist="Artist", duration_ms=190_000)
    stronger = Track(title="Song Title", artist="Artist", duration_ms=200_000)
    result = best_match(track, [weaker, stronger])
    assert result is stronger


def test_min_score_threshold_is_respected_directly():
    # sanity check the module constant hasn't silently drifted
    assert MATCH_DEFAULT.min_score == 75
