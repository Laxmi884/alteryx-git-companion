"""FastAPI app definition: /health endpoint and React StaticFiles mount."""

from __future__ import annotations

import logging
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

app = FastAPI(title="Alteryx Git Companion")


def _static_dir() -> Path:
    """Return the path to the compiled React frontend dist directory.

    - Inside a PyInstaller onefile bundle: uses sys._MEIPASS (the temp
      extraction directory where bundled files are placed at runtime).
    - During development / testing: uses a path relative to this file.
    """
    if getattr(sys, "frozen", False):
        # Running inside a PyInstaller bundle
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent
    return base / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """StaticFiles subclass that returns index.html for unknown routes.

    Standard StaticFiles returns 404 for paths not found in the directory.
    For a Single Page Application, unknown routes should fall back to index.html
    so the client-side router can handle them.
    """

    async def get_response(self, path: str, scope: Any) -> Response:
        try:
            return await super().get_response(path, scope)
        except Exception:
            # Fall back to index.html for unknown routes (SPA client-side routing)
            return await super().get_response("index.html", scope)


@app.get("/health")
def health() -> dict[str, str]:
    """Return server health status and application version."""
    return {"status": "ok", "version": version("alteryx-diff")}


# Mount the React SPA as a catch-all AFTER all API routes.
# SPAStaticFiles serves index.html for unknown routes (SPA fallback).
# Wrapped in try/except so a missing dist/ dir doesn't crash the server during
# development or unit tests.
try:
    app.mount(
        "/",
        SPAStaticFiles(directory=str(_static_dir()), html=True),
        name="frontend",
    )
except RuntimeError:
    logger.warning(
        "Frontend dist/ directory not found at %s — static files not served. "
        "Run 'make build' to compile the React frontend.",
        _static_dir(),
    )
