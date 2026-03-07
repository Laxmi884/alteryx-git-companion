# Phase 9: CLI Entry Point - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Thin Typer CLI adapter over `pipeline.run()`. The `acd diff` command parses two `.yxmd` files, runs the diff pipeline, and writes a report to disk. No business logic in the CLI layer — all computation lives in pipeline and stages. Output formats: HTML (default) and JSON (`--json`). Predictable exit codes (0/1/2) for CI/CD consumption.

</domain>

<decisions>
## Implementation Decisions

### Terminal output
- Single spinner/progress line while running (clears on completion)
- On success: one-line summary, e.g. `Report written to diff_report.html (12 changes detected)`
- On clean diff (exit 0): print `No differences found` message, no file written
- `--quiet` / `-q` flag suppresses all terminal output (spinner + summary); exit code only — for strict CI pipelines

### Error presentation
- File-not-found and unreadable-file errors: plain message to stderr (e.g. `Error: workflow_v1.yxmd not found`)
- Malformed XML errors: include parser detail — specific line number and element name (e.g. `Error: Invalid XML in workflow_v1.yxmd at line 42: unexpected token`)
- Stdout/stderr routing and verbose flag design: Claude's discretion (standard Unix conventions expected)

### JSON output
- `--json` writes to stdout (pipe-friendly: `acd diff a.yxmd b.yxmd --json | jq`)
- Top-level structure grouped by change type:
  ```json
  {
    "added": [...],
    "removed": [...],
    "modified": [...],
    "metadata": {...}
  }
  ```
- Governance metadata always included under `"metadata"` key in JSON (same fields as HTML report)
- When no differences found and `--json` is used: print empty diff JSON (consistent output, no special-casing needed by downstream tools):
  ```json
  {"added": [], "removed": [], "modified": [], "metadata": {...}}
  ```

### Governance metadata
- Minimum fields only: source file paths, SHA-256 file hashes, generation timestamp
- No extras (no tool version, no Alteryx Designer version, no node counts)
- In HTML report: footer section, collapsed by default — visible to auditors, unobtrusive for casual readers
- Hash display: full 64-character SHA-256 for verifiability (ALCOA+ compliance)
- Terminal stays clean: governance metadata appears only in the report file, not in the one-line completion summary

### Claude's Discretion
- stdout vs stderr routing for all output streams
- Whether to add a `--verbose` / `-v` flag for stack traces and stage timing on errors
- Exact spinner library/implementation
- Compression or formatting of JSON output (pretty-print vs compact)

</decisions>

<specifics>
## Specific Ideas

- `--quiet` flag is explicitly wanted for CI pipeline usage — not just a nice-to-have
- JSON output must be stdout-native so it works with `jq` and shell pipelines without intermediate files
- Governance footer in HTML should be collapsible — auditors can expand, everyone else ignores it
- Full 64-char SHA-256 is a hard requirement for ALCOA+ compliance verification

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-cli-entry-point*
*Context gathered: 2026-03-06*
