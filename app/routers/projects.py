"""Router for /api/projects — skeleton stubs only (Plan 02 implements)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import config_store, git_ops  # noqa: F401 — imported for Plan 02

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectIn(BaseModel):
    path: str


# NOTE: /check must be defined BEFORE /{id} so FastAPI resolves it correctly.


@router.get("/check")
def check_project(path: str) -> dict:
    """Check whether a folder is a git repo. Returns {is_git_repo: bool}."""
    raise HTTPException(status_code=501, detail="Not implemented — see Plan 02")


@router.get("")
def list_projects() -> list:
    """List all registered projects."""
    raise HTTPException(status_code=501, detail="Not implemented — see Plan 02")


@router.post("", status_code=201)
def add_project(body: ProjectIn) -> dict:
    """Register a new project folder."""
    raise HTTPException(status_code=501, detail="Not implemented — see Plan 02")


@router.delete("/{id}")
def remove_project(id: str) -> dict:
    """Remove a registered project by ID."""
    raise HTTPException(status_code=501, detail="Not implemented — see Plan 02")
