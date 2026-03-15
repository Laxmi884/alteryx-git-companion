"""Remote router — /api/remote/* endpoints for GitHub/GitLab auth and push.

Module-level service imports are required so unittest.mock.patch targeting
app.routers.remote.remote_auth (etc.) works correctly in tests.
"""

from __future__ import annotations

import contextlib
import subprocess
import threading
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import (
    config_store,  # noqa: F401
    git_ops,  # noqa: F401
    github_api,  # noqa: F401
    gitlab_api,  # noqa: F401
    remote_auth,
)

router = APIRouter(prefix="/api/remote", tags=["remote"])


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class TokenRequest(BaseModel):
    token: str


class PushRequest(BaseModel):
    project_id: str
    folder: str
    provider: str = "github"


# ---------------------------------------------------------------------------
# REMOTE-01: GitHub Device Flow endpoints
# ---------------------------------------------------------------------------


@router.post("/github/start")
def github_start() -> dict:
    """Start GitHub OAuth Device Flow — returns user_code and verification_uri.

    Kicks off poll_and_store in a background thread so the token is stored
    in keyring once the user authorises on GitHub.
    """
    data = remote_auth.request_device_code()
    device_code = data.get("device_code")
    interval = int(data.get("interval", 5))
    threading.Thread(
        target=remote_auth.poll_and_store,
        args=(device_code, interval),
        daemon=True,
    ).start()
    return {
        "user_code": data.get("user_code"),
        "verification_uri": data.get("verification_uri"),
        "device_code": device_code,
        "interval": interval,
        "expires_in": data.get("expires_in"),
    }


@router.get("/github/status")
def github_status() -> dict:
    """Return {connected: bool} based on whether a GitHub token is in keyring."""
    token = remote_auth.get_github_token()
    return {"connected": token is not None}


@router.post("/github/connect")
def github_connect(body: TokenRequest) -> dict:
    """Store a GitHub PAT directly (fallback for users who prefer PAT over OAuth).

    Trusts the user-supplied token without API validation — identical behaviour
    to the device-flow path which also stores an unvalidated token.
    """
    remote_auth.store_github_token(body.token)
    return {"connected": True}


# ---------------------------------------------------------------------------
# REMOTE-02: GitLab PAT connect and status endpoints
# ---------------------------------------------------------------------------


@router.post("/gitlab/connect")
def gitlab_connect(body: TokenRequest) -> dict:
    """Validate GitLab PAT and store in keyring if valid."""
    user = remote_auth.validate_gitlab_token(body.token)
    if user is not None:
        remote_auth.store_gitlab_token(body.token)
        return {"connected": True}
    return {"connected": False, "error": "Invalid token"}


@router.get("/gitlab/status")
def gitlab_status() -> dict:
    """Return {connected: bool} based on whether a GitLab token is in keyring."""
    token = remote_auth.get_gitlab_token()
    return {"connected": token is not None}


# ---------------------------------------------------------------------------
# REMOTE-04: Push endpoint
# ---------------------------------------------------------------------------


@router.post("/push")
def push(body: PushRequest) -> dict:
    """Push the project folder to its configured remote.

    FastAPI runs sync routes in a threadpool — no event loop blocking.

    Flow:
    1. Get stored token from keyring.
    2. Look up existing repo URL from config_store.
    3. If no URL: auto-create repo via GitHub/GitLab API, save URL.
    4. Call git_push with token via GIT_ASKPASS.
    """
    if body.provider == "github":
        token = remote_auth.get_github_token()
    else:
        token = remote_auth.get_gitlab_token()

    if not token:
        return {"success": False, "error": "Not connected"}

    repo_info = config_store.get_remote_repo(body.project_id)
    repo_url = repo_info.get(f"{body.provider}_url")
    created = False

    if not repo_url:
        # Auto-create remote repo
        try:
            if body.provider == "github":
                username = github_api.get_github_username(token)
                base_slug = github_api.slugify_folder_name(Path(body.folder).name)
                name = github_api.find_available_repo_name(token, username, base_slug)
                repo = github_api.create_github_repo(token, name)
                repo_url = repo["clone_url"]
            else:
                slug = github_api.slugify_folder_name(Path(body.folder).name)
                repo = gitlab_api.create_gitlab_project(token, slug)
                repo_url = repo["http_url_to_repo"]
            config_store.set_remote_repo(body.project_id, body.provider, repo_url)
            created = True
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": f"Failed to create repo: {exc}"}

    try:
        git_ops.git_push(body.folder, repo_url, token)
        return {"success": True, "repo_url": repo_url, "created": created}
    except subprocess.CalledProcessError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Pull endpoint
# ---------------------------------------------------------------------------


@router.post("/pull")
def pull(body: PushRequest) -> dict:
    """Pull latest changes from remote for the current branch (--ff-only)."""
    if body.provider == "github":
        token = remote_auth.get_github_token()
    else:
        token = remote_auth.get_gitlab_token()

    if not token:
        return {"success": False, "error": "Not connected"}

    repo_info = config_store.get_remote_repo(body.project_id)
    repo_url = repo_info.get(f"{body.provider}_url")
    if not repo_url:
        return {"success": False, "error": "No remote configured"}

    try:
        return git_ops.git_pull(body.folder, repo_url, token)
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# REMOTE-06b: Disconnect endpoints
# ---------------------------------------------------------------------------


@router.post("/github/disconnect")
def disconnect_github() -> dict:
    """Remove the stored GitHub token from the OS keyring."""
    import keyring  # noqa: PLC0415

    keyring.delete_password(remote_auth.SERVICE_GITHUB, remote_auth.USERNAME_KEY)
    return {"disconnected": True}


@router.post("/gitlab/disconnect")
def disconnect_gitlab() -> dict:
    """Remove the stored GitLab token from the OS keyring."""
    import keyring  # noqa: PLC0415

    keyring.delete_password(remote_auth.SERVICE_GITLAB, remote_auth.USERNAME_KEY)
    return {"disconnected": True}


# ---------------------------------------------------------------------------
# REMOTE-06: Ahead/behind status endpoint
# ---------------------------------------------------------------------------


@router.get("/status")
def remote_status(
    folder: str,
    project_id: str = "",
    provider: str = "github",
) -> dict:
    """Return ahead/behind counts, connection status, and repo URL for a project.

    If a token and repo URL are available, fetches from remote first to update
    the ahead/behind counts.
    """
    if provider == "github":
        token = remote_auth.get_github_token()
    else:
        token = remote_auth.get_gitlab_token()

    repo_info = config_store.get_remote_repo(project_id) if project_id else {}
    repo_url: str | None = repo_info.get(f"{provider}_url")

    ahead, behind = 0, 0
    if token and repo_url:
        with contextlib.suppress(Exception):
            git_ops.git_fetch(folder, repo_url, token)
            ahead, behind = git_ops.git_ahead_behind(folder)
    else:
        with contextlib.suppress(Exception):
            ahead, behind = git_ops.git_ahead_behind(folder)

    return {
        "ahead": ahead,
        "behind": behind,
        "github_connected": remote_auth.get_github_token() is not None,
        "gitlab_connected": remote_auth.get_gitlab_token() is not None,
        "repo_url": repo_url,
    }


@router.get("/behind-commits")
def remote_behind_commits(folder: str) -> list[dict]:
    """Return the list of commits on the upstream that are not yet local."""
    with contextlib.suppress(Exception):
        return git_ops.git_behind_commits(folder)
    return []
