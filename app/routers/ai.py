"""Router for /api/ai — request-scoped SSE stream for AI change narratives.

Phase 26 APPAI-02. Follows the watch.py EventSourceResponse pattern but is
request-scoped (opens on click, terminates after result event).

CORE-01 compliance: ALL langchain / langgraph / alteryx_diff.llm / pipeline
imports MUST stay inside event_generator() wrapped in try/except ImportError.
A top-level LLM import here will break the test suite on machines without
the [llm] extras installed.
"""

from __future__ import annotations

import contextlib
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

        # Detect initial commit (no parent) server-side
        is_initial_commit = not git_ops.git_has_commits_before(folder, sha)

        # Progress 1/3 (D-07 label — load-bearing)
        yield {
            "data": json.dumps({"type": "progress", "step": "Analyzing topology..."})
        }

        try:
            new_bytes = git_ops.git_show_file(folder, sha, file)
        except Exception as exc:
            yield {
                "data": json.dumps(
                    {"type": "error", "detail": f"git_show_file failed: {exc}"}
                )
            }
            return

        # Merge .acd/context.json business_context if present (APPAI-01 grounding)
        acd_ctx = pathlib.Path(folder) / ".acd" / "context.json"
        business_context: str | None = None
        if acd_ctx.exists():
            try:
                stored = json.loads(acd_ctx.read_text(encoding="utf-8"))
                business_context = stored.get("business_context")
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

        if is_initial_commit:
            # Initial commit — generate full workflow developer documentation
            fd, path_b = tempfile.mkstemp(suffix=".yxmd")
            try:
                os.write(fd, new_bytes)
                os.close(fd)
                from alteryx_diff.llm.context_builder import ContextBuilder
                from alteryx_diff.llm.doc_graph import generate_workflow_documentation
                from alteryx_diff.parser import parse_one

                doc = parse_one(pathlib.Path(path_b))
                context = ContextBuilder.build_from_workflow(doc)
                # Override temp file name with actual workflow filename
                context["workflow_name"] = pathlib.Path(file).stem
            finally:
                with contextlib.suppress(OSError):
                    os.unlink(path_b)

            if business_context:
                context["business_context"] = business_context

            try:
                workflow_doc = await generate_workflow_documentation(context, llm)
            except Exception as exc:
                yield {
                    "data": json.dumps(
                        {"type": "error", "detail": f"LLM call failed: {exc}"}
                    )
                }
                return

            import re as _re

            def _fmt(text: str) -> str:
                """Ensure numbered list items each start on their own line."""
                # Insert newline before "N. " patterns that aren't already at line start
                return _re.sub(r"(?<!\n)(\s)(\d+\.\s)", r"\n\2", text).strip()

            workflow_stem = pathlib.Path(file).stem
            risks_md = "\n".join(f"- {r}" for r in (workflow_doc.risks or []))
            markdown = (
                f"# {workflow_doc.workflow_name} — Developer Documentation\n\n"
                f"## Overview\n\n{_fmt(workflow_doc.overview)}\n\n"
                f"## Assumptions\n\n{_fmt(workflow_doc.assumptions)}\n\n"
                f"## Data Sources\n\n{_fmt(workflow_doc.data_sources)}\n\n"
                f"## Data Transformations\n\n{_fmt(workflow_doc.transformations)}\n\n"
                f"## Data Flow\n\n{_fmt(workflow_doc.data_flow)}\n\n"
                f"## Outputs\n\n{_fmt(workflow_doc.outputs)}\n\n"
                f"## Data Dictionary\n\n{_fmt(workflow_doc.data_dictionary)}\n\n"
                f"## Tool Inventory\n\n{_fmt(workflow_doc.tool_inventory)}\n\n"
                f"## Dependencies\n\n{_fmt(workflow_doc.dependencies)}\n\n"
                "## Configuration Notes\n\n"
                f"{_fmt(workflow_doc.configuration_notes)}\n\n"
                f"## Execution Guide\n\n{_fmt(workflow_doc.execution_guide)}\n\n"
                f"## Error Handling\n\n{_fmt(workflow_doc.error_handling)}\n\n"
                f"## Risks & Considerations\n\n{risks_md}\n"
            )

            # Save to workflow directory
            doc_path = pathlib.Path(folder) / f"{workflow_stem}-developer-doc.md"
            with contextlib.suppress(OSError):
                doc_path.write_text(markdown, encoding="utf-8")

            yield {
                "data": json.dumps(
                    {
                        "type": "result",
                        "narrative": markdown,
                        "risks": list(workflow_doc.risks or []),
                        "doc_path": str(doc_path),
                    }
                )
            }
        else:
            # Subsequent commit — generate change narrative from diff
            old_bytes = git_ops.git_show_file(folder, f"{sha}~1", file)
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
                    DiffRequest(
                        path_a=pathlib.Path(path_a), path_b=pathlib.Path(path_b)
                    )
                )
                context = ContextBuilder.build_from_diff(response.result)
            finally:
                with contextlib.suppress(OSError):
                    os.unlink(path_a)
                with contextlib.suppress(OSError):
                    os.unlink(path_b)

            if business_context:
                context["business_context"] = business_context

            try:
                from alteryx_diff.llm.doc_graph import generate_change_narrative

                narrative = await generate_change_narrative(context, llm)
            except Exception as exc:
                yield {
                    "data": json.dumps(
                        {"type": "error", "detail": f"LLM call failed: {exc}"}
                    )
                }
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
