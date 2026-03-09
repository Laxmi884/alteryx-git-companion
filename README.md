# Alteryx Canvas Diff (ACD)

A CLI tool that compares two Alteryx workflow files (`.yxmd`) or app files (`.yxwz`) and generates a structured, self-contained HTML diff report — showing exactly what changed at the tool, configuration, and connection level, including an embedded interactive workflow graph.

Built for analytics developers and governance teams who need to understand what changed between workflow versions without reading raw XML.

---

## Features

- **Zero false positives** — strips Alteryx XML noise (attribute reordering, whitespace, auto-generated GUIDs, timestamps, TempFile paths) before comparing
- **Field-level diffs** — reports before/after values for every changed configuration field, not just "this tool changed"
- **ToolID-regeneration safe** — two-pass matching (exact ToolID lookup → Hungarian algorithm fallback) prevents phantom add/remove pairs when Alteryx regenerates tool IDs on save
- **Interactive graph** — embedded vis-network graph with color-coded nodes (green=added, red=removed, yellow=modified, blue=connection change); click any node to see its inline diff
- **Self-contained HTML** — all CSS, JavaScript, and the graph library are inlined; report works offline and on air-gapped networks
- **ALCOA+ governance footer** — source file paths, SHA-256 hashes, and generation timestamp embedded in every report for audit compliance
- **CI/CD friendly** — `--json` flag writes machine-readable output to stdout; predictable exit codes (0/1/2)
- **Position-aware** — canvas X/Y positions are excluded from diff detection by default (layout noise); opt in with `--include-positions`
- **App file support** — `.yxwz` Alteryx App files are accepted as input; interface/UI-only tools (`AlteryxGuiToolkit.*` — tabs, text boxes, containers, actions) are filtered out by default to eliminate noise when comparing an app against a workflow; opt out with `--no-filter-ui-tools`

---

## Installation

### Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or pip

### With uv (recommended)

```bash
git clone <repo-url>
cd alteryx_diff

# Install and activate environment
uv sync

# The acd command is now available
uv run acd --help
```

To install as a global tool so `acd` is available anywhere:

```bash
uv tool install .
acd --help
```

### With pip

```bash
git clone <repo-url>
cd alteryx_diff

pip install .

# The acd command is now available
acd --help
```

### From source (editable install)

```bash
git clone <repo-url>
cd alteryx_diff

uv sync --all-groups   # includes dev dependencies
uv run acd --help
```

---

## Usage

### Basic diff

```bash
acd workflow_v1.yxmd workflow_v2.yxmd
```

Produces `diff_report.html` in the current directory and exits with code `1` (differences found).

> **Paths with spaces:** quote the arguments in your shell:
> ```bash
> acd "My Workflow v1.yxmd" "My Workflow v2.yxmd"
> ```

### Custom output path

```bash
acd workflow_v1.yxmd workflow_v2.yxmd --output reports/my_diff.html
```

### JSON output (for CI/CD)

```bash
acd workflow_v1.yxmd workflow_v2.yxmd --json
```

Writes JSON to stdout. No HTML file is created.

```bash
# Pipe to a file
acd workflow_v1.yxmd workflow_v2.yxmd --json > diff.json

# Pipe to jq for inspection
acd workflow_v1.yxmd workflow_v2.yxmd --json | jq '.modified[].tool_type'
```

### Include position changes

By default, canvas X/Y position changes are ignored (layout noise). To include them:

```bash
acd workflow_v1.yxmd workflow_v2.yxmd --include-positions
```

### Canvas layout in graph

By default, the graph uses hierarchical left-to-right auto-layout (follows data flow order). To use Alteryx canvas X/Y coordinates for node positions instead:

```bash
acd workflow_v1.yxmd workflow_v2.yxmd --canvas-layout
```

### Compare an app (.yxwz) against a workflow (.yxmd)

App files contain interface/UI-only tools (`AlteryxGuiToolkit.*` — tabs, text boxes, containers, actions) that have no counterpart in regular workflows. These are filtered out by default so only analytical tool changes are shown:

```bash
acd workflow.yxmd "My App.yxwz" --output review.html
```

To keep UI tools in the diff (e.g. comparing two apps where interface changes matter):

```bash
acd app_v1.yxwz app_v2.yxwz --no-filter-ui-tools --output review.html
```

### Quiet mode (CI pipelines)

Suppress all terminal output — only the exit code is returned:

```bash
acd workflow_v1.yxmd workflow_v2.yxmd --quiet
echo $?   # 0 = no diff, 1 = diff found, 2 = error
```

### Combine flags

```bash
# Canonical audit run: JSON output, positions included, quiet
acd workflow_v1.yxmd workflow_v2.yxmd --json --include-positions --quiet > audit.json

# Full HTML report with canvas layout
acd baseline.yxmd promoted.yxmd --output review.html --canvas-layout
```

---

## CLI Reference

```
acd [OPTIONS] WORKFLOW_A WORKFLOW_B
```

| Argument / Option | Default | Description |
|---|---|---|
| `WORKFLOW_A` | required | Baseline `.yxmd` or `.yxwz` file — quote paths that contain spaces |
| `WORKFLOW_B` | required | Changed `.yxmd` or `.yxwz` file — quote paths that contain spaces |
| `--output`, `-o` | `diff_report.html` | Output path for the HTML report (ignored when `--json` is set) |
| `--include-positions` | off | Include canvas X/Y position changes in diff detection (excluded by default to avoid layout noise) |
| `--canvas-layout` | off | Use Alteryx canvas X/Y coordinates for graph node positions (default: hierarchical auto-layout) |
| `--no-filter-ui-tools` | off | Keep `AlteryxGuiToolkit.*` interface tools in the diff (by default they are filtered out to reduce noise when comparing apps against workflows) |
| `--json` | off | Write JSON diff to stdout instead of HTML file (pipe-friendly) |
| `--quiet`, `-q` | off | Suppress all terminal output; exit code only (for CI pipelines) |
| `--help` | | Show help and exit |

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | No differences found |
| `1` | Differences detected |
| `2` | Error — missing file, malformed XML, unreadable input |

These codes are stable and suitable for CI/CD gating:

```bash
acd old.yxmd new.yxmd --quiet
if [ $? -eq 1 ]; then
  echo "Workflow changed — review required"
fi
```

---

## Output Formats

### HTML Report

The default output is a single self-contained `.html` file with:

- **Summary panel** — counts of added (green), removed (red), modified (yellow), and connection changes (blue)
- **Per-tool detail** — expandable sections for each modified tool showing before/after values for every changed field
- **Interactive graph** — embedded vis-network graph; click any node to see its inline configuration diff; toggle to show only changed nodes
- **Governance footer** — collapsible `<details>` section with source file absolute paths, SHA-256 file hashes, and generation timestamp (ALCOA+ audit compliance)
- **Report header** — both compared file names and generation timestamp

The report has zero CDN references — all JavaScript and CSS are inlined. It opens correctly on air-gapped networks.

### JSON Output (`--json`)

Schema written to stdout:

```json
{
  "added": [
    {
      "tool_id": 42,
      "tool_type": "AlteryxBasePluginsGui.Filter.Filter",
      "config": { "Expression": "Amount > 1000" }
    }
  ],
  "removed": [
    {
      "tool_id": 17,
      "tool_type": "AlteryxBasePluginsGui.DbFileInput.DbFileInput",
      "config": { "File": "sales_data.csv" }
    }
  ],
  "modified": [
    {
      "tool_id": 23,
      "tool_type": "AlteryxBasePluginsGui.Formula.Formula",
      "field_diffs": [
        {
          "field": "Expression",
          "before": "[Amount] * 1.05",
          "after": "[Amount] * 1.10"
        }
      ]
    }
  ],
  "metadata": {
    "file_a": "/absolute/path/to/workflow_v1.yxmd",
    "file_b": "/absolute/path/to/workflow_v2.yxmd",
    "sha256_a": "a3f2c1...",
    "sha256_b": "b7d9e4...",
    "generated_at": "2026-03-07T12:34:56.789123+00:00"
  }
}
```

When no differences are found, `added`, `removed`, and `modified` are empty arrays and the exit code is `0`.

---

## How It Works

ACD runs an immutable four-stage pipeline:

```
.yxmd files
    │
    ▼
┌─────────────┐
│   Parser    │  lxml — loads XML, validates structure, emits WorkflowDoc
└──────┬──────┘
       │ WorkflowDoc (nodes, connections, typed fields)
       ▼
┌─────────────┐
│ Normalizer  │  C14N canonicalization, GUID/timestamp stripping,
│             │  position separation, SHA-256 config hashing
└──────┬──────┘
       │ NormalizedWorkflowDoc (config_hash per node, position separate)
       ▼
┌─────────────┐
│   Matcher   │  Pass 1: exact ToolID lookup (O(n))
│             │  Pass 2: Hungarian algorithm fallback (scipy),
│             │          cost threshold 0.8 — rejects false matches
└──────┬──────┘
       │ MatchResult (paired nodes, unmatched additions/removals)
       ▼
┌─────────────┐
│   Differ    │  DeepDiff for field-level config changes,
│             │  frozenset symmetric difference for connections
└──────┬──────┘
       │ DiffResult
       ▼
  HTML / JSON renderer
```

**Why normalization matters:** Alteryx injects noise on every save — attribute ordering changes, auto-generated GUIDs, session timestamps, and TempFile paths. Without stripping these, every save would appear as a diff. The normalization layer eliminates all of this before any comparison happens.

**Why two-pass matching matters:** Alteryx can regenerate all ToolIDs when a workflow is re-saved in some versions. A naive ToolID-only matcher would report every tool as removed and re-added. The Hungarian algorithm fallback matches tools by configuration similarity and canvas proximity, preventing these phantom pairs.

---

## Development

### Setup

```bash
git clone <repo-url>
cd alteryx_diff

# Install all dependencies (runtime + dev)
uv sync --all-groups

# Install pre-commit hooks (ruff, mypy, trailing whitespace checks)
uv run pre-commit install
```

### Run tests

```bash
uv run pytest

# With verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_differ.py
```

### Type checking

```bash
uv run mypy src/
```

### Linting and formatting

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Fix auto-fixable lint issues
uv run ruff check --fix src/ tests/
```

### Project structure

```
alteryx_diff/
├── src/
│   └── alteryx_diff/
│       ├── cli.py              # Typer CLI adapter over pipeline.run()
│       ├── parser.py           # lxml-based .yxmd loader
│       ├── exceptions.py       # ParseError hierarchy (MalformedXMLError, etc.)
│       ├── models/             # Frozen dataclasses (WorkflowDoc, DiffResult, ...)
│       ├── normalizer/         # C14N, GUID stripping, config hashing
│       ├── matcher/            # Two-pass ToolID + Hungarian matcher
│       ├── differ/             # DeepDiff-based node + edge differ
│       ├── pipeline/           # pipeline.run(DiffRequest) → DiffResponse facade
│       ├── renderers/          # HTMLRenderer, GraphRenderer, JSONRenderer
│       └── static/             # vis-network 9.1.4 UMD bundle (vendored)
├── tests/
│   ├── fixtures/               # Typed fixture libraries per phase (ToolID-allocated)
│   └── test_*.py               # 105 tests, 1 intentional xfail
└── pyproject.toml
```

### Running as a module

```bash
uv run python -m alteryx_diff workflow_v1.yxmd workflow_v2.yxmd
```

---

## Known Limitations

- **GUID stripping** — the GUID field name registry (`GUID_VALUE_KEYS`) is not yet populated with confirmed field names from real `.yxmd` files. If Alteryx embeds session GUIDs inside tool configuration fields, those may appear as false-positive config_hash differences. The stripping mechanism is in place; the field names need real-file validation.
- **Browser-interactive behaviors** — the HTML graph's click-to-diff panel, show-only-changes toggle, and fit-to-screen animation are structurally correct but require manual browser testing to confirm rendering.
- **`.yxmc` / `.yxapp` formats** — not supported; only `.yxmd` and `.yxwz` files.
- **Macro recursion** — tools that reference macros are diffed as opaque nodes; internal macro changes are not surfaced.

---

## Roadmap

| Version | Scope |
|---|---|
| v1.0 ✅ | CLI diff, HTML report, interactive graph, JSON output, ALCOA+ governance |
| v1.1 | Resolve JSON schema divergence; populate GUID field registry from real files |
| v2.0 | REST API (`POST /diff`), `.yxmc` / `.yxapp` support, macro recursion |
