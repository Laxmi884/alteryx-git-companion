---
phase: 05-diff-engine
plan: "01"
subsystem: diff-engine
tags: [deepdiff, differ, diff, dataclass, property]

# Dependency graph
requires:
  - phase: 04-node-matcher
    provides: MatchResult with matched/removed/added NormalizedNode tuples
  - phase: 01-scaffold-and-data-models
    provides: AlteryxNode, AlteryxConnection, DiffResult, NodeDiff, EdgeDiff model types
provides:
  - diff() function computing complete workflow diff from MatchResult and connections
  - DiffResult.is_empty property for empty-result detection
  - deepdiff>=8.0 runtime dependency in pyproject.toml
affects: [06-pipeline-orchestration, 07-json-renderer, 08-html-report, 09-graph]

# Tech tracking
tech-stack:
  added: [deepdiff>=8.0]
  patterns:
    - "Atomic list treatment in field diffs — entire list surfaced as before/after when any element changes"
    - "Fast-path config_hash comparison before DeepDiff call — skips expensive diff for identical nodes"
    - "slots=True incompatible with @property on Python 3.11 dataclasses — remove slots from DiffResult only"
    - "mypy override for deepdiff.* (no stubs published) — ignore_missing_imports = true in pyproject.toml"
    - "deepdiff added to pre-commit mypy hook additional_dependencies for isolated env resolution"

key-files:
  created:
    - src/alteryx_diff/differ/__init__.py
    - src/alteryx_diff/differ/differ.py
  modified:
    - src/alteryx_diff/models/diff.py
    - pyproject.toml
    - .pre-commit-config.yaml

key-decisions:
  - "slots=True removed from DiffResult only (NodeDiff and EdgeDiff unchanged) — Python 3.11 slots=True dataclasses are incompatible with @property descriptors"
  - "deepdiff>=8.0 added as runtime dep (not dev-only) — differ stage calls DeepDiff() at pipeline runtime, not just in tests"
  - "_EXCLUDED_FIELDS frozenset starts empty — keys added as GUID-like fields are discovered from real fixture inspection per research recommendation"
  - "ValueError raised when config_hash differed but DeepDiff finds nothing — developer bug signal (hash collision or wrong exclusion list)"
  - "Iterable item changes use atomic list treatment — whole list surfaced as before/after rather than individual element indices"
  - "mypy deepdiff.* override added to pyproject.toml since deepdiff ships no type stubs"

patterns-established:
  - "_diff_node() validates its own output — raises ValueError if field_diffs is empty after hash diff detected"
  - "DeepDiff called with ignore_order=False, verbose_level=2 — preserves field order sensitivity and gets old/new values"
  - "Edge diffs sorted by (src_tool, src_anchor, dst_tool, dst_anchor) for deterministic tuple output"

requirements-completed: [DIFF-01, DIFF-02, DIFF-03]

# Metrics
duration: 8min
completed: 2026-03-05
---

# Phase 5 Plan 01: Diff Engine - Core Computation Summary

**DeepDiff-powered field-level workflow differ with three computation paths: node additions/removals via MatchResult, config modifications via per-field DeepDiff, and edge symmetric difference**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-05T15:41:51Z
- **Completed:** 2026-03-05T15:49:51Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- Patched DiffResult to remove slots=True and add is_empty property (Python 3.11 constraint)
- Installed deepdiff>=8.0 runtime dependency; added to pyproject.toml and pre-commit mypy hook
- Implemented differ/ package with diff(), _diff_node(), _diff_edges() and helper utilities
- Field-level config diff handles all DeepDiff change types: values_changed, dictionary_item_added/removed, iterable_item_added/removed (atomic list), type_changes
- All 48 existing tests + 1 xfailed pass with zero regressions; mypy --strict and ruff pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Patch DiffResult and install deepdiff** - `34f6f5b` (feat)
2. **Task 2: Implement differ/ package** - `b032a80` (feat)

## Files Created/Modified
- `src/alteryx_diff/models/diff.py` - DiffResult: slots=True removed, is_empty @property added
- `src/alteryx_diff/differ/__init__.py` - Public surface exporting diff()
- `src/alteryx_diff/differ/differ.py` - Full implementation: diff(), _diff_node(), _diff_edges(), _deepdiff_path_to_dotted(), _get_nested_value(), _get_parent_path()
- `pyproject.toml` - deepdiff>=8.0 added to [project].dependencies; mypy override for deepdiff.*
- `.pre-commit-config.yaml` - deepdiff>=8.0 added to mypy hook additional_dependencies

## Decisions Made
- Removed slots=True from DiffResult only (NodeDiff and EdgeDiff unchanged) — Python 3.11 slots=True dataclasses are incompatible with @property descriptors. This is the minimal change that enables is_empty without modifying other model types.
- deepdiff>=8.0 added as a runtime dependency (not dev-only) since the differ stage calls DeepDiff() during production pipeline execution.
- _EXCLUDED_FIELDS frozenset starts empty per research recommendation — paths added only when GUID-like fields are discovered from real .yxmd fixture inspection.
- Added mypy override for deepdiff.* with ignore_missing_imports = true since deepdiff ships no type stubs; also added deepdiff to pre-commit mypy hook additional_dependencies so the isolated hook env can resolve the import.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added mypy deepdiff override and pre-commit hook dependency**
- **Found during:** Task 2 (differ/ package implementation)
- **Issue:** Pre-commit mypy hook runs in isolated env and could not find deepdiff — `import-not-found` error blocked commit
- **Fix:** Added deepdiff>=8.0 to .pre-commit-config.yaml mypy additional_dependencies; added [[tool.mypy.overrides]] for deepdiff.* in pyproject.toml
- **Files modified:** .pre-commit-config.yaml, pyproject.toml
- **Verification:** Pre-commit mypy hook passed on retry commit
- **Committed in:** b032a80 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (missing critical — type checking infrastructure for new dependency)
**Impact on plan:** Auto-fix necessary for pre-commit hooks to work with deepdiff. No scope creep.

## Issues Encountered
- ruff-format reformatted files on first Task 2 commit attempt (tuple unpacking style). Files were re-staged and committed successfully on second attempt.
- Pre-commit mypy hook could not find deepdiff in its isolated environment. Fixed by adding deepdiff to additional_dependencies and adding pyproject.toml mypy override for deepdiff.* module.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 5 Plan 01 complete: diff() importable as `from alteryx_diff.differ import diff`
- DiffResult.is_empty available for pipeline orchestration empty-diff fast-path
- All three computation paths implemented and functionally verified
- Ready for Phase 6 pipeline orchestration to wire together: parse -> normalize -> match -> diff

---
*Phase: 05-diff-engine*
*Completed: 2026-03-05*
