---
phase: 06-pipeline-orchestration-and-json-renderer
plan: 01
subsystem: api
tags: [pipeline, dataclasses, facade, orchestration, alteryx-diff]

# Dependency graph
requires:
  - phase: 02-xml-parser-and-validation
    provides: parse() function returning tuple[WorkflowDoc, WorkflowDoc]
  - phase: 03-normalization-layer
    provides: normalize() function returning NormalizedWorkflowDoc
  - phase: 04-node-matcher
    provides: match() function returning MatchResult
  - phase: 05-diff-engine
    provides: diff() function returning DiffResult
provides:
  - DiffRequest dataclass (frozen, slots) as pipeline input type
  - DiffResponse dataclass (frozen, slots) as pipeline output type
  - run() facade that chains all four pipeline stages (parse -> normalize -> match -> diff)
  - alteryx_diff.pipeline public surface importable by CLI, tests, and API callers
affects:
  - 06-02 (JSON renderer — calls pipeline.run())
  - 09-cli (CLI adapter — calls pipeline.run() as sole programmatic entry point)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Facade pattern: single run() entry point hides all stage import details from callers
    - Frozen dataclass pattern: DiffRequest and DiffResponse use frozen=True, kw_only=True, slots=True
    - Entry-point-agnostic design: zero sys/print/CLI imports in pipeline module

key-files:
  created:
    - src/alteryx_diff/pipeline/__init__.py
    - src/alteryx_diff/pipeline/pipeline.py
  modified: []

key-decisions:
  - "DiffRequest and DiffResponse use frozen=True, kw_only=True, slots=True — consistent with project-wide pattern for all pipeline output types"
  - "match() receives list(norm_a.nodes) and list(norm_b.nodes) — tuple-to-list conversion required by matcher signature"
  - "diff() receives doc_a.connections and doc_b.connections from parser output, NOT norm_a/norm_b.connections — correct edge identity source"
  - "docstring placed before from __future__ import annotations to follow project convention and satisfy ruff E402"

patterns-established:
  - "Pipeline entry point pattern: DiffRequest(path_a=..., path_b=...) -> run() -> DiffResponse(result=DiffResult)"
  - "Package __init__.py pattern: module docstring first, then from __future__ import annotations, then imports"

requirements-completed: [CLI-03]

# Metrics
duration: 2min
completed: 2026-03-06
---

# Phase 6 Plan 1: Pipeline Orchestration Summary

**Entry-point-agnostic pipeline facade run() with frozen DiffRequest/DiffResponse dataclasses, chaining parse -> normalize -> match -> diff into a single callable.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-06T03:43:34Z
- **Completed:** 2026-03-06T03:45:52Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Created `src/alteryx_diff/pipeline/pipeline.py` with DiffRequest, DiffResponse frozen dataclasses and run() facade
- Created `src/alteryx_diff/pipeline/__init__.py` exporting the public surface (run, DiffRequest, DiffResponse)
- run() correctly chains parse -> normalize -> match -> diff with proper type conversions (list() for matcher, doc_a.connections for differ)
- mypy --strict passes clean; ruff check + format passes clean; pre-commit hooks all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pipeline package — DiffRequest, DiffResponse dataclasses and run() facade** - `137207e` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/alteryx_diff/pipeline/pipeline.py` - DiffRequest/DiffResponse dataclasses and run() facade implementation
- `src/alteryx_diff/pipeline/__init__.py` - Public surface: exports run, DiffRequest, DiffResponse via __all__

## Decisions Made

- **Docstring placement:** Placed module docstring before `from __future__ import annotations` (not after, as the plan snippet showed) to match the project convention used in differ/__init__.py and normalizer/__init__.py — plan snippet had wrong ordering that triggered ruff E402.
- **Tuple-to-list conversion:** match() receives `list(norm_a.nodes), list(norm_b.nodes)` — the matcher signature explicitly takes list, not tuple; conversion is mandatory.
- **Connection source:** diff() receives `doc_a.connections, doc_b.connections` (from WorkflowDoc, not NormalizedWorkflowDoc) — correct edge identity source per plan spec.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed module docstring placement in __init__.py to resolve ruff E402**
- **Found during:** Task 1 (pipeline package creation)
- **Issue:** Plan's code snippet placed `from __future__ import annotations` before the module docstring, causing ruff E402 (module level import not at top of file)
- **Fix:** Reordered to put docstring first, then `from __future__ import annotations`, matching the existing project convention used in differ/__init__.py and normalizer/__init__.py
- **Files modified:** src/alteryx_diff/pipeline/__init__.py
- **Verification:** `ruff check` passed clean; `mypy --strict` and pre-commit hooks all green
- **Committed in:** 137207e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in plan's code snippet ordering)
**Impact on plan:** Necessary correctness fix. No scope creep.

## Issues Encountered

None beyond the docstring ordering fix documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Pipeline facade complete — CLI (Plan 9) and JSON renderer (Plan 06-02) can now call `pipeline.run(DiffRequest(...))` directly
- DiffResult available via `response.result` for downstream rendering
- All four pipeline stages (parse, normalize, match, diff) verified to chain correctly through the facade

---
*Phase: 06-pipeline-orchestration-and-json-renderer*
*Completed: 2026-03-06*
