# Architecture Research

**Domain:** Structured XML diff tool — CLI-first, API-evolution path
**Researched:** 2026-02-28
**Confidence:** MEDIUM-HIGH (pipeline patterns HIGH, graph matching MEDIUM, HTML embedding HIGH, CLI-API evolution HIGH)

---

## Standard Architecture

### System Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                        ENTRY POINTS                                    │
│                                                                        │
│  ┌──────────────────────┐       ┌──────────────────────────────────┐   │
│  │   CLI (Typer)        │       │   API (FastAPI) — Phase 3        │   │
│  │   acd diff a b       │       │   POST /diff {file_a, file_b}    │   │
│  └──────────┬───────────┘       └───────────────┬──────────────────┘   │
│             │                                   │                      │
│             └──────────────┬────────────────────┘                      │
└──────────────────────────  │  ─────────────────────────────────────────┘
                             │ DiffRequest (dataclass)
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       PIPELINE CORE                                   │
│                                                                        │
│  ┌────────────┐   WorkflowDoc   ┌─────────────┐   WorkflowDoc (norm)  │
│  │  Parser    │ ─────────────── │ Normalizer  │ ──────────────────    │
│  │            │                 │             │                    │   │
│  └────────────┘                 └─────────────┘                   │   │
│                                                                    ▼   │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                     Differ                                      │    │
│  │   NodeMatcher ──────────────────► MatchResult                 │    │
│  │   (bipartite Hungarian / ID-first hybrid)                      │    │
│  │                                    │                           │    │
│  │   EdgeDiffer ◄─────────────────────┘                          │    │
│  │                                    │                           │    │
│  │   DiffResult ◄─────────────────────┘                          │    │
│  └─────────────────────────────────┬──────────────────────────────┘    │
│                                    │ DiffResult                        │
│                                    ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Renderer                                     │   │
│  │   HTMLRenderer ──────────────────────────────► report.html      │   │
│  │   JSONRenderer ──────────────────────────────► summary.json     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `Parser` | Load .yxmd XML, validate structure, emit `WorkflowDoc` | Normalizer |
| `Normalizer` | Strip noise (positions, GUIDs, timestamps, whitespace), sort attributes, emit canonical `WorkflowDoc` | Differ |
| `NodeMatcher` | Match nodes between two `WorkflowDoc` instances using ID-first then similarity fallback | Differ (sub-component) |
| `Differ` | Produce `DiffResult` from two normalized `WorkflowDoc` instances | Renderer |
| `HTMLRenderer` | Accept `DiffResult`, render Jinja2 template with inlined D3.js/vis.js, emit single `.html` file | Consumer (filesystem / API response) |
| `JSONRenderer` | Accept `DiffResult`, emit machine-readable summary | Consumer |
| `CLI entry` | Parse arguments, call pipeline, write output files | Pipeline Core only |
| `API entry` | Parse HTTP request, call pipeline, return response body | Pipeline Core only |

---

## Recommended Project Structure

```
alteryx_diff/
├── acd/                          # Main package
│   ├── __init__.py
│   ├── cli.py                    # Typer app — thin entry point only
│   │
│   ├── models/                   # Immutable data structures (frozen dataclasses)
│   │   ├── __init__.py
│   │   ├── workflow.py           # WorkflowDoc, AlteryxNode, AlteryxConnection
│   │   └── diff_result.py        # DiffResult, NodeDiff, EdgeDiff, ChangeType
│   │
│   ├── parser/                   # Stage 1: XML → WorkflowDoc
│   │   ├── __init__.py
│   │   └── yxmd_parser.py        # lxml-based parser
│   │
│   ├── normalizer/               # Stage 2: WorkflowDoc → canonical WorkflowDoc
│   │   ├── __init__.py
│   │   └── normalizer.py         # Strip noise, sort, canonicalize
│   │
│   ├── differ/                   # Stage 3: (WorkflowDoc, WorkflowDoc) → DiffResult
│   │   ├── __init__.py
│   │   ├── node_matcher.py       # ID-first + similarity-based fallback matching
│   │   ├── node_differ.py        # Config-level diff per matched pair
│   │   └── edge_differ.py        # Connection add/remove/rewire detection
│   │
│   ├── renderer/                 # Stage 4: DiffResult → output
│   │   ├── __init__.py
│   │   ├── html_renderer.py      # Jinja2 + inlined D3/vis.js
│   │   ├── json_renderer.py      # Machine-readable summary
│   │   └── templates/
│   │       └── report.html.j2    # Main Jinja2 template
│   │
│   ├── pipeline.py               # Orchestrates all 4 stages; entry-point-agnostic
│   └── api/                      # Phase 3: FastAPI adapter (thin wrapper)
│       ├── __init__.py
│       └── routes.py
│
├── tests/
│   ├── fixtures/                 # Golden .yxmd pairs + expected DiffResult snapshots
│   │   ├── simple_add/
│   │   ├── config_change/
│   │   └── id_regeneration/
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_normalizer.py
│   │   ├── test_node_matcher.py
│   │   └── test_differ.py
│   ├── integration/
│   │   └── test_pipeline.py      # Full pipeline fixture-pairs → DiffResult assertions
│   └── snapshot/
│       └── test_html_output.py   # HTML report snapshot tests
│
└── pyproject.toml
```

### Structure Rationale

- **`models/` before everything:** All data structures defined first. Every stage speaks the same language. No cross-stage coupling except through these types.
- **`pipeline.py` as the single orchestrator:** CLI and API both call `pipeline.run(request)`. Neither knows the stage implementations. This is the hexagonal architecture "application service" pattern.
- **`renderer/templates/` embedded in package:** Template lives alongside the renderer, not in a separate assets folder. Single-file HTML output is produced by inlining JS/CSS at build time inside the template itself.
- **`tests/fixtures/` as versioned pairs:** Fixture-based testing dominates for this domain. Each subdirectory is a scenario: two `.yxmd` files + expected `DiffResult` JSON.

---

## Architectural Patterns

### Pattern 1: Immutable Pipeline with Typed Handoffs

**What:** Each stage transforms its input into a new immutable data structure. No stage mutates its input. Stages communicate only through well-defined typed boundaries.

**When to use:** Any multi-stage transformation pipeline where debugging "where did the data go wrong" is critical. Immutability means you can inspect each stage's output independently.

**Trade-offs:** Slightly more memory than in-place mutation; Python frozen dataclasses add minimal overhead. Worth it for debuggability and testability.

**Example:**
```python
from dataclasses import dataclass, field
from typing import FrozenSet, Tuple

@dataclass(frozen=True)
class AlteryxNode:
    tool_id: int
    tool_type: str           # e.g. "DbFileInput", "Filter"
    x: float                 # canvas position — kept for layout, not diffing
    y: float
    config_hash: str         # SHA-256 of normalized config XML — for fast change detection
    config_xml: str          # full canonical config string — for diff display

@dataclass(frozen=True)
class AlteryxConnection:
    src_tool_id: int
    src_anchor: str          # e.g. "Output", "True", "False"
    dst_tool_id: int
    dst_anchor: str          # e.g. "Input"

@dataclass(frozen=True)
class WorkflowDoc:
    path: str
    nodes: FrozenSet[AlteryxNode]
    connections: FrozenSet[AlteryxConnection]
```

### Pattern 2: ID-First, Similarity-Fallback Node Matching

**What:** Attempt to match nodes between two `WorkflowDoc` instances by `ToolID` first (O(n) exact lookup). For unmatched nodes on either side, compute a similarity score matrix and use `scipy.optimize.linear_sum_assignment` (Hungarian algorithm, O(n³)) to find minimum-cost bipartite matching.

**When to use:** Alteryx ToolIDs can regenerate on save — this is documented in the project constraints. Pure ID matching produces false add/remove pairs. Pure similarity matching is slow and inaccurate when IDs are stable. Hybrid is correct and fast for the common case.

**Trade-offs:** Adds `scipy` dependency. O(n³) is fine up to 500 nodes (~500³ = 125M ops, sub-second in C). For the rare case of 500 fully-regenerated IDs, worst-case is acceptable given the 5-second SLA.

**Similarity cost function:**
```python
def node_similarity_cost(a: AlteryxNode, b: AlteryxNode) -> float:
    """Lower = more similar. Returns cost for Hungarian assignment."""
    if a.tool_type != b.tool_type:
        return 1.0  # Maximum cost — different tool types should not match
    # Spatial proximity (normalized by canvas size ~10000 units)
    position_cost = (abs(a.x - b.x) + abs(a.y - b.y)) / 20000.0
    # Config similarity
    config_cost = 0.0 if a.config_hash == b.config_hash else 0.3
    return min(1.0, position_cost + config_cost)
```

**Example:**
```python
from scipy.optimize import linear_sum_assignment
import numpy as np

def match_nodes(
    nodes_a: list[AlteryxNode],
    nodes_b: list[AlteryxNode]
) -> list[tuple[AlteryxNode | None, AlteryxNode | None]]:
    # Stage 1: exact ToolID match
    ids_a = {n.tool_id: n for n in nodes_a}
    ids_b = {n.tool_id: n for n in nodes_b}
    matched = []
    unmatched_a, unmatched_b = [], []
    for id_, node_a in ids_a.items():
        if id_ in ids_b:
            matched.append((node_a, ids_b[id_]))
        else:
            unmatched_a.append(node_a)
    for id_, node_b in ids_b.items():
        if id_ not in ids_a:
            unmatched_b.append(node_b)
    # Stage 2: similarity-based matching for unmatched
    if unmatched_a and unmatched_b:
        cost_matrix = np.array([
            [node_similarity_cost(a, b) for b in unmatched_b]
            for a in unmatched_a
        ])
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] < 0.8:  # Threshold: reject implausible matches
                matched.append((unmatched_a[r], unmatched_b[c]))
            else:
                matched.append((unmatched_a[r], None))  # Treat as removed
                matched.append((None, unmatched_b[c]))  # Treat as added
    return matched
```

### Pattern 3: Canonical XML Normalization Before Hashing

**What:** Before any comparison, run `lxml.etree.canonicalize()` on each node's configuration XML subtree. C14N sorts attributes alphabetically, normalizes whitespace, and removes comments. Then SHA-256 hash the result for fast equality checks.

**When to use:** Always, before any config comparison. This eliminates the #1 and #2 sources of false positives: attribute reordering (Alteryx reorders attributes on save) and whitespace drift.

**Trade-offs:** C14N is slightly slower than raw string comparison but negligible at 500 nodes. The hash enables O(1) change detection — only nodes with hash mismatches need full config diffing.

**The normalization contract (what gets stripped vs. preserved):**

| Element | Default behavior | `--include-positions` |
|---------|-----------------|----------------------|
| `Position` attributes (`x`, `y`) | Stripped from diff | Included |
| Auto-generated GUIDs | Stripped | Stripped |
| Save timestamps | Stripped | Stripped |
| Attribute order | Sorted by C14N | Sorted by C14N |
| Whitespace in text nodes | Normalized | Normalized |
| Tool configuration values | Preserved | Preserved |

**Example:**
```python
import hashlib
from lxml import etree

def canonicalize_config(config_element: etree._Element) -> str:
    """Return canonical string of config XML, stripping position noise."""
    # Deep copy to avoid mutating the tree
    node = copy.deepcopy(config_element)
    # Strip known noise attributes
    NOISE_ATTRS = {"x", "y", "BrushColor", "lastModified", "createdAt"}
    for el in node.iter():
        for attr in NOISE_ATTRS:
            el.attrib.pop(attr, None)
    return etree.canonicalize(etree.tostring(node))

def config_hash(canonical_xml: str) -> str:
    return hashlib.sha256(canonical_xml.encode()).hexdigest()
```

### Pattern 4: Self-Contained HTML Report via Jinja2 Inlining

**What:** The Jinja2 template does NOT reference external CDN URLs. All JavaScript (D3.js or vis.js) and CSS are inlined into the template at render time by reading the library files from the package and injecting them as `<script>` and `<style>` blocks. Diff data is injected as a `const DIFF_DATA = {...}` JSON literal inside a `<script>` tag.

**When to use:** Required for offline-capable reports. Users who receive the HTML report via email or Git artifact must be able to open it without internet access.

**Trade-offs:** Report file size increases (~200–500KB for D3.js). Acceptable for a developer tool. Use `gzip` in the API path if needed.

**Example Jinja2 template pattern:**
```html
<!DOCTYPE html>
<html>
<head>
  <style>{{ css_content }}</style>
</head>
<body>
  <script>
    const DIFF_DATA = {{ diff_json | safe }};
  </script>
  <script>{{ d3_js_content }}</script>
  <script>{{ report_js_content }}</script>
</body>
</html>
```

**Python renderer:**
```python
from importlib.resources import files
from jinja2 import Environment, PackageLoader
import json

class HTMLRenderer:
    def __init__(self):
        self._env = Environment(loader=PackageLoader("acd", "renderer/templates"))
        # Load D3.js once at import time — it's static
        self._d3_js = files("acd").joinpath("renderer/static/d3.v7.min.js").read_text()
        self._report_css = files("acd").joinpath("renderer/static/report.css").read_text()
        self._report_js = files("acd").joinpath("renderer/static/report.js").read_text()

    def render(self, diff_result: DiffResult) -> str:
        template = self._env.get_template("report.html.j2")
        return template.render(
            diff_json=json.dumps(diff_result.to_dict()),
            d3_js_content=self._d3_js,
            css_content=self._report_css,
            report_js_content=self._report_js,
        )
```

### Pattern 5: Hexagonal Core — Shared Pipeline, Swappable Entry Points

**What:** The pipeline is a plain Python function (or class) that accepts a `DiffRequest` and returns a `DiffResult`. It has no knowledge of HTTP, file I/O, or CLI argument parsing. CLI and API are thin adapters that translate their input format into a `DiffRequest` and their output format from a `DiffResult`.

**When to use:** From day one, even in Phase 1. It costs nothing extra to write `pipeline.run()` as a pure function and call it from `cli.py`. The payoff is Phase 3 — the FastAPI route becomes 15 lines.

**The interface contract:**
```python
# acd/pipeline.py

@dataclass
class DiffRequest:
    path_a: str
    path_b: str
    include_positions: bool = False
    output_format: str = "html"  # "html" | "json" | "both"

@dataclass
class DiffResponse:
    diff_result: DiffResult
    html_report: str | None       # rendered HTML, if requested
    json_summary: dict | None     # rendered JSON, if requested
    error: str | None = None

def run(request: DiffRequest) -> DiffResponse:
    """Single entry point. No side effects — caller decides what to write where."""
    try:
        doc_a = parse(request.path_a)
        doc_b = parse(request.path_b)
        norm_a = normalize(doc_a, include_positions=request.include_positions)
        norm_b = normalize(doc_b, include_positions=request.include_positions)
        diff = diff_workflows(norm_a, norm_b)
        return DiffResponse(
            diff_result=diff,
            html_report=HTMLRenderer().render(diff) if "html" in request.output_format else None,
            json_summary=JSONRenderer().render(diff) if "json" in request.output_format else None,
        )
    except Exception as e:
        return DiffResponse(diff_result=None, html_report=None, json_summary=None, error=str(e))
```

**CLI adapter (thin):**
```python
# acd/cli.py
import typer
from acd.pipeline import DiffRequest, run

app = typer.Typer()

@app.command()
def diff(
    file_a: str = typer.Argument(..., help="Path to original .yxmd"),
    file_b: str = typer.Argument(..., help="Path to modified .yxmd"),
    output: str = typer.Option("diff_report.html", "--output", "-o"),
    include_positions: bool = typer.Option(False, "--include-positions"),
):
    response = run(DiffRequest(path_a=file_a, path_b=file_b, include_positions=include_positions))
    if response.error:
        typer.echo(f"Error: {response.error}", err=True)
        raise typer.Exit(1)
    if response.html_report:
        Path(output).write_text(response.html_report)
        typer.echo(f"Report written to {output}")
```

**Phase 3 API adapter (also thin):**
```python
# acd/api/routes.py
from fastapi import FastAPI, UploadFile
from acd.pipeline import DiffRequest, run

app = FastAPI()

@app.post("/diff")
async def diff_endpoint(file_a: UploadFile, file_b: UploadFile):
    # Write uploads to temp paths, call the same pipeline
    with tempfile.NamedTemporaryFile(suffix=".yxmd") as fa, \
         tempfile.NamedTemporaryFile(suffix=".yxmd") as fb:
        fa.write(await file_a.read()); fa.flush()
        fb.write(await file_b.read()); fb.flush()
        response = run(DiffRequest(path_a=fa.name, path_b=fb.name))
    if response.error:
        raise HTTPException(status_code=422, detail=response.error)
    return {"html_report": response.html_report, "summary": response.json_summary}
```

---

## Data Flow

### Primary Flow: CLI Invocation

```
User: acd diff workflow_v1.yxmd workflow_v2.yxmd
    │
    ▼
cli.py: parse args → build DiffRequest
    │
    ▼
pipeline.run(DiffRequest)
    │
    ├─ Parser.parse(path_a) → WorkflowDoc(nodes, connections, path)
    ├─ Parser.parse(path_b) → WorkflowDoc(nodes, connections, path)
    │
    ├─ Normalizer.normalize(doc_a) → WorkflowDoc (noise stripped, hashes computed)
    ├─ Normalizer.normalize(doc_b) → WorkflowDoc (noise stripped, hashes computed)
    │
    ├─ Differ.diff(norm_a, norm_b)
    │       │
    │       ├─ NodeMatcher.match() → MatchResult (pairs + unmatched)
    │       │      Phase 1: ID lookup O(n)
    │       │      Phase 2: Hungarian on unmatched O(n³)
    │       │
    │       ├─ NodeDiffer.diff_pair(a, b) per matched pair
    │       │      config_hash match → UNCHANGED (fast path)
    │       │      hash mismatch → canonicalize both → difflib.unified_diff → MODIFIED
    │       │
    │       ├─ EdgeDiffer.diff_edges(conn_a, conn_b)
    │       │      Compare frozensets → symmetric difference → ADDED / REMOVED
    │       │
    │       └─ Returns DiffResult
    │
    ├─ HTMLRenderer.render(diff_result) → html_str
    │
    └─ Returns DiffResponse
    │
cli.py: write html_str to output path
    │
    ▼
User: opens report.html in browser
```

### State That Flows Between Stages

| Boundary | Data Structure | Key Fields |
|----------|---------------|------------|
| Parser → Normalizer | `WorkflowDoc` | `nodes: FrozenSet[AlteryxNode]`, `connections: FrozenSet[AlteryxConnection]`, raw config XML |
| Normalizer → Differ | `WorkflowDoc` (canonical) | Same structure, but `config_xml` is C14N, `config_hash` populated, position data conditionally stripped |
| NodeMatcher → NodeDiffer | `MatchResult` | `matched: list[tuple[AlteryxNode, AlteryxNode]]`, `added: list[AlteryxNode]`, `removed: list[AlteryxNode]` |
| Differ → Renderer | `DiffResult` | `node_diffs: list[NodeDiff]`, `edge_diffs: list[EdgeDiff]`, `summary: DiffSummary` |

### Object Model for Alteryx Workflows

```
WorkflowDoc
├── nodes: FrozenSet[AlteryxNode]
│   └── AlteryxNode
│       ├── tool_id: int              # Primary key — may regenerate on Alteryx save
│       ├── tool_type: str            # "Filter", "DbFileInput", etc. — stable
│       ├── x: float                  # Canvas X — layout only, stripped in diff
│       ├── y: float                  # Canvas Y — layout only, stripped in diff
│       ├── config_hash: str          # SHA-256(canonicalize(config_xml))
│       └── config_xml: str           # Canonical config XML string
│
└── connections: FrozenSet[AlteryxConnection]
    └── AlteryxConnection
        ├── src_tool_id: int
        ├── src_anchor: str           # "Output", "True", "False", "Error"
        ├── dst_tool_id: int
        └── dst_anchor: str           # "Input"
```

---

## Testing Strategy

### Fixture-Based Testing (Primary Approach)

Fixture pairs are versioned `.yxmd` files in `tests/fixtures/`. Each scenario tests one behavior. The fixture is the ground truth — assertions compare actual `DiffResult` against hand-verified expected output.

**Recommended fixture scenarios:**

| Scenario | Tests |
|----------|-------|
| `no_changes/` | Parser + normalizer + differ all return zero diffs |
| `tool_added/` | Correctly classified as ADDED |
| `tool_removed/` | Correctly classified as REMOVED |
| `config_change_filter/` | Filter expression change detected, positions ignored |
| `position_only_drift/` | Zero diffs with default flags, diffs present with `--include-positions` |
| `connection_rewire/` | Source anchor change detected |
| `id_regeneration/` | All IDs changed, tools matched by type+position, config preserved |
| `whitespace_only/` | Zero diffs — normalizer strips whitespace noise |
| `attribute_reorder/` | Zero diffs — C14N sorts attributes before comparison |
| `guid_injection/` | Zero diffs — GUID fields stripped by normalizer |

### Snapshot Testing for HTML Output

Use `pytest-snapshot` to catch regression in HTML report rendering. Snapshot tests verify the full rendered HTML against a stored baseline. Update snapshots explicitly with `--snapshot-update`.

### Property-Based Testing (Supplementary, for Normalizer)

Use `hypothesis` to verify normalizer invariants:
- "Any permutation of node attributes produces the same config hash" — verifies C14N correctness
- "Stripping position attributes twice is idempotent" — verifies normalizer safety

Property tests catch edge cases in canonicalization that fixture tests miss. They are supplementary, not primary.

### Unit Test Boundaries

| Stage | What to test | What NOT to test |
|-------|-------------|-----------------|
| Parser | Correct extraction of ToolID, type, x, y, config, connections from sample XML | Normalization (different stage) |
| Normalizer | Hash stability across attribute permutations; position stripping; GUID removal | Parsing or diffing |
| NodeMatcher | Correct match pairs for stable IDs; correct fallback for regenerated IDs; threshold rejection | Config diffing |
| Differ | Correct ChangeType for each pair type; edge rewire detection | HTML rendering |
| Renderer | Valid HTML output; D3 data injected correctly; no CDN references in output | Pipeline orchestration |

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Phase 1 CLI: 1-500 nodes | Single-process, in-memory, synchronous. No persistence. |
| Phase 3 API: concurrent requests | FastAPI async endpoints + `run_in_executor` for CPU-bound pipeline stages. No shared state — each request gets a fresh pipeline execution. |
| Phase 3 API: large workflows (1000+ nodes) | Hungarian algorithm O(n³) on 1000 fully-unmatched nodes could hit ~1B ops. Mitigation: type-group matching (only match nodes of same tool_type against each other). Reduces problem size by tool-type frequency. |
| SaaS: multi-tenant | Add request ID, user context to `DiffRequest`. Pipeline core remains stateless. Storage of reports moves to object store (S3). API layer handles auth. |

### Scaling Priorities

1. **First bottleneck:** Hungarian matching on large fully-regenerated ID sets. Fix: apply type-group constraint before cost matrix construction — reduces O(n³) to O((n/k)³) where k = number of tool types.
2. **Second bottleneck:** HTML rendering with 500 nodes — D3.js force simulation on 500 nodes is fast in-browser but the JSON embedded in the report grows. Fix: separate compact summary JSON from full config diff payload; lazy-load per-node config diff on click.

---

## Anti-Patterns

### Anti-Pattern 1: Diffing Raw XML Text Directly

**What people do:** Run `diff` or `difflib` on the raw `.yxmd` XML bytes. Ship that as the output.

**Why it's wrong:** Attribute reordering, whitespace drift, and GUID injection produce massive false-positive diff output. Every Alteryx save touches 10–30% of XML lines without functional change. This is the exact problem the normalizer exists to solve.

**Do this instead:** Parse → normalize (C14N) → diff the canonical representation. Never compare raw XML.

### Anti-Pattern 2: Using ToolID as the Only Matching Key

**What people do:** Build a dict keyed by `ToolID`, compare dict entries. If a `ToolID` is missing in one version, mark it as ADDED or REMOVED.

**Why it's wrong:** Alteryx regenerates ToolIDs on some save operations. A workflow with 50 tools can change all 50 IDs while being functionally identical. Pure ID matching produces 50 false REMOVED + 50 false ADDED entries.

**Do this instead:** ID-first matching with similarity-fallback. Accept the complexity of a two-phase matcher — it is the only correct approach for this domain.

### Anti-Pattern 3: Position in the Diff Signal

**What people do:** Include X/Y coordinates in the config hash or in the change detection logic.

**Why it's wrong:** Canvas position drift (tools nudged by a few pixels when the canvas reflows) is the #1 source of false positives in Alteryx diffs. Every time a large workflow is opened and closed, positions shift.

**Do this instead:** Parse positions for graph layout. Exclude them from the canonical config hash. Provide `--include-positions` as an explicit opt-in for teams that actually need it.

### Anti-Pattern 4: Coupling Pipeline to Entry Point

**What people do:** Write the diff logic inside the Typer command callback. When Phase 3 needs an API, duplicate the logic in the FastAPI route.

**Why it's wrong:** Logic diverges. Bugs are fixed in one place but not the other. Testing requires mocking CLI invocation.

**Do this instead:** `pipeline.run(DiffRequest) → DiffResponse`. CLI and API are 20-line adapters. All logic and all tests live in the pipeline.

### Anti-Pattern 5: External CDN References in HTML Report

**What people do:** Reference `https://cdn.jsdelivr.net/npm/d3@7/...` in the report template.

**Why it's wrong:** The report fails for users without internet access. Corporate firewalls block CDN traffic. The report becomes permanently broken when the CDN URL changes or expires.

**Do this instead:** Bundle D3.js (or vis.js) as a package resource and inline it into the template at render time. The report is a single, self-contained `.html` file that works offline forever.

---

## Suggested Build Order

Build order follows data flow dependencies. Each stage can be tested independently before the next is built.

```
Step 1: Models
  Define WorkflowDoc, AlteryxNode, AlteryxConnection, DiffResult, NodeDiff, EdgeDiff
  (No dependencies. Define these before writing a line of logic.)

Step 2: Parser
  Implement yxmd_parser.py producing WorkflowDoc from .yxmd path
  Test: unit tests with raw XML snippets

Step 3: Normalizer
  Implement normalizer.py (C14N, noise stripping, hash computation)
  Test: unit tests verifying hash stability across XML permutations

Step 4: NodeMatcher
  Implement ID-first + Hungarian fallback
  Test: unit tests with controlled node sets (known IDs, known positions, known types)

Step 5: Differ (NodeDiffer + EdgeDiffer)
  Wire NodeMatcher output into full DiffResult production
  Test: integration with fixture pairs — verify ChangeType correctness

Step 6: pipeline.py
  Wire all stages. Define DiffRequest / DiffResponse.
  Test: full pipeline integration tests against all fixture scenarios

Step 7: JSONRenderer
  Simpler output format. Build before HTML renderer.
  Test: snapshot tests on JSON output

Step 8: HTMLRenderer + Template
  Jinja2 template with inlined D3.js graph + color-coded summary
  Test: snapshot tests on rendered HTML; manual browser review

Step 9: CLI entry point
  Thin Typer adapter over pipeline.run()
  Test: Typer test runner invocation; end-to-end CLI smoke tests
```

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Alteryx Server (Phase 3) | Webhook → POST /diff endpoint | Server calls API on workflow promotion. Requires authentication layer. |
| Git / GitHub Actions (Phase 3) | CI step calls CLI; output posted as PR comment via gh CLI | Same pipeline, different invocation. |
| Alteryx Designer (Phase 4+, out of scope) | Plugin API — entirely different architecture | Not in scope for phases 1–3 |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| cli.py ↔ pipeline.py | Function call: `run(DiffRequest)` | No HTTP, no subprocess, no serialization overhead |
| api/routes.py ↔ pipeline.py | Same function call: `run(DiffRequest)` | API adapter writes temp files, calls same function |
| pipeline.py ↔ renderer/ | `DiffResult` dataclass | Renderer is pure function: takes `DiffResult`, returns `str` |
| renderer/ ↔ templates/ | Jinja2 `Environment` with `PackageLoader` | Template files are package resources, not filesystem paths |

---

## Sources

- [xmldiff Python library — architecture and API](https://xmldiff.readthedocs.io/en/stable/api.html) — MEDIUM confidence (verified via official docs)
- [lxml C14N canonicalization API](https://lxml.de/api.html) — HIGH confidence (official docs, confirmed attribute sorting behavior)
- [NetworkX bipartite minimum_weight_full_matching](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.bipartite.matching.minimum_weight_full_matching.html) — HIGH confidence (official docs)
- [NodeGit: Diffing and Merging Node Graphs (ACM SIGGRAPH 2023)](https://dl.acm.org/doi/10.1145/3618343) — MEDIUM confidence (abstract-level; full paper paywalled)
- [FastAPI layered architecture — sqr-072 LSST pattern](https://sqr-072.lsst.io/) — HIGH confidence (detailed architecture document, verified)
- [Pyvis HTML generation and cdn_resources inline option](https://pyvis.readthedocs.io/en/latest/tutorial.html) — MEDIUM confidence (official docs, inline option confirmed)
- [pytest-snapshot snapshot testing](https://pypi.org/project/pytest-snapshot/) — HIGH confidence (official PyPI page)
- [hypothesis property-based testing with pytest](https://hypothesis.works/articles/hypothesis-pytest-fixtures/) — HIGH confidence (official Hypothesis documentation)
- [scipy.optimize.linear_sum_assignment (Hungarian algorithm)](https://docs.scipy.org/doc/scipy-0.18.1/reference/generated/scipy.optimize.linear_sum_assignment.html) — HIGH confidence (official SciPy docs)
- [Alteryx XML structure — Community discussion](https://community.alteryx.com/t5/Alteryx-Designer-Desktop-Discussions/XML-to-Workflow-Understanding/td-p/1160582) — MEDIUM confidence (community source, consistent with PROJECT.md constraints)

---

*Architecture research for: Alteryx Canvas Diff (XML diff tool, CLI-first, API-evolution path)*
*Researched: 2026-02-28*
