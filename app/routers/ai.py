"""Router for /api/ai — request-scoped SSE stream for AI change narratives.

Phase 26 APPAI-02. Follows the watch.py EventSourceResponse pattern but is
request-scoped (opens on click, terminates after result event).

CORE-01 compliance: ALL langchain / langgraph / alteryx_diff.llm / pipeline
imports MUST stay inside event_generator() wrapped in try/except ImportError.
A top-level LLM import here will break the test suite on machines without
the [llm] extras installed.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.services import git_ops
from app.services.config_store import load_config

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/summary")
async def ai_summary(folder: str, sha: str, file: str, request: Request):
    """Stream AI change narrative events for a given commit + file.

    Event shapes (all SSE `data:` is JSON):
      {"type": "progress", "step": "Analyzing topology..."}   # D-07
      {"type": "progress", "step": "Annotating tools..."}     # D-07
      {"type": "progress", "step": "Assessing risks..."}      # D-07
      {"type": "result", "narrative": "...", "risks": [...]}
      {"type": "unavailable", "reason": "no_extras" | "no_model"}
      {"type": "error", "detail": "..."}

    Request-scoped (D-08): generator terminates after result/unavailable/error.
    """

    async def event_generator():
        # --- CORE-01: all LLM imports deferred inside the generator ---
        try:
            from alteryx_diff.llm import require_llm_deps

            require_llm_deps()
        except ImportError:
            yield {"data": json.dumps({"type": "unavailable", "reason": "no_extras"})}
            return

        cfg = load_config()
        model_str = cfg.get("llm_model")
        if not model_str:
            yield {"data": json.dumps({"type": "unavailable", "reason": "no_model"})}
            return

        # Progress 1/3 (D-07 label — load-bearing)
        yield {"data": json.dumps({"type": "progress", "step": "Analyzing topology..."})}

        # Build DiffResult via mkstemp pattern (same as history.py _run_diff)
        try:
            parent_sha = f"{sha}~1"
            old_bytes = git_ops.git_show_file(folder, parent_sha, file)
            new_bytes = git_ops.git_show_file(folder, sha, file)
        except Exception as exc:
            yield {"data": json.dumps({"type": "error", "detail": f"git_show_file failed: {exc}"})}
            return

        fd_a, path_a = tempfile.mkstemp(suffix=".yxmd")
        fd_b, path_b = tempfile.mkstemp(suffix=".yxmd")
        try:
            os.write(fd_a, old_bytes)
            os.close(fd_a)
            os.write(fd_b, new_bytes)
            os.close(fd_b)

            from alteryx_diff.llm.context_builder import ContextBuilder
            from alteryx_diff.pipeline import DiffRequest
            from alteryx_diff.pipeline import run as pipeline_run

            response = pipeline_run(
                DiffRequest(path_a=pathlib.Path(path_a), path_b=pathlib.Path(path_b))
            )
            context = ContextBuilder.build_from_diff(response.result)
        finally:
            try:
                os.unlink(path_a)
            except OSError:
                pass
            try:
                os.unlink(path_b)
            except OSError:
                pass

        # Merge .acd/context.json business_context if present (APPAI-01 grounding)
        acd_ctx = pathlib.Path(folder) / ".acd" / "context.json"
        if acd_ctx.exists():
            try:
                stored = json.loads(acd_ctx.read_text(encoding="utf-8"))
                bc = stored.get("business_context")
                if bc:
                    context["business_context"] = bc
            except (OSError, json.JSONDecodeError):
                pass

        # Progress 2/3 (D-07 label — load-bearing)
        yield {"data": json.dumps({"type": "progress", "step": "Annotating tools..."})}

        # Resolve LLM backend from cfg["llm_model"] — "provider:model_name"
        provider, _, model_name = model_str.partition(":")
        try:
            if provider == "ollama":
                from langchain_ollama import ChatOllama

                llm = ChatOllama(model=model_name, temperature=0)
            elif provider in ("openai", "openrouter"):
                from langchain_openai import ChatOpenAI

                kwargs: dict = {"model": model_name, "temperature": 0}
                if provider == "openrouter":
                    kwargs["base_url"] = "https://openrouter.ai/api/v1"
                    kwargs["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")
                else:
                    kwargs["api_key"] = os.environ.get("OPENAI_API_KEY", "")
                llm = ChatOpenAI(**kwargs)
            else:
                yield {
                    "data": json.dumps(
                        {"type": "error", "detail": f"Unknown LLM provider: {provider}"}
                    )
                }
                return
        except ImportError:
            yield {"data": json.dumps({"type": "unavailable", "reason": "no_extras"})}
            return

        # Progress 3/3 (D-07 label — load-bearing)
        yield {"data": json.dumps({"type": "progress", "step": "Assessing risks..."})}

        # Single-shot LLM call (generate_change_narrative is NOT a LangGraph
        # pipeline — progress events above are cosmetic timing signals per
        # RESEARCH Pitfall 1).
        try:
            from alteryx_diff.llm.doc_graph import generate_change_narrative

            narrative = await generate_change_narrative(context, llm)
        except Exception as exc:
            yield {"data": json.dumps({"type": "error", "detail": f"LLM call failed: {exc}"})}
            return

        yield {
            "data": json.dumps(
                {
                    "type": "result",
                    "narrative": narrative.narrative,
                    "risks": list(narrative.risks or []),
                }
            )
        }

    return EventSourceResponse(event_generator())
