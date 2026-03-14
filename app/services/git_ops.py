"""Git operations service — skeleton stubs (Plan 02 implements)."""

from __future__ import annotations


def is_git_repo(folder: str) -> bool:
    """Return True if the folder is inside a git repository."""
    raise NotImplementedError("implemented in Plan 02")


def git_init(folder: str) -> None:
    """Initialise a new git repository in the given folder."""
    raise NotImplementedError("implemented in Plan 02")


def get_git_identity() -> dict:
    """Return global git user.name and user.email as {'name': ..., 'email': ...}."""
    raise NotImplementedError("implemented in Plan 02")


def set_git_identity(name: str, email: str) -> None:
    """Set global git user.name and user.email."""
    raise NotImplementedError("implemented in Plan 02")
