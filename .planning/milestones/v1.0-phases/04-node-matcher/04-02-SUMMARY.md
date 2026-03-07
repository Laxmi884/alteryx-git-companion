---
phase: 04-node-matcher
plan: "02"
subsystem: matching
tags: [scipy, hungarian-algorithm, cost-matrix, position-cost, hash-cost, two-pass]

# Dependency graph
requires:
  - phase: 04-node-matcher plan 01
    provides: matcher package, MatchResult contract, _hungarian_match stub, COST_THRESHOLD

provides:
  - _cost.py with _build_cost_matrix (0.5*position + 0.5*hash), _position_cost (normalized Euclidean), _hash_cost (binary)
  - _hungarian_match() fully implemented with per-type grouping, linear_sum_assignment, post-assignment threshold rejection
  - match() is now a complete two-pass function — handles ToolID regeneration scenarios

affects:
  - 04-03-node-matcher (contract tests exercise match() end-to-end including Pass 2)
  - 05-diff-engine (consumes MatchResult.matched/removed/added)

# Tech tracking
tech-stack:
  added: [scipy-stubs>=1.13 (dev), numpy-typing-compat (transitive), optype (transitive)]
  patterns: [per-type cost matrix isolation, post-assignment threshold rejection, union-of-types routing]

key-files:
  created:
    - src/alteryx_diff/matcher/_cost.py
  modified:
    - src/alteryx_diff/matcher/matcher.py
    - pyproject.toml
    - uv.lock
    - .pre-commit-config.yaml

key-decisions:
  - "_cost.py is internal (underscore prefix) — not imported in __init__.py; no __all__; consumed exclusively by _hungarian_match()"
  - "Canvas bounds derived from UNION of old+new groups: consistent normalisation prevents asymmetric cost scaling"
  - "x_range/y_range default to 1.0 when spread is 0 — prevents ZeroDivisionError for type groups where all tools share same coordinate"
  - "Threshold (cost > 0.8) applied AFTER linear_sum_assignment per pair — pre-filtering with inf/nan corrupts scipy solver"
  - "zip(row_ind.tolist(), col_ind.tolist(), strict=True) — .tolist() converts numpy int arrays to Python int for set membership; strict=True per ruff B905"
  - "scipy-stubs added as dev dep; pre-commit mypy hook updated with numpy>=2.0, scipy>=1.13, scipy-stubs>=1.13 to resolve import-untyped errors in hook's isolated env"

patterns-established:
  - "Internal cost module: underscore prefix, no public surface, imported only by its sibling function"
  - "Post-assignment threshold gating: never pre-filter cost matrix; always run solver on full matrix then reject pairs"
  - "Union-of-types routing: set(old_by_type) | set(new_by_type) ensures no nodes are silently dropped"

requirements-completed: [DIFF-04]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 4 Plan 02: Node Matcher — Hungarian algorithm Pass 2 Summary

**Complete Hungarian algorithm fallback with per-type cost matrices (0.5 position + 0.5 config hash), scipy linear_sum_assignment, and post-assignment threshold rejection — zero phantom pairs on ToolID regeneration**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T15:50:45Z
- **Completed:** 2026-03-02T15:55:39Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `_cost.py` created with three helpers: `_position_cost` (normalized Euclidean, clamped to [0,1]), `_hash_cost` (binary 0.0/1.0), `_build_cost_matrix` (0.5/0.5 equal weighting, union canvas bounds)
- `_hungarian_match()` stub fully replaced: per-type grouping via `defaultdict`, one `linear_sum_assignment` call per type group, post-assignment threshold rejection at cost > 0.8
- Full ToolID regeneration scenario verified: 2 same-type, same-config, nearby-position nodes with different ToolIDs — matched with 0 removed, 0 added
- Cross-type isolation verified: Filter vs Join never paired regardless of position/hash similarity
- MatchResult invariants hold: `len(matched) + len(removed) == len(old)`, `len(matched) + len(added) == len(new)`
- mypy --strict passes on full matcher package (3 source files, 0 issues)
- Full 48-test suite passes green; 1 xfailed (GUID, expected); zero regressions
- scipy-stubs added as dev dependency; pre-commit mypy hook updated

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _cost.py with cost matrix construction helpers** — `1375014`
2. **Task 2: Replace _hungarian_match() stub with full implementation** — `c1038f0`

## Files Created/Modified

- `src/alteryx_diff/matcher/_cost.py` — Internal cost helpers: `_position_cost`, `_hash_cost`, `_build_cost_matrix`
- `src/alteryx_diff/matcher/matcher.py` — `_hungarian_match()` fully implemented; `defaultdict`, `linear_sum_assignment`, threshold gating
- `pyproject.toml` — Added `scipy-stubs` to dev dependency group
- `uv.lock` — Updated with scipy-stubs 1.17.1.0, numpy-typing-compat 20251206.2.4, optype 0.16.0
- `.pre-commit-config.yaml` — Added numpy>=2.0, scipy>=1.13, scipy-stubs>=1.13 to pre-commit mypy hook additional_dependencies

## Decisions Made

- `_cost.py` is an internal module (underscore prefix) — no `__all__`, not re-exported in `__init__.py`; only `_hungarian_match()` uses it
- Canvas bounds from UNION of old+new groups ensures symmetric normalisation — prevents a single outlier in one group from compressing costs in the other
- `x_range`/`y_range` default to `1.0` when spread is zero — guards against ZeroDivisionError for groups where all tools share the same canvas axis value
- `zip(row_ind.tolist(), col_ind.tolist(), strict=True)` — `.tolist()` converts numpy int64 to Python int (required for `set` membership test); `strict=True` per ruff B905 rule
- scipy-stubs needed for mypy --strict; added to both project dev deps and pre-commit hook's isolated environment

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added numpy/scipy to pre-commit mypy hook additional_dependencies**
- **Found during:** Task 1 commit attempt
- **Issue:** Pre-commit mypy runs in an isolated environment that doesn't see the project's installed packages. `numpy` import caused `import-not-found` in the hook env even though numpy is installed in the project venv.
- **Fix:** Added `numpy>=2.0` and `scipy>=1.13` to `.pre-commit-config.yaml` mypy hook `additional_dependencies`. Same fix pattern as [02-01] lxml-stubs.
- **Commit:** `1375014` (included in Task 1 commit)

**2. [Rule 3 - Blocking] Added scipy-stubs dev dependency for mypy --strict**
- **Found during:** Task 2 verification
- **Issue:** mypy --strict reported `Library stubs not installed for "scipy.optimize" [import-untyped]` — scipy ships with partial stubs but mypy requires the `scipy-stubs` package for full type resolution under `--strict`.
- **Fix:** `uv add --dev scipy-stubs` (resolved 1.17.1.0); added `scipy-stubs>=1.13` to pre-commit hook too.
- **Commit:** `c1038f0` (included in Task 2 commit)

**3. [Rule 3 - Blocking] Ruff line length fix (E501)**
- **Found during:** Task 2 commit attempt
- **Issue:** Two lines exceeded 88-character limit. ruff-format auto-split them on the second commit attempt.
- **Fix:** ruff-format reformatted the lines; re-staged and committed.
- **Commit:** `c1038f0`

## Issues Encountered

- `uv` binary not on PATH; located at `/Users/laxmikantmukkawar/.cache/uv/archive-v0/bkiNW9PCUPjqEK-u4PtHi/uv-0.8.12.data/scripts/uv` (same as Plan 01)

## Next Phase Readiness

- `match()` is now a complete two-pass function: Pass 1 exact ToolID + Pass 2 Hungarian fallback
- Full ToolID regeneration scenario produces zero phantom pairs
- Plan 04-03 can now write contract tests that exercise Pass 2 directly (no more `pytest.raises(NotImplementedError)` needed)

## Self-Check: PASSED

- FOUND: src/alteryx_diff/matcher/_cost.py
- FOUND: src/alteryx_diff/matcher/matcher.py
- FOUND: .planning/phases/04-node-matcher/04-02-SUMMARY.md
- FOUND: commit 1375014 (Task 1: _cost.py)
- FOUND: commit c1038f0 (Task 2: _hungarian_match)
- CONFIRMED: NotImplementedError stub removed from matcher.py
- CONFIRMED: mypy --strict passes (3 source files, 0 issues)
- CONFIRMED: 48 passed, 1 xfailed (full test suite green)

---
*Phase: 04-node-matcher*
*Completed: 2026-03-02*
