"""Remote auth service stub — GitHub Device Flow and GitLab PAT credential management.

All functions raise NotImplementedError. Implementations land in Plan 16-02.
"""

from __future__ import annotations


def request_device_code() -> dict:
    """Step 1: Request a device code from GitHub OAuth Device Flow.

    Returns dict with keys: device_code, user_code, verification_uri,
    expires_in, interval.
    """
    raise NotImplementedError


def poll_and_store(device_code: str, interval: int) -> None:
    """Step 2: Poll GitHub until user authorises or flow expires.

    Stores access token in OS keyring via store_github_token on success.
    Raises NotImplementedError until Plan 16-02 implements this.
    """
    raise NotImplementedError


def get_github_token() -> str | None:
    """Return the stored GitHub access token from OS keyring, or None."""
    raise NotImplementedError


def store_github_token(token: str) -> None:
    """Store a GitHub access token in OS keyring."""
    raise NotImplementedError


def validate_gitlab_token(token: str) -> dict | None:
    """Validate a GitLab PAT via GET /user.

    Returns user info dict on success, None if token is invalid.
    """
    raise NotImplementedError


def store_gitlab_token(token: str) -> None:
    """Store a GitLab PAT in OS keyring."""
    raise NotImplementedError


def get_gitlab_token() -> str | None:
    """Return the stored GitLab PAT from OS keyring, or None."""
    raise NotImplementedError
