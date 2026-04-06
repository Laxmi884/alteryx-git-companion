"""Router for /api/folder-picker — native OS folder picker dialog."""

from __future__ import annotations

import subprocess
import sys

from fastapi import APIRouter

router = APIRouter(prefix="/api/folder-picker", tags=["folder-picker"])

_MACOS_SCRIPT = 'POSIX path of (choose folder with prompt "Select Workflows Folder")'

_TKINTER_SCRIPT = """
import sys
try:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    try:
        path = filedialog.askdirectory(title="Select Workflows Folder")
    finally:
        root.destroy()
    print(path or "", end="")
except Exception:
    print("", end="")
"""


@router.post("")
async def pick_folder() -> dict:
    """Open OS native folder picker dialog and return selected folder path."""
    if sys.platform == "darwin":
        result = subprocess.run(
            ["osascript", "-e", _MACOS_SCRIPT],
            capture_output=True,
            text=True,
        )
        # osascript returns path with trailing newline; strip it
        path = result.stdout.strip()
    else:
        result = subprocess.run(
            [sys.executable, "-c", _TKINTER_SCRIPT],
            capture_output=True,
            text=True,
        )
        path = result.stdout.strip()

    if not path:
        return {"path": None, "cancelled": True}
    return {"path": path, "cancelled": False}
