---
phase: 26-companion-app-ai-integration
plan: "01"
subsystem: ai-integration-tests
tags: [tdd, red-state, wave-0, appai-01, appai-02]
dependency_graph:
  requires: []
  provides: [red-test-scaffold-appai-01, red-test-scaffold-appai-02]
  affects: [tests/test_save.py, tests/test_ai.py]
tech_stack:
  added: []
  patterns: [asyncio.run-wrapper, direct-handler-call-for-sse]
key_files:
  created:
    - tests/test_ai.py
  modified:
    - tests/test_save.py
decisions:
  - "asyncio.run() pattern used for async SSE tests (not pytest-asyncio — not installed in project)"
  - "4 business_context tests appended after discard endpoint tests, before any undo tests"
  - "5 ai tests use direct handler call pattern (not TestClient) to avoid SSE stream hang"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 2
---

# Phase 26 Plan 01: Wave 0 RED Test Scaffold Summary

**One-liner:** RED test scaffold for APPAI-01 (business_context persistence) and APPAI-02 (SSE AI summary endpoint), 9 tests total failing for correct reasons before any production code exists.

## Objective

Create Wave 0 failing test scaffold covering both Phase 26 requirements. No production code created. Plans 02–04 will turn these RED tests GREEN.

## Tasks Completed

### Task 1: Extend tests/test_save.py with RED business_context tests (APPAI-01)

**Commit:** 544bca9

**Files modified:** `tests/test_save.py`

4 new test functions appended after existing endpoint tests:

- `test_commit_body_accepts_business_context_field` — fails with `AttributeError: 'CommitBody' object has no attribute 'business_context'` (field not yet on CommitBody)
- `test_commit_with_business_context_writes_context_json` — fails with `AssertionError: .acd/context.json must be created when business_context is provided`
- `test_commit_without_business_context_does_not_write_context_json` — passes (negative case: context.json correctly absent since feature not implemented)
- `test_commit_with_empty_business_context_does_not_write_context_json` — passes (negative case)

**Collection output:**
```
4/16 tests collected (12 deselected) in 0.01s
```

**Run output (RED):**
```
FAILED tests/test_save.py::test_commit_body_accepts_business_context_field
FAILED tests/test_save.py::test_commit_with_business_context_writes_context_json
2 failed, 2 passed
```

### Task 2: Create tests/test_ai.py with RED SSE endpoint tests (APPAI-02)

**Commit:** 56f738b

**Files created:** `tests/test_ai.py`

5 new test functions:

- `test_ai_router_module_importable` — fails `ImportError: cannot import name 'ai' from 'app.routers'`
- `test_ai_router_registered_in_server` — fails `AssertionError: /api/ai/summary not in routes`
- `test_ai_summary_no_extras_emits_unavailable_no_extras` — fails `ImportError` (ai module absent)
- `test_ai_summary_no_model_configured_emits_unavailable_no_model` — fails `ImportError`
- `test_ai_summary_happy_path_emits_progress_then_result` — fails `ImportError`

**Collection output:**
```
5 tests collected in 0.01s
```

**Run output (RED):**
```
FAILED tests/test_ai.py::test_ai_router_module_importable
FAILED tests/test_ai.py::test_ai_router_registered_in_server
FAILED tests/test_ai.py::test_ai_summary_no_extras_emits_unavailable_no_extras
FAILED tests/test_ai.py::test_ai_summary_no_model_configured_emits_unavailable_no_model
FAILED tests/test_ai.py::test_ai_summary_happy_path_emits_progress_then_result
5 failed in 1.02s
```

## Overall Verification

```
uv run pytest tests/test_ai.py tests/test_save.py -k "business_context or ai_" -q --no-header
```

Result: 7 failed (5 ai + 2 business_context), 2 passed (negative cases), exits non-zero (RED).

**Production code unchanged:** `git diff --name-only app/ src/` — no output.

## Deviations from Plan

### Auto-adapted Pattern

**1. [Rule 1 - Convention] asyncio.run() wrapper instead of @pytest.mark.asyncio**
- **Found during:** Task 2
- **Issue:** pytest-asyncio is not installed in the project. The plan provided @pytest.mark.asyncio decorated tests as the primary form, but specified to convert if not installed.
- **Fix:** Converted all 3 async SSE tests to sync wrappers using `asyncio.run()` pattern, matching the convention established in `tests/test_watch.py::test_sse_endpoint_headers`.
- **Files modified:** `tests/test_ai.py` (created with the correct pattern from the start)

## Next Plan Handoff (Plans 02 and 03)

**Plan 02 (APPAI-01 — business_context persistence):**
- Add `business_context: str | None = None` to `CommitBody` in `app/routers/save.py`
- Write `.acd/context.json` when non-empty, skip when None or `""`
- Target tests: `test_commit_body_accepts_business_context_field`, `test_commit_with_business_context_writes_context_json`

**Plan 03 (APPAI-02 — SSE AI summary router):**
- Create `app/routers/ai.py` with `router` and `ai_summary` async endpoint
- Register `ai.router` in `app/server.py`
- Guard LLM imports with `require_llm_deps()` — `ImportError` → `no_extras` event
- Check `load_config()["llm_model"]` — missing → `no_model` event
- Stream 3 progress SSE events with D-07 labels, then result event
- Target: all 5 tests in `tests/test_ai.py`

## Known Stubs

None — this is a test-only plan. No production code was created.

## Self-Check: PASSED

- `tests/test_ai.py` exists: FOUND
- `tests/test_save.py` modified with 4 new functions: FOUND
- Commit 544bca9 exists: FOUND
- Commit 56f738b exists: FOUND
- `app/routers/ai.py` does NOT exist: CONFIRMED
- `git diff --name-only app/ src/` returns nothing: CONFIRMED
