# Requirements: Alteryx Canvas Diff (ACD)

**Defined:** 2026-03-01
**Core Value:** Accurate detection of functional changes — zero false positives from layout noise, zero missed configuration changes.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Parsing & Validation

- [x] **PARSE-01**: User can provide two `.yxmd` files as CLI arguments and the system loads both
- [x] **PARSE-02**: System validates XML structure on load and rejects malformed files before any processing begins
- [x] **PARSE-03**: System provides descriptive error messages for malformed, corrupted, or missing files
- [x] **PARSE-04**: System extracts ToolID, tool type, canvas X/Y position, configuration XML, and upstream/downstream connections for each tool into a typed internal object model

### Normalization

- [x] **NORM-01**: System strips whitespace differences and normalizes XML attribute ordering using C14N canonicalization to eliminate false positives
- [x] **NORM-02**: System removes non-functional Alteryx-generated metadata (GUIDs, timestamps, TempFile paths) before comparison
- [x] **NORM-03**: Canvas position (X/Y) is excluded from diff detection by default — stored separately for graph layout use only
- [x] **NORM-04**: User can opt in to position-based change detection via `--include-positions` flag with clear `--help` documentation explaining the default

### Diff Detection

- [x] **DIFF-01**: System detects tool additions (present in new, absent in old) and removals (present in old, absent in new)
- [x] **DIFF-02**: System detects tool configuration modifications and reports before/after field-level values for each changed field
- [x] **DIFF-03**: System detects connection additions, removals, and rewirings using full 4-tuple anchor identity (src_tool + src_anchor + dst_tool + dst_anchor)
- [x] **DIFF-04**: System uses two-pass node matching — exact ToolID lookup first, then Hungarian algorithm similarity fallback — to prevent phantom add/remove pairs when Alteryx regenerates ToolIDs

### HTML Report

- [x] **REPT-01**: Report includes a color-coded summary panel showing counts for added (green), removed (red), modified (yellow), and connection changes (blue)
- [x] **REPT-02**: Report includes expandable per-tool detail sections showing before/after field-level values for each modified tool
- [x] **REPT-03**: Report header displays report title, generation timestamp, and both compared file names
- [x] **REPT-04**: Report is fully self-contained HTML — all JavaScript and CSS embedded inline, no CDN references, functional on air-gapped networks

### Visual Graph

- [ ] **GRPH-01**: Report embeds an interactive graph rendering tools as nodes and connections as directed edges
- [x] **GRPH-02**: Graph uses hierarchical left-to-right auto-layout (topological sort following data flow direction) by default; user can opt in to Alteryx canvas X/Y coordinate positioning via `--canvas-layout` flag
- [x] **GRPH-03**: Graph nodes are color-coded by change type: green=added, red=removed, yellow=modified, blue=connection change; unchanged tools rendered in neutral color
- [ ] **GRPH-04**: User can hover or click on a graph node to display an inline configuration diff for that tool

### CLI

- [ ] **CLI-01**: User can run `python alteryx_diff.py workflow_v1.yxmd workflow_v2.yxmd` and receive a `diff_report.html` output file; `--output` flag for custom output path
- [ ] **CLI-02**: System exits with standardized codes: 0 = no differences found, 1 = differences detected, 2 = error (malformed input, missing file, etc.)
- [x] **CLI-03**: User can generate a JSON summary alongside or instead of the HTML report via `--json` flag, enabling CI/CD integration
- [ ] **CLI-04**: Report includes governance metadata section: source file paths, SHA-256 file hashes, generation timestamp (ALCOA+ audit compliance)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### File Format Support

- **FMT-01**: Support `.yxmc` (Alteryx macro) files as diff input
- **FMT-02**: Support `.yxapp` (Alteryx analytic app) files as diff input

### Macro Support

- **MACR-01**: Recursively parse and diff tools inside macro files referenced by a workflow
- **MACR-02**: Display macro-internal changes in the diff report with clear hierarchy

### API & Integrations

- **API-01**: REST API endpoint (`POST /diff`) accepting two workflow files, returning diff report
- **API-02**: Alteryx Server webhook integration — trigger diff on workflow promotion event
- **API-03**: Git PR comment bot — post diff summary as pull request comment on push

### Enhanced Visualization

- **VIZ-01**: Zoom and pan controls for large workflow graph navigation
- **VIZ-02**: Node clustering for large workflows (100+ tools) to prevent visual overload

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time canvas overlay inside Alteryx Designer | Requires Designer plugin API — Phase 2+ |
| Enterprise security framework (SSO, RBAC, audit logging) | Not needed for CLI prototype; Phase 3 with API |
| Three-way merge | Requires semantic understanding of Alteryx config values; 10x Phase 1 scope |
| AI natural language change summary | Hallucination risk unacceptable for regulated workflows before false-positive rate is proven |
| Web upload UI | Requires server infrastructure; Phase 3 with API |
| `.yxzp` packaged workflow support | ZIP container requires extraction pre-processing; defer until core parser is stable |
| Windows/Mac installer or executable | uv + pip install is sufficient for developer audience in v1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PARSE-01 | Phase 2 | Complete |
| PARSE-02 | Phase 2 | Complete |
| PARSE-03 | Phase 2 | Complete |
| PARSE-04 | Phase 1 | Complete |
| NORM-01 | Phase 3 | Complete |
| NORM-02 | Phase 3 | Complete |
| NORM-03 | Phase 3 | Complete |
| NORM-04 | Phase 3 | Complete |
| DIFF-01 | Phase 5 | Complete |
| DIFF-02 | Phase 5 | Complete |
| DIFF-03 | Phase 5 | Complete |
| DIFF-04 | Phase 4 | Complete |
| REPT-01 | Phase 7 | Complete |
| REPT-02 | Phase 7 | Complete |
| REPT-03 | Phase 7 | Complete |
| REPT-04 | Phase 7 | Complete |
| GRPH-01 | Phase 8 | Pending |
| GRPH-02 | Phase 8 | Complete |
| GRPH-03 | Phase 8 | Complete |
| GRPH-04 | Phase 8 | Pending |
| CLI-01 | Phase 9 | Pending |
| CLI-02 | Phase 9 | Pending |
| CLI-03 | Phase 6 | Complete |
| CLI-04 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 — GRPH-02 revised: hierarchical auto-layout as default, --canvas-layout flag for canvas X/Y positioning*
