# Phase 6: Pipeline Orchestration and JSON Renderer - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Wrap the full diff pipeline into a clean programmatic API (`pipeline.run(DiffRequest)` → `DiffResponse`), implement a `JSONRenderer` that serializes `DiffResult` to a structured JSON format, and expose a `--json` CLI flag that writes a `.json` file alongside the HTML report. Both CLI and future API callers can invoke the pipeline without importing any CLI or rendering concerns.

</domain>

<decisions>
## Implementation Decisions

### DiffRequest/DiffResponse shape
- `DiffRequest` contains only the two paths (`path_a`, `path_b`) — no config or output options
- `DiffResponse` is a thin dataclass wrapper: `DiffResponse(result: DiffResult)` — clean named return type, extensible without changing call sites
- Errors surface as raised exceptions — no error field on `DiffResponse`
- Pipeline module location: Claude's discretion based on existing codebase structure

### JSON output schema
- Top-level structure: `{ summary: { added, removed, modified, connections }, tools: [{ tool_name, changes: [...] }], connections: [...] }`
- Each per-tool change record includes: `id`, `display_name`, `change_type` (added/removed/modified)
- Connection changes live under a separate top-level `connections` key — they span tools and belong at the top level
- Schema documented as an inline docstring on `JSONRenderer` — no separate schema file

### --json flag behavior
- When `--json` is used, produce **both** `.html` and `.json` — no information lost
- JSON filename uses the same base name as the HTML report with `.json` extension (e.g., `diff_report.html` → `diff_report.json`)
- File output only — no stdout streaming
- CLI prints a confirmation message for the JSON file in the same style as the HTML confirmation

### Error handling in pipeline
- `pipeline.run()` raises exceptions — caller catches what it cares about (Pythonic)
- Exception types: Claude's discretion — check existing codebase, reuse or extend appropriately
- CLI catches pipeline exceptions at the boundary, prints a human-friendly error message, and exits with code 1
- If any tool's file fails to parse, the pipeline fails entirely — no partial/silent results

### Claude's Discretion
- Pipeline module file location within the codebase
- Exception class design (new typed exceptions vs. reusing existing ones)
- Exact progress/confirmation message wording for JSON output

</decisions>

<specifics>
## Specific Ideas

- No specific references — standard Pythonic API design expected
- The pipeline must be callable without any CLI import (enforced by a unit test per success criteria)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-pipeline-orchestration-and-json-renderer*
*Context gathered: 2026-03-05*
