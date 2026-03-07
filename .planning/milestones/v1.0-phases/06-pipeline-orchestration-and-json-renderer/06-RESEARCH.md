# Phase 6: Pipeline Orchestration and JSON Renderer - Research

**Researched:** 2026-03-05
**Domain:** Python pipeline facade pattern, dataclass serialization, JSON output, CLI flag extension
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**DiffRequest/DiffResponse shape:**
- `DiffRequest` contains only the two paths (`path_a`, `path_b`) — no config or output options
- `DiffResponse` is a thin dataclass wrapper: `DiffResponse(result: DiffResult)` — clean named return type, extensible without changing call sites
- Errors surface as raised exceptions — no error field on `DiffResponse`
- Pipeline module location: Claude's discretion based on existing codebase structure

**JSON output schema:**
- Top-level structure: `{ summary: { added, removed, modified, connections }, tools: [{ tool_name, changes: [...] }], connections: [...] }`
- Each per-tool change record includes: `id`, `display_name`, `change_type` (added/removed/modified)
- Connection changes live under a separate top-level `connections` key — they span tools and belong at the top level
- Schema documented as an inline docstring on `JSONRenderer` — no separate schema file

**--json flag behavior:**
- When `--json` is used, produce **both** `.html` and `.json` — no information lost
- JSON filename uses the same base name as the HTML report with `.json` extension (e.g., `diff_report.html` → `diff_report.json`)
- File output only — no stdout streaming
- CLI prints a confirmation message for the JSON file in the same style as the HTML confirmation

**Error handling in pipeline:**
- `pipeline.run()` raises exceptions — caller catches what it cares about (Pythonic)
- Exception types: Claude's discretion — check existing codebase, reuse or extend appropriately
- CLI catches pipeline exceptions at the boundary, prints a human-friendly error message, and exits with code 1
- If any tool's file fails to parse, the pipeline fails entirely — no partial/silent results

### Claude's Discretion
- Pipeline module file location within the codebase
- Exception class design (new typed exceptions vs. reusing existing ones)
- Exact progress/confirmation message wording for JSON output

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-03 | User can generate a JSON summary alongside or instead of the HTML report via `--json` flag, enabling CI/CD integration | Pipeline module wraps Phases 2-5 into `pipeline.run(DiffRequest) -> DiffResponse`; `JSONRenderer` serializes `DiffResult` to the locked schema; `--json` flag produces `.json` file alongside `.html`; a unit test confirms pipeline is entry-point-agnostic (no CLI import) |
</phase_requirements>

## Summary

Phase 6 builds two things that together satisfy CLI-03: a **pipeline facade** and a **JSON renderer**. The pipeline facade is a thin module (`pipeline.run(DiffRequest) -> DiffResponse`) that chains the five already-built stages — parse, normalize, match, diff — into a single callable with no side effects. The JSON renderer is a class (`JSONRenderer`) that serializes a `DiffResult` into the locked schema. A `--json` flag on the CLI connects both: it calls `pipeline.run()`, feeds the result to `JSONRenderer`, and writes the `.json` file alongside the `.html`.

The critical design insight is that the pipeline facade must be importable without any CLI or rendering concern — enforced by a unit test that does `from alteryx_diff.pipeline import run` with zero mention of `argparse`, `typer`, `sys`, or `print`. The existing four pipeline stages (parser, normalizer, matcher, differ) each expose a clean pure-function interface with no I/O, so composing them into a facade is straightforward. The `DiffRequest`/`DiffResponse` dataclasses follow the project-wide `frozen=True, kw_only=True, slots=True` pattern.

JSON serialization needs careful design because `DiffResult` contains `AlteryxNode` and `EdgeDiff` dataclasses (not directly JSON-serializable). The serializer must traverse the domain types and build Python dicts before calling `json.dumps`. The locked schema groups per-tool changes (added/removed/modified) and separates connections at the top level — this structure differs from the flat `DiffResult` internal model, so a deliberate mapping step is required. The `JSONRenderer` class is the right abstraction: it owns this mapping and documents the schema in its docstring.

**Primary recommendation:** Create `src/alteryx_diff/pipeline/` package with `pipeline.py` exposing `run(DiffRequest) -> DiffResponse`, `DiffRequest`, and `DiffResponse`. Create `src/alteryx_diff/renderers/json_renderer.py` with `JSONRenderer` class. Add `--json` flag to the future CLI entry point (or to a thin stub for this phase). Write a unit test that imports `pipeline.run` without any CLI import.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | 3.11+ | `DiffRequest`, `DiffResponse` value objects | Matches every other pipeline type in this codebase (`frozen=True, kw_only=True, slots=True`) |
| Python stdlib `json` | 3.11+ | `json.dumps` to produce JSON output | Already used in normalizer for canonical serialization; stdlib, zero dependencies |
| Python stdlib `pathlib` | 3.11+ | `Path` for file I/O in pipeline and JSON writer | Already used throughout (`parser.py` takes `pathlib.Path`) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `typing` | 3.11+ | Type annotations in pipeline and renderer | Already used project-wide |
| `alteryx_diff.parser` | internal | Parse step in pipeline | Only import inside `pipeline.py` |
| `alteryx_diff.normalizer` | internal | Normalize step in pipeline | Only import inside `pipeline.py` |
| `alteryx_diff.matcher` | internal | Match step in pipeline | Only import inside `pipeline.py` |
| `alteryx_diff.differ` | internal | Diff step in pipeline | Only import inside `pipeline.py` |
| `alteryx_diff.exceptions` | internal | `ParseError` reuse — pipeline surfaces existing exceptions | No new exception class needed for parse failures |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `json.dumps` with a custom serializer | `pydantic` or `attrs` with export methods | Zero-dep stdlib is sufficient; adding pydantic just for serialization is excessive overhead for a 3-field schema |
| `DiffResponse` thin dataclass wrapper | Return `DiffResult` directly | Wrapper provides a stable public API surface — `pipeline.run()` callers never have to change their call site if the return type evolves |
| Separate `renderers/` package | Single `renderer.py` file or inline in CLI | Phase 7 adds `HTMLRenderer`, so establishing a `renderers/` package now avoids refactoring later |

**Installation:**
```bash
# No new dependencies — stdlib only
# All existing deps (lxml, scipy, deepdiff) already in pyproject.toml
```

## Architecture Patterns

### Recommended Project Structure
```
src/alteryx_diff/
├── pipeline/
│   ├── __init__.py          # Public surface: run(), DiffRequest, DiffResponse
│   └── pipeline.py          # Implementation — chains parse/normalize/match/diff
├── renderers/
│   ├── __init__.py          # Public surface: JSONRenderer
│   └── json_renderer.py     # JSONRenderer class with render(DiffResult) -> str
tests/
├── fixtures/
│   └── pipeline.py          # Minimal .yxmd bytes for end-to-end pipeline tests (ToolIDs start at 601)
└── test_pipeline.py         # 4-5 tests: happy path, no-diff, exceptions, entry-point-agnostic
```

**Convention notes from existing codebase:**
- `__init__.py` is the sole public surface per project convention
- One public entry point per package (`parse`, `normalize`, `match`, `diff`, now `run`)
- `from __future__ import annotations` at the top of every module
- All model types imported from `alteryx_diff.models` (never sub-modules)
- `frozen=True, kw_only=True, slots=True` for all new dataclasses (except when `@property` is needed)
- `zip(..., strict=True)` enforced by ruff B905
- Fixture ToolIDs: Phase 5 uses 401-499. Phase 6 fixtures must start at 601.
- Tests use minimal inline fixture bytes — no real `.yxmd` files on disk; fixtures are Python constants

### Pattern 1: DiffRequest / DiffResponse Dataclasses

**What:** Thin value objects wrapping the two path inputs and the output result. Follow project-wide frozen dataclass pattern.
**When to use:** Always — these are the public API types for `pipeline.run()`.

```python
# src/alteryx_diff/pipeline/pipeline.py
from __future__ import annotations

import pathlib
from dataclasses import dataclass

from alteryx_diff.models import DiffResult


@dataclass(frozen=True, kw_only=True, slots=True)
class DiffRequest:
    """Input to pipeline.run(): paths to two .yxmd files to compare."""

    path_a: pathlib.Path
    path_b: pathlib.Path


@dataclass(frozen=True, kw_only=True, slots=True)
class DiffResponse:
    """Output of pipeline.run(): the completed DiffResult."""

    result: DiffResult
```

**Key design note:** `DiffRequest` holds only paths — no output format, no flags. The pipeline is entry-point-agnostic. `DiffResponse` wraps `DiffResult` so `pipeline.run()` has a stable named return type.

### Pattern 2: Pipeline Facade Function

**What:** A single `run()` function that chains parse → normalize → match → diff in order. Pure orchestration — no I/O except reading the two input files (delegated to `parser.parse()`).
**When to use:** All callers — CLI, unit tests, future API.

```python
# src/alteryx_diff/pipeline/pipeline.py
from alteryx_diff.differ import diff
from alteryx_diff.matcher import match
from alteryx_diff.normalizer import normalize
from alteryx_diff.parser import parse


def run(request: DiffRequest) -> DiffResponse:
    """Execute the full diff pipeline for two .yxmd files.

    Raises:
        MissingFileError: If either path does not exist.
        UnreadableFileError: If either path exists but cannot be read.
        MalformedXMLError: If either file contains invalid XML.

    Does NOT call sys.exit(), print(), or perform any file I/O beyond
    reading the two input .yxmd files via parser.parse().
    """
    doc_a, doc_b = parse(request.path_a, request.path_b)
    norm_a = normalize(doc_a)
    norm_b = normalize(doc_b)
    match_result = match(list(norm_a.nodes), list(norm_b.nodes))
    diff_result = diff(match_result, doc_a.connections, doc_b.connections)
    return DiffResponse(result=diff_result)
```

**Key design note:** `parse()` takes `pathlib.Path` arguments (confirmed from `parser.py` signature). `normalize()` takes `WorkflowDoc`. `match()` takes `list[NormalizedNode]` (from `matcher.py` signature: `match(old_nodes: list[NormalizedNode], new_nodes: list[NormalizedNode])`). `diff()` takes `MatchResult` plus the **original** `WorkflowDoc.connections` — not the normalized connections — to preserve edge identity from each workflow's own connection set.

### Pattern 3: JSONRenderer Class

**What:** A class with a single public method `render(result: DiffResult) -> str` that maps `DiffResult` domain types to the locked JSON schema.
**When to use:** Whenever JSON output is needed — CLI `--json` flag, future API response body.

```python
# src/alteryx_diff/renderers/json_renderer.py
from __future__ import annotations

import json
from typing import Any

from alteryx_diff.models import AlteryxNode, DiffResult, EdgeDiff, NodeDiff


class JSONRenderer:
    """Serialize a DiffResult to a JSON string matching the ACD diff schema.

    Schema (documented here, no separate schema file per CONTEXT.md):

    {
      "summary": {
        "added": <int>,       // count of added tools
        "removed": <int>,     // count of removed tools
        "modified": <int>,    // count of modified tools
        "connections": <int>  // count of connection changes (added + removed edges)
      },
      "tools": [
        {
          "tool_name": <str>,    // tool_type from AlteryxNode (e.g. "AlteryxBasePluginsGui.Filter")
          "changes": [
            {
              "id": <int>,           // ToolID as int
              "display_name": <str>, // tool_type (same as tool_name for now)
              "change_type": <str>   // "added" | "removed" | "modified"
            }
          ]
        }
      ],
      "connections": [
        {
          "src_tool": <int>,    // ToolID as int
          "src_anchor": <str>,
          "dst_tool": <int>,    // ToolID as int
          "dst_anchor": <str>,
          "change_type": <str>  // "added" | "removed"
        }
      ]
    }
    """

    def render(self, result: DiffResult) -> str:
        """Serialize result to a JSON string. Returns valid JSON."""
        payload = self._build_payload(result)
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _build_payload(self, result: DiffResult) -> dict[str, Any]:
        summary = {
            "added": len(result.added_nodes),
            "removed": len(result.removed_nodes),
            "modified": len(result.modified_nodes),
            "connections": len(result.edge_diffs),
        }
        tools = self._build_tools(result)
        connections = [self._edge_to_dict(e) for e in result.edge_diffs]
        return {"summary": summary, "tools": tools, "connections": connections}

    def _build_tools(self, result: DiffResult) -> list[dict[str, Any]]:
        # Group all per-tool changes by tool_type
        from collections import defaultdict
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for node in result.added_nodes:
            groups[node.tool_type].append(self._node_to_change(node, "added"))
        for node in result.removed_nodes:
            groups[node.tool_type].append(self._node_to_change(node, "removed"))
        for nd in result.modified_nodes:
            groups[nd.old_node.tool_type].append(
                self._node_diff_to_change(nd)
            )

        return [
            {"tool_name": tool_type, "changes": changes}
            for tool_type, changes in sorted(groups.items())
        ]

    def _node_to_change(self, node: AlteryxNode, change_type: str) -> dict[str, Any]:
        return {
            "id": int(node.tool_id),
            "display_name": node.tool_type,
            "change_type": change_type,
        }

    def _node_diff_to_change(self, nd: NodeDiff) -> dict[str, Any]:
        return {
            "id": int(nd.tool_id),
            "display_name": nd.old_node.tool_type,
            "change_type": "modified",
        }

    def _edge_to_dict(self, edge: EdgeDiff) -> dict[str, Any]:
        return {
            "src_tool": int(edge.src_tool),
            "src_anchor": edge.src_anchor,
            "dst_tool": int(edge.dst_tool),
            "dst_anchor": edge.dst_anchor,
            "change_type": edge.change_type,
        }
```

**Key design note:** `ToolID` is a `NewType` wrapping `int`. It must be cast with `int(node.tool_id)` before `json.dumps` — `json.dumps` accepts `int` but `NewType` aliases are transparently `int` at runtime, so this works. `AnchorName` is a `NewType` wrapping `str` — similarly transparent at runtime.

### Pattern 4: JSON File Writing (CLI Integration)

**What:** Convert the JSON renderer output to a file alongside the HTML report. The JSON path is derived from the HTML path by changing the suffix.
**When to use:** CLI `--json` flag handler, after pipeline completes.

```python
# In the CLI handler (future Phase 9 or stub for Phase 6)
import pathlib

html_path = pathlib.Path("diff_report.html")  # existing output path
json_path = html_path.with_suffix(".json")

renderer = JSONRenderer()
json_text = renderer.render(response.result)
json_path.write_text(json_text, encoding="utf-8")
print(f"JSON report written to {json_path}")  # same style as HTML confirmation
```

**Key design note:** `Path.with_suffix(".json")` is the correct stdlib method (confirmed: `pathlib.Path("diff_report.html").with_suffix(".json")` → `PosixPath('diff_report.json')`). No string manipulation needed.

### Pattern 5: Entry-Point-Agnostic Unit Test

**What:** A unit test that imports `pipeline.run` directly and calls it with `pathlib.Path` args pointing to minimal in-memory `.yxmd` byte fixtures. No CLI import anywhere in the test file.
**When to use:** As the required success-criterion test (SC 4 in phase description).

```python
# tests/test_pipeline.py
from __future__ import annotations

import pathlib
import tempfile

from alteryx_diff.pipeline import DiffRequest, DiffResponse, run
from alteryx_diff.models import DiffResult


def test_pipeline_run_returns_diff_response(tmp_path: pathlib.Path) -> None:
    """pipeline.run() returns DiffResponse — no CLI import anywhere in this file."""
    path_a = tmp_path / "a.yxmd"
    path_b = tmp_path / "b.yxmd"
    path_a.write_bytes(MINIMAL_YXMD_A)
    path_b.write_bytes(MINIMAL_YXMD_B)

    response = run(DiffRequest(path_a=path_a, path_b=path_b))

    assert isinstance(response, DiffResponse)
    assert isinstance(response.result, DiffResult)
```

**Key design note:** pytest's `tmp_path` fixture provides a temporary directory — no manual cleanup. The test writes minimal `.yxmd` XML bytes (constants in `tests/fixtures/pipeline.py`) to disk and calls `run()`. The absence of `import argparse`, `import typer`, `import sys`, and `import alteryx_diff.cli` anywhere in `test_pipeline.py` satisfies SC 4.

### Pattern 6: Pipeline __init__.py Export Convention

**What:** `pipeline/__init__.py` re-exports `run`, `DiffRequest`, `DiffResponse` — following the exact same pattern as `normalizer/__init__.py`, `matcher/__init__.py`, `differ/__init__.py`.

```python
# src/alteryx_diff/pipeline/__init__.py
"""Pipeline orchestration stage for alteryx_diff.

Public surface: run(), DiffRequest, DiffResponse

  from alteryx_diff.pipeline import run, DiffRequest, DiffResponse
  response = run(DiffRequest(path_a=path_a, path_b=path_b))
"""

from alteryx_diff.pipeline.pipeline import DiffRequest, DiffResponse, run

__all__ = ["run", "DiffRequest", "DiffResponse"]
```

### Anti-Patterns to Avoid

- **Importing `sys`, `print`, or CLI modules inside `pipeline.py`:** The pipeline must be callable from anywhere. A unit test explicitly verifies no CLI import. Any `sys.exit()` or `print()` call in `pipeline.py` is a defect.
- **Calling `normalize()` on already-normalized nodes:** `normalize()` takes a `WorkflowDoc`, not a `NormalizedWorkflowDoc`. Pass `doc_a`/`doc_b` (from parser output), not `norm_a`/`norm_b`.
- **Passing `norm_a.connections` to `diff()`:** The `diff()` function takes the original `WorkflowDoc.connections` — not the normalized collections — for correct edge identity. The correct call is `diff(match_result, doc_a.connections, doc_b.connections)`.
- **Putting `DiffRequest`/`DiffResponse` in `models/`:** These are pipeline-layer types, not domain model types. They belong in `pipeline/pipeline.py` alongside `run()`. Putting them in `models/` would couple the domain model to the pipeline API.
- **Hand-rolling JSON serialization with string concatenation:** Use `json.dumps` with a dict payload. String concatenation breaks on special characters in tool names or field values.
- **Using `json.dumps(default=str)` as a catch-all:** This silently converts non-serializable types to strings (including `ToolID` and `AnchorName` NewType values). Instead, explicitly cast with `int()` and `str()` in the serializer methods. Using `default=str` would hide serialization bugs.
- **Nesting connection changes under tools:** The locked schema places connections at the top-level `connections` key — not grouped under individual tools. Connection changes span tools and belong at the top level.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization of domain types | Custom `__json__` methods on dataclasses | `JSONRenderer` mapping to plain dicts + `json.dumps` | Dataclasses are frozen; adding serialization concerns to domain models violates separation of concerns; one explicit renderer is easier to test and modify |
| JSON path derivation from HTML path | String replacement (`".html"` → `".json"`) | `pathlib.Path.with_suffix(".json")` | `with_suffix` handles edge cases (no extension, multiple dots); stdlib, zero risk |
| Pipeline result error union type | `result: DiffResult | str` error field | Raise exceptions (Pythonic) | Python convention: use exceptions for errors, not union return types; existing `ParseError` hierarchy already defines the exception types callers need to catch |

**Key insight:** The `JSONRenderer` pattern (one class, one `render()` method, explicit dict-building) is the Python standard for "build a data payload, then serialize it." The alternative (attaching `to_dict()` methods to every domain model) spreads serialization concerns across the codebase and makes it harder to support multiple output formats (JSON vs HTML vs future formats).

## Common Pitfalls

### Pitfall 1: match() Expects list, not tuple
**What goes wrong:** `match(norm_a.nodes, norm_b.nodes)` raises `TypeError` or mypy error because `NormalizedWorkflowDoc.nodes` is `tuple[NormalizedNode, ...]` but `match()` signature is `match(old_nodes: list[NormalizedNode], new_nodes: list[NormalizedNode])`.
**Why it happens:** The normalizer and model use tuples (immutable, project-wide convention), but the matcher was implemented accepting lists (likely for internal mutation during pass 2).
**How to avoid:** Call `match(list(norm_a.nodes), list(norm_b.nodes))` in `pipeline.run()`. The `list()` conversion is O(n) and correct.
**Warning signs:** `mypy` error `Argument 1 to "match" has incompatible type "tuple[NormalizedNode, ...]"; expected "list[NormalizedNode]"`.

### Pitfall 2: ToolID / AnchorName NewTypes Are int/str at Runtime But Require Explicit Conversion for json.dumps
**What goes wrong:** `json.dumps({"id": tool_id})` where `tool_id` is `ToolID` — works at runtime (NewType is transparent) but mypy `--strict` may flag it, and explicit `int()` cast makes intent clear.
**Why it happens:** `NewType` creates a distinct type at static analysis time but is just the base type at runtime. `json.dumps` only checks the runtime type.
**How to avoid:** Always use `int(node.tool_id)` and `str(edge.src_anchor)` in the renderer's dict-building methods. Explicit casts document the intent and satisfy mypy strict mode.
**Warning signs:** mypy error `Argument has type "ToolID"; expected "int"` in renderer methods.

### Pitfall 3: diff() Uses original WorkflowDoc.connections, not NormalizedWorkflowDoc.connections
**What goes wrong:** Using `norm_a.connections` instead of `doc_a.connections` produces identical results for simple cases (connections pass through normalization unchanged) but is semantically wrong. Future normalization changes that filter connections could silently break the pipeline.
**Why it happens:** `NormalizedWorkflowDoc.connections` is a passthrough copy of `WorkflowDoc.connections`, so the bug is hidden in tests.
**How to avoid:** Always pass `doc_a.connections` and `doc_b.connections` (the outputs from `parse()`) to `diff()`. The `diff()` function signature uses `AlteryxConnection`, which is the connection type on `WorkflowDoc`, not on `NormalizedWorkflowDoc`.
**Warning signs:** Tests pass but code review catches the wrong source variable.

### Pitfall 4: Circular Import If Pipeline Imports from CLI Layer
**What goes wrong:** `pipeline.py` imports from a CLI or `__main__` module → `ImportError` or circular dependency when tests import `pipeline`.
**Why it happens:** Phase 6 adds a `--json` flag, which is CLI territory. If the flag's handler code is placed inside `pipeline.py` instead of the CLI layer, the pipeline gains a CLI dependency.
**How to avoid:** `pipeline.py` contains zero imports from CLI, `__main__`, `argparse`, or `typer`. The `--json` flag logic (writing the file, printing confirmation) lives in the CLI entry point only. `pipeline.run()` returns `DiffResponse` and does nothing else.
**Warning signs:** Any `import sys`, `import argparse`, or `from alteryx_diff.__main__` inside `pipeline/`.

### Pitfall 5: JSON Schema Mismatch — connections Count in Summary
**What goes wrong:** `summary.connections` is set to the total number of `EdgeDiff` entries (both added and removed), but caller expects only one type.
**Why it happens:** Ambiguity in "connection changes count" — could mean "changed connections" (pairs) or "total edge diff events."
**How to avoid:** Per the locked schema, `summary.connections` = `len(result.edge_diffs)` (all edge diff events: added + removed). This is the total count of connection change records in the `connections` array. Keep it consistent: `len(result.edge_diffs)` == `len(connections array)`.
**Warning signs:** `summary.connections` != `len(payload["connections"])`.

### Pitfall 6: tools Array Grouping — Modified Node Uses old_node.tool_type
**What goes wrong:** A `NodeDiff` entry for a modified node uses `nd.new_node.tool_type` instead of `nd.old_node.tool_type` for the `tool_name` grouping key.
**Why it happens:** Both old and new nodes have the same `tool_type` for modifications (tool type never changes — only config changes). Using `new_node.tool_type` is technically identical but semantically inconsistent.
**How to avoid:** Consistently use `nd.old_node.tool_type` for modified nodes — the "old" tool is the identity anchor. Added nodes use `node.tool_type` directly. Removed nodes use `node.tool_type` directly.
**Warning signs:** Test assertion on `tool_name` for a modified node fails when tool_type is accidentally different between old/new (which shouldn't happen, but defensive consistency is better).

## Code Examples

Verified patterns from project codebase:

### Full pipeline.run() chain (confirmed import signatures)
```python
# Source: src/alteryx_diff/parser.py — parse(path_a: pathlib.Path, path_b: pathlib.Path)
# Source: src/alteryx_diff/normalizer/normalizer.py — normalize(workflow_doc: WorkflowDoc)
# Source: src/alteryx_diff/matcher/matcher.py — match(old_nodes: list[NormalizedNode], new_nodes: list[NormalizedNode])
# Source: src/alteryx_diff/differ/differ.py — diff(match_result: MatchResult, old_connections, new_connections)

def run(request: DiffRequest) -> DiffResponse:
    doc_a, doc_b = parse(request.path_a, request.path_b)
    norm_a = normalize(doc_a)
    norm_b = normalize(doc_b)
    match_result = match(list(norm_a.nodes), list(norm_b.nodes))
    diff_result = diff(match_result, doc_a.connections, doc_b.connections)
    return DiffResponse(result=diff_result)
```

### DiffResult fields available for serialization (from models/diff.py)
```python
# Source: src/alteryx_diff/models/diff.py
# DiffResult fields:
#   added_nodes: tuple[AlteryxNode, ...]
#   removed_nodes: tuple[AlteryxNode, ...]
#   modified_nodes: tuple[NodeDiff, ...]
#   edge_diffs: tuple[EdgeDiff, ...]
#
# AlteryxNode fields: tool_id: ToolID, tool_type: str, x: float, y: float, config: dict[str, Any]
# NodeDiff fields: tool_id: ToolID, old_node: AlteryxNode, new_node: AlteryxNode, field_diffs: dict[str, tuple[Any, Any]]
# EdgeDiff fields: src_tool: ToolID, src_anchor: AnchorName, dst_tool: ToolID, dst_anchor: AnchorName, change_type: str
```

### pathlib.Path.with_suffix usage (stdlib, confirmed)
```python
# Source: Python 3.11 pathlib documentation
from pathlib import Path
html_path = Path("output/diff_report.html")
json_path = html_path.with_suffix(".json")
# Result: PosixPath('output/diff_report.json')
```

### json.dumps with explicit dict payload (project pattern from normalizer)
```python
# Source: src/alteryx_diff/normalizer/normalizer.py — json.dumps already used for C14N hashing
import json

payload = {
    "summary": {"added": 1, "removed": 0, "modified": 2, "connections": 1},
    "tools": [{"tool_name": "Filter", "changes": [{"id": 5, "display_name": "Filter", "change_type": "added"}]}],
    "connections": [{"src_tool": 1, "src_anchor": "Output", "dst_tool": 2, "dst_anchor": "Input", "change_type": "added"}]
}
json_text = json.dumps(payload, indent=2, ensure_ascii=False)
```

### Exception reuse — existing ParseError hierarchy
```python
# Source: src/alteryx_diff/exceptions.py
# ParseError base with .filepath and .message attributes
# Subclasses: MissingFileError, UnreadableFileError, MalformedXMLError
# pipeline.run() does not catch these — they propagate to the caller
# CLI catches ParseError at its boundary and exits with code 2
from alteryx_diff.exceptions import ParseError
try:
    response = run(request)
except ParseError as exc:
    print(f"Error reading {exc.filepath}: {exc.message}", file=sys.stderr)
    sys.exit(2)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Each stage called independently by the CLI | `pipeline.run()` facade chains all stages | Phase 6 design | CLI becomes a thin adapter; future API callers have one entry point; test isolation confirmed by unit test |
| No JSON output format | `JSONRenderer` producing locked schema | Phase 6 new feature | Machine-readable output enables CI/CD integration (CLI-03) |
| Output decisions embedded in pipeline stages | Output decisions deferred to callers | Phase 1-5 design (no print/sys.exit in any stage) | Pipeline remains entry-point-agnostic by construction |

**Deprecated/outdated:**
- Any pattern that puts `sys.exit()` or `print()` inside `pipeline.py`: inconsistent with the phase success criterion and existing stage conventions. All existing stages (parser, normalizer, matcher, differ) explicitly document "MUST NOT call sys.exit, print, or logging."

## Open Questions

1. **CLI entry point for --json flag**
   - What we know: Phase 9 builds the full CLI (`alteryx_diff.py` entrypoint with Typer). Phase 6 success criterion requires `--json` to produce a `.json` file.
   - What's unclear: Whether Phase 6 creates a minimal `__main__.py` CLI stub to hang the `--json` flag on, or whether the `--json` integration is tested only via a non-CLI test that calls `JSONRenderer` directly.
   - Recommendation: For Phase 6, implement the `--json` behavior as a plain function (not Typer-dependent). A thin `_write_json(result: DiffResult, html_path: Path) -> None` helper in the `renderers/` package satisfies SC 3 without requiring a full CLI. The full Typer flag wires up in Phase 9.

2. **tools array ordering in JSON output**
   - What we know: The locked schema shows `tools: [{ tool_name, changes: [...] }]`. No ordering constraint specified.
   - What's unclear: Whether tools should be sorted alphabetically by `tool_name`, by first appearance, or by change_type order (added/removed/modified).
   - Recommendation: Sort alphabetically by `tool_name` for deterministic output — needed for tests and CI diffs. `sorted(groups.items())` achieves this.

3. **Fixture approach for pipeline tests**
   - What we know: Previous phases used Python constant bytes fixtures (e.g., `tests/fixtures/diffing.py` has `MatchResult` objects directly). The pipeline tests need actual `.yxmd` file bytes since `parser.parse()` reads from disk.
   - What's unclear: Whether to write minimal XML bytes to `tmp_path` (pytest fixture) or create actual `.yxmd` fixture files in `tests/fixtures/`.
   - Recommendation: Use `tmp_path` (pytest built-in). Write minimal valid `.yxmd` XML bytes from Python constants in `tests/fixtures/pipeline.py` to `tmp_path` files. This follows the spirit of existing fixtures (Python constants) while satisfying the parser's disk-read requirement. No `.yxmd` files committed to the repo.

## Sources

### Primary (HIGH confidence)
- `src/alteryx_diff/parser.py` — `parse(path_a: pathlib.Path, path_b: pathlib.Path) -> tuple[WorkflowDoc, WorkflowDoc]` signature verified
- `src/alteryx_diff/normalizer/normalizer.py` — `normalize(workflow_doc: WorkflowDoc) -> NormalizedWorkflowDoc` signature verified
- `src/alteryx_diff/matcher/matcher.py` — `match(old_nodes: list[NormalizedNode], new_nodes: list[NormalizedNode]) -> MatchResult` signature verified; `list` not `tuple` for both args
- `src/alteryx_diff/differ/differ.py` — `diff(match_result: MatchResult, old_connections: tuple[AlteryxConnection, ...], new_connections: tuple[AlteryxConnection, ...]) -> DiffResult` signature verified; uses `doc_a.connections` not `norm_a.connections`
- `src/alteryx_diff/models/diff.py` — `DiffResult`, `NodeDiff`, `EdgeDiff` field names and types verified; `DiffResult` already has `frozen=True, kw_only=True` without `slots=True`
- `src/alteryx_diff/models/workflow.py` — `AlteryxNode.tool_id: ToolID`, `AlteryxNode.tool_type: str` confirmed
- `src/alteryx_diff/exceptions.py` — `ParseError`, `MissingFileError`, `UnreadableFileError`, `MalformedXMLError` with `.filepath` and `.message` attributes confirmed
- `src/alteryx_diff/normalizer/normalizer.py` — `json.dumps(sort_keys=True, separators=..., ensure_ascii=False)` pattern already in use; confirms json stdlib is project standard
- Python 3.11 pathlib docs — `Path.with_suffix()` behavior confirmed for single-extension paths
- `pyproject.toml` — `requires-python = ">=3.11"`, `pytest`, `mypy --strict`, `ruff` confirmed as test infrastructure; no new deps needed for Phase 6

### Secondary (MEDIUM confidence)
- Python 3.11 `json` module docs — `json.dumps(indent=2, ensure_ascii=False)` for human-readable output with Unicode preservation

### Tertiary (LOW confidence)
- None — all critical claims verified with codebase inspection or official docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only (json, pathlib, dataclasses); all import signatures verified from actual source files
- Architecture: HIGH — pipeline facade follows exact same structure as normalizer/matcher/differ packages; JSON renderer pattern is standard Python; file location reasoning derived from existing conventions
- Pitfalls: HIGH — tuple vs list for match() derived from actual matcher.py signature; ToolID/AnchorName cast requirement derived from NewType behavior; connection source pitfall derived from diff() signature analysis

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stdlib-only phase; project conventions locked; no external library churn risk)
