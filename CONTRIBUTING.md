# Contributing

## Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

```
<type>(<optional scope>): <description>

<optional body>

<optional footer>
```

Common types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

Examples:

```
feat(matcher): query destinations by ISRC before falling back to fuzzy search
fix(cli): dedup favorites with normalize() instead of raw lower()
docs: reorder install instructions, pip first
```

A breaking change gets a `!` after the type/scope, or a `BREAKING CHANGE:` footer:

```
feat(clients)!: rename Client.search_track to _search_track for subclasses
```

You can write commits by hand following the format above, or use the guided prompt:

```bash
cz commit
```

Check a message against the format before committing:

```bash
cz check --commit-msg-file <file>
```

## Releasing

Version numbers, `CHANGELOG.md`, and the git tag are generated from commit
history with [commitizen](https://commitizen-tools.github.io/commitizen/),
based on the commit types above (`fix` bumps patch, `feat` bumps minor, a
breaking change bumps major once the project is past `1.0.0`; see
`major_version_zero` in `pyproject.toml` for how that's handled pre-1.0).

This is automated for merges into `master`:

1. Merging `dev` into `master` (or any push to `master`) runs
   `prepare-release.yml`. If there are commits eligible for a release since
   the last tag, it opens or updates a PR titled `bump: version to vX.Y.Z`
   with the version bump and generated changelog already applied. Nothing
   is tagged or published at this point.
2. Review that PR like any other, then merge it. `tag-release.yml` tags the
   version it bumped to and calls `release.yml`, which builds and publishes
   to PyPI via Trusted Publishing.

If there's nothing eligible to release, no PR gets opened; the workflow
just no-ops.

To bump locally instead (for a manual/out-of-band release):

```bash
cz bump
git push && git push --tags
```

Pushing the tag directly also triggers `release.yml` the normal way.

Preview what a bump would do without changing anything:

```bash
cz bump --dry-run
```

## Tests and linting

```bash
pip install -e ".[dev]"
pytest tests/
ruff check sssync tests
```

CI runs both on Python 3.11 through 3.13 for every push to `master`, `dev`,
and every pull request.
