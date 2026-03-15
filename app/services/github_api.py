"""GitHub REST API service stub — repo creation, user info, collision resolution.

All functions raise NotImplementedError. Implementations land in Plan 16-02.
"""

from __future__ import annotations


def create_github_repo(token: str, name: str) -> dict:
    """POST /user/repos — create a private repo.

    Returns GitHub API response dict with clone_url, html_url, etc.
    """
    raise NotImplementedError


def get_github_username(token: str) -> str:
    """GET /user — resolve the authenticated user's login name."""
    raise NotImplementedError


def github_repo_exists(token: str, owner: str, repo_name: str) -> bool:
    """Return True if the repo owner/repo_name exists on GitHub."""
    raise NotImplementedError


def find_available_repo_name(token: str, owner: str, base_slug: str) -> str:
    """Find a non-colliding repo name by appending -2, -3, etc. as needed."""
    raise NotImplementedError
