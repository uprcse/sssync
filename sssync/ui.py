"""Progress display — rich-based, with graceful non-TTY fallback.

In a terminal: spinner for indeterminate steps, progress bar with live
counts for track matching. Piped/CI: silent, plain output only.
"""

import sys

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )

    _HAS_RICH = True
except ImportError:  # pragma: no cover — rich is a hard dep, this is safety
    _HAS_RICH = False

console = Console(stderr=True) if _HAS_RICH else None


def is_interactive() -> bool:
    return sys.stderr.isatty() and _HAS_RICH


class DummyProgress:
    """Non-TTY stand-in: same API, no output, task() returns a no-op id."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def add_task(self, description, **kwargs):
        return 0

    def update(self, task_id, **kwargs):
        pass

    def advance(self, task_id, amount=1):
        pass

    @property
    def tasks(self):
        class _T:
            total = None
            completed = 0

            @property
            def finished(self):
                return True

        return [_T()]


class DummySpinner:
    def __init__(self, text=""):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def progress_bar(transient: bool = False):
    """Indeterminate-safe progress: spinner while total is unknown,
    bar + M/N counts once the total lands."""
    if not is_interactive():
        return DummyProgress()
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=transient,
    )


def spinner(text: str):
    """Small spinner for one-off waits (auth, fetching lists)."""
    if not is_interactive():
        return DummySpinner()
    from rich.progress import Progress as _P

    p = _P(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    )
    p.add_task(text, total=None)
    return p
