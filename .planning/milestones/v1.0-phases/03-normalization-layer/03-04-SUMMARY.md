---
phase: 03-normalization-layer
plan: "04"
subsystem: testing

tags: [pytest, normalization, tdd, contract-tests, sha256, fixtures]

requires:
  - phase: 03-01
    provides: NormalizedNode, NormalizedWorkflowDoc frozen dataclasses
  - phase: 03-02
    provides: normalize() entry point, strip_noise(), GUID_VALUE_KEYS, pattern sentinels
  - phase: 03-03
    provides: NodePair fixture pairs and ROUND_TRIP_WORKFLOW for all 7 NORM scenarios

provides:
  - "tests/test_normalizer.py with 15 test functions covering NORM-01 through NORM-04"
  - "Regression safety net for the normalization pipeline — catches any future pattern breakage"
  - "GUID xfail test as living documentation of pending GUID_VALUE_KEYS registration"

affects:
  - 04-node-matcher
  - 05-differ
  - 09-cli

tech-stack:
  added: []
  patterns:
    - "Module-level test functions (no classes) — matches Phase 2 test convention from test_parser.py"
    - "_hash_pair(NodePair) helper keeps test bodies to 2-3 lines; all complexity in fixtures"
    - "_hash_of(AlteryxNode) -> str helper wraps single node in WorkflowDoc and calls normalize()"
    - "pytest.mark.xfail(strict=True) for GUID pending test — test present and documented but expected to fail"
    - "dataclasses.FrozenInstanceError (Python 3.11+) for frozen contract validation, not AttributeError"
    - "zip(strict=True) in idempotency loop — explicit signal that both result sets must have same length"

key-files:
  created:
    - tests/test_normalizer.py
  modified: []

key-decisions:
  - "xfail strict=True on GUID test — forces ERROR (not silent pass) if GUID_VALUE_KEYS populated without removing xfail mark"
  - "Ruff E501 line limit 88 chars enforced by pre-commit hook — all assert messages split across continuation f-strings"
  - "B905 zip() strict=True added in idempotency test — ruff enforces explicit strict parameter on all zip() calls"
  - "Unused imports (AnchorName, NormalizedNode, NormalizedWorkflowDoc) removed by ruff autofix — test file uses only ToolID, AlteryxNode, WorkflowDoc from models"

patterns-established:
  - "Test file imports: only what is directly used; ruff removes unused imports on commit"
  - "All assert messages use f-string multiline splitting to stay within 88-char line limit"

requirements-completed:
  - NORM-01
  - NORM-02
  - NORM-03
  - NORM-04

duration: 4min
completed: 2026-03-02
---

# Phase 3 Plan 04: Normalization Contract Test Suite Summary

**15-test contract suite covering NORM-01 through NORM-04 using NodePair fixtures — regression safety net for normalize() pipeline with xfail GUID pending test**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T03:18:24Z
- **Completed:** 2026-03-02T03:22:37Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Created tests/test_normalizer.py with 15 test functions covering all four NORM requirements
- Full test suite: 48 passed, 1 xfailed (GUID test pending GUID_VALUE_KEYS registration) — zero unexpected failures
- All normalization behavioral contracts verified: attribute ordering, noise stripping, position separation, signature flag-agnosticism, source immutability, frozen dataclass enforcement, idempotency, and hash format

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests/test_normalizer.py** - `1fdd1b1` (test)
2. **Task 2: Run full test suite verification** - verification only, no files changed

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `tests/test_normalizer.py` — 15-test normalization contract suite covering NORM-01 through NORM-04

## Decisions Made

- xfail strict=True on GUID test: forces an ERROR (not silent pass) if GUID_VALUE_KEYS is populated without removing the xfail mark — ensures the developer explicitly acknowledges the change
- Ruff E501 line limit 88 chars enforced by pre-commit hook: all long assert messages split across continuation f-strings
- B905 zip(strict=True) added in idempotency test: ruff enforces explicit strict parameter on all zip() calls
- Unused imports removed by ruff autofix: AnchorName, NormalizedNode, NormalizedWorkflowDoc not directly used in tests — only ToolID, AlteryxNode, WorkflowDoc needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff linting violations from pre-commit hook**

- **Found during:** Task 1 (test file creation and commit)
- **Issue:** Pre-commit ruff-check hook found 27 E501 (line too long > 88 chars), B905 (zip without strict=), and unused imports; ruff-format reformatted the file
- **Fix:** Shortened all assert messages by splitting across continuation f-strings; added strict=True to zip(); kept all test semantics identical
- **Files modified:** tests/test_normalizer.py
- **Verification:** Pre-commit hooks passed on second commit attempt; all 15 tests still pass
- **Committed in:** 1fdd1b1 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking linting violations)
**Impact on plan:** Required 2 commit attempts to clear pre-commit hooks. Test semantics and coverage unchanged.

## Issues Encountered

Pre-commit ruff hooks enforced E501 (88-char line limit) strictly on docstrings and f-string assertion messages. The plan's code template used strings longer than 88 characters throughout. Fixed by splitting all long strings across continuation f-strings and shortening docstrings while preserving meaning.

## Next Phase Readiness

- Phase 3 normalization layer is complete: data models (03-01), pipeline (03-02), fixtures (03-03), contract tests (03-04) all done
- normalize() behavioral contracts are fully locked in — Phase 4 (NodeMatcher) and Phase 5 (differ) can rely on these contracts
- GUID_VALUE_KEYS still empty — add "@GUID" when confirmed from real .yxmd inspection (test_guid_key_stripped_to_sentinel will automatically become a passing test)

---
*Phase: 03-normalization-layer*
*Completed: 2026-03-02*
