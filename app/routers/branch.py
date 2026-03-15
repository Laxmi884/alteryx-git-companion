"""Branch management router — stubs for Phase 17.

Endpoints raise NotImplementedError — implementations added in Plans 17-02 and 17-03.
Module-level git_ops import required for mock.patch targeting in tests.
"""

from __future__ import annotations

import subprocess  # noqa: F401 — required for mock.patch targeting

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services import git_ops  # noqa: F401 — required for mock.patch targeting

router = APIRouter(prefix="/api/branch", tags=["branch"])


class BranchCreateRequest(BaseModel):
    folder: str
    description: str


class BranchCheckoutRequest(BaseModel):
    folder: str
    branch: str


class BranchDeleteRequest(BaseModel):
    folder: str
    branch: str
    force: bool = False


@router.get("/{project_id}")
def list_branches(
    project_id: str,
    folder: str = Query(...),
) -> list[dict]:
    """Return branches for the project folder."""
    raise NotImplementedError


@router.post("/{project_id}/create")
def create_branch(project_id: str, body: BranchCreateRequest) -> dict:
    """Create a new experiment branch from HEAD."""
    raise NotImplementedError


@router.post("/{project_id}/checkout")
def checkout_branch(project_id: str, body: BranchCheckoutRequest) -> dict:
    """Checkout a branch; blocked if working tree is dirty."""
    raise NotImplementedError


@router.delete("/{project_id}/delete")
def delete_branch(project_id: str, body: BranchDeleteRequest) -> dict:
    """Delete a branch; blocked for protected branch names."""
    raise NotImplementedError


@router.get("/{project_id}/merge-base")
def get_merge_base(
    project_id: str,
    folder: str = Query(...),
    branch: str = Query(...),
) -> dict:
    """Return the merge base SHA between branch and main/master."""
    raise NotImplementedError
