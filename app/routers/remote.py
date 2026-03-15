"""Remote router stub — /api/remote/* endpoints for GitHub/GitLab auth and push.

All endpoint implementations raise NotImplementedError. They land in Plan 16-02/03.
Module-level service imports are required so unittest.mock.patch targeting
app.routers.remote.remote_auth (etc.) works correctly in tests.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services import (
    github_api,  # noqa: F401
    gitlab_api,  # noqa: F401
    remote_auth,  # noqa: F401
)

router = APIRouter(prefix="/api/remote", tags=["remote"])
