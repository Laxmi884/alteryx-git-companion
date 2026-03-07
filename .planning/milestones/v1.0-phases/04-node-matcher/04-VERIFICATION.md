---
phase: 04-node-matcher
verified: 2026-03-02T00:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
gaps: []
human_verification: []
---

# Phase 4: Node Matcher Verification Report

**Phase Goal:** When Alteryx regenerates ToolIDs, the node matcher still correctly pairs old and new tool instances rather than producing phantom add/remove pairs.
**Verified:** 2026-03-02
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All truths are drawn from the four Success Criteria in ROADMAP.md plus the consolidated must-haves across all three PLANs.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Two workflows where all ToolIDs were regenerated produce zero phantom additions or removals | VERIFIED | `test_full_toolid_regeneration` passes: old IDs 310/311, new IDs 390/391 — matched=2, removed=0, added=0 |
| 2 | A genuinely added tool is identified as an addition, not a rematch | VERIFIED | `test_genuine_addition` passes: added[0].source.tool_id == 331 |
| 3 | A genuinely removed tool is identified as a removal, not matched to an unrelated tool | VERIFIED | `test_genuine_removal` passes: removed[0].source.tool_id == 341 |
| 4 | Cost threshold > 0.8 rejects low-confidence matches as distinct add/remove pairs | VERIFIED | `test_threshold_rejection` passes: Join at (0,0)/"threshold_old" vs (10000,10000)/"threshold_new" — matched=0 |
| 5 | scipy is installed and importable as a project dependency | VERIFIED | `scipy>=1.13` in pyproject.toml `[project] dependencies`; `from scipy.optimize import linear_sum_assignment` succeeds |
| 6 | match() entry point exists and handles Pass 1 (exact ToolID lookup O(n)) | VERIFIED | `matcher.py` lines 44-55: `new_by_id = {n.source.tool_id: n for n in new_nodes}` — O(n) dict lookup implemented |
| 7 | MatchResult frozen dataclass is exported from the matcher package | VERIFIED | `__init__.py` exports `["match", "MatchResult"]`; `MatchResult` is `@dataclass(frozen=True, kw_only=True, slots=True)` |
| 8 | Two workflows with identical ToolIDs produce zero removed/added | VERIFIED | `test_exact_id_match` passes: 3 nodes all matched via Pass 1, removed=0, added=0 |
| 9 | Tools of different types are never matched against each other | VERIFIED | `test_cross_type_isolation` passes; `_hungarian_match` uses `set(old_by_type) | set(new_by_type)` grouping — cross-type is a hard block |
| 10 | _hungarian_match() is fully implemented (not a stub) | VERIFIED | No `NotImplementedError` in `matcher.py`; full `defaultdict` + `linear_sum_assignment` + threshold gating at lines 73-147 |
| 11 | All 9 DIFF-04 test cases pass | VERIFIED | `pytest tests/test_matcher.py -v`: 9 passed, 0 failed |
| 12 | No test imports scipy, numpy, or internal matcher submodules | VERIFIED | `grep` on `test_matcher.py` and `fixtures/matching.py` confirms zero scipy/numpy/_cost/matcher.py imports |
| 13 | Full test suite (57 tests) passes green with zero failures | VERIFIED | `pytest tests/ -x -q`: 57 passed, 1 xfailed |

**Score:** 13/13 truths verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Provides | Level 1: Exists | Level 2: Substantive | Level 3: Wired | Status |
|----------|----------|-----------------|----------------------|-----------------|--------|
| `src/alteryx_diff/matcher/__init__.py` | Public surface: `match()` and `MatchResult` | YES | YES — re-exports from `matcher.matcher`; `__all__` defined | YES — consumed by tests via `from alteryx_diff.matcher import` | VERIFIED |
| `src/alteryx_diff/matcher/matcher.py` | `MatchResult` dataclass + `match()` Pass 1 + `COST_THRESHOLD` | YES | YES — 148 lines; `class MatchResult`, `def match`, `COST_THRESHOLD = 0.8`, full `_hungarian_match` | YES — imported by `__init__.py`; called by test suite | VERIFIED |
| `pyproject.toml` | scipy runtime dependency | YES | YES — `scipy>=1.13` present in `[project] dependencies` | YES — scipy importable in venv | VERIFIED |

### Plan 02 Artifacts

| Artifact | Provides | Level 1: Exists | Level 2: Substantive | Level 3: Wired | Status |
|----------|----------|-----------------|----------------------|-----------------|--------|
| `src/alteryx_diff/matcher/_cost.py` | `_build_cost_matrix`, `_position_cost`, `_hash_cost` | YES | YES — 110 lines; all three functions implemented; ZeroDivisionError guard at lines 94-97 | YES — `from alteryx_diff.matcher._cost import _build_cost_matrix` in `matcher.py` line 16 | VERIFIED |
| `src/alteryx_diff/matcher/matcher.py` | `_hungarian_match()` fully implemented | YES | YES — NotImplementedError stub replaced; `defaultdict`, `linear_sum_assignment`, per-type grouping, threshold gating | YES — called by `match()` at line 59 when unmatched nodes remain | VERIFIED |

### Plan 03 Artifacts

| Artifact | Provides | Level 1: Exists | Level 2: Substantive | Level 3: Wired | Status |
|----------|----------|-----------------|----------------------|-----------------|--------|
| `tests/fixtures/matching.py` | NormalizedNode fixture library; ToolIDs start at 301 | YES | YES — 129 lines; `make_node()` builder + 7 fixture pairs (14 lists); ToolIDs 301-399 | YES — imported by `test_matcher.py` line 12-27 | VERIFIED |
| `tests/test_matcher.py` | 9 contract tests covering all DIFF-04 scenarios | YES | YES — 163 lines; all 9 named test functions present; `_check_invariant` helper defined and called in every test | YES — discovered and executed by pytest; 9 passed | VERIFIED |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `matcher/__init__.py` | `matcher/matcher.py` | `from alteryx_diff.matcher.matcher import MatchResult, match` | WIRED | Line 9 of `__init__.py` — exact pattern match |
| `matcher/matcher.py` | `alteryx_diff.models` | `from alteryx_diff.models import NormalizedNode` | WIRED | Line 17 of `matcher.py` — NormalizedNode used in type annotations and runtime |
| `matcher/matcher.py` | `matcher/_cost.py` | `from alteryx_diff.matcher._cost import _build_cost_matrix` | WIRED | Line 16 of `matcher.py`; `_build_cost_matrix` called at line 123 |
| `matcher/_cost.py` | `scipy.optimize.linear_sum_assignment` | `from scipy.optimize import linear_sum_assignment` | WIRED (via `matcher.py`) | NOTE: Plan 02 key_links listed this in `_cost.py` but the actual implementation places the scipy import in `matcher.py` line 14. `_cost.py` correctly builds the cost matrix only — `linear_sum_assignment` is called in `_hungarian_match()`. This is a better separation of concerns and the tests confirm correct behavior. |
| `tests/test_matcher.py` | `alteryx_diff.matcher` | `from alteryx_diff.matcher import match, MatchResult` | WIRED | Line 10 of `test_matcher.py` — tests go through public API only |
| `tests/fixtures/matching.py` | `alteryx_diff.models` | `from alteryx_diff.models import NormalizedNode` | WIRED | Line 12 of `matching.py` — NormalizedNode used in all fixture construction |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DIFF-04 | 04-01, 04-02, 04-03 | System uses two-pass node matching — exact ToolID lookup first, then Hungarian algorithm similarity fallback — to prevent phantom add/remove pairs when Alteryx regenerates ToolIDs | SATISFIED | Pass 1 O(n) dict lookup in `matcher.py` lines 44-54; Pass 2 Hungarian in `_hungarian_match()` lines 73-147 using `linear_sum_assignment` with per-type grouping and post-assignment threshold at `COST_THRESHOLD = 0.8`; all 9 contract tests pass |

**Orphaned requirements check:** REQUIREMENTS.md maps only DIFF-04 to Phase 4 (traceability table line 108). All three plans claim DIFF-04. No orphaned requirements.

---

## Anti-Patterns Found

Scanned files: `matcher/__init__.py`, `matcher/matcher.py`, `matcher/_cost.py`, `tests/fixtures/matching.py`, `tests/test_matcher.py`

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | No anti-patterns found |

Specific checks performed:
- No TODO/FIXME/XXX/HACK/PLACEHOLDER comments in any file
- No `NotImplementedError` stub remaining in `matcher.py` (stub was replaced in Plan 02)
- No empty implementations (`return null`, `return {}`, `return []`)
- No scipy/numpy imports in test files or fixture files
- No internal module imports (`_cost`, `matcher.matcher` directly) in test files

---

## Human Verification Required

None. All success criteria for Phase 4 are fully verifiable programmatically:
- Correctness is captured by the 9 contract tests
- scipy integration verified by import test and test execution
- mypy --strict passes (0 issues across 3 source files)
- Count invariant mathematically verified in `_check_invariant` helper

---

## Gaps Summary

No gaps. All 13 observable truths are verified, all 7 artifacts pass all three levels, all 6 key links are wired, DIFF-04 is satisfied, and the full 57-test suite passes green.

---

## Implementation Quality Notes

1. **COST_THRESHOLD placement:** Defined at module level in `matcher.py` (line 19) as the plan specified. Applied post-assignment at the pair level (line 134) — correct per CONTEXT.md; never pre-filters the cost matrix.

2. **scipy import location:** `linear_sum_assignment` is imported in `matcher.py`, not `_cost.py`. Plan 02's key_links entry for `_cost.py -> scipy` was aspirational but the implementation placed the call in `_hungarian_match()` in `matcher.py`. This is a correct design choice (cost module computes costs only; solver call belongs with the algorithm), and all behavior tests confirm it works correctly.

3. **ZeroDivisionError guard:** `_cost.py` lines 90-97 use dual-check: initializes `x_range`/`y_range` to 1.0 if `len(xs) <= 1`, then additionally sets to 1.0 if the computed range is exactly 0.0. This is belt-and-suspenders protection per the plan specification.

4. **zip strict=True:** `zip(row_ind.tolist(), col_ind.tolist(), strict=True)` at line 133 of `matcher.py` — ruff B905 compliance confirmed.

5. **Union-of-types routing:** `set(old_by_type) | set(new_by_type)` at line 103 ensures no nodes silently dropped when a type appears only in old or only in new.

---

_Verified: 2026-03-02_
_Verifier: Claude (gsd-verifier)_
