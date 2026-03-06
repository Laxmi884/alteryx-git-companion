---
phase: 05-diff-engine
plan: "02"
subsystem: testing
tags: [fixtures, diffing, pytest, sha256, MatchResult, AlteryxConnection]

# Dependency graph
requires:
  - phase: 04-node-matcher
    provides: MatchResult dataclass consumed directly by all 11 fixture scenarios
  - phase: 03-normalization-layer
    provides: NormalizedNode, ConfigHash, config hash convention (SHA-256 json.dumps)
  - phase: 01-scaffold-and-data-models
    provides: AlteryxNode, AlteryxConnection, ToolID, AnchorName types
provides:
  - 11 named fixture scenarios as 3-tuple constants (MatchResult, old_conns, new_conns)
  - Complete coverage of all DIFF-01/DIFF-02/DIFF-03 test case inputs
  - ToolID range 401-419 reserved for Phase 5 differ fixtures
affects:
  - 05-diff-engine/05-03 (imports all 11 constants directly)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fixture-as-module-level-constants pattern: each scenario is a tuple constant, not a pytest fixture function"
    - "3-tuple export pattern: (MatchResult, old_conns_tuple, new_conns_tuple)"
    - "SHA-256 hashes via json.dumps(config, sort_keys=True) matching Phase 3 normalizer convention"
    - "Module-level assert guards verify hash invariants at import time"

key-files:
  created:
    - tests/fixtures/diffing.py
  modified: []

key-decisions:
  - "ToolIDs start at 401 and use sequential allocation 401-419 — no collision with Phases 1-4 (max 399)"
  - "Hash invariants checked with module-level assert statements at import time — fails fast if config construction is wrong"
  - "Individual node exports (EDGE_ADDED_NODE_410, etc.) added for edge scenarios — tests can assert on specific ToolIDs"
  - "dict[str, Any] used instead of bare dict for helper function signatures — avoids mypy type-arg violations"

patterns-established:
  - "Differ fixture file parallels matching.py structure: helpers at top, scenarios below with section comments"
  - "All edge scenarios export named node constants alongside the scenario tuple"

requirements-completed: [DIFF-01, DIFF-02, DIFF-03]

# Metrics
duration: 3min
completed: 2026-03-06
---

# Phase 5 Plan 02: Differ Fixture Library Summary

**11 MatchResult + connection-tuple fixture scenarios for every DIFF-01/DIFF-02/DIFF-03 test case, with SHA-256 hashes matching Phase 3 normalizer convention and ToolIDs 401-419**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-06T03:04:10Z
- **Completed:** 2026-03-06T03:07:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `tests/fixtures/diffing.py` with 11 named scenario constants
- Each scenario exported as `(MatchResult, old_connections_tuple, new_connections_tuple)` 3-tuple
- All ToolIDs in range 401-419, no collision with Phases 1-4 fixtures
- Config hashes computed via SHA-256 of `json.dumps(config, sort_keys=True)` — matches Phase 3 normalizer
- Module-level assert guards verify hash invariants (modified scenarios have differing hashes, identical scenarios have matching hashes)
- Edge scenarios export individual node constants for fine-grained ToolID assertions in test_differ.py
- All 57 existing tests continue to pass (1 xfailed, unchanged)

## Task Commits

Each task was committed atomically:

1. **Task 1: Build differ fixture library** - `cdab949` (feat)

**Plan metadata:** (to be added)

## Files Created/Modified
- `tests/fixtures/diffing.py` — 11 fixture scenario constants covering node add/remove, config modifications (flat, nested, list, absent keys), edge add/remove/rewire, and identical workflows

## Decisions Made
- Used `dict[str, Any]` typing instead of bare `dict` for helper function signatures to avoid mypy `type-arg` violations (ruff E501 also required function signatures to be reformatted to fit 88-char line limit)
- Added module-level `assert` statements for hash invariants rather than runtime checks — fails fast at import time if config data is wrong
- Exported individual `EDGE_ADDED_NODE_*`, `EDGE_REMOVED_NODE_*`, and `EDGE_REWIRED_NODE_*` constants so test_differ.py can assert on specific ToolIDs without re-constructing nodes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed line-length violations caught by ruff E501**
- **Found during:** Task 1 (commit attempt)
- **Issue:** Type annotation on `_make_node` and `_hash` helpers used bare `dict` which caused `# type: ignore[type-arg]` comments that pushed lines over 88 chars
- **Fix:** Replaced bare `dict` with `dict[str, Any]` (adding `from typing import Any` import), removing the need for type-ignore comments entirely
- **Files modified:** tests/fixtures/diffing.py
- **Verification:** `awk 'length > 88' tests/fixtures/diffing.py` returns no output; ruff check passes
- **Committed in:** cdab949 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - type annotation bug causing line-length violation)
**Impact on plan:** Fix necessary for pre-commit hook compliance. No scope change.

## Issues Encountered
- ruff-format auto-reformatted the type annotation style for scenario constants (long tuple type annotations split across lines) — accepted reformatting, then fixed the remaining E501 violation manually

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 11 fixture scenarios ready for Plan 05-03 (test_differ.py)
- Each scenario covers one distinct behavior path the differ must handle
- SCENARIO_IDENTICAL_WORKFLOWS is the DiffResult.is_empty == True baseline
- Edge scenarios have named node exports for fine-grained assertion

## Self-Check: PASSED

- tests/fixtures/diffing.py: FOUND
- 05-02-SUMMARY.md: FOUND
- Commit cdab949: FOUND
- All 11 scenarios importable: VERIFIED
- pytest 57 passed, 1 xfailed: VERIFIED

---
*Phase: 05-diff-engine*
*Completed: 2026-03-06*
