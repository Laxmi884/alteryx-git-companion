---
phase: 03-normalization-layer
plan: "02"
subsystem: normalizer
tags: [sha256, json-canonicalization, regex, noise-stripping, hashing]

# Dependency graph
requires:
  - phase: 03-01
    provides: NormalizedNode and NormalizedWorkflowDoc frozen dataclasses
  - phase: 02-xml-parser-and-validation
    provides: WorkflowDoc, AlteryxNode, AlteryxConnection types from parser
provides:
  - normalize() pure function: WorkflowDoc -> NormalizedWorkflowDoc
  - patterns.py single-source registry for all Alteryx noise-stripping patterns
  - strip_noise() recursive deep-copy stripper for config dicts
  - 64-char SHA-256 hex config_hash via strip -> json.dumps(sort_keys=True) -> sha256 pipeline
affects:
  - 03-03 (phase 3 contract tests will validate patterns against fixture pairs)
  - 05-differ (uses config_hash as fast-path equality signal)
  - 09-cli (normalize() is called via pipeline.run())

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-source pattern registry: all noise-stripping rules live exclusively in patterns.py"
    - "Key-targeted GUID stripping: GUID_VALUE_KEYS frozenset, not value regex, avoids over-stripping"
    - "Deep-copy guard in strip_noise(): source AlteryxNode.config never mutated"
    - "Canonical JSON serialization: json.dumps(sort_keys=True, separators=(',',':')) for C14N"
    - "typing.cast() for narrowing Any return from recursive _strip_value() to dict[str, Any]"

key-files:
  created:
    - src/alteryx_diff/normalizer/__init__.py
    - src/alteryx_diff/normalizer/patterns.py
    - src/alteryx_diff/normalizer/_strip.py
    - src/alteryx_diff/normalizer/normalizer.py
  modified: []

key-decisions:
  - "GUID_VALUE_KEYS frozenset starts empty — keys added as discovered from real fixture inspection (not pre-populated speculatively)"
  - "C14N via json.dumps(sort_keys=True) not lxml etree.canonicalize() — parser produces Python dicts, not XML element objects"
  - "position=(node.x, node.y) is a separate field, never included in config_hash computation — layout noise cannot affect diff"
  - "default=str in json.dumps is safety net for non-JSON-serializable types (RESEARCH.md Pitfall 3)"
  - "Used typing.cast() instead of type: ignore[return-value] to satisfy mypy --strict on _strip_value Any return"

patterns-established:
  - "Normalizer module structure: patterns.py (registry) -> _strip.py (logic) -> normalizer.py (entry point) -> __init__.py (surface)"
  - "Pure function pipeline: no I/O, no side effects, flag-agnostic (--include-positions is Phase 5/9 concern)"

requirements-completed: [NORM-01, NORM-02]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 3 Plan 02: Normalization Pipeline Implementation Summary

**SHA-256 config hashing pipeline via strip_noise + json.dumps(sort_keys=True), with patterns.py as single-source registry for TempFile/ISO8601/GUID noise stripping**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T03:05:35Z
- **Completed:** 2026-03-02T03:08:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `patterns.py` as single-source registry: TEMPFILE_PATH_PATTERN, ISO8601_PATTERN, GUID_VALUE_KEYS frozenset (empty, populated from fixtures in Phase 3 tests), and three sentinel constants
- Created `_strip.py` with recursive `strip_noise()` that deep-copies before mutation and applies key-targeted GUID stripping before regex-based path/timestamp stripping
- Created `normalizer.py` with `normalize(WorkflowDoc) -> NormalizedWorkflowDoc` entry point: strip -> json.dumps(sort_keys=True) -> sha256 pipeline; position carried separately
- Attribute-reordered configs produce identical 64-char hex config_hash values (NORM-01); TempFile paths and ISO8601 timestamps stripped to sentinels (NORM-02); all 34 prior tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create normalizer/patterns.py — single-source stripping patterns registry** - `a276131` (feat)
2. **Task 2: Create normalizer/_strip.py and normalizer/normalizer.py — full pipeline** - `4287de6` (feat)

## Files Created/Modified

- `src/alteryx_diff/normalizer/__init__.py` - Package init; exports `normalize()` as public surface
- `src/alteryx_diff/normalizer/patterns.py` - Single-source registry for all noise-stripping patterns (compiled at import time)
- `src/alteryx_diff/normalizer/_strip.py` - Recursive `strip_noise()` with deep-copy guard and key-targeted GUID stripping
- `src/alteryx_diff/normalizer/normalizer.py` - `normalize()` entry point and `_compute_config_hash()` helper

## Decisions Made

- `GUID_VALUE_KEYS` starts empty: per RESEARCH.md, GUID key names are discovered from real .yxmd fixture inspection in Phase 3 tests, not pre-populated speculatively
- C14N via `json.dumps(sort_keys=True)` not `lxml etree.canonicalize()`: Phase 2 parser produces Python dicts (not XML element objects), so lxml's XML canonicalization does not apply
- `position=(node.x, node.y)` is structurally separate from `config_hash`: layout-only canvas moves must never affect the config comparison path; `--include-positions` flag is a Phase 5/9 concern
- `default=str` in `json.dumps`: safety net for non-JSON-serializable types per RESEARCH.md Pitfall 3

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mypy `no-any-return` error in strip_noise() return type**
- **Found during:** Task 2 (pre-commit mypy hook)
- **Issue:** `_strip_value()` returns `Any`; `strip_noise()` is declared `-> dict[str, Any]`; plan used `type: ignore[return-value]` but mypy flagged `unused-ignore` because the actual error code is `no-any-return`
- **Fix:** Used `typing.cast(dict[str, Any], _strip_value(copy.deepcopy(config)))` to narrow the type correctly without a suppress comment
- **Files modified:** `src/alteryx_diff/normalizer/_strip.py`
- **Verification:** mypy hook passed; 34 tests still pass
- **Committed in:** `4287de6` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed ruff E501 line-too-long in patterns.py comments**
- **Found during:** Task 1 (pre-commit ruff-check hook)
- **Issue:** Comments in `GUID_VALUE_KEYS` block exceeded 88-character line limit
- **Fix:** Shortened comment wording to fit within line length limit
- **Files modified:** `src/alteryx_diff/normalizer/patterns.py`
- **Verification:** ruff-check hook passed
- **Committed in:** `a276131` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both auto-fixes required for pre-commit hooks to pass. No scope creep; plan semantics unchanged.

## Issues Encountered

- Pre-commit ruff reformatted `patterns.py` on first commit attempt (quote style change from single to double quotes in regex); re-staged and re-committed
- Pre-commit ruff-format then ruff-check both ran independently: format passed but check found E501 in comments; fixed by shortening comment text

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `normalize()` is importable from `alteryx_diff.normalizer` and produces `NormalizedWorkflowDoc`
- All six pattern constants exported from `patterns.py` for Phase 3 contract tests to validate against fixture pairs
- `GUID_VALUE_KEYS` frozenset ready to be populated from real .yxmd fixture inspection in Phase 3 tests
- All 34 prior tests continue to pass; normalization pipeline is ready for Phase 3 contract test validation

---
*Phase: 03-normalization-layer*
*Completed: 2026-03-01*
