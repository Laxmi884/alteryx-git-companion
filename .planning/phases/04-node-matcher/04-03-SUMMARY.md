---
phase: 04-node-matcher
plan: "03"
subsystem: matching
tags: [contract-tests, matcher, two-pass, fixture-library, DIFF-04]

# Dependency graph
requires:
  - phase: 04-node-matcher plan 01
    provides: match() entry point, MatchResult contract
  - phase: 04-node-matcher plan 02
    provides: _hungarian_match() full implementation, per-type cost matrix, threshold rejection

provides:
  - NormalizedNode fixture library (tests/fixtures/matching.py) — 7 fixture pairs, ToolIDs 301+
  - 9 contract tests covering all DIFF-04 scenarios (tests/test_matcher.py)
  - _check_invariant helper asserting count conservation (matched+removed==old, matched+added==new)

affects:
  - 05-diff-engine (DIFF-04 verified — diff engine can safely consume MatchResult)

# Tech tracking
tech-stack:
  added: []
  patterns: [fixture library separation (fixtures/matching.py), count invariant helper used in every test]

key-files:
  created:
    - tests/fixtures/matching.py
    - tests/test_matcher.py
  modified: []

key-decisions:
  - "Fixture ToolIDs start at 301 — no collision with Phase 1 (1-100), Phase 2 (1-2), Phase 3 (101-201) fixtures"
  - "make_node() builder imported but not re-exported in tests — used only locally in test_match_result_count_invariant"
  - "THRESHOLD fixture uses (0,0) vs (10000,10000) with different hash — ensures cost > 0.8 reliably triggers rejection"
  - "Cross-type test uses same hash + same position — documents that type isolation is unconditional, not cost-based"

patterns-established:
  - "Fixture-per-scenario: each test scenario has dedicated OLD/NEW list constants in matching.py — one-file extension point"
  - "Count invariant helper: _check_invariant() embedded in test file, called in every test case as a mandatory assertion"

requirements-completed: [DIFF-04]

# Metrics
duration: 2min
completed: 2026-03-02
---

# Phase 4 Plan 03: Node Matcher — Contract Tests Summary

**9 DIFF-04 contract tests with NormalizedNode fixture library covering exact match, full regen, partial regen, genuine add/remove, threshold rejection, empty inputs, cross-type isolation, and count invariant**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-02T15:58:39Z
- **Completed:** 2026-03-02T16:00:59Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `tests/fixtures/matching.py` created with `make_node()` builder and 14 fixture lists (7 OLD/NEW pairs)
- All ToolIDs start at 301 — no collision with any prior fixture files
- `tests/test_matcher.py` created with 9 tests covering every DIFF-04 scenario
- `_check_invariant()` helper defined once, called in all 9 tests — count conservation enforced
- No imports from internal modules (scipy, numpy, _cost.py, matcher.py) in either test file
- Full project test suite: 57 passed, 1 xfailed (9 new + 48 existing, zero regressions)
- DIFF-04 requirement fully verified end-to-end: Pass 1 exact ToolID, Pass 2 Hungarian, threshold rejection, cross-type isolation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests/fixtures/matching.py with NormalizedNode fixture library** — `e830255`
2. **Task 2: Write tests/test_matcher.py — 9 test cases covering all DIFF-04 scenarios** — `060851a`

## Files Created/Modified

- `tests/fixtures/matching.py` — `make_node()` convenience builder; 7 fixture pairs (EXACT_MATCH, FULL_REGEN, PARTIAL_REGEN, GENUINE_ADD, GENUINE_REMOVE, THRESHOLD, CROSS_TYPE)
- `tests/test_matcher.py` — 9 contract tests + `_check_invariant()` helper; only public API imports

## Decisions Made

- ToolIDs for matching fixtures start at 301 to avoid collision with all prior phase fixtures (Phase 1: 1-100, Phase 2: 1-2, Phase 3: 101-201)
- THRESHOLD fixture uses extreme positions (0,0 vs 10000,10000) with different hashes to guarantee cost > 0.8 reliably regardless of canvas bounds calculation
- CROSS_TYPE fixture uses same hash and same position intentionally — verifies type isolation is a hard block in the algorithm, not a cost-based coincidence
- `_check_invariant()` is a module-level helper (not a pytest fixture) — called explicitly in each test body for clear failure attribution

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff-format line length fixes (E501)**
- **Found during:** Task 1 and Task 2 commit attempts
- **Issue:** ruff-check reported E501 lines > 88 characters in both files (long inline comments)
- **Fix:** Shortened/split offending comment lines; ruff-format auto-reformatted multi-line return in make_node()
- **Files modified:** tests/fixtures/matching.py, tests/test_matcher.py
- **Commits:** e830255, 060851a (fixes folded into task commits)

## Issues Encountered

- pytest run outside venv shows `ModuleNotFoundError: No module named 'numpy'` — resolved by using `.venv/bin/python -m pytest` instead of system `python`

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- DIFF-04 requirement is fully locked in: all 9 test scenarios pass green
- Phase 5 diff engine can safely consume `MatchResult.matched/removed/added`
- Regression detection: any future change to `match()`, `_hungarian_match()`, or `_cost.py` that breaks behavior will fail at least one of the 9 contract tests

## Self-Check: PASSED

- FOUND: tests/fixtures/matching.py
- FOUND: tests/test_matcher.py
- FOUND: commit e830255 (Task 1: fixture library)
- FOUND: commit 060851a (Task 2: 9 contract tests)
- CONFIRMED: 9 passed (pytest tests/test_matcher.py -v)
- CONFIRMED: 57 passed, 1 xfailed (full suite, zero regressions)
- CONFIRMED: No scipy/numpy/internal imports in test files

---
*Phase: 04-node-matcher*
*Completed: 2026-03-02*
