---
phase: 03-normalization-layer
plan: "03"
subsystem: testing
tags: [fixtures, normalization, pytest, contract-testing, node-pair]

# Dependency graph
requires:
  - phase: 03-02
    provides: normalize() pipeline, patterns.py registry, strip_noise(), NormalizedNode
  - phase: 03-01
    provides: NormalizedNode and NormalizedWorkflowDoc frozen dataclasses
  - phase: 02-xml-parser-and-validation
    provides: AlteryxNode, AlteryxConnection, WorkflowDoc types
provides:
  - tests/fixtures/normalization.py: importable fixture library for test_normalizer.py
  - 7 NodePair fixtures covering all normalization contract scenarios
  - ROUND_TRIP_WORKFLOW WorkflowDoc for idempotency testing
  - GUID_PAIR_KEY exported for conditional xfail logic
affects:
  - 03-04 (test_normalizer.py consumes all fixtures from this file)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fixture-test separation: fixture definitions in fixtures/normalization.py, assertions in test_normalizer.py"
    - "NodePair NamedTuple with expect_equal bool: self-documenting contract assertions"
    - "GUID_PAIR_KEY export pattern: test file checks key in GUID_VALUE_KEYS before asserting"
    - "Negative test fixtures: US_DATE_PAIR and TEMPFILE_VS_NOFILE_PAIR document what must NOT be stripped"

key-files:
  created:
    - tests/fixtures/normalization.py
  modified: []

key-decisions:
  - "Fixture file separation from test file: each fixture is one-file-change extension point for new Alteryx metadata patterns"
  - "GUID_PAIR_KEY exported as str: test_normalizer.py checks GUID_PAIR_KEY in GUID_VALUE_KEYS before asserting equality (avoids unconditional failure when frozenset is empty)"
  - "US_DATE_PAIR with expect_equal=False: documents that MM/DD/YYYY user-supplied dates must NOT be stripped — regression guard"
  - "TEMPFILE_VS_NOFILE_PAIR with expect_equal=False: normalizer equalizes paths not key presence/absence — intentional correct behavior"
  - "ToolIDs start at 101: avoid collision with Phase 2 fixture nodes (ToolID 1 and 2 used in XML fixtures)"

patterns-established:
  - "NodePair NamedTuple pattern: (a, b, expect_equal, description) for self-documenting fixture pairs"
  - "Fixture IDs 101-114 for normalization nodes, 201+ for round-trip workflow nodes"

requirements-completed: [NORM-03, NORM-04]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 3 Plan 03: Normalization Fixtures Library Summary

**Importable fixture library with 7 NodePair fixtures and ROUND_TRIP_WORKFLOW covering all normalization contract scenarios — attribute ordering, position drift, TempFile stripping, ISO 8601 timestamp stripping, GUID key-targeted stripping, and two negative tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-02T03:11:16Z
- **Completed:** 2026-03-02T03:13:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/fixtures/normalization.py` as an importable fixture library for plan 03-04's test file
- 7 NodePairs exported: ATTR_ORDER_PAIR (C14N), POSITION_DRIFT_PAIR (position excluded from hash), TEMPFILE_PAIR, TEMPFILE_VS_NOFILE_PAIR, TIMESTAMP_PAIR, GUID_PAIR, US_DATE_PAIR
- ROUND_TRIP_WORKFLOW WorkflowDoc exported with 2 nodes and 1 connection for idempotency testing
- GUID_PAIR_KEY exported as `"@GUID"` string enabling conditional xfail in test_normalizer.py
- All 34 prior tests still pass; no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests/fixtures/normalization.py with all fixture pairs** - `2b04bb1` (feat)

## Files Created/Modified

- `tests/fixtures/normalization.py` - Importable fixture library with NodePair NamedTuple, 7 fixture pairs, ROUND_TRIP_WORKFLOW, and GUID_PAIR_KEY

## Decisions Made

- Fixture file separated from test file: adding a new Alteryx metadata pattern requires only one-file changes (fixtures/normalization.py + patterns.py), keeping both files small and maintainable
- GUID_PAIR_KEY exported as a string constant: test_normalizer.py can check `GUID_PAIR_KEY in GUID_VALUE_KEYS` before asserting — avoids unconditional test failure while GUID_VALUE_KEYS is still empty (awaiting real .yxmd file inspection in Phase 3/4)
- ToolIDs starting at 101: prevents collision with Phase 2 XML fixture nodes that use ToolID 1 and 2

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff E501 line-too-long in description strings**
- **Found during:** Task 1 (pre-commit ruff-check hook)
- **Issue:** 5 description strings and comments exceeded 88-character line limit; plan-provided code included exact long strings that ruff rejected
- **Fix:** Wrapped long description strings in parenthesized multi-line string concatenation; shortened verbose comment text; condensed one description string slightly
- **Files modified:** `tests/fixtures/normalization.py`
- **Verification:** `ruff check` passes; 34 tests still pass; all fixture structure assertions still pass
- **Committed in:** `2b04bb1` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - ruff E501 line length)
**Impact on plan:** Auto-fix required for pre-commit hooks to pass. Semantic content of fixture descriptions preserved; only string wrapping changed. No scope creep.

## Issues Encountered

- Pre-commit ruff-check failed on first commit attempt due to E501 in 5 lines; fixed by wrapping description strings across lines and shortening one comment — same pattern as 03-02 deviation

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `tests/fixtures/normalization.py` is importable and all 7 NodePairs + ROUND_TRIP_WORKFLOW have correct structure
- All fixture `expect_equal` values are documented and correct: True for ATTR_ORDER_PAIR, POSITION_DRIFT_PAIR, TEMPFILE_PAIR, TIMESTAMP_PAIR, GUID_PAIR; False for TEMPFILE_VS_NOFILE_PAIR and US_DATE_PAIR
- GUID_PAIR_KEY enables test_normalizer.py to xfail GUID_PAIR test until real .yxmd file inspection populates GUID_VALUE_KEYS
- Ready for plan 03-04: test_normalizer.py can import all fixtures and write parametrized assertions

---
*Phase: 03-normalization-layer*
*Completed: 2026-03-01*

## Self-Check: PASSED

- FOUND: tests/fixtures/normalization.py
- FOUND: .planning/phases/03-normalization-layer/03-03-SUMMARY.md
- FOUND commit: 2b04bb1 (task commit)
- FOUND commit: 00ca693 (docs commit)
