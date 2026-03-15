"""GitLab REST API service stub — PAT validation and project creation.

All functions raise NotImplementedError. Implementations land in Plan 16-02.
"""

from __future__ import annotations


def validate_gitlab_token_api(token: str) -> dict | None:
    """Validate a GitLab PAT via GET /api/v4/user.

    Returns user info dict on success, None if token is invalid (401).
    """
    raise NotImplementedError


def create_gitlab_project(token: str, name: str) -> dict:
    """POST /api/v4/projects — create a private GitLab project.

    Returns GitLab API response dict with http_url_to_repo, etc.
    """
    raise NotImplementedError
