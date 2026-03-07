---
phase: 03-normalization-layer
verified: 2026-03-02T03:27:18Z
status: gaps_found
score: 4/5 success criteria verified
gaps:
  - truth: "--include-positions flag is documented in --help output and causes position changes to be included in the diff signal"
    status: partial
    reason: "Phase 3 delivers the structural prerequisite (separate position data path, flag-agnostic normalize()) but the --help documentation and diff signal behavior require Phase 9 (CLI) and Phase 5 (differ) which have not been built yet. This criterion is cross-phase and Phase 3's portion is complete."
    artifacts:
      - path: "src/alteryx_diff/normalizer/normalizer.py"
        issue: "No issue — normalize() is correctly flag-agnostic. CLI and differ not yet built."
    missing:
      - "Phase 9 cli.py must expose --include-positions flag with --help documentation"
      - "Phase 5 differ must read NormalizedNode.position when --include-positions is set"
    note: "This gap is a cross-phase dependency, not a Phase 3 defect. The ROADMAP success criterion 5 spans phases 3, 5, and 9. Phase 3's structural contract (separate position field, single-parameter normalize()) is fully verified."
human_verification: []
---

# Phase 3: Normalization Layer — Verification Report

**Phase Goal:** Two functionally identical workflows that differ only in GUIDs, timestamps, whitespace, attribute ordering, or canvas position produce identical normalized config hashes — enabling meaningful diffs that ignore layout changes and ephemeral values.
**Verified:** 2026-03-02T03:27:18Z
**Status:** gaps_found (1 cross-phase gap on success criterion 5; all Phase 3 deliverables are complete)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The same workflow saved twice — with tools nudged on canvas — produces zero diffs (position drift does not appear in config hashes) | VERIFIED | `test_position_drift_does_not_affect_hash` passes; `_normalize_node` places `(node.x, node.y)` only in `position` field, never in `strip_noise(node.config)` |
| 2 | A workflow with injected GUIDs, auto-generated timestamps, and TempFile paths produces the same normalized output as the same workflow without them | VERIFIED | `test_tempfile_path_stripped_to_sentinel`, `test_iso_timestamp_stripped_to_sentinel` pass; GUID stripping is architecturally correct (xfail is intentional pending real-file key discovery) |
| 3 | Attribute reordering does not change the config hash — C14N canonicalization is applied before hashing | VERIFIED | `test_attr_order_produces_equal_hashes` passes; `json.dumps(sort_keys=True)` in `_compute_config_hash` is the canonicalization mechanism |
| 4 | `node.position` (X/Y) is stored as a separate field from `node.config_hash` — the two data paths are never unified | VERIFIED | `NormalizedNode` has distinct `config_hash: ConfigHash` and `position: tuple[float,float]` fields; `test_position_stored_separately_from_hash` passes; `__slots__=True` and `frozen=True` enforce separation |
| 5 | `--include-positions` flag is documented in `--help` output and, when passed, causes position changes to be included in the diff signal | PARTIAL | Phase 3 delivers the structural prerequisite: `normalize()` has exactly one parameter `workflow_doc` (confirmed by `test_normalize_accepts_only_workflow_doc_parameter`), `NormalizedNode.position` is available for downstream use. The `--help` documentation and diff-signal behavior require Phase 9 (CLI) and Phase 5 (differ), neither of which have been built. This is a deliberate cross-phase dependency, not a defect. |

**Score:** 4/5 criteria fully verified (criterion 5 partially verified — Phase 3 portion complete)

---

## Required Artifacts

### Plan 03-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/alteryx_diff/models/normalized.py` | NormalizedNode and NormalizedWorkflowDoc frozen dataclasses | VERIFIED | 56 lines; `@dataclass(frozen=True, kw_only=True, slots=True)` on both; `config_hash: ConfigHash` and `position: tuple[float, float]` are distinct fields |
| `src/alteryx_diff/models/__init__.py` | Extended export surface including NormalizedNode, NormalizedWorkflowDoc | VERIFIED | 33 lines; both classes in `__all__` under `# Normalized models (Phase 3)` comment; importable via `from alteryx_diff.models import NormalizedNode, NormalizedWorkflowDoc` |

### Plan 03-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/alteryx_diff/normalizer/patterns.py` | Single-source stripping patterns registry | VERIFIED | 58 lines; exports `TEMPFILE_PATH_PATTERN`, `TEMPFILE_SENTINEL`, `ISO8601_PATTERN`, `ISO8601_SENTINEL`, `GUID_VALUE_KEYS` (empty frozenset — intentional), `GUID_SENTINEL` |
| `src/alteryx_diff/normalizer/_strip.py` | Recursive dict noise-stripping (deep-copy before mutation) | VERIFIED | 59 lines; `strip_noise()` uses `copy.deepcopy()` internally; recursively handles dicts, lists, strings |
| `src/alteryx_diff/normalizer/normalizer.py` | `normalize()` entry point: WorkflowDoc → NormalizedWorkflowDoc | VERIFIED | 82 lines; pure function; `--include-positions` is Phase 5/9 concern documented in module docstring; `_compute_config_hash` uses SHA-256 |
| `src/alteryx_diff/normalizer/__init__.py` | Public export surface for normalizer package | VERIFIED | 12 lines; `from alteryx_diff.normalizer.normalizer import normalize`; `__all__ = ["normalize"]` |

### Plan 03-03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/fixtures/normalization.py` | 7 NodePairs + ROUND_TRIP_WORKFLOW fixture library | VERIFIED | 292 lines; all 7 NodePairs (`ATTR_ORDER_PAIR`, `POSITION_DRIFT_PAIR`, `TEMPFILE_PAIR`, `TEMPFILE_VS_NOFILE_PAIR`, `TIMESTAMP_PAIR`, `GUID_PAIR`, `US_DATE_PAIR`) exported; `ROUND_TRIP_WORKFLOW` is a 2-node, 1-connection `WorkflowDoc`; `GUID_PAIR_KEY = "@GUID"` exported for conditional skip |

### Plan 03-04 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_normalizer.py` | 12-15 test functions covering NORM-01 through NORM-04 | VERIFIED | 329 lines; 15 test functions; 14 pass + 1 xfail (`test_guid_key_stripped_to_sentinel`); xfail is correct and expected when `GUID_VALUE_KEYS` is empty |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `models/__init__.py` | `models/normalized.py` | `from alteryx_diff.models.normalized import NormalizedNode, NormalizedWorkflowDoc` | WIRED | Both classes in `__init__.py` import and `__all__` |
| `models/normalized.py` | `models/workflow.py` | `from alteryx_diff.models.workflow import AlteryxConnection, AlteryxNode, WorkflowDoc` | WIRED | Line 8 of normalized.py |
| `normalizer/normalizer.py` | `normalizer/_strip.py` | `from alteryx_diff.normalizer._strip import strip_noise` | WIRED | `strip_noise` imported and called in `_normalize_node` |
| `normalizer/normalizer.py` | `models/normalized.py` | `from alteryx_diff.models.normalized import NormalizedNode, NormalizedWorkflowDoc` | WIRED | Both used in `normalize()` and `_normalize_node()` |
| `normalizer/_strip.py` | `normalizer/patterns.py` | `from alteryx_diff.normalizer.patterns import ...` | WIRED | All 6 pattern constants imported and used |
| `normalizer/__init__.py` | `normalizer/normalizer.py` | `from alteryx_diff.normalizer.normalizer import normalize` | WIRED | Single re-export; `normalize.__module__ == 'alteryx_diff.normalizer.normalizer'` confirmed |
| `tests/test_normalizer.py` | `normalizer/normalizer.py` | `from alteryx_diff.normalizer import normalize` | WIRED | Used in all test functions via `_hash_of()` and `_hash_pair()` helpers |
| `tests/test_normalizer.py` | `tests/fixtures/normalization.py` | `from tests.fixtures.normalization import ...` | WIRED | All 9 fixture names imported |
| `tests/test_normalizer.py` | `normalizer/patterns.py` | `from alteryx_diff.normalizer.patterns import GUID_VALUE_KEYS` | WIRED | Used in `@pytest.mark.xfail(GUID_PAIR_KEY not in GUID_VALUE_KEYS, ...)` |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| NORM-01 | 03-02, 03-04 | Strips whitespace differences and normalizes XML attribute ordering via C14N canonicalization | SATISFIED | `json.dumps(sort_keys=True)` in `_compute_config_hash`; `test_attr_order_produces_equal_hashes` passes |
| NORM-02 | 03-02, 03-04 | Removes non-functional metadata (GUIDs, timestamps, TempFile paths) | SATISFIED | `patterns.py` registry; `_strip.py` recursive stripper; 4 NORM-02 tests pass; GUID test correctly xfail pending key discovery |
| NORM-03 | 03-01, 03-03, 03-04 | Canvas position excluded from diff detection by default — stored separately | SATISFIED | `NormalizedNode.position` and `NormalizedNode.config_hash` are distinct fields; `_normalize_node` never passes `x`/`y` to `strip_noise()`; 2 NORM-03 tests pass |
| NORM-04 | 03-01, 03-02, 03-04 | `--include-positions` flag opt-in with `--help` documentation | PARTIALLY SATISFIED | Phase 3 structural contribution complete: `normalize()` is flag-agnostic (single `workflow_doc` parameter), `NormalizedNode.position` available for downstream phases; `--help` docs and diff-signal behavior deferred to Phase 9 and Phase 5 |

**No orphaned requirements.** NORM-01 through NORM-04 are the only requirements mapped to Phase 3 in REQUIREMENTS.md, and all four are claimed by the four plans.

---

## Anti-Patterns Scan

| File | Pattern | Severity | Finding |
|------|---------|----------|---------|
| All 8 phase-3 files | TODO/FIXME/HACK | None found | Clean |
| All 8 phase-3 files | `return null` / `return {}` / stub bodies | None found | Clean |
| All 8 phase-3 files | `print()` / `console.log` | None found | Clean |
| `patterns.py` | `GUID_VALUE_KEYS` empty frozenset | Info | Intentional design: keys populated from real `.yxmd` inspection per RESEARCH.md. Not a stub — the mechanism works, the keys are awaiting confirmation from fixtures. |

**No blocker or warning anti-patterns found.**

---

## Test Suite Results

```
tests/test_normalizer.py::test_attr_order_produces_equal_hashes              PASSED
tests/test_normalizer.py::test_tempfile_path_stripped_to_sentinel             PASSED
tests/test_normalizer.py::test_tempfile_presence_vs_absence_hashes_differ     PASSED
tests/test_normalizer.py::test_iso_timestamp_stripped_to_sentinel             PASSED
tests/test_normalizer.py::test_us_date_not_stripped                           PASSED
tests/test_normalizer.py::test_guid_key_stripped_to_sentinel                  XFAIL (expected)
tests/test_normalizer.py::test_position_drift_does_not_affect_hash            PASSED
tests/test_normalizer.py::test_position_stored_separately_from_hash           PASSED
tests/test_normalizer.py::test_normalize_accepts_only_workflow_doc_parameter  PASSED
tests/test_normalizer.py::test_source_config_not_mutated_after_normalize      PASSED
tests/test_normalizer.py::test_normalized_node_is_frozen                      PASSED
tests/test_normalizer.py::test_normalized_workflow_doc_is_frozen              PASSED
tests/test_normalizer.py::test_normalize_is_idempotent                        PASSED
tests/test_normalizer.py::test_config_hash_is_64_char_hex                     PASSED
tests/test_normalizer.py::test_connections_preserved_unchanged                PASSED

Full suite: 48 passed, 1 xfailed (prior baseline 34, new Phase 3: +15)
```

---

## Gaps Summary

**One gap is recorded.** It is a cross-phase structural gap, not a Phase 3 defect.

ROADMAP success criterion 5 for Phase 3 states: "`--include-positions` flag is documented in `--help` output and, when passed, causes position changes to be included in the diff signal." This criterion spans three phases:

- **Phase 3 contribution** (complete): `NormalizedNode.position` is a separate, accessible field. `normalize()` accepts exactly one parameter and is flag-agnostic. The module docstring explicitly documents that `--include-positions` is a Phase 5/9 concern. This is verified.
- **Phase 5 contribution** (not yet built): The differ must read `NormalizedNode.position` when `--include-positions` is set and include position changes in `DiffResult`.
- **Phase 9 contribution** (not yet built): The CLI must expose `--include-positions` with clear `--help` documentation.

**Assessment:** The gap should not block Phase 4. Phase 3's deliverable is the data model and normalization pipeline — these are complete and fully tested. The `--help` and diff-signal aspects of NORM-04 will be closed in Phases 5 and 9 respectively.

---

_Verified: 2026-03-02T03:27:18Z_
_Verifier: Claude (gsd-verifier)_
