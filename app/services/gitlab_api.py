"""GitLab REST API service — PAT validation and project creation."""

from __future__ import annotations

import httpx

GITLAB_BASE = "https://gitlab.com/api/v4"


def validate_gitlab_token(token: str) -> dict | None:
    """Validate a GitLab PAT via GET /api/v4/user.

    Returns user info dict on success, None if token is invalid (401).
    """
    resp = httpx.get(
        f"{GITLAB_BASE}/user",
        headers={"PRIVATE-TOKEN": token},
    )
    if resp.status_code == 200:
        return resp.json()
    return None


def create_gitlab_project(token: str, name: str) -> dict:
    """POST /api/v4/projects — create a private GitLab project.

    Returns GitLab API response dict with http_url_to_repo, etc.
    """
    resp = httpx.post(
        f"{GITLAB_BASE}/projects",
        headers={"PRIVATE-TOKEN": token},
        json={"name": name, "visibility": "private"},
    )
    resp.raise_for_status()
    return resp.json()
