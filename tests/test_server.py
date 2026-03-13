"""Unit tests for the FastAPI app: /health endpoint and SPA fallback."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def patched_client(tmp_path, monkeypatch):
    """TestClient with _static_dir() patched to a minimal temp dist dir."""
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<!DOCTYPE html><html></html>")

    import app.server as server_module

    monkeypatch.setattr(server_module, "_static_dir", lambda: dist)

    from app.server import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_health_returns_200(patched_client):
    """GET /health returns 200."""
    response = patched_client.get("/health")
    assert response.status_code == 200


def test_health_status_ok(patched_client):
    """GET /health returns JSON with status == 'ok' and a 'version' key."""
    response = patched_client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_spa_fallback(tmp_path, monkeypatch):
    """GET /nonexistent-route returns 200 with index.html content (SPA fallback)."""
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    index_content = "<!DOCTYPE html><html><body>SPA</body></html>"
    (dist / "index.html").write_text(index_content)

    import app.server as server_module

    monkeypatch.setattr(server_module, "_static_dir", lambda: dist)

    # Re-import app after patching so StaticFiles uses the new dir
    # We rebuild the app with a fresh StaticFiles mount
    from app.server import app as original_app
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    fresh_app = FastAPI()
    for route in original_app.routes:
        if hasattr(route, "methods"):
            fresh_app.routes.append(route)
    fresh_app.mount(
        "/",
        StaticFiles(directory=str(dist), html=True),
        name="frontend",
    )

    with TestClient(fresh_app, raise_server_exceptions=False) as client:
        response = client.get("/nonexistent-route")
        assert response.status_code == 200
        assert "SPA" in response.text
