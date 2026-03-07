---
phase: 03-normalization-layer
plan: "01"
subsystem: models
tags: [dataclass, normalization, frozen, slots, config-hash, position]

# Dependency graph
requires:
  - phase: 01-scaffold-and-data-models
    provides: AlteryxNode, AlteryxConnection, WorkflowDoc, ConfigHash, ToolID frozen dataclasses
provides:
  - NormalizedNode frozen dataclass with source, config_hash, and position fields
  - NormalizedWorkflowDoc frozen dataclass with source, nodes, and connections fields
  - Public export surface extended: all 10 model types importable from alteryx_diff.models
affects: [03-normalization-layer, 04-node-matcher, 05-differ]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - frozen=True, kw_only=True, slots=True dataclass convention extended to Phase 3 models
    - Two-path separation contract: config_hash and position as distinct fields on NormalizedNode

key-files:
  created:
    - src/alteryx_diff/models/normalized.py
  modified:
    - src/alteryx_diff/models/__init__.py

key-decisions:
  - "NormalizedNode.position is tuple[float, float] separate from config_hash — layout-only moves never affect config comparison path (NORM-04)"
  - "NormalizedNode.source carries original AlteryxNode for downstream identity access (tool_id, tool_type)"
  - "normalized.py imports from models.types and models.workflow directly (not from models) to avoid circular import"
  - "No __all__ in normalized.py — __init__.py is the sole public surface"

patterns-established:
  - "Two-path separation: config_hash vs position as distinct fields ensures layout noise cannot cause false-positive config diffs"
  - "Source-carrying pattern: normalized models carry their original parsed counterpart for downstream metadata access"

requirements-completed: [NORM-03, NORM-04]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 03 Plan 01: Normalized Models Summary

**NormalizedNode and NormalizedWorkflowDoc frozen dataclasses establishing the two-path config-hash/position separation contract for the normalization pipeline**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-02T03:00:06Z
- **Completed:** 2026-03-02T03:02:50Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created NormalizedNode frozen dataclass with source, config_hash (ConfigHash), and position (tuple[float, float]) fields — enforcing the two-path separation that prevents layout noise from triggering config diffs
- Created NormalizedWorkflowDoc frozen dataclass with source, nodes (tuple[NormalizedNode, ...]), and connections (tuple[AlteryxConnection, ...]) fields
- Extended alteryx_diff.models public export surface to include NormalizedNode and NormalizedWorkflowDoc alongside the 8 existing Phase 1 and Phase 2 models
- All 34 existing tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create normalized.py with NormalizedNode and NormalizedWorkflowDoc** - `0583552` (feat)
2. **Task 2: Extend models __init__.py to export normalized models** - `8741759` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `src/alteryx_diff/models/normalized.py` - New module with NormalizedNode and NormalizedWorkflowDoc frozen dataclasses
- `src/alteryx_diff/models/__init__.py` - Extended with normalized import line and __all__ entries under Phase 3 comment

## Decisions Made
- NormalizedNode.position is tuple[float, float] as a separate field from config_hash, enforcing the NORM-04 contract that layout-only canvas moves cannot affect config comparison
- NormalizedNode.source carries the full original AlteryxNode (not just tool_id) so downstream stages can read all identity fields without additional lookups
- normalized.py imports directly from models.types and models.workflow (not from models package) to avoid circular imports since normalized.py lives inside the models package
- No __all__ defined in normalized.py — the __init__.py is the sole public interface per project convention

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff E501 line-too-long in normalized.py docstrings**
- **Found during:** Task 1 (pre-commit hook on commit attempt)
- **Issue:** Two docstring lines in NormalizedWorkflowDoc exceeded the 88-character line limit (90 and 93 chars)
- **Fix:** Wrapped long docstring lines by inserting a newline before the closing triple-quote
- **Files modified:** src/alteryx_diff/models/normalized.py
- **Verification:** ruff check passed on subsequent commit attempt
- **Committed in:** 0583552 (Task 1 commit, after fix)

**2. [Rule 3 - Blocking] Fixed ruff E501 line-too-long in __init__.py docstring**
- **Found during:** Task 2 (pre-commit hook on commit attempt)
- **Issue:** Module docstring example line showing both NormalizedNode and NormalizedWorkflowDoc imports exceeded 88 chars (107 chars)
- **Fix:** Split the example import line into two separate import statements in the docstring
- **Files modified:** src/alteryx_diff/models/__init__.py
- **Verification:** ruff check passed on subsequent commit attempt
- **Committed in:** 8741759 (Task 2 commit, after fix)

---

**Total deviations:** 2 auto-fixed (2 blocking — ruff line-length violations in docstrings caught by pre-commit hook)
**Impact on plan:** Both fixes were cosmetic docstring formatting, required for pre-commit hook compliance. No behavior or contract changes.

## Issues Encountered
- `uv` binary not on PATH in non-interactive bash invocations; resolved by using the project venv pytest directly at `.venv/bin/pytest`

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- NormalizedNode and NormalizedWorkflowDoc contracts are defined; Phase 3 Plans 02-04 (normalizer implementation, contract tests) can program against these types
- The two-path separation (config_hash vs position) is locked as a structural guarantee for NORM-03 and NORM-04
- All Phase 1 and Phase 2 model exports remain unchanged — no breaking changes to downstream callers

---
*Phase: 03-normalization-layer*
*Completed: 2026-03-01*
