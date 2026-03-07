---
phase: 04-node-matcher
plan: "01"
subsystem: matching
tags: [scipy, hungarian-algorithm, dataclass, matcher, two-pass]

# Dependency graph
requires:
  - phase: 03-normalization-layer
    provides: NormalizedNode frozen dataclass with source (AlteryxNode), config_hash, position fields

provides:
  - matcher package with match() entry point and MatchResult output contract
  - Pass 1 exact ToolID lookup O(n) — handles stable-ToolID common case
  - MatchResult frozen dataclass with matched/removed/added tuple fields
  - COST_THRESHOLD = 0.8 constant for Pass 2 cost gating
  - _hungarian_match() stub raising NotImplementedError (isolation point for Plan 02)

affects:
  - 04-02-node-matcher (Hungarian Pass 2 implements _hungarian_match stub)
  - 04-03-node-matcher (contract tests exercise match() end-to-end)
  - 05-diff-engine (consumes MatchResult.matched/removed/added)

# Tech tracking
tech-stack:
  added: [scipy>=1.13, numpy>=2.4 (scipy transitive dep)]
  patterns: [two-pass matching with stub isolation, frozen dataclass for pipeline output contract]

key-files:
  created:
    - src/alteryx_diff/matcher/__init__.py
    - src/alteryx_diff/matcher/matcher.py
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "scipy>=1.13 added as runtime dep (uv resolved 1.17.1); lower bound per plan spec so future uv resolves stay flexible"
  - "_hungarian_match() stub raises NotImplementedError — enables test isolation in Plan 03 without importing scipy"
  - "MatchResult follows project-wide frozen=True, kw_only=True, slots=True pattern for all pipeline output types"
  - "Pass 2 skipped entirely when unmatched_old or unmatched_new is empty — avoids NotImplementedError on fully-matched workflows"

patterns-established:
  - "Pipeline stage output contract: frozen dataclass with tuple fields (not list) for immutability"
  - "Stub isolation: raise NotImplementedError in stub function so callers that never hit pass 2 work without Plan 02"

requirements-completed: [DIFF-04]

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 4 Plan 01: Node Matcher — scipy dependency and Pass 1 exact ToolID match Summary

**Two-pass matcher package skeleton with O(n) exact ToolID Pass 1, MatchResult contract, scipy runtime dependency, and NotImplementedError stub for Hungarian Pass 2**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T15:46:07Z
- **Completed:** 2026-03-02T15:48:55Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- scipy>=1.13 added to pyproject.toml and installed (resolved: scipy 1.17.1, numpy 2.4.2)
- matcher package created with `match()` and `MatchResult` as public surface in `__init__.py`
- Pass 1 exact ToolID lookup implemented in `matcher.py` — O(n), handles the common stable-ToolID case
- `MatchResult` frozen dataclass with `matched`, `removed`, `added` tuple fields; `COST_THRESHOLD = 0.8` constant defined
- `_hungarian_match()` stub raises `NotImplementedError` — enables Plan 03 test isolation
- Full 48-test suite (Phase 3 normalization) passes green; 1 xfailed (GUID, expected); zero regressions
- mypy --strict passes on `src/alteryx_diff/matcher/`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add scipy dependency and create matcher package skeleton** - `1da3bb9` (feat)
2. **Task 2: Run full test suite to confirm no regressions** - (verification only, no code changes committed)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/alteryx_diff/matcher/__init__.py` - Public surface: exposes `match()` and `MatchResult`; re-exports from `matcher.matcher`
- `src/alteryx_diff/matcher/matcher.py` - `MatchResult` frozen dataclass + `match()` Pass 1 + `_hungarian_match()` stub + `COST_THRESHOLD`
- `pyproject.toml` - Added `scipy>=1.13` to `[project] dependencies`
- `uv.lock` - Updated lock file with scipy 1.17.1 and numpy 2.4.2 (transitive)

## Decisions Made

- Used `scipy>=1.13` lower bound (not `>=1.17.1` that uv pinned) to keep the constraint flexible for future resolves while uv installs 1.17.1 locally
- `_hungarian_match()` stub raises `NotImplementedError` rather than returning empty lists — forces explicit Plan 02 implementation and prevents silent incorrect behavior for mismatched ToolID workflows
- Pass 2 short-circuits entirely when either `unmatched_old` or `unmatched_new` is empty — identical-ToolID workflows never touch the stub

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `uv` was not on PATH (shell profile not sourced in execution environment). Located binary at `~/.cache/uv/archive-v0/.../uv` and used absolute path. No code changes required.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `from alteryx_diff.matcher import match, MatchResult` works end-to-end
- Pass 1 correct for all workflows with stable ToolIDs (the common case)
- Plan 02 implements `_hungarian_match()` in `_cost.py` to handle ToolID-churned workflows
- Plan 03 adds contract tests using `match()` end-to-end, exercising both pass 1 (direct) and pass 2 (via `pytest.raises(NotImplementedError)` for now)

---
*Phase: 04-node-matcher*
*Completed: 2026-03-02*
