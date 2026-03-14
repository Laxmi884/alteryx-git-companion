"""Git operations service — subprocess wrappers for git commands."""

from __future__ import annotations

import subprocess


def is_git_repo(folder: str) -> bool:
    """Return True if the folder is inside a git repository."""
    result = subprocess.run(
        ["git", "-C", folder, "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def git_init(folder: str) -> None:
    """Initialise a new git repository in the given folder."""
    subprocess.run(
        ["git", "-C", folder, "init"],
        capture_output=True,
        text=True,
        check=True,
    )


def get_git_identity() -> dict:
    """Return global git user.name and user.email as {'name': ..., 'email': ...}."""

    def _get(key: str) -> str | None:
        r = subprocess.run(
            ["git", "config", "--global", key],
            capture_output=True,
            text=True,
        )  # check=False intentional — exit 1 means key not set, not an error
        return r.stdout.strip() or None

    return {"name": _get("user.name"), "email": _get("user.email")}


def set_git_identity(name: str, email: str) -> None:
    """Set global git user.name and user.email."""
    subprocess.run(["git", "config", "--global", "user.name", name], check=True)
    subprocess.run(["git", "config", "--global", "user.email", email], check=True)
