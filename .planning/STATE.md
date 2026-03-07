---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: MVP
status: complete
last_updated: "2026-03-07"
progress:
  total_phases: 9
  completed_phases: 9
  total_plans: 27
  completed_plans: 27
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-07)

**Core value:** Accurate detection of functional changes — zero false positives from layout noise, zero missed configuration changes.
**Current focus:** Planning next milestone — run `/gsd:new-milestone` to start

## Current Position

Milestone: v1.0 MVP — SHIPPED 2026-03-07
Status: All 9 phases complete; 27/27 plans; 105 tests passing; milestone archived
Last activity: 2026-03-07 - Completed quick task 4: modernize diff report UI/UX — dark mode CSS variables, draggable graph nodes, fullscreen graph toggle

Progress: [██████████] 100% (27/27 plans)

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
| Phase 05-diff-engine P03 | 3 | 2 tasks | 1 files |
| Phase 06-pipeline-orchestration-and-json-renderer P01 | 2 | 1 tasks | 2 files |
| Phase 06-pipeline-orchestration-and-json-renderer P02 | 2 | 1 tasks | 2 files |
| Phase 06-pipeline-orchestration-and-json-renderer P03 | 4 | 2 tasks | 3 files |
| Phase 07-html-report P01 | 5 | 2 tasks | 5 files |
| Phase 07-html-report P02 | 3 | 2 tasks | 2 files |
| Phase 08-visual-graph P01 | 4 | 2 tasks | 3 files |
| Phase 08-visual-graph P02 | 3 | 2 tasks | 3 files |
| Phase 08-visual-graph P03 | 6 | 2 tasks | 2 files |
| Phase 09-cli-entry-point P01 | 7 | 2 tasks | 6 files |
| Phase 09-cli-entry-point P02 | 2 | 1 tasks | 2 files |
| Phase 09-cli-entry-point P03 | 5 | 2 tasks | 3 files |

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
- [Phase 05-diff-engine]: 12 test functions instead of plan's stated 11 — plan count was off by one; all planned behaviors covered
- [06-01]: DiffRequest and DiffResponse use frozen=True, kw_only=True, slots=True — consistent with project-wide pattern for all pipeline output types
- [06-01]: match() receives list(norm_a.nodes), list(norm_b.nodes) — tuple-to-list conversion required by matcher signature
- [06-01]: diff() receives doc_a.connections, doc_b.connections from parser output, NOT norm_a/norm_b.connections — correct edge identity source
- [06-01]: docstring placed before from __future__ import annotations — plan snippet had wrong order; fixed to match project convention (ruff E402)
- [Phase 06-02]: Docstring placed after from __future__ import annotations in __init__.py — ruff E402 requires import at top of file
- [Phase 06-02]: summary.connections count computed from len(connections) list — invariant enforced by construction order in _build_payload()
- [Phase 06-02]: Renderer pattern established: each renderer is a class in renderers/<name>_renderer.py re-exported from renderers/__init__.py
- [06-03]: NodeDiff unused in test_json_renderer.py — removed import; plan snippet included it but no test uses NodeDiff directly (ruff F401)
- [06-03]: Entry-point-agnostic test guard confirmed: test_pipeline.py has zero sys/argparse/typer/cli imports
- [06-03]: ToolIDs 601+ allocated for Phase 6 pipeline fixtures; written to tmp_path, not committed to disk
- [Phase 07-01]: Used Environment(autoescape=True) per ruff B701 requirement; ruff noqa: E501 for template file; DIFF_DATA via application/json script tag with tojson filter; Connection toggle uses loop.index as tool_id key
- [Phase 07-02]: pytest import and SINGLE_REMOVED removed from test_html_renderer.py (ruff F401 auto-fixed) — no parametrize or marks used
- [Phase 07-02]: DIFF_DATA extraction pattern established for HTML tests: locate id=diff-data> tag, slice to </script>, json.loads()
- [08-01]: vis-network 9.1.4 vendored as standalone UMD bundle (702KB) — no npm/CDN dependency, single-file HTML output remains self-contained
- [08-01]: networkx.* mypy override added to pyproject.toml — networkx has no type stubs; follows same pattern as deepdiff override (ignore_missing_imports)
- [08-01]: load_vis_js() uses importlib.resources with filesystem fallback — editable installs and built packages both work without code change
- [08-01]: COLOR_MAP is a module-level constant in _graph_builder.py — single source of truth for diff status colors shared by Python builder and JS template
- [08-02]: GraphRenderer produces an HTML fragment (not a full document) — HTMLRenderer owns the document wrapper; fragment embedded via {{ graph_html | safe }}
- [08-02]: nodes_json and edges_json passed as pre-serialized Python strings with | safe — avoids Jinja2 double-encoding of JSON
- [08-02]: vis-network UMD injected inside IIFE to avoid global scope pollution
- [08-02]: graph_html defaults to "" in HTMLRenderer.render() — zero behavior change for existing callers; all 7 tests pass
- [08-03]: ADDED_DIFF, REMOVED_DIFF, MODIFIED_NODE_DIFF kept in fixtures file but not imported in test file — ruff F401 prevents unused imports in test code; fixtures available for Phase 9 CLI tests
- [08-03]: _extract_graph_nodes() uses first ']' after 'var GRAPH_NODES = ' marker — reliable for flat array of objects with no nested arrays
- [08-03]: test_hierarchical_layout asserts pos[801] < pos[802] directional inequality — robust to future LAYOUT_SCALE changes
- [09-01]: typer.* and rich.* mypy overrides added to pyproject.toml (no stubs published) — follows deepdiff/networkx pattern
- [09-01]: typer>=0.12 and rich>=13.0 added to pre-commit mypy additional_dependencies so hook env resolves imports
- [09-01]: _cli_json_output() built in cli.py not JSONRenderer — preserves 5 passing JSONRenderer tests, different schema {added, removed, modified, metadata} vs {summary, tools, connections}
- [09-01]: Position-only NodeDiff built directly (field_diffs={'position': ...}) — bypasses _diff_node() which raises ValueError on no config diff
- [09-01]: Spinner skipped when --json set — avoids edge cases with stderr/stdout stream confusion in JSON parsing tools
- [09-02]: metadata=None default in HTMLRenderer.render() ensures zero regression for all 7 existing test_html_renderer.py tests
- [09-02]: Footer uses HTML <details>/<summary> (no JS) — collapsed by default, auditors expand manually
- [09-02]: Inline comment on metadata=metadata kwarg shortened to fit ruff E501 88-char limit (cli.py has no noqa: E501 exemption)
- [Phase 09-03]: CliRunner() without mix_stderr — click 8.2+ always separates stdout/stderr; constructor arg removed in click 8.2
- [Phase 09-03]: OSError guard wraps _file_sha256() in cli.py — missing file raises FileNotFoundError before pipeline, must map to exit code 2
- [Phase 09-03]: Single-command Typer invocation: runner.invoke(app, [path_a, path_b]) — no subcommand prefix in args list

### Pending Todos

- Validate GUID_VALUE_KEYS against real .yxmd files (tech debt from v1.0)
- Wire JSONRenderer into CLI --json path or document _cli_json_output() schema as stable (tech debt from v1.0)

### Blockers/Concerns

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | fix parser to find nodes inside containers in yxmd workflows | 2026-03-07 | b30bb25 | [1-fix-parser-to-find-nodes-inside-containe](./quick/1-fix-parser-to-find-nodes-inside-containe/) |
| 2 | fix graph node overlap — filter containers, shorten labels, increase scale | 2026-03-07 | b9667e2 | [2-fix-graph-layout-overlap](./quick/2-fix-graph-layout-overlap/) |
| 3 | improve graph visualization for modern UI — soft tint palette, curved edges, polished controls | 2026-03-07 | efd47cc | [3-improve-graph-visualization-for-modern-u](./quick/3-improve-graph-visualization-for-modern-u/) |
| 4 | modernize diff report UI/UX — dark mode CSS variables, draggable graph nodes, fullscreen graph toggle | 2026-03-07 | e1697dd | [4-modernize-diff-report-ui-ux-with-dark-mo](./quick/4-modernize-diff-report-ui-ux-with-dark-mo/) |

## Session Continuity

Last session: 2026-03-07
Stopped at: Completed quick task 4: modernize-diff-report-ui-ux-with-dark-mo
Resume file: None
