"""History router — list commits and diff endpoints (stub for Plan 01)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import git_ops  # noqa: F401 — required for mock.patch targeting

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/{project_id}")
def list_history(project_id: str, folder: str = Query(...)) -> list:
    """Return commit history for the project folder.

    Returns a list of commit entries with sha, message, author, timestamp,
    files_changed, and has_parent fields.
    """
    raise NotImplementedError


@router.get("/{sha}/diff")
def get_diff(
    sha: str,
    folder: str = Query(...),
    file: str = Query(...),
    compare_to: str | None = Query(None),
) -> object:
    """Return a diff for the given sha and file.

    Returns {"is_first_commit": true} when sha has no parent.
    Returns HTML string when sha has a parent commit.
    """
    raise NotImplementedError
