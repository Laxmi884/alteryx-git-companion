# Phase 26: Companion App AI Integration - Research

**Researched:** 2026-04-05
**Domain:** FastAPI SSE streaming, React EventSource hooks, LLM integration, business context persistence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Business Context Field**
- D-01: Field appears ONCE — on the first commit in a new project only. `hasAnyCommits === false` is the condition. After first save, field never reappears.
- D-02: Field is optional. Save Version button works regardless. If blank, `.acd/context.json` is not created (or written as empty string — implementer's discretion).
- D-03: Storage: `.acd/context.json` in the project folder. Separate from `config_store` (which uses platformdirs for app-global config).

**AI Summary Trigger**
- D-04: AI summary is on-demand — triggered by a button. Panel visible but empty until clicked.
- D-05: Button/panel shown for all non-first-commit diffs. First-commit diffs (`is_first_commit: true`) show existing "first commit" state, no AI panel.

**LLM Unavailable States**
- D-06: Both unavailable cases show a muted, single-line message — no CTAs, no install hints, no links:
  - LLM extras not installed: "AI summary unavailable — install LLM extras"
  - Model not configured: "No LLM model configured"
  Backend differentiates the two cases; frontend renders the appropriate message.

**Progress Streaming (SSE)**
- D-07: Backend sends one SSE event per LangGraph node as it completes, plus a final event with the complete ChangeNarrative:
  - `{"type": "progress", "step": "Analyzing topology..."}`
  - `{"type": "progress", "step": "Annotating tools..."}`
  - `{"type": "progress", "step": "Assessing risks..."}`
  - `{"type": "result", "narrative": "...", "risks": [...]}`
  Uses the same `EventSourceResponse` pattern from `watch.py`.
- D-08: New SSE endpoint is request-scoped (one stream per user click). Frontend opens `EventSource` on button click, closes it when the `result` event arrives or on error.

### Claude's Discretion
- Exact button label and placement within `DiffViewer.tsx` (above/below the iframe)
- Whether `.acd/context.json` is written on empty input or left absent
- Whether the AI summary panel has a loading skeleton while waiting for the first SSE event
- New FastAPI router file name (e.g., `app/routers/ai.py` or `app/routers/doc.py`)
- Test structure for the new SSE endpoint and frontend React component

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| APPAI-01 | User sees a "Business context" text field on first commit in the companion app; input is saved to `.acd/context.json` and used as LLM grounding context | Backend: extend `CommitBody` + `commit_version` endpoint to accept `business_context`; write `.acd/context.json` via Path. Frontend: add Textarea to `ChangesPanel.tsx` inside `!hasAnyCommits` block; pass `business_context` in POST body. |
| APPAI-02 | User sees an AI-generated change summary in the companion app diff viewer, streamed live via SSE while the LLM generates it | Backend: new `app/routers/ai.py` with `GET /api/ai/summary` endpoint using `EventSourceResponse`. Frontend: new `useAISummary` hook + AI summary panel inside `DiffViewer.tsx`. LLM: call `generate_change_narrative()` from `doc_graph.py`; stream progress events for each LangGraph node. |
</phase_requirements>

---

## Summary

Phase 26 adds two AI features to the companion app that consume the LLM pipeline built in Phases 23-25. Both features are additive changes — no existing functionality is removed or modified beyond extending the save endpoint and two React components.

The business context feature (APPAI-01) is the simpler of the two: a Textarea in `ChangesPanel.tsx` guarded by the already-tracked `hasAnyCommits` prop, and a small extension to the `/api/save/commit` endpoint to persist the value to `.acd/context.json`. The `.acd/` directory already exists in the project for backup files. The save endpoint just needs an optional field added to `CommitBody`.

The AI summary panel (APPAI-02) is the more complex feature. It requires a new FastAPI router (`app/routers/ai.py`) exposing a request-scoped SSE stream, a new React hook (`useAISummary.ts`) following the `useWatchEvents.ts` pattern, and a panel in `DiffViewer.tsx`. The key complexity is that `generate_change_narrative()` is a single async LLM call — not a LangGraph multi-node graph — so the backend must manually emit progress SSE events before and after calling it, simulating step labels that match D-07. The function itself returns a `ChangeNarrative` with `narrative` (str) and `risks` (list[str]).

**Primary recommendation:** Build in three areas — (1) extend `save.py`/`ChangesPanel.tsx` for business context, (2) new `app/routers/ai.py` SSE endpoint with manual progress events, (3) new `useAISummary.ts` hook + panel in `DiffViewer.tsx`.

---

## Standard Stack

### Core (already installed — no new packages needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sse_starlette` | (already installed) | `EventSourceResponse` for SSE streaming | Already used in `watch.py` — exact same pattern |
| `fastapi` | (already installed) | API router for `/api/ai/summary` | Project standard |
| `alteryx_diff.llm.doc_graph` | (project source) | `generate_change_narrative(context, llm)` | Built in Phase 25 — the function to call |
| `alteryx_diff.llm.context_builder` | (project source) | `ContextBuilder.build_from_diff()` | Built in Phase 23 — converts DiffResult to LLM context |
| `alteryx_diff.llm` | (project source) | `require_llm_deps()` — guard for LLM extras check | Built in Phase 23 — standard import guard |
| `app.services.config_store` | (project source) | `load_config()` — reads `cfg["llm_model"]` | Pattern established in Phase 25 CLI |
| React 18 + TypeScript | (already installed) | Frontend hook + component | Project standard |
| shadcn/ui (`Button`, `Textarea`, `Card`) | (already installed) | UI components | Already in `src/components/ui/` |
| lucide-react | (already installed) | Icons (spinner, etc.) | Project icon library |

### No New Installations Required

[VERIFIED: codebase grep] All needed packages exist. `sse_starlette` is confirmed installed (used in `watch.py`). LLM library at `alteryx_diff.llm` confirmed in `src/`. All shadcn components (`Button`, `Textarea`, `Card`, `CardContent`) confirmed present in `src/components/ui/`.

---

## Architecture Patterns

### Pattern 1: Request-Scoped SSE Stream (the critical difference from `watch.py`)

The watch SSE is a persistent connection (lives for the entire browser session, no explicit end). The AI summary SSE is request-scoped — it opens, streams a finite sequence of events, then terminates.

**Key difference from `watch.py`:** No subscription/unsubscription to a shared queue manager. The generator runs the LLM call directly, yields progress events, yields the result event, then returns. The EventSource closes when the HTTP response body completes.

**Backend pattern (`app/routers/ai.py`):**

```python
# Source: watch.py pattern, adapted for request-scoped finite stream
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

@router.get("/summary")
async def ai_summary(folder: str, sha: str, file: str, request: Request):
    async def event_generator():
        # 1. Check LLM extras
        try:
            from alteryx_diff.llm import require_llm_deps
            require_llm_deps()
        except ImportError:
            yield {"data": json.dumps({"type": "unavailable", "reason": "no_extras"})}
            return

        # 2. Check model configured
        cfg = load_config()
        model_str = cfg.get("llm_model")
        if not model_str:
            yield {"data": json.dumps({"type": "unavailable", "reason": "no_model"})}
            return

        # 3. Stream progress events (one per logical step)
        yield {"data": json.dumps({"type": "progress", "step": "Analyzing topology..."})}
        # ... build context, call LLM ...
        yield {"data": json.dumps({"type": "progress", "step": "Annotating tools..."})}
        # ... (LLM call happens here) ...
        yield {"data": json.dumps({"type": "progress", "step": "Assessing risks..."})}

        # 4. Stream result
        yield {"data": json.dumps({"type": "result", "narrative": "...", "risks": [...]})}

    return EventSourceResponse(event_generator())
```

**CRITICAL NOTE on progress events vs `generate_change_narrative`:** `generate_change_narrative()` is a single structured LLM call (NOT a multi-node LangGraph pipeline). It does not natively yield progress events. The backend must manually emit progress SSE events BEFORE calling the function, then yield the result when it returns. The step labels ("Analyzing topology...", "Annotating tools...", "Assessing risks...") are cosmetic signals that fire in sequence before and during the single LLM call, not real node-by-node events. [VERIFIED: codebase — `generate_change_narrative` in `doc_graph.py` lines 262-299 uses `structured_llm.ainvoke()` — single call]

**Simplest viable approach:** Yield progress event 1, then yield progress event 2, then `await generate_change_narrative(...)`, then yield progress event 3, then yield the result. This satisfies D-07 exactly.

### Pattern 2: Frontend EventSource Hook (`useAISummary.ts`)

Follows `useWatchEvents.ts` but is callback-triggered (not mounted on component mount) and closes on completion.

```typescript
// Source: app/frontend/src/hooks/useWatchEvents.ts — adapted
export function useAISummary() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'result' | 'unavailable' | 'error'>('idle')
  const [steps, setSteps] = useState<string[]>([])
  const [narrative, setNarrative] = useState<string | null>(null)
  const [risks, setRisks] = useState<string[]>([])
  const esRef = useRef<EventSource | null>(null)

  function trigger(folder: string, sha: string, file: string) {
    esRef.current?.close()
    setStatus('loading')
    setSteps([])
    const es = new EventSource(`/api/ai/summary?folder=...&sha=...&file=...`)
    es.onmessage = (e) => {
      const payload = JSON.parse(e.data)
      if (payload.type === 'progress') {
        setSteps(prev => [...prev, payload.step])
      } else if (payload.type === 'result') {
        setNarrative(payload.narrative)
        setRisks(payload.risks ?? [])
        setStatus('result')
        es.close()
      } else if (payload.type === 'unavailable') {
        setStatus('unavailable')
        // store reason for message selection
        es.close()
      }
    }
    es.onerror = () => { setStatus('error'); es.close() }
    esRef.current = es
  }

  function reset() { esRef.current?.close(); setStatus('idle'); setSteps([]); setNarrative(null) }

  return { status, steps, narrative, risks, trigger, reset }
}
```

**Key difference from `useWatchEvents`:** Not called at app mount level. Called per-DiffViewer instance on button click. Uses a `ref` to track the EventSource so cleanup works on unmount.

### Pattern 3: Business Context Persistence

`.acd/context.json` lives at `{project_folder}/.acd/context.json`. The `.acd/` directory is already created by the backup functionality (confirmed in `save.py`: `.acd-backup/`). The write is done in the `/api/save/commit` endpoint.

```python
# In commit_version(), after git_ops.git_commit_files():
if body.business_context:
    acd_dir = Path(body.folder) / ".acd"
    acd_dir.mkdir(parents=True, exist_ok=True)
    (acd_dir / "context.json").write_text(
        json.dumps({"business_context": body.business_context}),
        encoding="utf-8"
    )
```

`CommitBody` gets an optional field:
```python
class CommitBody(BaseModel):
    project_id: str
    folder: str
    files: list[str]
    message: str
    business_context: str | None = None  # new optional field
```

### Pattern 4: LLM Model Resolution in App Layer

The CLI (`_resolve_model_string`) already reads `cfg["llm_model"]` from `config_store`. The app backend router for AI summary should do the same:

```python
from app.services.config_store import load_config

cfg = load_config()
model_str = cfg.get("llm_model")
```

The `_resolve_llm` logic from `cli.py` needs to be replicated or extracted into a shared helper in `app/services/` — OR the app router can inline the same `provider:model_name` parsing. Since the app layer cannot use `typer.Exit`, it raises `HTTPException` or returns an SSE unavailability event instead.

**Recommended approach:** Inline the `provider:model_name` parsing directly in `app/routers/ai.py`. It is ~15 lines and avoids creating a shared module dependency between CLI and app layers (which risks breaking CORE-01 compliance by adding a module-level LLM import somewhere it shouldn't be).

### Pattern 5: CORE-01 Compliance (Critical)

All LLM imports inside the new router MUST be deferred (inside the `event_generator` function, not at module level). This maintains CORE-01 compliance: the app router module must be importable without LLM extras installed.

```python
# WRONG — breaks CORE-01:
from alteryx_diff.llm import require_llm_deps  # top of file

# CORRECT — deferred inside generator:
async def event_generator():
    try:
        from alteryx_diff.llm import require_llm_deps
        require_llm_deps()
    except ImportError:
        yield ...
        return
```

[VERIFIED: codebase — Phase 25 STATE.md note: "Patched generate_documentation at source module... due to deferred import inside document() function body (CORE-01 compliance)"]

### Pattern 6: Building the DiffResult for context

The AI summary endpoint needs a `DiffResult` to pass to `ContextBuilder.build_from_diff()`. The history router already has `_run_diff()` which calls `pipeline_run()` and returns HTML. The AI router needs to call `pipeline_run()` too, but for the `DiffResult` not the HTML.

```python
# Reuse the same git_show_file + mkstemp pattern from history.py
from alteryx_diff.pipeline import DiffRequest, run as pipeline_run
from app.services import git_ops

old_bytes = git_ops.git_show_file(folder, f"{sha}~1", file)
new_bytes = git_ops.git_show_file(folder, sha, file)

# mkstemp pattern (Windows-safe — same as history.py _run_diff)
fd_a, path_a = tempfile.mkstemp(suffix=".yxmd")
fd_b, path_b = tempfile.mkstemp(suffix=".yxmd")
try:
    os.write(fd_a, old_bytes); os.close(fd_a)
    os.write(fd_b, new_bytes); os.close(fd_b)
    response = pipeline_run(DiffRequest(path_a=Path(path_a), path_b=Path(path_b)))
    diff_result = response.result
finally:
    os.unlink(path_a); os.unlink(path_b)

context = ContextBuilder.build_from_diff(diff_result)
```

The business context from `.acd/context.json` should be merged into the context dict before passing to `generate_change_narrative()`:

```python
acd_context_path = Path(folder) / ".acd" / "context.json"
if acd_context_path.exists():
    stored = json.loads(acd_context_path.read_text(encoding="utf-8"))
    context["business_context"] = stored.get("business_context", "")
```

### Recommended Project Structure Changes

```
app/
├── routers/
│   ├── ai.py              # NEW — GET /api/ai/summary SSE endpoint
│   ├── save.py            # MODIFIED — CommitBody + business_context persist
│   ├── watch.py           # unchanged
│   └── ...
├── server.py              # MODIFIED — include ai.router
└── frontend/
    └── src/
        ├── hooks/
        │   ├── useAISummary.ts    # NEW — request-scoped EventSource hook
        │   └── useWatchEvents.ts  # unchanged
        └── components/
            ├── ChangesPanel.tsx   # MODIFIED — business context Textarea
            └── DiffViewer.tsx     # MODIFIED — AI summary panel
```

### Anti-Patterns to Avoid

- **Top-level LLM import in new router:** Breaks CORE-01 — must be deferred inside `event_generator`.
- **Re-opening EventSource on every render:** The `useAISummary` hook must only open EventSource on explicit `trigger()` call, not in a `useEffect` without proper guards.
- **Assuming `.acd/` exists:** Use `mkdir(parents=True, exist_ok=True)` before writing `context.json`.
- **Using `compare_to` (merge-base sha) for AI summary:** The AI summary endpoint always diffs `sha` vs `sha~1` (the previous commit), same as the default history diff. The `compare_to` param is a UI-only experiment branch feature.
- **Forgetting to register the router in `server.py`:** Every previous router failure has been traced to missing `app.include_router(...)`. This is a recurring pitfall in this codebase. [VERIFIED: STATE.md multiple entries]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE streaming | Custom chunked HTTP response | `sse_starlette.EventSourceResponse` | Already used in `watch.py`; browser auto-reconnect, correct headers |
| LLM model instantiation | Custom HTTP calls to Ollama/OpenAI | `_resolve_llm` pattern from `cli.py` (inline it) | Handles ollama/openai/openrouter providers with correct kwargs |
| Diff computation for context | Re-implement XML parsing | `pipeline_run()` + `ContextBuilder.build_from_diff()` | Already battle-tested; handles .yxmd and .yxwz |
| Structured LLM output | Manual JSON parsing | `generate_change_narrative()` with `ChangeNarrative` Pydantic model | Validated output, no JSON parse errors |
| Import guard for LLM extras | Custom try/except | `require_llm_deps()` from `alteryx_diff.llm` | Provides consistent error message; maintains CORE-01 boundary |

---

## Common Pitfalls

### Pitfall 1: Progress Events Are Cosmetic, Not Real Node Events

**What goes wrong:** Developer tries to hook into LangGraph node callbacks to emit real per-node SSE events.
**Why it happens:** D-07 says "one SSE event per LangGraph node" but `generate_change_narrative()` is NOT a LangGraph graph — it is a single structured LLM call.
**How to avoid:** Emit progress events manually in sequence before/during the single `await generate_change_narrative()` call. The three step labels must fire, but they are timing approximations not real pipeline signals.
**Warning signs:** Trying to pass a callback/stream to `generate_change_narrative()` — the function signature is `(context: dict, llm: BaseChatModel) -> ChangeNarrative`, no streaming argument.

### Pitfall 2: CORE-01 Module-Level LLM Import

**What goes wrong:** `from alteryx_diff.llm.doc_graph import generate_change_narrative` at the top of `app/routers/ai.py` breaks test suite for users without `[llm]` extras.
**Why it happens:** Easy to forget when writing a new router.
**How to avoid:** ALL langchain/langgraph/alteryx_diff.llm imports inside the `event_generator` async generator function, wrapped in `try/except ImportError`.
**Warning signs:** `ImportError` in test collection output on machines without LLM extras.

### Pitfall 3: Missing Router Registration in server.py

**What goes wrong:** The new `ai.router` is not added to `app.include_router(...)` in `server.py` — endpoint returns 404 or 405.
**Why it happens:** Has happened for every new router in this project's history (see STATE.md).
**How to avoid:** Router registration is a mandatory step. After creating `app/routers/ai.py`, immediately add it to `server.py` imports and `app.include_router(ai.router)`.
**Warning signs:** TestClient returns 404 for `/api/ai/summary`.

### Pitfall 4: EventSource Not Closed on Component Unmount

**What goes wrong:** User navigates away from DiffViewer while SSE is streaming; EventSource continues sending events to a garbage-collected component.
**Why it happens:** `useEffect` cleanup not wiring up `es.close()`.
**How to avoid:** Store EventSource in a `useRef`. Close it in both the `result` handler and the `useEffect` cleanup return function (if hook is mounted in `useEffect`).
**Warning signs:** Memory leaks in browser dev tools; "Can't perform React state update on unmounted component" warnings.

### Pitfall 5: `sha~1` Does Not Exist for First Commits

**What goes wrong:** The AI summary endpoint calls `git_show_file(folder, f"{sha}~1", file)` but the commit has no parent — `git show sha~1:file` fails.
**Why it happens:** First-commit handling.
**How to avoid:** The frontend should never call the AI summary endpoint for first-commit diffs (D-05). The backend should still guard: catch `FileNotFoundError` or subprocess error from `git_show_file` and return an appropriate SSE event or HTTP error.
**Warning signs:** `git_show_file` raising `FileNotFoundError` or `subprocess.CalledProcessError`.

### Pitfall 6: asyncio in SSE Generator with Blocking git Calls

**What goes wrong:** `git_show_file` is a synchronous subprocess call. Running it directly inside an `async def event_generator()` blocks the event loop.
**Why it happens:** The `_run_diff` call in history.py is synchronous (runs in a regular `def`, not `async def`). The new AI router calls the same git operations inside an async generator.
**How to avoid:** For short subprocess calls (sub-second), blocking the event loop briefly is acceptable in this codebase (the history router already does this synchronously). If needed, wrap with `asyncio.get_event_loop().run_in_executor(None, ...)`.
**Warning signs:** Server freezes during AI summary streaming when other requests are pending.

---

## Code Examples

### Backend: New Router Skeleton

```python
# app/routers/ai.py
# Source: watch.py EventSourceResponse pattern; history.py _run_diff pattern
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
    """Stream AI change narrative as SSE events.

    Events:
      {"type": "progress", "step": "..."}       — one per logical step
      {"type": "result", "narrative": "...", "risks": [...]}  — final
      {"type": "unavailable", "reason": "no_extras"|"no_model"}
      {"type": "error", "detail": "..."}
    """
    async def event_generator():
        # All LLM imports deferred — CORE-01 compliance
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

        yield {"data": json.dumps({"type": "progress", "step": "Analyzing topology..."})}

        # Build diff context using same mkstemp pattern as history.py
        try:
            parent_sha = f"{sha}~1"
            old_bytes = git_ops.git_show_file(folder, parent_sha, file)
            new_bytes = git_ops.git_show_file(folder, sha, file)
        except FileNotFoundError as e:
            yield {"data": json.dumps({"type": "error", "detail": str(e)})}
            return

        fd_a, path_a = tempfile.mkstemp(suffix=".yxmd")
        fd_b, path_b = tempfile.mkstemp(suffix=".yxmd")
        try:
            os.write(fd_a, old_bytes); os.close(fd_a)
            os.write(fd_b, new_bytes); os.close(fd_b)

            from alteryx_diff.pipeline import DiffRequest
            from alteryx_diff.pipeline import run as pipeline_run
            from alteryx_diff.llm.context_builder import ContextBuilder

            response = pipeline_run(
                DiffRequest(path_a=pathlib.Path(path_a), path_b=pathlib.Path(path_b))
            )
            context = ContextBuilder.build_from_diff(response.result)
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

        # Merge business context if present
        import pathlib as _pl
        acd_ctx = _pl.Path(folder) / ".acd" / "context.json"
        if acd_ctx.exists():
            try:
                stored = json.loads(acd_ctx.read_text(encoding="utf-8"))
                context["business_context"] = stored.get("business_context", "")
            except Exception:
                pass

        yield {"data": json.dumps({"type": "progress", "step": "Annotating tools..."})}

        # Build LLM instance — inline provider:model_name parsing
        provider, _, model_name = model_str.partition(":")
        try:
            if provider == "ollama":
                from langchain_ollama import ChatOllama
                llm = ChatOllama(model=model_name, temperature=0)
            elif provider in ("openai", "openrouter"):
                from langchain_openai import ChatOpenAI
                import os as _os
                kwargs: dict = {"model": model_name, "temperature": 0}
                if provider == "openrouter":
                    kwargs["base_url"] = "https://openrouter.ai/api/v1"
                    kwargs["api_key"] = _os.environ.get("OPENROUTER_API_KEY", "")
                else:
                    kwargs["api_key"] = _os.environ.get("OPENAI_API_KEY", "")
                llm = ChatOpenAI(**kwargs)
            else:
                yield {"data": json.dumps({"type": "error", "detail": f"Unknown provider: {provider}"})}
                return
        except ImportError as e:
            yield {"data": json.dumps({"type": "unavailable", "reason": "no_extras"})}
            return

        yield {"data": json.dumps({"type": "progress", "step": "Assessing risks..."})}

        from alteryx_diff.llm.doc_graph import generate_change_narrative
        narrative = await generate_change_narrative(context, llm)

        yield {"data": json.dumps({"type": "result", "narrative": narrative.narrative, "risks": narrative.risks})}

    return EventSourceResponse(event_generator())
```

### Frontend: `useAISummary` Hook Skeleton

```typescript
// app/frontend/src/hooks/useAISummary.ts
// Source: useWatchEvents.ts pattern — adapted for request-scoped finite stream
import { useState, useRef } from 'react'

type SummaryStatus = 'idle' | 'loading' | 'result' | 'unavailable_no_extras' | 'unavailable_no_model' | 'error'

export function useAISummary() {
  const [status, setStatus] = useState<SummaryStatus>('idle')
  const [steps, setSteps] = useState<string[]>([])
  const [narrative, setNarrative] = useState<string | null>(null)
  const [risks, setRisks] = useState<string[]>([])
  const [errorDetail, setErrorDetail] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)

  function trigger(folder: string, sha: string, file: string) {
    esRef.current?.close()
    setStatus('loading')
    setSteps([])
    setNarrative(null)
    setRisks([])
    setErrorDetail(null)

    const url = `/api/ai/summary?folder=${encodeURIComponent(folder)}&sha=${encodeURIComponent(sha)}&file=${encodeURIComponent(file)}`
    const es = new EventSource(url)

    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data)
        if (payload.type === 'progress') {
          setSteps((prev) => [...prev, payload.step as string])
        } else if (payload.type === 'result') {
          setNarrative(payload.narrative as string)
          setRisks((payload.risks as string[]) ?? [])
          setStatus('result')
          es.close()
          esRef.current = null
        } else if (payload.type === 'unavailable') {
          setStatus(payload.reason === 'no_extras' ? 'unavailable_no_extras' : 'unavailable_no_model')
          es.close()
          esRef.current = null
        } else if (payload.type === 'error') {
          setErrorDetail(payload.detail as string)
          setStatus('error')
          es.close()
          esRef.current = null
        }
      } catch {
        // Ignore malformed events
      }
    }

    es.onerror = () => {
      setStatus('error')
      es.close()
      esRef.current = null
    }

    esRef.current = es
  }

  function reset() {
    esRef.current?.close()
    esRef.current = null
    setStatus('idle')
    setSteps([])
    setNarrative(null)
    setRisks([])
    setErrorDetail(null)
  }

  return { status, steps, narrative, risks, errorDetail, trigger, reset }
}
```

### Backend: Extended CommitBody

```python
# app/routers/save.py — extend CommitBody only
class CommitBody(BaseModel):
    project_id: str
    folder: str
    files: list[str]
    message: str
    business_context: str | None = None  # new optional field — APPAI-01
```

### Backend: Write context.json in commit_version

```python
# In commit_version(), after git_ops.git_commit_files() succeeds:
if body.business_context:
    from pathlib import Path
    import json as _json
    acd_dir = Path(body.folder) / ".acd"
    acd_dir.mkdir(parents=True, exist_ok=True)
    (acd_dir / "context.json").write_text(
        _json.dumps({"business_context": body.business_context}),
        encoding="utf-8",
    )
```

### Frontend: ChangesPanel business_context field addition

The `handleSave` function's fetch body needs `business_context`:
```typescript
body: JSON.stringify({
  project_id: projectId,
  folder: projectPath,
  files: checkedFiles,
  message: commitMessage,
  business_context: businessContext || null,   // new
}),
```

The `!hasAnyCommits` block in the JSX gets a Textarea after the amber Card (per UI-SPEC line 108-117):
```tsx
{!hasAnyCommits && (
  <div className="flex flex-col gap-1.5">
    <label htmlFor="business-context" className="text-sm font-medium">
      Business context
    </label>
    <Textarea
      id="business-context"
      placeholder="Describe what these workflows do and who uses them (optional)"
      value={businessContext}
      onChange={(e) => setBusinessContext(e.target.value)}
      rows={3}
      className="resize-none"
    />
    <p className="text-xs text-muted-foreground">
      Saved once to help the AI understand your project.
    </p>
  </div>
)}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `generate_documentation` (4-node LangGraph) | `generate_change_narrative` (single structured call) | Phase 25 | Simpler; no real per-node progress — progress events must be manually emitted |
| Persistent SSE (watch/badge) | Request-scoped SSE (AI summary) | Phase 26 (new) | No queue subscription needed; generator terminates after final result event |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `.acd/` directory already exists or can be created with `mkdir(parents=True, exist_ok=True)` — no special init step needed | Architecture Patterns | Minor — would need to add explicit dir creation step in Wave 0 |
| A2 | `app.services.git_ops.git_show_file` exists and is the correct function for retrieving file content at a specific SHA | Code Examples | Would need to find the correct git function name |
| A3 | `cfg["llm_model"]` is the exact config key written by Phase 25 CLI for model preference | Architecture Patterns (model resolution) | If key name differs, AI summary will always show "No LLM model configured" |

**A2 verification:** [VERIFIED: codebase — `git_show_file` is called in `history.py` lines 101-106 via `git_ops.git_show_file(folder, parent_sha, file)` — confirmed correct function]

**A3 verification:** [VERIFIED: codebase — `cli.py` line 231 `stored = cfg.get("llm_model")` reads from config_store — key is `"llm_model"`]

**A1 verification:** [VERIFIED: codebase — `save.py` line 33: `git_discard_files` uses `.acd-backup` dir pattern; `context.json` goes in `.acd/` (different subdirectory). `mkdir(parents=True, exist_ok=True)` is the correct safe pattern]

**If this table is effective empty (A1, A2, A3 all verified):** All critical claims verified from codebase. Assumptions table is informational only.

---

## Open Questions (RESOLVED)

1. **Business context grounding: how is it passed to `generate_change_narrative()`?**
   - What we know: `ContextBuilder.build_from_diff()` returns `{"summary": ..., "changes": ...}`. The LLM prompt in `generate_change_narrative()` passes this as `json.dumps(context, indent=2)`.
   - What's unclear: Adding `context["business_context"] = "..."` will include it in the JSON dump, so the LLM will see it — but there is no explicit mention of it in the system or human prompts.
   - Recommendation: Add a line to the human message prompt in `generate_change_narrative()` referencing `business_context` if present, OR document that the raw context inclusion is sufficient. For Phase 26, raw inclusion in the context dict is sufficient (the LLM will use it if present). No prompt surgery required.

2. **`compare_to` parameter for AI summary?**
   - What we know: The diff viewer has a `compare_to` (merge-base SHA) for experiment branches. The AI summary endpoint uses `sha~1` as the parent by default.
   - What's unclear: Should the AI summary also accept `compare_to` for experiment branch diffs?
   - Recommendation: Skip `compare_to` support in Phase 26. The AI panel is only shown for non-first-commit diffs; the D-08 description says "one stream per user click" with `folder`, `sha`, and `file` params only.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | All backend | ✓ | 3.12.4 | — |
| pytest | Test suite | ✓ | 7.4.4 | — |
| `sse_starlette` | `EventSourceResponse` | ✓ (used in watch.py) | (project-installed) | — |
| `fastapi` | API router | ✓ (project core) | (project-installed) | — |
| `alteryx_diff[llm]` | LLM call | conditionally — guarded by `require_llm_deps()` | (optional extras) | Graceful "unavailable" SSE event |
| `langchain_ollama` / `langchain_openai` | LLM provider | conditionally — guarded by try/except ImportError | (optional extras) | Same graceful path |

**Missing dependencies with no fallback:** None — all LLM extras have graceful fallback paths per D-06.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `pythonpath = ["."]` |
| Quick run command | `pytest tests/test_save.py tests/test_ai.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| APPAI-01 | `CommitBody` accepts optional `business_context` field | unit | `pytest tests/test_save.py -x -k business_context` | ❌ Wave 0 |
| APPAI-01 | `commit_version` writes `.acd/context.json` when `business_context` is non-empty | unit | `pytest tests/test_save.py -x -k context_json` | ❌ Wave 0 |
| APPAI-01 | `commit_version` does NOT write `.acd/context.json` when `business_context` is empty/None | unit | `pytest tests/test_save.py -x -k no_context_json` | ❌ Wave 0 |
| APPAI-02 | `GET /api/ai/summary` returns `text/event-stream` content type | unit | `pytest tests/test_ai.py -x -k sse_headers` | ❌ Wave 0 |
| APPAI-02 | SSE stream emits `unavailable` event when LLM extras not installed | unit | `pytest tests/test_ai.py -x -k no_extras` | ❌ Wave 0 |
| APPAI-02 | SSE stream emits `unavailable` event when no model configured | unit | `pytest tests/test_ai.py -x -k no_model` | ❌ Wave 0 |
| APPAI-02 | SSE stream emits `progress` events followed by `result` event (happy path, mocked LLM) | unit | `pytest tests/test_ai.py -x -k happy_path` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_save.py tests/test_ai.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ai.py` — covers APPAI-02 SSE endpoint tests
- [ ] `tests/test_save.py` — extend with APPAI-01 business_context tests (file exists, needs new test functions)
- [ ] Test pattern for SSE endpoint: use the `watch_events` direct-call pattern from `test_watch.py` — call `ai_summary()` directly with `AsyncMock(return_value=True)` for `request.is_disconnected`. LLM calls mocked with `AsyncMock`.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Internal app — no auth on any endpoint |
| V3 Session Management | no | Same |
| V4 Access Control | no | Same |
| V5 Input Validation | yes | FastAPI/Pydantic validates query params (`folder`, `sha`, `file`); `CommitBody` Pydantic validates `business_context` |
| V6 Cryptography | no | No new crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `folder` query param | Tampering | Mitigated by OS — existing pattern in history.py; `folder` is a registered project path (not user-supplied arbitrary path) |
| LLM prompt injection via `business_context` | Tampering | Context injected as JSON value, not raw string in prompt — JSON encoding prevents most prompt injection |
| Overly large `business_context` input | Denial of Service | Frontend has no character limit (per D-02); backend could truncate at a reasonable limit (~2000 chars) — implementer's discretion |

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] `app/routers/watch.py` — EventSourceResponse + event_generator pattern (lines 19-58)
- [VERIFIED: codebase] `app/frontend/src/hooks/useWatchEvents.ts` — frontend EventSource hook pattern
- [VERIFIED: codebase] `src/alteryx_diff/llm/doc_graph.py` — `generate_change_narrative()` signature and implementation (lines 262-299)
- [VERIFIED: codebase] `src/alteryx_diff/llm/context_builder.py` — `ContextBuilder.build_from_diff()` output shape
- [VERIFIED: codebase] `src/alteryx_diff/llm/models.py` — `ChangeNarrative` Pydantic model (narrative: str, risks: list[str])
- [VERIFIED: codebase] `app/routers/save.py` — `CommitBody` shape, `commit_version` endpoint
- [VERIFIED: codebase] `app/routers/history.py` — `_run_diff` pattern using `pipeline_run()` + mkstemp
- [VERIFIED: codebase] `src/alteryx_diff/cli.py` — `_resolve_model_string()` and `_resolve_llm()` (model resolution pattern)
- [VERIFIED: codebase] `app/server.py` — router registration pattern
- [VERIFIED: codebase] `tests/test_watch.py` — SSE test pattern (direct handler call with AsyncMock)
- [VERIFIED: context] `.planning/phases/26-companion-app-ai-integration/26-CONTEXT.md` — all locked decisions
- [VERIFIED: context] `.planning/phases/26-companion-app-ai-integration/26-UI-SPEC.md` — UI design contract
- [VERIFIED: context] `.planning/STATE.md` — CORE-01 compliance notes, router registration pitfall pattern

### Secondary (MEDIUM confidence)
- [CITED: project codebase conventions] shadcn/ui component path convention (`src/components/ui/` not `@/components/ui/`) — established in Phase 11 and repeated for every subsequent phase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in codebase
- Architecture: HIGH — patterns read directly from existing router + hook code
- Pitfalls: HIGH — most sourced from STATE.md Accumulated Context (observed failures in prior phases)
- LLM integration: HIGH — function signatures read from source

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable codebase — no fast-moving external dependencies)
