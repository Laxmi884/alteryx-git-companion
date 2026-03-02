# Roadmap: Alteryx Canvas Diff (ACD)

## Overview

ACD is built as an immutable four-stage pipeline: Parser → Normalizer → Differ → Renderer. Each phase delivers one self-contained, testable layer of that pipeline. Phases 1-5 build the engine; Phases 6-9 build the outputs and entry point. The two highest-risk problems — ToolID phantom pairs and position leakage into the diff signal — are both addressed in Phases 3 and 4 before any diff logic depends on them. The CLI is deliberately built last as a thin adapter over `pipeline.run()`, preserving the hexagonal architecture that makes Phase 3 API addition a 15-line wrapper.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Scaffold and Data Models** - Project structure, pyproject.toml, and all typed dataclasses that every stage communicates through (completed 2026-03-01)
- [x] **Phase 2: XML Parser and Validation** - lxml-based parser that loads .yxmd files, validates structure, and emits WorkflowDoc (completed 2026-03-01)
- [x] **Phase 3: Normalization Layer** - C14N canonicalization, GUID/timestamp stripping, position separation, and SHA-256 config hashing (completed 2026-03-02)
- [ ] **Phase 4: Node Matcher** - Two-pass ToolID-first lookup with Hungarian algorithm fallback to prevent phantom add/remove pairs
- [ ] **Phase 5: Diff Engine** - NodeDiffer and EdgeDiffer producing DiffResult with full before/after field-level values
- [ ] **Phase 6: Pipeline Orchestration and JSON Renderer** - pipeline.run() entry point wiring all stages; JSONRenderer as first output serializer
- [ ] **Phase 7: HTML Report** - Jinja2 report with color-coded summary, expandable per-tool detail sections, self-contained inline output
- [ ] **Phase 8: Visual Graph** - Interactive graph with hierarchical auto-layout default and opt-in canvas X/Y positioning via --canvas-layout flag; color-coded change types and hover/click inline diff
- [ ] **Phase 9: CLI Entry Point** - Typer CLI adapter over pipeline.run(), exit codes, --output, --canvas-layout, and --include-positions flags, governance metadata, performance validation

## Phase Details

### Phase 1: Scaffold and Data Models
**Goal**: The project structure and all shared data contracts exist so that every subsequent phase has typed boundaries to program against.
**Depends on**: Nothing (first phase)
**Requirements**: PARSE-04
**Success Criteria** (what must be TRUE):
  1. `pyproject.toml` is present with `requires-python = ">=3.11"` and all declared dependencies; `uv sync` succeeds from a clean checkout
  2. `WorkflowDoc`, `AlteryxNode`, `AlteryxConnection`, `DiffResult`, `NodeDiff`, and `EdgeDiff` dataclasses exist as frozen types in `models/`
  3. A developer can import any model class and construct an instance with typed fields (ToolID, type, position, config, connections) without errors
  4. `pytest` runs and passes on the empty scaffold (zero test failures, no import errors)
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Initialize uv project, pyproject.toml, directory structure, and pre-commit hooks
- [ ] 01-02-PLAN.md — Define all frozen dataclasses in models/ (WorkflowDoc, AlteryxNode, AlteryxConnection, DiffResult, NodeDiff, EdgeDiff)
- [ ] 01-03-PLAN.md — Write model unit tests and verify pytest passes on clean scaffold

### Phase 2: XML Parser and Validation
**Goal**: A developer can point the parser at two .yxmd files and get back two valid WorkflowDoc instances, or a descriptive error if either file is malformed.
**Depends on**: Phase 1
**Requirements**: PARSE-01, PARSE-02, PARSE-03
**Success Criteria** (what must be TRUE):
  1. Given two valid .yxmd files, `parse(path_a, path_b)` returns two `WorkflowDoc` instances with all tools, configs, and connections populated
  2. Given a malformed XML file, the parser raises a typed exception before any downstream processing begins, not a generic lxml traceback
  3. Given a missing or unreadable file, the error message identifies the file path and problem in plain English
  4. Parser contains zero calls to `sys.exit`, `print`, or file I/O outside of loading the input file — importable and callable without a CLI context
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Implement exceptions.py (ParseError hierarchy) and parser.py (lxml-based parse() with pre-flight, parse, and convert stages)
- [x] 02-02-PLAN.md — Write fixture-based parser tests in tests/fixtures/__init__.py and tests/test_parser.py covering happy path, all error classes, edge cases, and fail-fast behavior

### Phase 3: Normalization Layer
**Goal**: Two functionally identical workflows that differ only in GUIDs, timestamps, whitespace, attribute ordering, or canvas position produce identical normalized config hashes.
**Depends on**: Phase 2
**Requirements**: NORM-01, NORM-02, NORM-03, NORM-04
**Success Criteria** (what must be TRUE):
  1. The same workflow saved twice — with tools nudged on canvas — produces zero diffs (position drift does not appear in config hashes)
  2. A workflow with injected GUIDs, auto-generated timestamps, and TempFile paths produces the same normalized output as the same workflow without them
  3. Attribute reordering (XML attributes in different sequence) does not change the config hash — C14N canonicalization is applied before hashing
  4. `node.position` (X/Y) is stored as a separate field from `node.config_hash` — the two data paths are never unified
  5. `--include-positions` flag is documented in `--help` output and, when passed, causes position changes to be included in the diff signal
**Plans**: 4 plans

Plans:
- [ ] 03-01-PLAN.md — Define NormalizedNode and NormalizedWorkflowDoc frozen dataclasses in models/; extend models/__init__.py export surface
- [ ] 03-02-PLAN.md — Implement normalizer package: patterns.py (stripping registry), _strip.py (recursive noise stripper), normalizer.py (normalize() entry point), __init__.py
- [ ] 03-03-PLAN.md — Create tests/fixtures/normalization.py fixture library: 7 NodePairs and ROUND_TRIP_WORKFLOW covering all normalization scenarios
- [ ] 03-04-PLAN.md — Write normalization contract test suite in tests/test_normalizer.py: 15 tests covering NORM-01 through NORM-04, idempotency, source mutation protection, frozen contracts

### Phase 4: Node Matcher
**Goal**: When Alteryx regenerates ToolIDs, the node matcher still correctly pairs old and new tool instances rather than producing phantom add/remove pairs.
**Depends on**: Phase 3
**Requirements**: DIFF-04
**Success Criteria** (what must be TRUE):
  1. Two workflows where one was saved after Alteryx regenerated all ToolIDs produce zero phantom additions or removals — all tools are correctly matched
  2. A tool genuinely added to the new workflow is identified as an addition, not a rematch of an existing tool
  3. A tool genuinely removed from the old workflow is identified as a removal, not matched to an unrelated tool
  4. The matcher cost function threshold (>0.8) rejects low-confidence matches and treats them as distinct add/remove pairs rather than forcing a false match
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md — Add scipy dependency; implement matcher/ package with MatchResult dataclass and match() Pass 1 (exact ToolID lookup, O(n) dict); _hungarian_match() stub
- [ ] 04-02-PLAN.md — Implement _cost.py (cost matrix helpers) and complete _hungarian_match() (per-type Hungarian with linear_sum_assignment + threshold rejection at cost > 0.8)
- [ ] 04-03-PLAN.md — Create tests/fixtures/matching.py (7 fixture pairs, ToolIDs 301+) and tests/test_matcher.py (9 tests covering all DIFF-04 scenarios)

### Phase 5: Diff Engine
**Goal**: Given two matched WorkflowDocs, the diff engine reports every functional change — tool additions, removals, configuration modifications with before/after values, and connection changes — with no false positives.
**Depends on**: Phase 4
**Requirements**: DIFF-01, DIFF-02, DIFF-03
**Success Criteria** (what must be TRUE):
  1. A tool added to the new workflow appears in `DiffResult.added_nodes` with its full configuration
  2. A tool removed from the old workflow appears in `DiffResult.removed_nodes` with its full configuration
  3. A tool with a changed filter expression shows before and after values for exactly the changed fields — unchanged fields are not reported
  4. A rewired connection (same source tool, different destination anchor) appears in `DiffResult.edge_diffs` using full 4-tuple anchor identity (src_tool + src_anchor + dst_tool + dst_anchor)
  5. Two functionally identical workflows produce an empty `DiffResult` — no additions, no removals, no modifications
**Plans**: TBD

Plans:
- [ ] 05-01: Implement NodeDiffer using config hash fast-path for equality, DeepDiff dict conversion for field-level before/after values on modified tools; emit NodeDiff per matched pair
- [ ] 05-02: Implement EdgeDiffer using frozenset symmetric difference on connection 4-tuples (src_tool, src_anchor, dst_tool, dst_anchor); classify additions, removals, and rewirings
- [ ] 05-03: Write diff engine integration tests covering all change types (add, remove, modify, rewire) using fixture workflow pairs; verify empty result for functionally identical workflows

### Phase 6: Pipeline Orchestration and JSON Renderer
**Goal**: A single call to `pipeline.run(DiffRequest)` produces a `DiffResponse` containing a JSON-serializable diff summary, and both CLI and future API can call it without importing any CLI or rendering concerns.
**Depends on**: Phase 5
**Requirements**: CLI-03
**Success Criteria** (what must be TRUE):
  1. `pipeline.run(DiffRequest(path_a, path_b))` returns a `DiffResponse` containing the full `DiffResult` without any call to `sys.exit`, `print`, or file I/O
  2. The JSON renderer serializes `DiffResult` to a valid JSON structure with counts for added, removed, modified, and connection changes, plus per-tool detail records
  3. `--json` flag produces a `.json` file alongside or instead of the HTML report with the same diff data in machine-readable form
  4. A unit test imports and calls `pipeline.run()` without any CLI import — confirms pipeline is entry-point-agnostic
**Plans**: TBD

Plans:
- [ ] 06-01: Implement pipeline.py with DiffRequest/DiffResponse dataclasses; wire Parser → Normalizer → NodeMatcher → Differ stages; enforce no sys.exit/print/file-I/O in pipeline
- [ ] 06-02: Implement JSONRenderer serializing DiffResult to structured JSON; validate schema covers counts and per-tool records
- [ ] 06-03: Write pipeline integration tests calling pipeline.run() without CLI; write JSON renderer tests validating output schema and content against fixture DiffResults

### Phase 7: HTML Report
**Goal**: A governance reviewer can open the HTML report in a browser — on an air-gapped network — and see a color-coded summary and expandable per-tool configuration diffs without installing any software.
**Depends on**: Phase 6
**Requirements**: REPT-01, REPT-02, REPT-03, REPT-04
**Success Criteria** (what must be TRUE):
  1. The report opens correctly in a standard browser with no internet connection — all JavaScript and CSS are embedded inline, zero CDN references in the rendered HTML
  2. The summary panel shows counts for added (green), removed (red), modified (yellow), and connection changes (blue) matching the DiffResult values
  3. Each modified tool has an expandable detail section showing before and after values for each changed field — unchanged fields are not shown
  4. The report header displays the generation timestamp and both compared file names
  5. A 500-tool workflow produces a report that opens in under 3 seconds — lazy-loading per-tool detail via JSON-in-script-tag pattern
**Plans**: TBD

Plans:
- [ ] 07-01: Design Jinja2 HTML template with color-coded summary panel, report header (title, timestamp, filenames), and JavaScript expand/collapse for per-tool detail sections
- [ ] 07-02: Implement HTMLRenderer embedding DiffResult as `const DIFF_DATA = {...}` JSON in a script tag; implement lazy per-tool expand logic in vanilla JavaScript
- [ ] 07-03: Implement inline embedding of all CSS and JavaScript at render time; verify output file passes offline rendering test (disable network, open in browser)
- [ ] 07-04: Write HTML renderer tests validating self-contained output, summary counts, detail section content, and header fields against fixture DiffResults

### Phase 8: Visual Graph
**Goal**: A reviewer can see the workflow topology in the report — color-coded by change type — and click any changed node to see its configuration diff without leaving the browser tab.
**Depends on**: Phase 7
**Requirements**: GRPH-01, GRPH-02, GRPH-03, GRPH-04
**Success Criteria** (what must be TRUE):
  1. By default, the graph renders tools as nodes and connections as directed edges using hierarchical left-to-right auto-layout (topological sort following data flow direction); passing `--canvas-layout` switches positioning to Alteryx canvas X/Y coordinates
  2. Nodes are color-coded: green for added, red for removed, yellow for modified, blue for connection change, neutral for unchanged
  3. Hovering or clicking a node displays the inline configuration diff for that tool without a page reload or external request
  4. A 500-tool workflow graph renders without browser hang — physics is disabled; default hierarchical layout uses topological sort, `--canvas-layout` mode uses fixed coordinate positioning
  5. The graph is embedded inline in the self-contained HTML file — no external graph library CDN references at report open time
**Plans**: TBD

Plans:
- [ ] 08-01: Spike pyvis self-contained HTML output reliability — verify cdn_resources='in_line' behavior, identify Bootstrap CDN leak, implement and test post-processing workaround; decide pyvis vs custom D3.js template based on spike result
- [ ] 08-02: Implement NetworkX DiGraph construction from DiffResult; assign diff-status attributes (added/removed/modified/unchanged) to nodes for color mapping
- [ ] 08-03: Implement graph renderer using chosen approach (pyvis or D3.js): default hierarchical left-to-right layout via topological sort; apply change-type color scheme; disable physics; embed as inline HTML
- [ ] 08-04: Implement `--canvas-layout` rendering mode: position nodes at Alteryx canvas X/Y coordinates instead of hierarchical layout; keep physics disabled
- [ ] 08-05: Implement hover/click node interaction displaying inline config diff panel from DIFF_DATA; test interaction in browser against fixture workflow with all change types
- [ ] 08-06: Write graph rendering tests validating node count, edge count, color assignments, default layout vs canvas-layout behavior, and self-contained HTML output against fixture DiffResults

### Phase 9: CLI Entry Point
**Goal**: A developer can run `acd diff workflow_v1.yxmd workflow_v2.yxmd` from the terminal and receive a diff report, with predictable exit codes that CI/CD systems can consume.
**Depends on**: Phase 8
**Requirements**: CLI-01, CLI-02, CLI-04
**Success Criteria** (what must be TRUE):
  1. `acd diff workflow_v1.yxmd workflow_v2.yxmd` produces `diff_report.html` in the current directory; `--output` flag writes to a custom path
  2. Exit code is 0 when no differences are found, 1 when differences are detected, and 2 when an error occurs (missing file, malformed XML)
  3. The report includes a governance metadata section with source file paths, SHA-256 file hashes, and generation timestamp (ALCOA+ audit compliance)
  4. End-to-end execution on a 500-tool synthetic workflow completes in under 5 seconds on developer hardware
  5. `acd --help` documents all flags including `--include-positions` (controls diff detection, excludes positions by default) and `--canvas-layout` (controls graph rendering, switches from hierarchical auto-layout to canvas X/Y coordinates) with a clear explanation of each flag's distinct purpose
**Plans**: TBD

Plans:
- [ ] 09-01: Implement Typer CLI app in cli.py as a thin adapter over pipeline.run(); add --output, --include-positions, --canvas-layout, --json flags; register pyproject.toml entry point `acd = "alteryx_diff.cli:app"`
- [ ] 09-02: Implement standardized exit codes (0/1/2) and ANSI-safe TTY output; verify CLI contains zero business logic (all logic in pipeline and stages)
- [ ] 09-03: Add governance metadata section to HTML and JSON output: source file paths, SHA-256 file hashes, generation timestamp
- [ ] 09-04: Build 500-tool synthetic fixture; run end-to-end performance benchmark; instrument stage timings; validate <5 second SLA
- [ ] 09-05: Write end-to-end CLI smoke tests covering success path, diff-found path, error paths, exit codes, --output flag, --canvas-layout flag, and --include-positions flag behavior

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Scaffold and Data Models | 3/3 | Complete   | 2026-03-01 |
| 2. XML Parser and Validation | 2/2 | Complete   | 2026-03-01 |
| 3. Normalization Layer | 4/4 | Complete   | 2026-03-02 |
| 4. Node Matcher | 2/3 | In Progress|  |
| 5. Diff Engine | 0/3 | Not started | - |
| 6. Pipeline Orchestration and JSON Renderer | 0/3 | Not started | - |
| 7. HTML Report | 0/4 | Not started | - |
| 8. Visual Graph | 0/6 | Not started | - |
| 9. CLI Entry Point | 0/5 | Not started | - |
