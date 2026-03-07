# Phase 9: CLI Entry Point - Research

**Researched:** 2026-03-06
**Domain:** Python CLI (Typer), exit codes, governance metadata (SHA-256, ALCOA+), CI/CD integration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Phase Boundary:** Thin Typer CLI adapter over `pipeline.run()`. The `acd diff` command parses two `.yxmd` files, runs the diff pipeline, and writes a report to disk. No business logic in the CLI layer — all computation lives in pipeline and stages. Output formats: HTML (default) and JSON (`--json`). Predictable exit codes (0/1/2) for CI/CD consumption.

**Terminal output:**
- Single spinner/progress line while running (clears on completion)
- On success: one-line summary, e.g. `Report written to diff_report.html (12 changes detected)`
- On clean diff (exit 0): print `No differences found` message, no file written
- `--quiet` / `-q` flag suppresses all terminal output (spinner + summary); exit code only — for strict CI pipelines

**Error presentation:**
- File-not-found and unreadable-file errors: plain message to stderr (e.g. `Error: workflow_v1.yxmd not found`)
- Malformed XML errors: include parser detail — specific line number and element name (e.g. `Error: Invalid XML in workflow_v1.yxmd at line 42: unexpected token`)
- Stdout/stderr routing and verbose flag design: Claude's discretion (standard Unix conventions expected)

**JSON output:**
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

**Governance metadata:**
- Minimum fields only: source file paths, SHA-256 file hashes, generation timestamp
- No extras (no tool version, no Alteryx Designer version, no node counts)
- In HTML report: footer section, collapsed by default — visible to auditors, unobtrusive for casual readers
- Hash display: full 64-character SHA-256 for verifiability (ALCOA+ compliance)
- Terminal stays clean: governance metadata appears only in the report file, not in the one-line completion summary

**Claude's Discretion:**
- stdout vs stderr routing for all output streams
- Whether to add a `--verbose` / `-v` flag for stack traces and stage timing on errors
- Exact spinner library/implementation
- Compression or formatting of JSON output (pretty-print vs compact)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-01 | User can run `python alteryx_diff.py workflow_v1.yxmd workflow_v2.yxmd` and receive a `diff_report.html` output file; `--output` flag for custom output path | Typer `@app.command()` with positional Path arguments and `--output` Option; pyproject.toml `acd` entry point already declared |
| CLI-02 | System exits with standardized codes: 0 = no differences found, 1 = differences detected, 2 = error (malformed input, missing file, etc.) | `raise typer.Exit(code=N)` — HIGH confidence from official Typer docs; existing `ParseError` hierarchy maps cleanly to exit code 2 |
| CLI-04 | Report includes governance metadata section: source file paths, SHA-256 file hashes, generation timestamp (ALCOA+ audit compliance) | `hashlib.file_digest(f, "sha256")` (Python 3.11+ stdlib); HTML footer section + JSON `"metadata"` key; no new dependencies needed |
</phase_requirements>

---

## Summary

Phase 9 is the final integration layer — a thin Typer CLI adapter that wires together all previously-built pipeline components (Phase 6 `pipeline.run()`, Phase 7 `HTMLRenderer`, Phase 8 `GraphRenderer`, Phase 6 `JSONRenderer`) behind a single `acd diff` command. All business logic already exists and has been tested; this phase adds the entry point, flag routing, exit code protocol, governance metadata, and the performance gate.

The key insight from the existing codebase: `pipeline.run()` already returns a `DiffResponse` and raises `ParseError` subclasses (`MissingFileError`, `UnreadableFileError`, `MalformedXMLError`) — the CLI need only catch these and map them to exit code 2. The `DiffResult.is_empty` property gives exit code 0 vs 1 for free. Governance metadata (SHA-256) is pure stdlib — `hashlib.file_digest()` added in Python 3.11, which is the project's minimum.

The `--include-positions` flag requires extending the pipeline call: the differ stage compares `config_hash` values only; enabling positions means also comparing `NormalizedNode.position` tuples for matched pairs. This is a 5-10 line extension to the differ layer, not a new stage. The `--canvas-layout` flag passes through directly to `GraphRenderer.render(canvas_layout=True)` — that parameter already exists.

**Primary recommendation:** Implement `cli.py` with a single `@app.command()` for `acd diff`, update the existing `pyproject.toml` entry point (`acd = "alteryx_diff.__main__:main"`) to point to the new `cli.py`, and add `typer>=0.12` as a runtime dependency via `uv add`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | >=0.12 (latest: 0.24.1) | CLI framework — argument parsing, help generation, completion | Built on Click, adds type-hint-driven arg parsing; project ROADMAP.md explicitly names Typer |
| rich | bundled with typer | Spinner (`console.status()`), styled terminal output | Included as Typer dependency; no separate install required |
| hashlib | stdlib (Python 3.11+) | SHA-256 file hashing for governance metadata | `file_digest()` added in 3.11 — project requires `>=3.11`; zero extra dependencies |
| pathlib | stdlib | Path handling for input files and output path | Already used across project; `Path.resolve()` for display |
| datetime | stdlib | ISO-8601 generation timestamp | Already used in `html_renderer.py` via `datetime.now(UTC).isoformat()` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typer.testing.CliRunner | (with typer) | In-process CLI testing without subprocess | All smoke tests for Phase 9 — avoids filesystem/subprocess overhead |
| sys | stdlib | Explicit stderr writes when Typer's echo isn't sufficient | Routing error messages to stderr only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| typer | click directly | Typer is already the project decision in ROADMAP.md; click lacks type-hint integration |
| typer | argparse | argparse requires more boilerplate; no auto-completion |
| rich.console.Console.status() | yaspin | yaspin is not installed; rich is already bundled with typer |
| hashlib.file_digest() | manual chunk-read + update | file_digest() is cleaner and available on Python 3.11+ (project minimum) |

**Installation:**
```bash
uv add typer
```
Rich is installed automatically as a Typer dependency. No additional packages needed.

---

## Architecture Patterns

### Recommended Project Structure

```
src/alteryx_diff/
├── cli.py                 # Typer app — ONLY entry point code, no business logic
├── __main__.py            # Thin shim: from alteryx_diff.cli import app; app()
├── pipeline/
│   └── pipeline.py        # run() already exists — no changes needed for basic case
├── differ/
│   └── differ.py          # diff() — may need include_positions param extension
├── renderers/
│   ├── html_renderer.py   # render() — needs governance footer added
│   ├── json_renderer.py   # render() — needs "metadata" key added
│   └── graph_renderer.py  # render(canvas_layout=True) — already implemented
└── exceptions.py          # ParseError hierarchy — already maps to exit code 2

tests/
├── test_cli.py            # End-to-end CLI smoke tests via CliRunner
└── fixtures/
    └── cli.py             # .yxmd byte fixtures for CLI tests (ToolIDs 901+)
```

### Pattern 1: Single Subcommand Typer App

**What:** The `acd diff` command where `diff` is a registered subcommand.
**When to use:** This project has one command now; structure allows future commands (e.g., `acd validate`, `acd render`) without restructuring.
**Example:**
```python
# src/alteryx_diff/cli.py
# Source: https://typer.tiangolo.com/tutorial/commands/
import typer
import pathlib

app = typer.Typer(no_args_is_help=True)

@app.command()
def diff(
    workflow_a: pathlib.Path = typer.Argument(..., help="Baseline .yxmd file"),
    workflow_b: pathlib.Path = typer.Argument(..., help="Changed .yxmd file"),
    output: pathlib.Path = typer.Option(
        pathlib.Path("diff_report.html"),
        "--output", "-o",
        help="Output path for the HTML report",
    ),
    include_positions: bool = typer.Option(
        False,
        "--include-positions",
        help="Include canvas X/Y position changes in diff detection (excluded by default)",
    ),
    canvas_layout: bool = typer.Option(
        False,
        "--canvas-layout",
        help="Use Alteryx canvas X/Y coordinates for graph layout (default: hierarchical auto-layout)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="Suppress all terminal output; emit exit code only (for CI pipelines)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Write JSON diff to stdout instead of HTML file",
    ),
) -> None:
    """Compare two Alteryx .yxmd workflow files and generate a diff report."""
    ...
```

### Pattern 2: Exit Code Protocol

**What:** Mapping pipeline outcomes and exceptions to Unix exit codes.
**When to use:** Always — all exit paths must use this protocol.
**Example:**
```python
# Source: https://typer.tiangolo.com/tutorial/terminating/
from alteryx_diff.exceptions import ParseError, MalformedXMLError

try:
    response = pipeline.run(request)
except MalformedXMLError as e:
    typer.echo(f"Error: Invalid XML in {e.filepath}: {e.message}", err=True)
    raise typer.Exit(code=2)
except ParseError as e:
    typer.echo(f"Error: {e.message}", err=True)
    raise typer.Exit(code=2)

if response.result.is_empty:
    if not quiet:
        typer.echo("No differences found")
    raise typer.Exit(code=0)
else:
    # write report, then:
    raise typer.Exit(code=1)
```

### Pattern 3: Rich Spinner (clears on completion)

**What:** Single-line spinner that clears itself when the pipeline finishes.
**When to use:** When `--quiet` is NOT set.
**Example:**
```python
# Source: https://typer.tiangolo.com/tutorial/progressbar/
from rich.console import Console

console = Console()

if not quiet:
    with console.status("Running diff...", spinner="dots"):
        response = pipeline.run(request)
else:
    response = pipeline.run(request)
```
`console.status()` uses `transient=True` by default — the spinner line disappears on exit, leaving a clean terminal.

### Pattern 4: SHA-256 File Hash (ALCOA+ compliance)

**What:** Full 64-character SHA-256 hex digest of each input file for audit traceability.
**When to use:** Always — computed before pipeline.run() and embedded in output.
**Example:**
```python
# Source: https://docs.python.org/3/library/hashlib.html
import hashlib

def _file_sha256(path: pathlib.Path) -> str:
    """Return 64-char SHA-256 hex digest for a file (Python 3.11+ hashlib.file_digest)."""
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256")
    return digest.hexdigest()
```
Returns a 64-character lowercase hex string. No chunking logic needed — `file_digest()` handles large files efficiently.

### Pattern 5: Typer CliRunner Testing

**What:** In-process testing of CLI commands without spawning subprocesses.
**When to use:** All CLI smoke tests.
**Example:**
```python
# Source: https://typer.tiangolo.com/tutorial/testing/
from typer.testing import CliRunner
from alteryx_diff.cli import app

runner = CliRunner(mix_stderr=False)

def test_diff_success_exit_code_1(tmp_path):
    path_a = tmp_path / "a.yxmd"
    path_b = tmp_path / "b.yxmd"
    path_a.write_bytes(MINIMAL_YXMD_A)
    path_b.write_bytes(MINIMAL_YXMD_B)
    result = runner.invoke(app, ["diff", str(path_a), str(path_b)])
    assert result.exit_code == 1  # differences detected

def test_diff_clean_exit_code_0(tmp_path):
    path_a = tmp_path / "a.yxmd"
    path_b = tmp_path / "b.yxmd"
    path_a.write_bytes(IDENTICAL_YXMD)
    path_b.write_bytes(IDENTICAL_YXMD)
    result = runner.invoke(app, ["diff", str(path_a), str(path_b)])
    assert result.exit_code == 0

def test_diff_missing_file_exit_code_2(tmp_path):
    path_b = tmp_path / "b.yxmd"
    path_b.write_bytes(MINIMAL_YXMD_B)
    result = runner.invoke(app, ["diff", "nonexistent.yxmd", str(path_b)])
    assert result.exit_code == 2
    assert "Error" in result.stderr
```

### Pattern 6: pyproject.toml Entry Point

**What:** The existing entry point needs updating from `__main__:main` to `cli:app`.
**Important:** `pyproject.toml` already declares `acd = "alteryx_diff.__main__:main"`. The `__main__.py` does NOT exist yet — this is created in Phase 9.
```toml
# pyproject.toml (current — will be updated in Phase 9)
[project.scripts]
acd = "alteryx_diff.__main__:main"
```
Recommended pattern for Phase 9:
```toml
[project.scripts]
acd = "alteryx_diff.cli:app"
```
Then `__main__.py` becomes a thin module-invocation shim (`python -m alteryx_diff`):
```python
# src/alteryx_diff/__main__.py
from alteryx_diff.cli import app
app()
```

### Pattern 7: Governance Metadata Structure

**What:** Minimum ALCOA+ fields to include in every output.
**When to use:** Always — both HTML footer and JSON `"metadata"` key.
```python
import datetime

def _build_governance_metadata(
    path_a: pathlib.Path,
    path_b: pathlib.Path,
    hash_a: str,
    hash_b: str,
) -> dict:
    return {
        "file_a": str(path_a.resolve()),
        "file_b": str(path_b.resolve()),
        "sha256_a": hash_a,  # 64-char hex
        "sha256_b": hash_b,  # 64-char hex
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
```

### Anti-Patterns to Avoid

- **Business logic in cli.py:** Any diff computation, normalization, or rendering logic in the CLI layer violates the hexagonal architecture. All computation stays in pipeline and stage modules.
- **sys.exit() instead of raise typer.Exit():** `sys.exit()` does not unwind Typer's cleanup; always use `raise typer.Exit(code=N)`.
- **Writing governance metadata to terminal:** The one-line completion summary must NOT include SHA-256 hashes — terminal stays clean, metadata only in report file.
- **Hardcoding output filename before checking `--json`:** When `--json` is set, no HTML file is written; output goes to stdout. Don't create/open the output file path before this check.
- **`--quiet` + `--json` conflict:** `--json` writes to stdout; `--quiet` suppresses stderr/spinner. These flags are compatible — `--quiet` should suppress spinner and summary, not stdout JSON.
- **Not resolving paths before display:** Use `path.resolve()` for absolute paths in governance metadata and completion summary. Relative paths are ambiguous in audit records.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Argument parsing | Manual `sys.argv` parsing or argparse | `typer` with type hints | Typer auto-generates `--help`, type coercion, shell completion |
| Spinner animation | Custom ANSI cursor control | `rich.console.Console().status()` | Handles TTY detection, Windows compat, clears correctly |
| SHA-256 file hashing | Manual chunk-read loop | `hashlib.file_digest(f, "sha256")` | Stdlib since Python 3.11, handles large files efficiently, auditable |
| TTY detection (color output) | Manual `os.isatty()` checks | Rich's Console (auto-detects NO_COLOR, isatty) | Rich already bundled with Typer; handles CI/non-TTY silently |
| CLI test subprocess | `subprocess.run(["acd", ...])` in tests | `typer.testing.CliRunner` | In-process, fast, captures stdout/stderr separately, no PATH issues |

**Key insight:** Rich is already bundled with Typer 0.12+ — any spinner, TTY detection, or styled output is free. Don't introduce additional terminal libraries.

---

## Common Pitfalls

### Pitfall 1: `--include-positions` Has No Pipeline Hook Yet

**What goes wrong:** The `--include-positions` flag is documented and parsed by the CLI, but the differ stage (`differ.diff()`) currently only compares `config_hash` values for matched pairs — `NormalizedNode.position` is never consulted. Passing the flag does nothing unless the differ is extended.
**Why it happens:** NORM-04 deliberately separated position from config_hash. The differ has no `include_positions` parameter.
**How to avoid:** Extend `differ.diff()` to accept `include_positions: bool = False`. When `True`, also compare `old_norm.position != new_norm.position` for matched pairs. This is a small extension to the existing matched-pair loop in `differ.py`, not a new module.
**Warning signs:** Test passes `--include-positions` and asserts exit code 1 on position-only change, but gets exit code 0.

### Pitfall 2: `--json` Outputs to stdout but HTML writes to file — Don't Mix

**What goes wrong:** JSON mode is pipe-friendly (`acd diff a.yxmd b.yxmd --json | jq`). If the CLI accidentally prints spinner output or the completion summary to stdout in JSON mode, `jq` will fail with parse errors.
**Why it happens:** Rich's `Console` defaults to stdout. JSON output also goes to stdout.
**How to avoid:** When `--json` is set, use `Console(stderr=True)` for spinner/summary or suppress entirely. Write JSON with `typer.echo(json_str)` to stdout. When `--quiet` is also set, suppress the spinner but still write JSON to stdout.
**Warning signs:** `acd diff a.yxmd b.yxmd --json | jq '.'` fails with "parse error".

### Pitfall 3: Entry Point Path Mismatch

**What goes wrong:** `pyproject.toml` currently declares `acd = "alteryx_diff.__main__:main"` but `__main__.py` does not exist. After Phase 9, the entry point may be updated to point to `cli:app`.
**Why it happens:** The entry point was declared speculatively in Phase 1 before `cli.py` was written.
**How to avoid:** Create `__main__.py` as a shim AND update the entry point to `cli:app`. Run `uv pip install -e .` and verify `acd --help` works after implementation.
**Warning signs:** `acd: command not found` or `ImportError: cannot import name 'main' from 'alteryx_diff.__main__'`.

### Pitfall 4: `mix_stderr=False` in CliRunner for Tests

**What goes wrong:** Default `CliRunner()` merges stderr into `result.stdout`. Tests that check error messages in stderr will pass even if the error went to stdout, masking routing bugs.
**Why it happens:** `mix_stderr=True` is the CliRunner default (inherited from Click).
**How to avoid:** Always create `runner = CliRunner(mix_stderr=False)` in test files. Access `result.stderr` for error message assertions.
**Warning signs:** Error message assertion passes with `result.stdout` but test actually checks stdout, not stderr.

### Pitfall 5: `governance.generated_at` Timestamp Drift Between HTML and JSON

**What goes wrong:** If the timestamp is computed separately for HTML and JSON output in the same run, they will differ by milliseconds — breaking audit reproducibility.
**Why it happens:** Each renderer has an independent `datetime.now()` call (see `html_renderer.py` line: `datetime.now(UTC).isoformat()`).
**How to avoid:** Compute governance metadata once in the CLI layer before calling any renderer. Pass the pre-built metadata dict (or dataclass) to both `HTMLRenderer.render()` and `JSONRenderer.render()` as a parameter.
**Warning signs:** HTML report timestamp and JSON `metadata.generated_at` differ in audit comparison.

### Pitfall 6: `--output` Flag Writes Silently Even on Clean Diff

**What goes wrong:** User expects "no file written on clean diff" (per CONTEXT.md decision) but CLI writes an empty/no-diff HTML file to the output path anyway.
**Why it happens:** Output file writing logic isn't gated on `result.is_empty`.
**How to avoid:** When `result.is_empty` is True, print "No differences found" and exit 0 WITHOUT writing any file. Only write the HTML or JSON file when there are actual differences to report.

---

## Code Examples

Verified patterns from official sources and project codebase:

### Complete CLI skeleton
```python
# src/alteryx_diff/cli.py
# Source: typer.tiangolo.com (official docs), project pipeline/pipeline.py
from __future__ import annotations

import datetime
import hashlib
import pathlib
import sys

import typer
from rich.console import Console

from alteryx_diff.exceptions import MalformedXMLError, ParseError
from alteryx_diff.pipeline import DiffRequest, run
from alteryx_diff.renderers import GraphRenderer, HTMLRenderer, JSONRenderer

app = typer.Typer(no_args_is_help=True)
_console = Console(stderr=True)  # spinner + summary to stderr; stdout clean for --json


@app.command()
def diff(
    workflow_a: pathlib.Path = typer.Argument(..., help="Baseline .yxmd file"),
    workflow_b: pathlib.Path = typer.Argument(..., help="Changed .yxmd file"),
    output: pathlib.Path = typer.Option(
        pathlib.Path("diff_report.html"), "--output", "-o",
        help="Output path for the HTML report (ignored when --json is set)",
    ),
    include_positions: bool = typer.Option(
        False, "--include-positions",
        help="Include canvas X/Y position changes in diff detection (excluded by default to avoid layout noise)",
    ),
    canvas_layout: bool = typer.Option(
        False, "--canvas-layout",
        help="Use Alteryx canvas X/Y coordinates for graph node positions (default: hierarchical auto-layout following data flow)",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress all terminal output; exit code only"),
    json_output: bool = typer.Option(False, "--json", help="Write JSON diff to stdout (pipe-friendly)"),
) -> None:
    """Compare two Alteryx .yxmd workflow files and report differences."""
    # Compute governance metadata upfront (single timestamp for audit consistency)
    hash_a = _file_sha256(workflow_a)
    hash_b = _file_sha256(workflow_b)
    metadata = _build_governance_metadata(workflow_a, workflow_b, hash_a, hash_b)

    # Run pipeline with optional spinner
    try:
        if quiet:
            response = run(DiffRequest(path_a=workflow_a, path_b=workflow_b))
        else:
            with _console.status("Running diff...", spinner="dots"):
                response = run(DiffRequest(path_a=workflow_a, path_b=workflow_b))
    except MalformedXMLError as e:
        typer.echo(f"Error: Invalid XML in {e.filepath}: {e.message}", err=True)
        raise typer.Exit(code=2)
    except ParseError as e:
        typer.echo(f"Error: {e.message}", err=True)
        raise typer.Exit(code=2)

    result = response.result

    if result.is_empty:
        if not quiet:
            typer.echo("No differences found", err=True)
        raise typer.Exit(code=0)

    # Render and write output
    if json_output:
        json_str = JSONRenderer().render(result, metadata=metadata)
        typer.echo(json_str)  # stdout — pipe-friendly
    else:
        graph_renderer = GraphRenderer()
        graph_html = graph_renderer.render(
            result,
            all_connections=...,  # see implementation notes below
            nodes_old=...,
            nodes_new=...,
            canvas_layout=canvas_layout,
        )
        html = HTMLRenderer().render(result, graph_html=graph_html, metadata=metadata)
        output.write_text(html, encoding="utf-8")
        if not quiet:
            change_count = (
                len(result.added_nodes) + len(result.removed_nodes)
                + len(result.modified_nodes) + len(result.edge_diffs)
            )
            typer.echo(f"Report written to {output} ({change_count} changes detected)", err=True)

    raise typer.Exit(code=1)


def _file_sha256(path: pathlib.Path) -> str:
    """Return 64-char SHA-256 hex digest. Uses hashlib.file_digest (Python 3.11+)."""
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256")
    return digest.hexdigest()


def _build_governance_metadata(
    path_a: pathlib.Path, path_b: pathlib.Path, hash_a: str, hash_b: str
) -> dict:
    return {
        "file_a": str(path_a.resolve()),
        "file_b": str(path_b.resolve()),
        "sha256_a": hash_a,
        "sha256_b": hash_b,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
```

### GraphRenderer needs nodes from pipeline — pipeline must expose them

The current `pipeline.run()` returns only `DiffResponse(result=DiffResult)`. But `GraphRenderer.render()` needs `nodes_old`, `nodes_new`, and `all_connections`. The CLI must either:
1. Extend `DiffResponse` to carry `doc_a`, `doc_b` (preferred — keeps pipeline clean), OR
2. The CLI calls `parse()`, `normalize()` etc. directly (violates thin-adapter principle)

The correct approach is extending `DiffResponse`:
```python
# pipeline/pipeline.py — extend DiffResponse
@dataclass(frozen=True, kw_only=True, slots=True)
class DiffResponse:
    result: DiffResult
    doc_a: WorkflowDoc   # NEW — needed by CLI for GraphRenderer
    doc_b: WorkflowDoc   # NEW — needed by CLI for GraphRenderer
```
Then CLI uses:
```python
graph_html = GraphRenderer().render(
    result,
    all_connections=response.doc_a.connections + response.doc_b.connections,
    nodes_old=response.doc_a.nodes,
    nodes_new=response.doc_b.nodes,
    canvas_layout=canvas_layout,
)
```

### Extending `differ.diff()` for `--include-positions`

```python
# differ/differ.py — add include_positions parameter
def diff(
    match_result: MatchResult,
    old_connections: tuple[AlteryxConnection, ...],
    new_connections: tuple[AlteryxConnection, ...],
    *,
    include_positions: bool = False,  # NEW — default preserves existing behavior
) -> DiffResult:
    ...
    for old_norm, new_norm in match_result.matched:
        config_changed = old_norm.config_hash != new_norm.config_hash
        position_changed = include_positions and old_norm.position != new_norm.position
        if config_changed or position_changed:
            node_diff = _diff_node(old_norm.source, new_norm.source)
            modified_nodes_list.append(node_diff)
    ...
```

### Governance HTML footer (collapsed by default)

```html
<!-- Add to html_renderer.py _TEMPLATE — after existing sections, before </div> -->
<details id="governance">
  <summary style="cursor:pointer;color:#888;font-size:0.85em;padding:12px 0;">
    Governance Metadata (ALCOA+)
  </summary>
  <div style="font-family:ui-monospace,monospace;font-size:0.82em;padding:8px 0;color:#555;">
    <div><b>File A:</b> {{ metadata.file_a }}</div>
    <div><b>SHA-256 A:</b> {{ metadata.sha256_a }}</div>
    <div><b>File B:</b> {{ metadata.file_b }}</div>
    <div><b>SHA-256 B:</b> {{ metadata.sha256_b }}</div>
    <div><b>Generated:</b> {{ metadata.generated_at }}</div>
  </div>
</details>
```
Uses HTML `<details>`/`<summary>` — collapsed by default, no JavaScript needed, auditors expand manually.

### JSON output with governance metadata

The CONTEXT.md specifies a different JSON schema than the current `JSONRenderer.render()` output (which produces `{summary, tools, connections}`). The `--json` flag output uses `{added, removed, modified, metadata}`. This is a NEW JSON schema for the CLI mode — distinct from the existing renderer output. Options:
1. Add a `metadata` parameter to `JSONRenderer.render()` and restructure to the new schema
2. Create a separate `CLIJsonRenderer` for the `--json` mode output

The simpler approach: pass `metadata` into `JSONRenderer` and let it append the `"metadata"` key to the existing output structure. The CONTEXT.md schema adds `"metadata"` alongside `added/removed/modified` — the existing renderer produces `{summary, tools, connections}`, which groups differently. Recommend building a separate CLI JSON output function rather than breaking the existing `JSONRenderer` contract (which has 5 passing tests).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| argparse for Python CLIs | Typer (type-hint based) | ~2020 | Auto-generates help, type coercion, completion; project already chose Typer in ROADMAP |
| `sys.exit(code)` | `raise typer.Exit(code=N)` | Typer 0.x | Proper cleanup; CliRunner captures the code correctly |
| Manual chunked file reading for SHA-256 | `hashlib.file_digest(f, "sha256")` | Python 3.11 | Cleaner, stdlib, handles large files; project requires >=3.11 |
| HTML `<div>` toggle for collapsible sections | HTML `<details>`/`<summary>` | HTML5 | No JavaScript needed; better accessibility; works in PDF export |
| `mix_stderr=True` (CliRunner default) | `CliRunner(mix_stderr=False)` | Click 8.2 / Typer 0.160+ | Allows separate stdout/stderr assertions in tests |

**Deprecated/outdated:**
- `typer.Exit(0)` without `raise`: Must use `raise typer.Exit(code=0)` — the exception must be raised, not just constructed.
- `__main__:main` entry point: Project currently declares this but `__main__.py` doesn't exist yet; Phase 9 must create it or update the entry point to `cli:app`.

---

## Open Questions

1. **Does `DiffResponse` need to carry `doc_a`/`doc_b` for `GraphRenderer`?**
   - What we know: `GraphRenderer.render()` requires `nodes_old`, `nodes_new`, `all_connections` — none of which are in the current `DiffResponse`.
   - What's unclear: Whether the pipeline should be extended to return `doc_a`/`doc_b`, or whether the CLI calls individual pipeline stages directly.
   - Recommendation: Extend `DiffResponse` — this is the cleanest hexagonal architecture approach. Only `run()` calls the stages; the CLI stays thin. One existing test (`test_pipeline.py`) must be updated to account for the new fields.

2. **JSON schema for `--json` flag vs existing `JSONRenderer` output**
   - What we know: CONTEXT.md specifies `{added, removed, modified, metadata}` for `--json` output. Existing `JSONRenderer` produces `{summary, tools, connections}` — a different structure.
   - What's unclear: Whether to modify `JSONRenderer` (breaking change to 5 passing tests) or build a new CLI-specific serializer.
   - Recommendation: Build a separate `_cli_json_output()` function in `cli.py` that produces the CONTEXT.md schema. This preserves the existing `JSONRenderer` contract and avoids test regressions.

3. **`--include-positions` impact on `_diff_node()` when only position changed**
   - What we know: `_diff_node()` uses `DeepDiff` on `node.config` dicts. Position is NOT in the config dict — it's a separate `NormalizedNode.position` field.
   - What's unclear: If `include_positions=True` and position changed but config hash did NOT change, calling `_diff_node()` on two nodes with identical configs will raise `ValueError("config_hash differed but DeepDiff found no changes")`.
   - Recommendation: When `include_positions=True` and `position_changed` but NOT `config_changed`, create a `NodeDiff` with `field_diffs={"position": (old_norm.position, new_norm.position)}` directly, bypassing `_diff_node()`.

---

## Validation Architecture

> nyquist_validation is not set in .planning/config.json — skipping this section.

---

## Sources

### Primary (HIGH confidence)
- https://typer.tiangolo.com/tutorial/terminating/ — `raise typer.Exit(code=N)` protocol, verified official docs
- https://typer.tiangolo.com/tutorial/testing/ — `CliRunner`, `mix_stderr=False`, `result.exit_code`, `result.stderr`
- https://typer.tiangolo.com/tutorial/commands/ — Subcommand structure, `@app.command()`, `no_args_is_help=True`
- https://typer.tiangolo.com/tutorial/progressbar/ — Rich spinner with `Progress(SpinnerColumn(), transient=True)`
- https://docs.python.org/3/library/hashlib.html — `hashlib.file_digest(f, "sha256")` (Python 3.11+), `hexdigest()` returns 64-char string
- https://pypi.org/project/typer/ — Latest version 0.24.1 (released 2026-02-21); dependencies: click, rich, shellingham
- Project source: `src/alteryx_diff/pipeline/pipeline.py` — `pipeline.run()` raises `ParseError` subclasses, returns `DiffResponse`
- Project source: `src/alteryx_diff/exceptions.py` — `ParseError`, `MalformedXMLError`, `MissingFileError`, `UnreadableFileError` with `filepath` and `message` attributes
- Project source: `src/alteryx_diff/models/diff.py` — `DiffResult.is_empty` property for exit code determination
- Project source: `src/alteryx_diff/renderers/graph_renderer.py` — `GraphRenderer.render(canvas_layout=bool)` already implemented
- Project source: `pyproject.toml` — entry point declared as `acd = "alteryx_diff.__main__:main"`; `typer` not yet in dependencies

### Secondary (MEDIUM confidence)
- https://typer.tiangolo.com/tutorial/commands/one-or-multiple/ — Single command + callback pattern for `acd diff` structure
- Multiple sources agree: `rich.console.Console().status()` is transient by default (clears spinner on exit)

### Tertiary (LOW confidence)
- Search results suggest `CliRunner(mix_stderr=False)` behavior changed in Click 8.2 / Typer 0.160 — verify against installed versions before relying on `result.stderr` separation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Typer confirmed at 0.24.1, hashlib.file_digest confirmed Python 3.11+ stdlib, all from official docs
- Architecture patterns: HIGH — patterns verified against official Typer docs and existing project codebase
- Pitfalls: HIGH for most; MEDIUM for `mix_stderr` behavioral change (single source)
- `--include-positions` extension: HIGH — based on direct code reading of existing differ and normalizer

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (Typer stable; stdlib hashlib very stable)
