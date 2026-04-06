---
phase: 26-companion-app-ai-integration
plan: "03"
subsystem: backend-api
tags: [sse, ai, fastapi, streaming, core-01]
dependency_graph:
  requires: [26-01]
  provides: [APPAI-02-backend]
  affects: [app/routers/ai.py, app/server.py]
tech_stack:
  added: []
  patterns: [EventSourceResponse, deferred-import, mkstemp-tempfile]
key_files:
  created:
    - app/routers/ai.py
  modified:
    - app/server.py
decisions:
  - "Deferred all LLM imports inside event_generator to maintain CORE-01 compliance"
  - "Used mkstemp pattern for temp files matching history.py convention (Windows-safe)"
  - "Progress events positioned before the deferred import block (Annotating tools) so topology analysis and tool annotation happen before LLM backend is resolved"
  - "ai.router appended after branch.router — SPA catch-all mount remains last"
metrics:
  duration: ~8min
  completed: 2026-04-05
  tasks_completed: 2
  files_modified: 2
---

# Phase 26 Plan 03: AI SSE Router Backend Summary

Request-scoped SSE endpoint at `GET /api/ai/summary` streaming 3 progress events then a `ChangeNarrative` result, with CORE-01-compliant deferred LLM imports.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create app/routers/ai.py SSE endpoint | 5a516b3 | app/routers/ai.py, tests/test_ai.py, tests/test_save.py |
| 2 | Register ai.router in server.py | 9090369 | app/server.py |

## What Was Built

**`app/routers/ai.py`** — New FastAPI router providing `GET /api/ai/summary` as an EventSourceResponse. The endpoint:

1. Defers all LLM/langchain imports inside `event_generator()` (CORE-01 compliance — module imports cleanly without `[llm]` extras)
2. Emits `{"type": "unavailable", "reason": "no_extras"}` if `require_llm_deps()` raises ImportError
3. Emits `{"type": "unavailable", "reason": "no_model"}` if `cfg["llm_model"]` is absent
4. On happy path: emits 3 progress events with exact D-07 labels:
   - `"Analyzing topology..."`
   - `"Annotating tools..."`
   - `"Assessing risks..."`
5. Calls `generate_change_narrative(context, llm)` and emits `{"type": "result", "narrative": ..., "risks": [...]}`
6. Uses mkstemp pattern for temp `.yxmd` files (Windows-safe, same as history.py)
7. Merges `.acd/context.json` business_context if present (APPAI-01 grounding)
8. Supports ollama, openai, and openrouter providers from `cfg["llm_model"]`

**`app/server.py`** — Added `ai` to router import tuple (alphabetical) and `app.include_router(ai.router)` after branch.router.

## Test Results

All 5 Plan 01 RED tests now GREEN:
- `test_ai_router_module_importable` — PASSED
- `test_ai_router_registered_in_server` — PASSED
- `test_ai_summary_no_extras_emits_unavailable_no_extras` — PASSED
- `test_ai_summary_no_model_configured_emits_unavailable_no_model` — PASSED
- `test_ai_summary_happy_path_emits_progress_then_result` — PASSED

Full suite: 244 passed, 4 pre-existing failures (test_remote, test_save APPAI-01 from Plan 02), 1 pre-existing error (test_cli.py CliRunner.mix_stderr).

## Deviations from Plan

None — plan executed exactly as written. The implementation matches the skeleton in 26-RESEARCH.md lines 380–496 precisely.

## Known Stubs

None — all event paths are wired. The `no_extras` and `no_model` unavailable paths are intentional graceful degradation, not stubs.

## Threat Flags

None — no new network endpoints beyond the planned `/api/ai/summary`. The endpoint takes `folder`, `sha`, `file` as query params (no user-controlled shell execution). Git operations go through the existing `git_ops.git_show_file` which uses subprocess with fixed args.

## Self-Check: PASSED

- `app/routers/ai.py` — FOUND
- `app/server.py` (modified) — FOUND
- `.planning/phases/26-companion-app-ai-integration/26-03-SUMMARY.md` — FOUND
- Commit `5a516b3` — FOUND (feat(26-03): create app/routers/ai.py SSE endpoint)
- Commit `9090369` — FOUND (feat(26-03): register ai.router in server.py)
- All 5 test_ai.py tests GREEN — VERIFIED
