"""Exceptions for sssync — cli.py is the only place that converts to exit codes."""


class SssyncError(Exception):
    """Base class for all sssync errors."""


class ConfigError(SssyncError):
    """Missing or invalid configuration."""


class AuthError(SssyncError):
    """A service rejected our credentials."""


class ReadOnlyError(SssyncError):
    """A write was attempted on a read-only client."""


class NotFoundError(SssyncError):
    """A requested resource (playlist, track) does not exist."""
