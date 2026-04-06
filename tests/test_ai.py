"""Tests for Phase 26 AI summary SSE endpoint (APPAI-02).

RED state: app/routers/ai.py does not exist yet. These tests will go GREEN
when Plan 03 creates the router.

Pattern: follows tests/test_watch.py — direct async generator iteration with
AsyncMock for request.is_disconnected. TestClient hangs on streaming SSE
responses, so we call the route handler function directly.

Note: project uses asyncio.run() pattern (not pytest-asyncio).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: iterate an async generator and collect parsed event dicts
# ---------------------------------------------------------------------------


async def _collect(agen):
    events = []
    async for ev in agen:
        # EventSourceResponse generator yields dicts like {"data": "<json-str>"}
        if isinstance(ev, dict) and "data" in ev:
            events.append(json.loads(ev["data"]))
        else:
            events.append(ev)
    return events


# ---------------------------------------------------------------------------
# Module + registration sanity
# ---------------------------------------------------------------------------


def test_ai_router_module_importable():
    """APPAI-02 CORE-01: importing app.routers.ai must not fail when LLM extras absent."""
    from app.routers import ai  # noqa: F401

    assert hasattr(ai, "router"), "app/routers/ai.py must export `router`"


def test_ai_router_registered_in_server():
    """APPAI-02: GET /api/ai/summary must be registered on the FastAPI app."""
    from app.server import app

    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/ai/summary" in paths, (
        "ai.router must be included in server.py via app.include_router(ai.router)"
    )


# ---------------------------------------------------------------------------
# SSE contract tests (direct handler call — TestClient hangs on streams)
# ---------------------------------------------------------------------------


def test_ai_summary_no_extras_emits_unavailable_no_extras():
    """APPAI-02 D-06: ImportError from require_llm_deps -> single unavailable event."""
    import asyncio

    async def _run():
        from app.routers import ai

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        with patch.dict("sys.modules", {"alteryx_diff.llm": MagicMock()}):
            import sys

            sys.modules["alteryx_diff.llm"].require_llm_deps = MagicMock(
                side_effect=ImportError("llm extras not installed")
            )
            response = await ai.ai_summary(
                folder="/tmp/x", sha="abc123", file="w.yxmd", request=request
            )
            # EventSourceResponse wraps the generator; extract it.
            generator = response.body_iterator
            events = await _collect(generator)

        assert len(events) == 1
        assert events[0] == {"type": "unavailable", "reason": "no_extras"}

    asyncio.run(_run())


def test_ai_summary_no_model_configured_emits_unavailable_no_model():
    """APPAI-02 D-06: missing llm_model key in config -> unavailable no_model."""
    import asyncio

    async def _run():
        from app.routers import ai

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        # require_llm_deps succeeds; load_config returns dict without llm_model
        fake_llm = MagicMock()
        fake_llm.require_llm_deps = MagicMock(return_value=None)
        with patch.dict("sys.modules", {"alteryx_diff.llm": fake_llm}), patch(
            "app.routers.ai.load_config", return_value={}
        ):
            response = await ai.ai_summary(
                folder="/tmp/x", sha="abc123", file="w.yxmd", request=request
            )
            events = await _collect(response.body_iterator)

        assert len(events) == 1
        assert events[0] == {"type": "unavailable", "reason": "no_model"}

    asyncio.run(_run())


def test_ai_summary_happy_path_emits_progress_then_result():
    """APPAI-02 D-07: three progress events (exact D-07 labels) then a result event."""
    import asyncio

    async def _run():
        from app.routers import ai

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        fake_llm_module = MagicMock()
        fake_llm_module.require_llm_deps = MagicMock(return_value=None)

        fake_narrative = MagicMock()
        fake_narrative.narrative = "Two tools added to the filter stage."
        fake_narrative.risks = ["Null handling for new column"]

        fake_ctx_builder = MagicMock()
        fake_ctx_builder.ContextBuilder.build_from_diff = MagicMock(
            return_value={"summary": "s", "changes": []}
        )

        fake_pipeline = MagicMock()
        fake_pipeline.run = MagicMock(return_value=MagicMock(result=MagicMock()))
        fake_pipeline.DiffRequest = MagicMock()

        fake_doc_graph = MagicMock()
        fake_doc_graph.generate_change_narrative = AsyncMock(return_value=fake_narrative)

        # Patch git_show_file to return fake bytes; patch all deferred imports.
        with patch(
            "app.services.git_ops.git_show_file", return_value=b"<xml/>"
        ), patch(
            "app.routers.ai.load_config",
            return_value={"llm_model": "ollama:llama3"},
        ), patch.dict(
            "sys.modules",
            {
                "alteryx_diff.llm": fake_llm_module,
                "alteryx_diff.llm.context_builder": fake_ctx_builder,
                "alteryx_diff.llm.doc_graph": fake_doc_graph,
                "alteryx_diff.pipeline": fake_pipeline,
                "langchain_ollama": MagicMock(ChatOllama=MagicMock()),
            },
        ):
            response = await ai.ai_summary(
                folder="/tmp/x", sha="abc123", file="w.yxmd", request=request
            )
            events = await _collect(response.body_iterator)

        # Expect exactly 3 progress events with D-07 labels, then 1 result event.
        progress_events = [e for e in events if e.get("type") == "progress"]
        result_events = [e for e in events if e.get("type") == "result"]
        assert [p["step"] for p in progress_events] == [
            "Analyzing topology...",
            "Annotating tools...",
            "Assessing risks...",
        ], f"progress steps must match D-07 exactly, got: {progress_events}"
        assert len(result_events) == 1
        assert result_events[0]["narrative"] == "Two tools added to the filter stage."
        assert result_events[0]["risks"] == ["Null handling for new column"]

    asyncio.run(_run())
