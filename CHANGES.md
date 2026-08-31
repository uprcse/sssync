# Changes

Code review + test pass over `matcher.py` and `sync.py` (and the code paths
they depend on). No network calls were made; all client interaction in tests
goes through an in-memory `FakeClient` (see `tests/conftest.py`).

## Bugs fixed

- **`sync.py` — inconsistent dedup identity broke on punctuation/diacritics.**
  `sync_playlist` decided which source tracks were "already in the dest
  playlist" using raw `.lower()` on title/artist, while every other identity
  check in the codebase (`resolve_tracks`, `matcher.best_match`) uses
  `matcher.normalize()` (strips diacritics and punctuation too). A track like
  `"Don't Stop Believin'"` already in the dest playlist as `"Dont Stop
  Believin"` would not be recognized as a duplicate, get re-searched, and
  potentially get appended a second time. Fixed `sync_playlist` to use
  `normalize()` for the `have`/`missing` comparison, matching the rest of the
  codebase.

- **`sync.py` — `SyncReport.errors` was declared but never populated.**
  The dataclass has an `errors: list[str]` field and `summary()` prints it,
  but `resolve_tracks` caught `search_track` exceptions with a bare
  `except Exception` and silently dropped the message, only recording the
  track as unmatched. A real API failure (timeout, auth error, malformed
  response) looked identical to "no match found" in the report. Changed
  `resolve_tracks` to return `(resolved, unmatched, errors)` and `sync_playlist`
  now copies those into `report.errors`.

- **`sync.py` — Jellyfin sources could never be referenced by playlist name.**
  `sync_playlist` special-cased `source.name == "jellyfin"` to skip the
  `find_playlist_by_name` lookup entirely, forcing every Jellyfin-as-source
  sync to pass a raw playlist id. This contradicts the CLI's own docs
  ("PLAYLIST can be a name, an id, or a URL") and served no purpose —
  `JellyfinClient.find_playlist_by_name` works fine, and passing an id simply
  fails to match any name and falls through to the existing `ref:` fallback,
  same as it does for every other source. Removed the special case.

- **`cli.py` `favorites` — compared track ids across two different services.**
  `existing = {t.source_id for t in dst.get_favorite_tracks()}` was compared
  against `src_tracks`' `source_id`s, but `source_id` is native to whichever
  service produced the `Track` (a Qobuz numeric id vs. a Spotify base62 id,
  etc.) — the two id spaces never overlap. In practice this made the "already
  a favorite" check a no-op: every run treated every source favorite as
  missing, re-searching and re-adding tracks that were already synced. Fixed
  to compare by normalized `(title, artist)` identity, the same approach
  `sync_playlist` already uses for playlist tracks.

## Cleanup (no behavior change)

- Deleted `sssync/source.py` and `sssync/sources/{qobuz,jellyfin}.py`. These
  were an orphaned, unused duplicate of `sssync/clients/` — a second,
  independent set of `Track`/`Playlist`/`Source` definitions that had already
  drifted from the real implementation (e.g. a different JSON key for
  playlist pagination) and were not imported anywhere (`grep` confirmed zero
  references outside the files themselves). Left in place, they're a trap
  for a future edit landing in the dead copy instead of the live one used by
  `config.sources_registry()`.
- Removed dead imports: `resolve_tracks`/`best_match` were imported but never
  called in `cli.py`'s `favorites` command; `best_match` was imported but
  unused in `sync.py`.
- Simplified `SpotifyClient._to_track`'s ISRC extraction — it used a
  `dict and [dict] or []` one-liner to work around `{}` being falsy;
  replaced with `(t.get("external_ids") or {}).get("isrc")`. No behavior
  change, just readability.

## Reviewed, not changed (notes for follow-up)

- **No concurrency anywhere.** `resolve_tracks` issues one `search_track`
  HTTP call per unmatched track, sequentially. This is correct (no race
  conditions to speak of) but will be slow for large playlists. Left as-is —
  adding concurrency would need per-client rate-limit handling that's out of
  scope for this pass.
- **`sync --all` does redundant work per playlist.** In `cli.py`, each
  playlist is synced via `sync_playlist(src, dst, p.source_id, p.name, ...)`.
  Since `p.source_id` is an id, not a name, `find_playlist_by_name` inside
  `sync_playlist` always misses (after doing a full, possibly paginated,
  `list_playlists()` call) before falling back to treating the ref as an id.
  Functionally harmless but O(n) wasted `list_playlists()` calls for an
  `--all` sync of n playlists. Would need a "this ref is already an id" flag
  threaded through `sync_playlist` to fix properly.
- **`JellyfinClient.get_playlist_tracks` hardcodes `Limit=10000`** with no
  offset pagination — playlists larger than that are silently truncated.
  Unlikely in practice; not fixed.
- **`_jf_isrc` (clients/jellyfin.py) guesses ISRC by shape** (12 alphanumeric
  chars, first two alphabetic) among arbitrary `ProviderIds` values. Low risk
  of a false positive on some other provider id of the same shape; left as a
  heuristic since Jellyfin doesn't expose a dedicated ISRC field.

## Tests added

`tests/conftest.py` — `FakeClient`, an in-memory `Client` implementation for
scripting playlists/library/search results/errors without any network I/O.

`tests/test_matcher.py` — `normalize` (case/diacritics/punctuation), `match_score`
(duration tolerance/weighting), `is_match` (title/artist thresholds, the
duration-mismatch escape hatch for near-exact titles), and `best_match`
(ISRC-exact precedence, case-insensitive ISRC, highest-score selection,
no-match-below-threshold).

`tests/test_sync.py` — `resolve_tracks` (dest-library identity shortcut,
search fallback, unmatched-on-None, error capture/continuation) and
`sync_playlist` (create vs. reuse dest playlist, dry-run makes no writes,
punctuation-insensitive dedup against existing dest tracks, error propagation
into the report, and a regression test for the Jellyfin-by-name fix).

32 tests, all passing:

```
python3 -m pytest tests/
```
