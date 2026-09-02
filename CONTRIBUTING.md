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

```bash
cz bump
git push && git push --tags
```

`cz bump` computes the next version from commits since the last tag, updates
`sssync/__init__.py` and `CHANGELOG.md`, and creates the version commit and
tag. Pushing the tag triggers `.github/workflows/release.yml`, which builds
and publishes to PyPI via Trusted Publishing.

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
