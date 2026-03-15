"""Remote router — /api/remote/* endpoints for GitHub/GitLab auth and push.

Module-level service imports are required so unittest.mock.patch targeting
app.routers.remote.remote_auth (etc.) works correctly in tests.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import (
    git_ops,
    github_api,  # noqa: F401
    gitlab_api,  # noqa: F401
    remote_auth,
)

router = APIRouter(prefix="/api/remote", tags=["remote"])


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class GitLabConnectRequest(BaseModel):
    token: str


class PushRequest(BaseModel):
    project_id: str
    folder: str


# ---------------------------------------------------------------------------
# REMOTE-01: GitHub Device Flow endpoints
# ---------------------------------------------------------------------------


@router.post("/github/start")
def github_start() -> dict:
    """Start GitHub OAuth Device Flow — returns user_code and verification_uri."""
    data = remote_auth.request_device_code()
    return {
        "user_code": data.get("user_code"),
        "verification_uri": data.get("verification_uri"),
        "device_code": data.get("device_code"),
        "interval": data.get("interval"),
        "expires_in": data.get("expires_in"),
    }


@router.get("/github/status")
def github_status() -> dict:
    """Return {connected: bool} based on whether a GitHub token is in keyring."""
    token = remote_auth.get_github_token()
    return {"connected": token is not None}


# ---------------------------------------------------------------------------
# REMOTE-02: GitLab PAT connect endpoint
# ---------------------------------------------------------------------------


@router.post("/gitlab/connect")
def gitlab_connect(body: GitLabConnectRequest) -> dict:
    """Validate GitLab PAT and store in keyring if valid."""
    user = remote_auth.validate_gitlab_token(body.token)
    if user is not None:
        remote_auth.store_gitlab_token(body.token)
        return {"connected": True}
    return {"connected": False, "error": "Invalid token"}


# ---------------------------------------------------------------------------
# REMOTE-04: Push endpoint
# ---------------------------------------------------------------------------


@router.post("/push")
def push(body: PushRequest) -> dict:
    """Push the project folder to its configured remote."""
    token = remote_auth.get_github_token()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated with GitHub")

    try:
        # remote_url would normally come from project config; placeholder for plan 16-03
        remote_url = f"https://github.com/{body.project_id}.git"
        git_ops.git_push(body.folder, remote_url, token)
        return {"success": True}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# REMOTE-06: Ahead/behind status endpoint
# ---------------------------------------------------------------------------


@router.get("/status")
def remote_status(folder: str) -> dict:
    """Return ahead/behind counts and connection status for a project folder."""
    ahead, behind = git_ops.git_ahead_behind(folder)
    github_connected = remote_auth.get_github_token() is not None
    gitlab_connected = remote_auth.get_gitlab_token() is not None
    return {
        "ahead": ahead,
        "behind": behind,
        "github_connected": github_connected,
        "gitlab_connected": gitlab_connected,
    }
