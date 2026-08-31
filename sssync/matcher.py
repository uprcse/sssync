"""Track matching — ISRC first, then fuzzy title/artist/duration."""

import re
import unicodedata

from rapidfuzz import fuzz

from .clients.base import Track

TITLE_THRESHOLD = 80
ARTIST_THRESHOLD = 75
DURATION_TOLERANCE_MS = 5000
MIN_SCORE = 75


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def match_score(a: Track, b: Track) -> float:
    """0-100 similarity between two tracks."""
    t = fuzz.ratio(normalize(a.title), normalize(b.title))
    ar = fuzz.ratio(normalize(a.artist), normalize(b.artist))
    dur = 100.0
    if a.duration_ms and b.duration_ms:
        diff = abs(a.duration_ms - b.duration_ms)
        dur = 100.0 if diff <= DURATION_TOLERANCE_MS else max(0.0, 100 - diff / 100)
    return 0.5 * t + 0.3 * ar + 0.2 * dur


def is_match(a: Track, b: Track) -> bool:
    t = fuzz.ratio(normalize(a.title), normalize(b.title))
    ar = fuzz.ratio(normalize(a.artist), normalize(b.artist))
    title_ok = t >= TITLE_THRESHOLD
    artist_ok = ar >= ARTIST_THRESHOLD
    if not (title_ok and artist_ok):
        return False
    if a.duration_ms and b.duration_ms:
        if abs(a.duration_ms - b.duration_ms) > DURATION_TOLERANCE_MS and t < 90:
            return False
    return True


def best_match(track: Track, candidates: list[Track]) -> Track | None:
    """Pick the best candidate: ISRC exact, else highest fuzzy score."""
    if track.isrc:
        for c in candidates:
            if c.isrc and c.isrc.upper() == track.isrc.upper():
                return c
    best, best_s = None, 0.0
    for c in candidates:
        if is_match(track, c):
            s = match_score(track, c)
            if s > best_s:
                best, best_s = c, s
    if best is not None and best_s >= MIN_SCORE:
        return best
    return None
