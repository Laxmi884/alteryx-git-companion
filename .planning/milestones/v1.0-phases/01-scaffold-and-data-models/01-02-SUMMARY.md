---
phase: 01-scaffold-and-data-models
plan: "02"
subsystem: database
tags: [python, dataclasses, mypy, newtypes, typing]

# Dependency graph
requires:
  - phase: 01-01
    provides: uv src-layout scaffold with pyproject.toml, pre-commit hooks, and models/ directory stub

provides:
  - Three NewType aliases (ToolID, ConfigHash, AnchorName) in models/types.py
  - Six frozen dataclasses (AlteryxNode, AlteryxConnection, WorkflowDoc, NodeDiff, EdgeDiff, DiffResult) in workflow.py and diff.py
  - Single public export surface via models/__init__.py exposing all 9 symbols via __all__
  - mypy --strict passing on all 4 model files with zero errors

affects:
  - 01-03
  - 02-parse
  - 03-normalize
  - 04-match
  - 05-diff
  - 06-report
  - 07-render
  - 08-visualize
  - 09-cli

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "frozen=True, kw_only=True, slots=True on all dataclasses for immutability and memory efficiency"
    - "NewType aliases for domain-opaque types distinct from primitives at mypy level"
    - "field(default_factory=dict/tuple) for mutable/collection defaults in frozen dataclasses"
    - "Single __init__.py export surface — callers import from alteryx_diff.models, never from sub-modules"
    - "from __future__ import annotations in all model files for deferred annotation evaluation"

key-files:
  created:
    - src/alteryx_diff/models/types.py
    - src/alteryx_diff/models/workflow.py
    - src/alteryx_diff/models/diff.py
    - src/alteryx_diff/models/__init__.py
  modified: []

key-decisions:
  - "All dataclasses use @dataclass(frozen=True, kw_only=True, slots=True) — frozen for immutability, kw_only for explicit construction, slots for memory efficiency"
  - "AlteryxNode.config is dict[str, Any] with field(default_factory=dict) — flat key/value map; raw XML not stored in model layer"
  - "WorkflowDoc.nodes and connections are tuple[T, ...] with field(default_factory=tuple) — immutable collections compatible with frozen=True"
  - "AlteryxNode is topology-free — no connection references; all connections stored on WorkflowDoc"
  - "AlteryxNode.x and y are flat float fields — no nested Position dataclass, no tuple"
  - "NodeDiff.field_diffs is dict[str, tuple[Any, Any]] mapping field name to (old_value, new_value)"

patterns-established:
  - "Domain NewTypes: ToolID(int), ConfigHash(str), AnchorName(str) — distinct from primitives in mypy, constructed via ToolID(42)"
  - "Frozen dataclass pattern: @dataclass(frozen=True, kw_only=True, slots=True) — use for all model types in this project"
  - "Public surface pattern: re-export everything through __init__.py with explicit __all__"
  - "Collection defaults in frozen dataclasses: field(default_factory=tuple) not = ()"

requirements-completed: [PARSE-04]

# Metrics
duration: 4min
completed: 2026-03-01
---

# Phase 1 Plan 02: Data Models Summary

**Six frozen dataclasses and three NewType aliases defining the typed inter-phase API, passing mypy --strict across all four model files**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-01T14:36:04Z
- **Completed:** 2026-03-01T14:39:24Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Three domain NewType aliases (ToolID, ConfigHash, AnchorName) providing mypy-level type safety distinct from plain int/str
- Six frozen dataclasses with full type annotations covering workflow documents (AlteryxNode, AlteryxConnection, WorkflowDoc) and diff results (NodeDiff, EdgeDiff, DiffResult)
- Single canonical import surface via `alteryx_diff.models` — all 9 symbols accessible from one location with `__all__` defined
- Zero mypy --strict errors across all 4 model files; all pre-commit hooks pass (ruff-check, ruff-format, mypy)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write models/types.py — ToolID, ConfigHash, AnchorName NewTypes** - `56a1d98` (feat)
2. **Task 2: Write models/workflow.py and models/diff.py — all six dataclasses** - `40fc1d4` (feat)
3. **Task 3: Write models/__init__.py — single public export surface** - `370ffe0` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `src/alteryx_diff/models/types.py` - Three NewType aliases: ToolID(int), ConfigHash(str), AnchorName(str)
- `src/alteryx_diff/models/workflow.py` - AlteryxNode (tool_id, tool_type, x, y, config), AlteryxConnection (src/dst tool+anchor), WorkflowDoc (filepath, nodes tuple, connections tuple)
- `src/alteryx_diff/models/diff.py` - NodeDiff (tool_id, old_node, new_node, field_diffs), EdgeDiff (src/dst tool+anchor, change_type), DiffResult (four tuple fields)
- `src/alteryx_diff/models/__init__.py` - Re-exports all 9 symbols with __all__; canonical import surface for all downstream phases

## Decisions Made
- Used `@dataclass(frozen=True, kw_only=True, slots=True)` on all six dataclasses as specified — frozen prevents post-construction mutation, kw_only forces explicit field names at construction, slots reduces memory overhead
- `AlteryxNode.config: dict[str, Any]` with `field(default_factory=dict)` — flat map design serves Phase 3 normalizer (iterate/strip keys) and Phase 5 differ (field-level comparison) without leaking XML structure into model layer
- tuple fields use `field(default_factory=tuple)` consistently — never bare `= ()` (would raise ValueError in frozen dataclass at class definition time)
- `from __future__ import annotations` at top of workflow.py and diff.py — defers annotation evaluation, avoids any potential forward-reference issues as models cross-import

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed E501 line-too-long in types.py docstring**
- **Found during:** Task 1 (Write models/types.py)
- **Issue:** ToolID docstring was 91 characters, exceeding ruff's 88-char line limit; pre-commit ruff-check hook blocked commit
- **Fix:** Shortened docstring from "Distinct from plain int at mypy level" to "Distinct from plain int in mypy" (85 chars)
- **Files modified:** src/alteryx_diff/models/types.py
- **Verification:** ruff check passes with no errors
- **Committed in:** 56a1d98 (Task 1 commit)

**2. [Rule 1 - Bug] Ruff auto-removed unused AlteryxConnection import from diff.py**
- **Found during:** Task 2 (Write models/workflow.py and diff.py)
- **Issue:** diff.py imported AlteryxConnection from workflow.py but did not reference it directly in class definitions (it's used via AlteryxNode reference only); ruff F401 unused import
- **Fix:** Ruff auto-fixed by removing the unused import; re-staged and committed
- **Files modified:** src/alteryx_diff/models/diff.py
- **Verification:** ruff check and mypy --strict both pass; DiffResult/NodeDiff/EdgeDiff all verified correct
- **Committed in:** 40fc1d4 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs — linting issues caught by pre-commit hooks)
**Impact on plan:** Both fixes were linting correctness issues. No semantic or behavioral changes. No scope creep.

## Issues Encountered
- Pre-commit hooks (ruff-check + ruff-format) blocked commits twice due to line-length and unused-import violations in the plan-provided code snippets. Both resolved by fixing the offending lines and re-staging.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 9 model symbols are importable from `alteryx_diff.models` — downstream phases can begin coding against typed contracts immediately
- mypy --strict baseline established; all future phases must maintain zero-error compliance
- Plan 01-03 (final scaffold tasks) can proceed without dependency on these models

---
*Phase: 01-scaffold-and-data-models*
*Completed: 2026-03-01*
