"""Router for /api/git/identity — skeleton stubs only (Plan 02 implements)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/git/identity", tags=["git"])


class IdentityIn(BaseModel):
    name: str
    email: str


@router.get("")
def get_identity() -> dict:
    """Get the current global git user.name and user.email."""
    raise HTTPException(status_code=501, detail="Not implemented — see Plan 02")


@router.post("")
def set_identity(body: IdentityIn) -> dict:
    """Set global git user.name and user.email."""
    raise HTTPException(status_code=501, detail="Not implemented — see Plan 02")
