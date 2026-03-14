"""Router for /api/folder-picker — native OS folder picker dialog."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

# tkinter import is inside _pick_folder() to prevent crash in headless CI

router = APIRouter(prefix="/api/folder-picker", tags=["folder-picker"])


def _pick_folder() -> str | None:
    """Run in a thread (blocking). tkinter imported here to avoid headless CI crash."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.wm_attributes(
            "-topmost", True
        )  # Required on Windows: brings dialog in front of browser
        try:
            path = filedialog.askdirectory(title="Select Workflows Folder")
        finally:
            root.destroy()
        return path or None
    except Exception:
        return None


@router.post("")
async def pick_folder() -> dict:
    """Open OS native folder picker dialog and return selected folder path."""
    selected = await asyncio.to_thread(_pick_folder)
    if selected is None:
        return {"path": None, "cancelled": True}
    return {"path": selected, "cancelled": False}
