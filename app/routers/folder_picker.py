"""Router for /api/folder-picker — skeleton stub only (Plan 02 implements)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

# tkinter import is inside function body to prevent crash in headless CI

router = APIRouter(prefix="/api/folder-picker", tags=["folder-picker"])


async def _pick_folder() -> str | None:
    """Open a native folder picker dialog and return the selected path."""
    import tkinter as tk
    from tkinter import filedialog

    loop = asyncio.get_event_loop()

    def _run() -> str:
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title="Select workflow folder")
        root.destroy()
        return path

    return await loop.run_in_executor(None, _run)


@router.post("")
async def pick_folder() -> dict:
    """Open OS native folder picker dialog and return selected folder path."""
    raise HTTPException(status_code=501, detail="Not implemented — see Plan 02")
