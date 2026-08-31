"""Track matching — ISRC first, then fuzzy title/artist/duration.

Thresholds are configurable via a MatchConfig; module-level defaults
apply when none is supplied.
"""

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

from .clients.base import Track


@dataclass
class MatchConfig:
    title_threshold: int = 80
    artist_threshold: int = 75
    duration_tolerance_ms: int = 5000
    min_score: float = 75.0


DEFAULT = MatchConfig()


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def match_score(a: Track, b: Track, cfg: MatchConfig = DEFAULT) -> float:
    """0-100 similarity between two tracks."""
    t = fuzz.ratio(normalize(a.title), normalize(b.title))
    ar = fuzz.ratio(normalize(a.artist), normalize(b.artist))
    dur = 100.0
    if a.duration_ms and b.duration_ms:
        diff = abs(a.duration_ms - b.duration_ms)
        if diff <= cfg.duration_tolerance_ms:
            dur = 100.0
        else:
            dur = max(0.0, 100 - diff / 100)
    return 0.5 * t + 0.3 * ar + 0.2 * dur


def is_match(a: Track, b: Track, cfg: MatchConfig = DEFAULT) -> bool:
    t = fuzz.ratio(normalize(a.title), normalize(b.title))
    ar = fuzz.ratio(normalize(a.artist), normalize(b.artist))
    title_ok = t >= cfg.title_threshold
    artist_ok = ar >= cfg.artist_threshold
    if not (title_ok and artist_ok):
        return False
    return not (
        a.duration_ms
        and b.duration_ms
        and abs(a.duration_ms - b.duration_ms) > cfg.duration_tolerance_ms
        and t < 90
    )


def best_match(
    track: Track,
    candidates: list[Track],
    cfg: MatchConfig = DEFAULT,
) -> Track | None:
    """Pick the best candidate: ISRC exact, else highest fuzzy score."""
    if track.isrc:
        for c in candidates:
            if c.isrc and c.isrc.upper() == track.isrc.upper():
                return c
    best, best_s = None, 0.0
    for c in candidates:
        if is_match(track, c, cfg):
            s = match_score(track, c, cfg)
            if s > best_s:
                best, best_s = c, s
    if best is not None and best_s >= cfg.min_score:
        return best
    return None
