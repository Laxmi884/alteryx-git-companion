"""Router for /api/watch — SSE badge events and per-project watch status."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.services.watcher_manager import watcher_manager

router = APIRouter(prefix="/api/watch", tags=["watch"])

_QUEUE_POLL_INTERVAL = 0.5  # seconds between disconnect checks


@router.get("/events")
async def watch_events(request: Request):
    """SSE stream of badge_update events for all registered projects.

    Frontend subscribes once on mount. Each event has the shape:
    {"type": "badge_update", "project_id": "...", "changed_count": N}

    The browser's EventSource API auto-reconnects on error — no manual
    reconnect logic needed for same-host connections.
    """

    async def event_generator():
        q = watcher_manager.subscribe()
        # Seed with current state so new subscribers see existing changes immediately
        for project_id, info in watcher_manager.get_status().items():
            q.put_nowait(
                {
                    "type": "badge_update",
                    "project_id": project_id,
                    "changed_count": info["changed_count"],
                }
            )
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        q.get(), timeout=_QUEUE_POLL_INTERVAL
                    )
                    yield {"data": json.dumps(event)}
                except TimeoutError:
                    # No event yet — loop back to check disconnect
                    continue
        except asyncio.CancelledError:
            pass
        finally:
            watcher_manager.unsubscribe(q)

    return EventSourceResponse(event_generator())


@router.get("/status")
def watch_status() -> dict:
    """Return per-project change counts and commit status.

    Response shape:
    {
      "<project_id>": {
        "changed_count": int,
        "total_workflows": int,
        "has_any_commits": bool
      }
    }

    Called by Phase 13 (Save Version) at save-time to determine whether
    to show the initial-commit warning (has_any_commits=False).
    """
    return watcher_manager.get_status()
