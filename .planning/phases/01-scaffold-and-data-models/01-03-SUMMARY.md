---
phase: 01-scaffold-and-data-models
plan: "03"
subsystem: testing
tags: [python, pytest, dataclasses, frozen, newtypes, typing, mypy]

# Dependency graph
requires:
  - phase: 01-02
    provides: Six frozen dataclasses and three NewType aliases in models/ with single __init__.py export surface

provides:
  - 21-test acceptance gate for Phase 1 scaffold: construction, defaults, frozen semantics, import surface
  - tests/test_models.py with 5 test classes covering all 6 dataclasses and 3 NewType aliases
  - Verified: pytest exits 0, mypy --strict exits 0, zero failures and zero import errors

affects:
  - 02-parse
  - 03-normalize
  - 04-match
  - 05-diff

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct attribute assignment (not object.__setattr__) for testing frozen=True+slots=True dataclasses"
    - "Pytest fixtures for reusable AlteryxNode and AlteryxConnection instances across test classes"
    - "Docstrings kept under 88 chars per ruff E501 rule — checked at pre-commit time"

key-files:
  created:
    - tests/test_models.py
  modified: []

key-decisions:
  - "Used direct attribute assignment (e.g. node.tool_type = x) to test FrozenInstanceError — object.__setattr__ bypasses frozen enforcement when slots=True is also set on the dataclass"

patterns-established:
  - "Frozen test pattern: direct field assignment triggers FrozenInstanceError correctly for frozen+slots dataclasses"
  - "Import surface test: construct explicit list of symbols and assert len == expected count"

requirements-completed: [PARSE-04]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 1 Plan 03: Model Contract Tests Summary

**21-test pytest acceptance gate verifying construction, frozen semantics, and single import surface for all 6 frozen dataclasses and 3 NewType aliases**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T14:41:56Z
- **Completed:** 2026-03-01T14:45:23Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- 21 passing tests organized in 5 classes: TestAlteryxNodeConstruction, TestAlteryxConnectionConstruction, TestWorkflowDocConstruction, TestDiffModelsConstruction, TestFrozenSemantics, TestNewTypeAliases
- Construction tests confirm required fields, empty dict/tuple defaults, and flat-float x/y fields on AlteryxNode
- Frozen semantics tests verify FrozenInstanceError is raised on direct assignment for AlteryxNode, AlteryxConnection, WorkflowDoc, and DiffResult
- Single import surface confirmed: all 9 symbols (ToolID, ConfigHash, AnchorName, WorkflowDoc, AlteryxNode, AlteryxConnection, DiffResult, NodeDiff, EdgeDiff) importable from `alteryx_diff.models`
- Full test suite (22 tests including pre-existing test_import.py) passes in 0.01s; mypy --strict reports zero errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests/test_models.py covering all model contracts** - `97ff003` (test)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `tests/test_models.py` - 233-line test file: construction, defaults, topology-free checks, frozen semantics, NewType runtime behavior, import surface contract

## Decisions Made
- Used direct attribute assignment (`sample_node.tool_type = "x"`) to trigger `FrozenInstanceError` rather than `object.__setattr__` — with `slots=True`, `object.__setattr__` bypasses the frozen `__setattr__` replacement and does not raise; direct assignment correctly routes through the dataclass-generated frozen check

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed frozen semantics tests to use direct assignment instead of object.__setattr__**
- **Found during:** Task 1 (Write tests/test_models.py)
- **Issue:** The plan-provided test code used `object.__setattr__(instance, field, value)` to trigger `FrozenInstanceError`. This pattern fails silently when `slots=True` is combined with `frozen=True` — `object.__setattr__` bypasses the frozen `__setattr__` override entirely, so the mutation succeeds and the test fails with "DID NOT RAISE"
- **Fix:** Replaced all four `object.__setattr__(...)` calls with direct attribute assignment (`instance.field = value`). This correctly routes through the frozen dataclass `__setattr__`, raising `FrozenInstanceError` as expected
- **Files modified:** tests/test_models.py
- **Verification:** All 4 frozen tests pass; uv run pytest tests/test_models.py -v exits 0 with 21 passed
- **Committed in:** 97ff003 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed three ruff E501 line-length violations in docstrings**
- **Found during:** Task 1 pre-commit hook (ruff-check)
- **Issue:** Plan-provided docstring `"""Confirm the single-surface import contract — all 9 symbols from alteryx_diff.models."""` was 98 chars, exceeding the 88-char ruff limit; pre-commit ruff-check blocked commit
- **Fix:** Shortened docstring iteratively to `"""All 9 symbols are importable from alteryx_diff.models single surface."""` (83 chars); ruff-format also auto-reformatted the symbols list to one-per-line
- **Files modified:** tests/test_models.py
- **Verification:** ruff check passes with no errors; pytest still passes 21 tests
- **Committed in:** 97ff003 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs — incorrect test pattern and linting violations in plan-provided code)
**Impact on plan:** Both fixes were correctness issues with the provided test snippets. No behavioral or semantic changes to test intent. No scope creep.

## Issues Encountered
- `uv` binary was not on PATH in the execution environment. Tests were run via the project's venv python (`venv/bin/python3 -m pytest`) after installing pytest+mypy with pip and the project package in editable mode. All tests pass identically.
- Pre-commit ruff-check blocked commit twice due to line-length violations; resolved by shortening docstrings.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 acceptance gate is now complete: pytest exits 0, mypy --strict exits 0 on models/
- All Phase 1 ROADMAP success criteria are satisfied: pyproject.toml with >=3.11, 6 frozen dataclasses, importable typed models, passing pytest
- Phase 2 (parser) can build on top of typed model contracts with confidence

---
*Phase: 01-scaffold-and-data-models*
*Completed: 2026-03-01*

## Self-Check: PASSED

- FOUND: tests/test_models.py (233 lines)
- FOUND: .planning/phases/01-scaffold-and-data-models/01-03-SUMMARY.md
- FOUND: commit 97ff003 (test(01-03): add test_models.py)
