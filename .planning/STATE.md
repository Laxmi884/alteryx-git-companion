---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-06T03:08:35.998Z"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 15
  completed_plans: 14
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Accurate detection of functional changes — zero false positives from layout noise, zero missed configuration changes.
**Current focus:** Phase 5 — Diff Engine

## Current Position

Phase: 5 of 9 (Diff Engine) — IN PROGRESS
Plan: 2 of 3 in current phase — COMPLETE
Status: Phase 5 Plan 02 complete — differ fixture library with 11 scenarios (MatchResult + connection tuples)
Last activity: 2026-03-06 — Plan 05-02 complete: tests/fixtures/diffing.py with 11 DIFF-01/DIFF-02/DIFF-03 scenarios; ToolIDs 401-419; 57 passed, 1 xfailed

Progress: [████▌░░░░░] 52% (14/27 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 4 min
- Total execution time: 25 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-scaffold-and-data-models | 3 | 13 min | 4 min |
| 02-xml-parser-and-validation | 2 | 10 min | 5 min |
| 03-normalization-layer | 4 | 9 min | 2 min |

**Recent Trend:**
- Last 5 plans: 03-03 (2 min), 03-04 (4 min), 04-01 (3 min), 04-02 (4 min), 04-03 (2 min)
- Trend: stable

*Updated after each plan completion*
| Phase 01-scaffold-and-data-models P03 | 3 | 1 tasks | 1 files |
| Phase 02-xml-parser-and-validation P01 | 7 | 2 tasks | 4 files |
| Phase 02-xml-parser-and-validation P02 | 3 | 2 tasks | 2 files |
| Phase 03-normalization-layer P01 | 2 | 2 tasks | 2 files |
| Phase 03-normalization-layer P02 | 3 | 2 tasks | 4 files |
| Phase 03-normalization-layer P03 | 2 | 1 tasks | 1 files |
| Phase 03-normalization-layer P04 | 4 | 2 tasks | 1 files |
| Phase 04-node-matcher P01 | 3 | 2 tasks | 4 files |
| Phase 04-node-matcher P02 | 4 | 2 tasks | 5 files |
| Phase 04-node-matcher P03 | 2 | 2 tasks | 2 files |
| Phase 05-diff-engine P01 | 8 | 2 tasks | 5 files |
| Phase 05-diff-engine P02 | 3 | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Python 3.11+ required (NetworkX 3.6.1 hard constraint) — do not target 3.10
- [Roadmap]: NodeMatcher built in Phase 4 before any diff logic — ToolID phantom pair risk is HIGH recovery cost if shipped wrong
- [Roadmap]: pyvis CDN spike scheduled as first plan of Phase 8 before committing to pyvis vs D3.js
- [Roadmap]: CLI built last (Phase 9) as thin Typer adapter — pipeline.run() is the only entry point for all stages
- [01-01]: Used Python 3.13 in .python-version (not 3.11) — 3.13.7 installed locally, satisfies >=3.11, avoids uv python download
- [01-01]: pre-commit mypy hook restricted to src/ only (files: ^src/) — isolated hook env cannot resolve project package imports in tests/
- [01-01]: Added tests/test_import.py smoke test — pytest exits code 5 with zero tests, plan requires exit 0
- [01-02]: All 6 dataclasses use frozen=True, kw_only=True, slots=True — immutability, explicit construction, memory efficiency
- [01-02]: AlteryxNode.config is dict[str, Any] with field(default_factory=dict) — flat map; raw XML not in model layer
- [01-02]: WorkflowDoc collections (nodes, connections) are tuple[T, ...] — immutable, compatible with frozen=True
- [01-02]: AlteryxNode is topology-free; all connections stored on WorkflowDoc
- [Phase 01-03]: Used direct attribute assignment (not object.__setattr__) to test FrozenInstanceError — with slots=True, object.__setattr__ bypasses frozen enforcement
- [02-01]: lxml-stubs added to dev deps and pre-commit mypy hook additional_dependencies — required for mypy --strict to resolve lxml private types
- [02-01]: type: ignore[type-arg] on _ElementTree[_Element] — lxml-stubs 0.5.1 is non-generic; annotation preserves intent, ignore suppresses stubs error
- [02-01]: ParseError hierarchy carries filepath + message attributes; CLI catches ParseError base for exit code 2
- [02-02]: test_parse_directory_raises accepts (UnreadableFileError, MalformedXMLError) — OS-level directory read behavior varies between platforms
- [02-02]: b"..." byte-string literals used for all XML fixture constants — explicit bytes, UTF-8 implicit, no BOM required for lxml
- [03-01]: NormalizedNode.position is tuple[float, float] as a separate field from config_hash — layout-only moves never affect config comparison path (NORM-04)
- [03-01]: NormalizedNode.source carries full AlteryxNode for downstream identity access (tool_id, tool_type)
- [03-01]: normalized.py imports from models.types and models.workflow directly (not from models package) — avoids circular import since file lives inside models/
- [03-01]: No __all__ in normalized.py — __init__.py is the sole public surface per project convention
- [03-02]: GUID_VALUE_KEYS frozenset starts empty — keys added as discovered from real fixture inspection (not pre-populated speculatively)
- [03-02]: C14N via json.dumps(sort_keys=True) not lxml etree.canonicalize() — parser produces Python dicts, not XML element objects
- [03-02]: position=(node.x, node.y) is a separate field, never included in config_hash computation — layout noise cannot affect diff
- [03-02]: Used typing.cast() instead of type: ignore[return-value] to satisfy mypy --strict on _strip_value Any return
- [03-03]: Fixture file separated from test file — each new Alteryx metadata pattern is a one-file-change extension point (fixtures/normalization.py + patterns.py)
- [03-03]: GUID_PAIR_KEY exported as str — test_normalizer.py checks GUID_PAIR_KEY in GUID_VALUE_KEYS before asserting (avoids unconditional failure while frozenset empty)
- [03-03]: ToolIDs start at 101 in normalization fixtures — avoids collision with Phase 2 XML fixture nodes (ToolID 1 and 2)
- [03-04]: xfail strict=True on GUID test — forces ERROR (not silent pass) if GUID_VALUE_KEYS populated without removing xfail mark
- [03-04]: B905 zip(strict=True) enforced by ruff — all zip() calls require explicit strict parameter in this codebase
- [03-04]: Unused imports removed by ruff autofix — test file only needs ToolID, AlteryxNode, WorkflowDoc from models layer
- [04-01]: scipy>=1.13 added as runtime dep (uv resolved 1.17.1); lower bound per plan spec so future uv resolves stay flexible
- [04-01]: _hungarian_match() stub raises NotImplementedError — enables test isolation in Plan 03 without importing scipy
- [04-01]: MatchResult follows project-wide frozen=True, kw_only=True, slots=True pattern for all pipeline output types
- [04-01]: Pass 2 skipped entirely when unmatched_old or unmatched_new is empty — avoids NotImplementedError on fully-matched workflows
- [04-02]: _cost.py is internal (underscore prefix) — no __all__, not re-exported; consumed exclusively by _hungarian_match()
- [04-02]: Canvas bounds from UNION of old+new groups — consistent normalisation, prevents asymmetric cost scaling
- [04-02]: x_range/y_range default to 1.0 when spread is 0 — guards ZeroDivisionError for same-coordinate type groups
- [04-02]: Threshold (cost > 0.8) applied AFTER linear_sum_assignment per pair — pre-filtering corrupts scipy solver
- [04-02]: scipy-stubs added as dev dep; pre-commit mypy hook updated with numpy>=2.0, scipy>=1.13, scipy-stubs>=1.13
- [04-03]: Fixture ToolIDs start at 301 — no collision with Phase 1 (1-100), Phase 2 (1-2), Phase 3 (101-201) fixtures
- [04-03]: THRESHOLD fixture uses (0,0) vs (10000,10000) with different hashes — guarantees cost > 0.8 reliably
- [04-03]: Cross-type test uses same hash + same position — documents type isolation is unconditional (not cost-based)
- [04-03]: _check_invariant() is a module-level helper called in every test — count conservation enforced as mandatory assertion
- [Phase 05-01]: slots=True removed from DiffResult only — Python 3.11 slots=True dataclasses are incompatible with @property descriptors
- [Phase 05-01]: deepdiff>=8.0 added as runtime dep — differ stage calls DeepDiff() at pipeline runtime, not just in tests
- [Phase 05-01]: _EXCLUDED_FIELDS frozenset starts empty — keys added as GUID-like fields are discovered from real fixture inspection
- [Phase 05-01]: mypy deepdiff.* override added to pyproject.toml; deepdiff added to pre-commit mypy additional_dependencies (no stubs published)
- [Phase 05-diff-engine]: ToolIDs 401-419 for Phase 5 differ fixtures — sequential allocation, no collision with Phases 1-4 (max 399)
- [Phase 05-diff-engine]: Module-level assert guards verify hash invariants at import time — fails fast if config data is wrong
- [Phase 05-diff-engine]: dict[str, Any] typing in helper functions (not bare dict) — avoids mypy type-arg violations per codebase conventions

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: Alteryx XML format assumptions (TempFile element structure, GUID field names, position XPath) need validation against real .yxmd files in Phase 3 fixture tests — inferred from community sources, not Alteryx official docs
- [Phase 8]: pyvis Bootstrap CDN leak confirmed (issue #228) but post-processing workaround implementation details unverified — spike required before committing graph approach

## Session Continuity

Last session: 2026-03-06
Stopped at: Completed 05-02-PLAN.md — 11 differ fixture scenarios: tests/fixtures/diffing.py with MatchResult + connection tuples for all DIFF-01/DIFF-02/DIFF-03 test cases; 57 passed, 1 xfailed; ready for 05-03 test_differ.py
Resume file: None
