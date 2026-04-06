# Phase 23: LLM Foundation - Research

**Researched:** 2026-04-04
**Domain:** Python optional extras, ContextBuilder data transformation, pytest test isolation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Package Extras**
- D-01: Add `[project.optional-dependencies] llm = [...]` to `pyproject.toml` with pins: `langchain~=1.2`, `langgraph~=1.1`, `langchain-ollama~=1.0`, `ragas~=0.4`, `tiktoken>=0.7`
- D-02: The `langchain~=0.3` pin in ARCHITECTURE.md is stale — use `~=1.2` as confirmed in STACK.md research (langchain 1.2.14 is current production-stable)

**Optional Import Guard**
- D-03: `llm/__init__.py` exposes `require_llm_deps()` — raises `ImportError` with a clear install hint (`pip install alteryx-diff[llm]`) when extras absent, returns cleanly when present
- D-04: The existing codebase must have zero top-level imports from `alteryx_diff.llm.*` — this is the #1 risk; any accidental top-level import will break the 252-test suite for users without extras

**ContextBuilder — build_from_workflow**
- D-05: Output includes `workflow_name`, `tool_count`, `tools`, `connections`, `topology` keys
- D-06: Each entry in `tools[]` includes the full `AlteryxNode.config` dict (no field curation in Phase 23)
- D-07: `topology` contains: `connections` list + `source_tools`, `sink_tools`, `branch_points` (precomputed via networkx DiGraph)

**ContextBuilder — build_from_diff**
- D-08: Output includes `summary` and `changes` keys
- D-09: `changes` is structured by change category: `added`, `removed`, `modified`, `edge_changes`
- D-10: `summary` contains high-level counts: `{added_count, removed_count, modified_count, edge_change_count}`

**Test Isolation Strategy**
- D-11: `pytest.importorskip('langchain')` at the top of every `tests/llm/` test file
- D-12: CI runs two jobs: `core` (bare `pip install alteryx-diff`, must pass 252 existing tests) and `llm` (`pip install "alteryx-diff[llm]"`, runs llm tests)
- D-13: LLM tests live under `tests/llm/` (new subdirectory)

### Claude's Discretion

- `llm/context_builder.py` module structure and class design
- Whether `ContextBuilder` is a class with static methods or plain functions — either works
- mypy handling of optional imports (TYPE_CHECKING guard pattern recommended)
- Exact `summary` field content beyond counts (e.g., workflow name inclusion)

### Deferred Ideas (OUT OF SCOPE)

- **LightRAG / graph-based RAG** — Relevant if Phase 27+ expands to handle large workflow corpora where subgraph retrieval is needed. Not applicable for single-workflow context building in v1.2.
- **Curated config field filtering** — Filtering `AlteryxNode.config` to "interesting" fields for token efficiency. Deferred to Phase 24 (prompt engineering layer); Phase 23 passes full config dict.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-01 | User can install core `alteryx-diff` without LLM deps; `pip install alteryx-diff[llm]` activates LLM features; core CLI works with zero LLM imports present | `[project.optional-dependencies]` block in pyproject.toml + `require_llm_deps()` guard + two-job CI structure (see Architecture Patterns) |
| CORE-02 | `ContextBuilder` transforms `WorkflowDoc`/`DiffResult` into a token-efficient JSON context dict; raw XML never passes the LLM boundary | Verified model fields on `WorkflowDoc`, `AlteryxNode`, `DiffResult`, `NodeDiff`, `EdgeDiff`; networkx DiGraph topology computation pattern (see Code Examples) |

</phase_requirements>

---

## Summary

Phase 23 creates the foundation for all v1.2 LLM work: (1) a `[llm]` optional extras group in `pyproject.toml` that gates LLM dependencies, and (2) a `ContextBuilder` that transforms the existing frozen dataclasses (`WorkflowDoc`, `DiffResult`) into plain dicts for LLM consumption. No LLM pipeline, no CLI, no UI changes touch this phase.

The existing codebase is clean: the src tree has no `llm/` subpackage yet (confirmed by directory listing), and no existing source or test file imports from `alteryx_diff.llm`. The `require_llm_deps()` guard in `llm/__init__.py` is the single zero-import enforcement point. The 252-test suite has one pre-existing failure (`test_remote.py::test_post_push_success`) unrelated to this phase; the CI `core` job should skip that test or document it as a known pre-existing issue.

The key model fields are confirmed from source: `WorkflowDoc.filepath`, `.nodes: tuple[AlteryxNode, ...]`, `.connections: tuple[AlteryxConnection, ...]`; `AlteryxNode.tool_id: ToolID`, `.tool_type: str`, `.x: float`, `.y: float`, `.config: dict[str, Any]`; `DiffResult.added_nodes`, `.removed_nodes`, `.modified_nodes`, `.edge_diffs`; `NodeDiff.tool_id`, `.field_diffs: dict[str, tuple[Any, Any]]`; `EdgeDiff.src_tool`, `.src_anchor`, `.dst_tool`, `.dst_anchor`, `.change_type: str`. networkx is already in core deps and used in `_graph_builder.py` — the `ContextBuilder` can import it with no gating.

**Primary recommendation:** Implement Phase 23 as three deliverables in order: (1) pyproject.toml `[project.optional-dependencies]` block, (2) `src/alteryx_diff/llm/__init__.py` with `require_llm_deps()`, (3) `src/alteryx_diff/llm/context_builder.py` with `ContextBuilder` class. Then add CI workflow and `tests/llm/` tests.

---

## Standard Stack

### Core (Phase 23 scope only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | `>=3.6` (already in core deps) | DiGraph topology computation for `source_tools`, `sink_tools`, `branch_points` | Already in pyproject.toml core; confirmed at 3.6.1 on this machine; used by `_graph_builder.py` |
| langchain | `~=1.2` (optional extras only) | Gate check in `require_llm_deps()` only — no imports in Phase 23 code body | Verified at 1.2.14 on PyPI (STACK.md); D-02 locks this version |
| pytest | `>=8.0` (already in dev group) | Test framework; `pytest.importorskip('langchain')` for LLM test files | Confirmed: `uv run pytest` resolves to pytest 9.0.2 here |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| langgraph | `~=1.1` (optional extras only) | Listed in extras gate only; Phase 24 uses it | Only in Phase 24+ |
| langchain-ollama | `~=1.0` (optional extras only) | Listed in extras gate only; Phase 24 uses it | Only in Phase 24+ |
| ragas | `~=0.4` (optional extras only) | Listed in extras gate only; Phase 27 uses it | Only in Phase 27 |
| tiktoken | `>=0.7` (optional extras only) | Listed in extras gate only | Phase 24+ token budgets |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pytest.importorskip()` | Manual `try/except ImportError` in each test | `importorskip` is the idiomatic pytest mechanism; produces SKIP (not ERROR) and requires one line |
| class-based `ContextBuilder` | Plain module-level functions | Class is marginally better for future parametrization (e.g., `max_tools`, `include_positions`); D-05–D-10 describe methods not functions |

**Installation — optional extras:**
```bash
# Core only (existing behavior — must stay working):
uv sync

# With LLM extras (activates ContextBuilder features):
uv sync --extra llm

# End-user pip:
pip install "alteryx-diff[llm]"
```

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
src/alteryx_diff/
└── llm/
    ├── __init__.py          # require_llm_deps() guard — no top-level llm imports
    └── context_builder.py   # ContextBuilder class (pure Python, no LLM imports)

tests/
└── llm/
    ├── __init__.py          # empty
    ├── test_context_builder_workflow.py
    └── test_context_builder_diff.py
```

CI:
```
.github/workflows/
└── test.yml                 # new: two-job matrix (core + llm)
```

pyproject.toml change:
```
[project.optional-dependencies]  # new section (currently absent)
llm = [...]
```

### Pattern 1: pyproject.toml Optional Extras (PEP 621 / uv_build)

**What:** Add `[project.optional-dependencies]` section to the existing `pyproject.toml`. The build backend is `uv_build` (confirmed). PEP 621 `[project.optional-dependencies]` is fully supported.

**Key fact:** The current `pyproject.toml` uses `[dependency-groups]` for dev dependencies (not `[project.optional-dependencies]`). The `[project.optional-dependencies]` section does not exist yet — must be added. Dev deps must stay in `[dependency-groups]` (they already are).

**Example (source: STACK.md, verified against uv docs):**
```toml
[project.optional-dependencies]
llm = [
    "langchain~=1.2",
    "langgraph~=1.1",
    "langchain-ollama~=1.0",
    "ragas~=0.4",
    "tiktoken>=0.7",
]
```

Note: STACK.md includes `langchain-core~=1.2` as a transitive dep. D-01 does not list it explicitly. Since langchain 1.2 pulls langchain-core automatically, do NOT pin langchain-core explicitly — avoids resolver conflicts.

### Pattern 2: Optional Import Guard

**What:** `llm/__init__.py` exports `require_llm_deps()`. No LLM package is imported at module level — not even inside `__init__.py` top-level scope.

**When to use:** Called as the first statement in any code path that uses LLM features (CLI commands, FastAPI endpoints). NOT called in the ContextBuilder itself (ContextBuilder is pure Python, no LLM deps).

**Example (source: ARCHITECTURE.md):**
```python
# src/alteryx_diff/llm/__init__.py
from __future__ import annotations


def require_llm_deps() -> None:
    """Raise ImportError with install hint when [llm] extras are absent."""
    missing: list[str] = []
    try:
        import langchain  # noqa: F401
    except ImportError:
        missing.append("langchain~=1.2")
    try:
        import langgraph  # noqa: F401
    except ImportError:
        missing.append("langgraph~=1.1")
    if missing:
        raise ImportError(
            "LLM documentation features require optional dependencies.\n"
            "Install them with:\n\n"
            "    pip install 'alteryx-diff[llm]'\n\n"
            f"Missing: {', '.join(missing)}"
        )
```

**Critical rule:** The `alteryx_diff.llm` package must be importable with zero LLM extras present. This means: no top-level `import langchain` anywhere in `llm/__init__.py` or `llm/context_builder.py`. The `require_llm_deps()` deferred import inside the function body is the only acceptable pattern.

### Pattern 3: ContextBuilder Class

**What:** A dataclass or plain class in `llm/context_builder.py`. Takes `WorkflowDoc`/`DiffResult` as input, returns plain dicts. No LLM imports — this file imports only from `alteryx_diff.models` and `networkx`.

**When to use:** Called by the Phase 24 DocumentationGraph before invoking the LLM. Also tested standalone in Phase 23 tests.

**Key design points:**
- `build_from_workflow(doc: WorkflowDoc) -> dict` — serializes nodes and computes topology using networkx DiGraph
- `build_from_diff(result: DiffResult) -> dict` — serializes changes by category
- Output is always plain `dict` (JSON-serializable) — not a dataclass
- The `AlteryxNode.config` field is `dict[str, Any]` — pass through directly; no curation in Phase 23

### Pattern 4: networkx DiGraph for Topology Computation

**What:** Build a `nx.DiGraph` from `WorkflowDoc.connections`, then compute in-degree/out-degree to classify tools.

**Source nodes:** `in_degree == 0`
**Sink nodes:** `out_degree == 0`
**Branch points:** `out_degree > 1`

**Example (source: confirmed networkx 3.6.1 API from _graph_builder.py):**
```python
import networkx as nx
from alteryx_diff.models.workflow import WorkflowDoc


def _compute_topology(doc: WorkflowDoc) -> dict:
    G: nx.DiGraph = nx.DiGraph()
    for node in doc.nodes:
        G.add_node(node.tool_id)
    for conn in doc.connections:
        G.add_edge(conn.src_tool, conn.dst_tool)

    return {
        "connections": [
            {
                "src_tool": c.src_tool,
                "src_anchor": c.src_anchor,
                "dst_tool": c.dst_tool,
                "dst_anchor": c.dst_anchor,
            }
            for c in doc.connections
        ],
        "source_tools": [n for n in G.nodes if G.in_degree(n) == 0],
        "sink_tools": [n for n in G.nodes if G.out_degree(n) == 0],
        "branch_points": [n for n in G.nodes if G.out_degree(n) > 1],
    }
```

### Pattern 5: pytest.importorskip for LLM Tests

**What:** Skip an entire test file when `langchain` is not installed — produces SKIP status (not ERROR).

**Example (source: D-11, standard pytest docs):**
```python
# tests/llm/test_context_builder_workflow.py
from __future__ import annotations

langchain = pytest.importorskip("langchain")  # skips file if langchain absent

import pytest
from alteryx_diff.llm.context_builder import ContextBuilder
...
```

**Important:** `pytest.importorskip()` must appear before any other imports that depend on the optional package. For Phase 23, `ContextBuilder` itself has no LLM imports, so `pytest.importorskip('langchain')` functions purely as the "is llm extra installed?" guard — consistent with D-11.

### Pattern 6: Two-Job CI Structure

**What:** A new `.github/workflows/test.yml` (separate from `release.yml`) running on pull_request and push to main. Two jobs:

- `core` — installs with `uv sync` (no extras), runs `pytest tests/ --ignore=tests/llm/`
- `llm` — installs with `uv sync --extra llm`, runs `pytest tests/llm/`

**Why separate from release.yml:** `release.yml` runs only on `v*` tags, on Windows, and builds the exe. Test CI needs to run on every PR on Linux for speed. The existing `release.yml` has no test step — a new `test.yml` is the right addition.

**Example skeleton:**
```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:

jobs:
  core:
    name: Core tests (no LLM extras)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install uv
      - run: uv sync
      - run: uv run pytest tests/ --ignore=tests/llm/ -q

  llm:
    name: LLM tests (with extras)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install uv
      - run: uv sync --extra llm
      - run: uv run pytest tests/llm/ -q
```

### Pattern 7: mypy TYPE_CHECKING Guard for Optional Types

**What:** When a function signature references a type from an optional dependency (e.g., `BaseChatModel`), use `TYPE_CHECKING` to keep the annotation visible to mypy without a runtime import.

**When to use:** Phase 23's `ContextBuilder` does NOT reference any LLM types in its signatures — it only takes `WorkflowDoc` and `DiffResult`. This pattern is needed in Phase 24+ when `doc_graph.py` references `BaseChatModel`.

**Example (for Phase 24 reference, documented here per research focus area):**
```python
from __future__ import annotations  # postponed evaluation — makes TYPE_CHECKING guard safe
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


def build_doc_graph(llm: BaseChatModel) -> ...:  # type is string at runtime (postponed eval)
    ...
```

**Pyproject.toml mypy note:** The existing `[tool.mypy]` has `ignore_missing_imports = false` and `strict = true`. A new `[[tool.mypy.overrides]]` section is needed for the optional LLM modules so mypy does not fail on a bare install:
```toml
[[tool.mypy.overrides]]
module = ["langchain.*", "langgraph.*", "langchain_ollama.*", "ragas.*", "tiktoken.*"]
ignore_missing_imports = true
```

### Anti-Patterns to Avoid

- **Top-level LLM imports in existing modules:** Any `import langchain` at the top of `cli.py`, `pipeline.py`, `server.py`, or any existing file breaks the 252-test suite for users without extras. Confirmed clean today — must stay clean.
- **Importing `alteryx_diff.llm` in `alteryx_diff/__init__.py`:** Would force LLM import on every `import alteryx_diff` call.
- **Putting LLM packages in `[dependency-groups]`:** Dev deps use `[dependency-groups]` (confirmed in existing pyproject.toml). LLM packages go in `[project.optional-dependencies]` only.
- **Pinning `langchain-core` explicitly:** It is a transitive dep pulled by langchain 1.2. Explicit pin risks resolver conflicts.
- **Using `try/except ImportError` at module top-level in `llm/context_builder.py`:** The ContextBuilder has no LLM imports at all — no guard needed there. Only `require_llm_deps()` inside `__init__.py` uses the deferred import pattern.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Skip test when dep missing | Custom `@pytest.mark.skipif(importlib.util.find_spec(...))` | `pytest.importorskip('langchain')` | Standard mechanism; produces correct SKIP status; one line |
| Graph in/out degree computation | Custom adjacency-list degree counter | `nx.DiGraph.in_degree(n)` / `nx.out_degree(n)` | networkx already in core deps; these are O(1) lookups |
| Python serialization of frozen dataclass | Manual `{'tool_id': node.tool_id, ...}` for every field | `dataclasses.asdict(node)` then exclude/modify | `asdict()` recursively converts nested dataclasses; `AlteryxNode.config` is already `dict[str, Any]` so it passes through cleanly |

**Key insight:** `ContextBuilder` is pure data transformation — no LLM, no external calls, no file I/O. It should be testable with zero extras installed and should run in milliseconds.

---

## Common Pitfalls

### Pitfall 1: Top-Level Import Breaks Core Install

**What goes wrong:** A developer adds `from alteryx_diff.llm.context_builder import ContextBuilder` at the top of `cli.py` for convenience. Every user running `pip install alteryx-diff` (no extras) gets `ModuleNotFoundError: No module named 'langchain'` on `acd` startup — even though ContextBuilder itself has no LLM imports. The import resolution chain (`cli.py` -> `llm/context_builder.py` -> `llm/__init__.py`) still succeeds, but any import of `alteryx_diff.llm` causes Python to execute `llm/__init__.py` which calls `require_llm_deps()` if that's placed at module scope.

Wait — more precisely: the real risk is if `llm/__init__.py` itself imports langchain at module scope. If `require_llm_deps()` is a pure function (deferred imports inside the function body), then `import alteryx_diff.llm` succeeds with no extras. The risk is in `context_builder.py` doing `import langchain` at top level (it should never need to, since ContextBuilder is pure Python).

**How to avoid:** Grep for `import langchain`, `import langgraph`, `from langchain`, `from langgraph` in all non-`tests/llm/` files as a verification step in the CI `core` job. Alternatively: the CI `core` job (`uv sync`, no extras) inherently catches this — if any top-level LLM import exists, the 252-test suite will fail with `ModuleNotFoundError`.

**Warning signs:** `test_import.py` or any core test fails with `ModuleNotFoundError` on the `core` CI job.

### Pitfall 2: WorkflowDoc Has No `.name` Field

**What goes wrong:** `build_from_workflow` sets `"workflow_name": doc.name` — but `WorkflowDoc` (confirmed from source) has only `filepath`, `nodes`, and `connections`. There is no `.name` field.

**How to avoid:** Derive `workflow_name` from `filepath` using `Path(doc.filepath).stem`. This gives the filename without extension (e.g., `"my_workflow"`). Document this as the behavior.

**Source confirmation:** `WorkflowDoc` is a frozen dataclass with exactly: `filepath: str`, `nodes: tuple[AlteryxNode, ...]`, `connections: tuple[AlteryxConnection, ...]` — no name field.

### Pitfall 3: ToolID is a NewType(int) — Not Bare int

**What goes wrong:** When serializing `AlteryxNode.tool_id` or connection tool IDs to a JSON dict, code does `{"tool_id": node.tool_id}`. This works at runtime (NewType is transparent), but mypy under strict mode will flag mixing `ToolID` with `int` or with JSON serialization that expects `int`.

**How to avoid:** Use `int(node.tool_id)` when building output dicts to explicitly convert the NewType to plain int. This is both type-safe and makes the output schema clear.

### Pitfall 4: dataclasses.asdict() Fails on Frozen Slots Dataclasses

**What goes wrong:** `AlteryxNode` is `@dataclass(frozen=True, kw_only=True, slots=True)`. `dataclasses.asdict()` works fine with slots dataclasses in Python 3.11+. However, if `config: dict[str, Any]` contains non-serializable values (e.g., nested objects), `asdict()` will recurse into them. For `AlteryxNode`, the config is already a flat `dict[str, Any]` built by the parser — but verify the actual config values are JSON-primitive types.

**How to avoid:** Serialize manually for the tools list to control output shape exactly per D-05/D-06. Use `{"tool_id": int(node.tool_id), "tool_type": node.tool_type, "config": node.config}` rather than `dataclasses.asdict()`, which also includes `x` and `y` fields that are not needed in the LLM context.

### Pitfall 5: NodeDiff.field_diffs is dict[str, tuple[Any, Any]] — Tuple Needs Conversion

**What goes wrong:** `NodeDiff.field_diffs` is `dict[str, tuple[Any, Any]]` (old_value, new_value). Tuples are not JSON-serializable. The `build_from_diff` output for `modified` entries needs these as lists.

**How to avoid:** Serialize `field_diffs` as `{field: [old_val, new_val]}` (list not tuple) in the output dict. Consistent with D-09's schema: `"field_diffs: {field: [old_val, new_val]}"`.

### Pitfall 6: mypy Strict Mode Fails on Optional Dep Imports

**What goes wrong:** `pyproject.toml` has `[tool.mypy] strict = true` and `ignore_missing_imports = false`. Running `mypy src/` without `[llm]` extras installed causes mypy to error on any import of langchain types — even inside `if TYPE_CHECKING:` blocks — because the stubs are not present.

**How to avoid:** Add `[[tool.mypy.overrides]]` for all LLM modules with `ignore_missing_imports = true`. This is required in Phase 23 when `llm/__init__.py` is added (the deferred imports inside `require_llm_deps()` body will be seen by mypy as unresolved even inside function scope).

### Pitfall 7: pytest test_remote.py Pre-Existing Failure

**What goes wrong:** One test (`test_remote.py::test_post_push_success`) is already failing in the current codebase (confirmed by running the suite). If the CI `core` job runs the full test suite, this pre-existing failure will appear to block Phase 23 merges.

**How to avoid:** The CI `core` job should either: (a) document and skip this pre-existing test with `@pytest.mark.xfail`, or (b) use `pytest --ignore=tests/test_remote.py` temporarily. The plan should explicitly address this so the new CI doesn't regress on unrelated work. This is pre-existing, not a Phase 23 regression.

---

## Code Examples

### build_from_workflow Output Shape

```python
# Source: D-05, D-06, D-07 from CONTEXT.md
# workflow_name derived from filepath (WorkflowDoc has no .name field)
from pathlib import Path
import networkx as nx

def build_from_workflow(self, doc: WorkflowDoc) -> dict:
    G: nx.DiGraph = nx.DiGraph()
    for node in doc.nodes:
        G.add_node(int(node.tool_id))
    for conn in doc.connections:
        G.add_edge(int(conn.src_tool), int(conn.dst_tool))

    return {
        "workflow_name": Path(doc.filepath).stem,
        "tool_count": len(doc.nodes),
        "tools": [
            {
                "tool_id": int(node.tool_id),
                "tool_type": node.tool_type,
                "config": node.config,  # full dict — no curation in Phase 23
            }
            for node in doc.nodes
        ],
        "connections": [
            {
                "src_tool": int(c.src_tool),
                "src_anchor": c.src_anchor,
                "dst_tool": int(c.dst_tool),
                "dst_anchor": c.dst_anchor,
            }
            for c in doc.connections
        ],
        "topology": {
            "connections": [
                {
                    "src_tool": int(c.src_tool),
                    "src_anchor": c.src_anchor,
                    "dst_tool": int(c.dst_tool),
                    "dst_anchor": c.dst_anchor,
                }
                for c in doc.connections
            ],
            "source_tools": [n for n in G.nodes if G.in_degree(n) == 0],
            "sink_tools": [n for n in G.nodes if G.out_degree(n) == 0],
            "branch_points": [n for n in G.nodes if G.out_degree(n) > 1],
        },
    }
```

### build_from_diff Output Shape

```python
# Source: D-08, D-09, D-10 from CONTEXT.md
def build_from_diff(self, result: DiffResult) -> dict:
    return {
        "summary": {
            "added_count": len(result.added_nodes),
            "removed_count": len(result.removed_nodes),
            "modified_count": len(result.modified_nodes),
            "edge_change_count": len(result.edge_diffs),
        },
        "changes": {
            "added": [
                {"tool_id": int(n.tool_id), "tool_type": n.tool_type}
                for n in result.added_nodes
            ],
            "removed": [
                {"tool_id": int(n.tool_id), "tool_type": n.tool_type}
                for n in result.removed_nodes
            ],
            "modified": [
                {
                    "tool_id": int(nd.tool_id),
                    "tool_type": nd.new_node.tool_type,
                    "field_diffs": {
                        field: list(vals)  # tuple[Any, Any] -> [old, new]
                        for field, vals in nd.field_diffs.items()
                    },
                }
                for nd in result.modified_nodes
            ],
            "edge_changes": [
                {
                    "change_type": ed.change_type,  # "added" or "removed"
                    "src_tool": int(ed.src_tool),
                    "dst_tool": int(ed.dst_tool),
                    "anchors": {
                        "src": ed.src_anchor,
                        "dst": ed.dst_anchor,
                    },
                }
                for ed in result.edge_diffs
            ],
        },
    }
```

### LLM Test File Template

```python
# tests/llm/test_context_builder_workflow.py
from __future__ import annotations

import pytest

langchain = pytest.importorskip("langchain")  # skips entire file if extras absent

from alteryx_diff.llm.context_builder import ContextBuilder
from alteryx_diff.models.workflow import AlteryxNode, AlteryxConnection, WorkflowDoc
from alteryx_diff.models.types import ToolID, AnchorName


def test_build_from_workflow_keys():
    doc = WorkflowDoc(
        filepath="/some/workflow.yxmd",
        nodes=(
            AlteryxNode(tool_id=ToolID(1), tool_type="AlteryxBasePluginsGui.Filter.Filter",
                        x=100.0, y=200.0, config={"Expression": "true"}),
        ),
        connections=(),
    )
    cb = ContextBuilder()
    result = cb.build_from_workflow(doc)
    assert set(result.keys()) == {"workflow_name", "tool_count", "tools", "connections", "topology"}
    assert result["workflow_name"] == "workflow"
    assert result["tool_count"] == 1
    assert set(result["topology"].keys()) == {"connections", "source_tools", "sink_tools", "branch_points"}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `langchain~=0.3` pin (in ARCHITECTURE.md) | `langchain~=1.2` (production-stable) | Late 2025 (langchain 1.0 GA) | StateGraph state must be `TypedDict` not Pydantic in Phase 24; 1.x patterns differ from 0.3 in some areas |
| Pydantic BaseModel for LangGraph state | TypedDict only | langchain 1.0 breaking change | Phase 24 impact only; Phase 23 is pure Python dicts |
| `[project.optional-dependencies]` absent in pyproject.toml | Must be added (currently missing) | Phase 23 | New section; does not affect existing `[dependency-groups]` dev deps |

**Deprecated/outdated:**
- `langchain~=0.3` pin referenced in ARCHITECTURE.md: stale — superseded by STACK.md and D-02. The environment currently has langchain 0.3.27 installed; Phase 23 targets 1.2 in the extras definition.
- `ragas.SingleTurnSample.single_turn_ascore()`: removed in ragas 1.0; use `evaluate()` with `EvaluationDataset`. Phase 23 scope only; relevant to Phase 27.

---

## Open Questions

1. **Pre-existing test_remote.py failure**
   - What we know: `test_remote.py::test_post_push_success` fails in the current suite (confirmed by running tests)
   - What's unclear: Whether this should be marked `xfail` before Phase 23 or documented as known-broken in CI
   - Recommendation: The Phase 23 plan should add `@pytest.mark.xfail` to that test (or skip it in the CI `core` job via `--deselect`) so the new CI job passes cleanly. Do not leave it silently breaking Phase 23 CI.

2. **Topology `connections` duplication**
   - What we know: D-07 puts a `connections` list inside `topology`. The top-level output also has a `connections` key (D-05). This duplicates the connection data.
   - What's unclear: Whether both are intentional (the top-level `connections` is a flat list; `topology.connections` is the same data serving graph context)
   - Recommendation: Implement as specified (D-05 and D-07 both require it). The duplication is intentional — Phase 24 may consume topology separately from the raw connections. Document this in docstrings.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | All code | Yes | 3.11.x (confirmed via pyproject.toml `requires-python`) | — |
| uv | Package management / CI | Yes | 0.10.10 (confirmed on this machine) | `pip install uv` in CI |
| networkx | Topology computation | Yes | 3.6.1 (confirmed) | — (already in core deps) |
| pytest | Test framework | Yes | 9.0.2 via uv, 7.4.4 system | Use `uv run pytest` |
| langchain 1.2 | `[llm]` extras | NOT installed in core env | 0.3.27 (stale) in current env | Install via `uv sync --extra llm` |
| GitHub Actions ubuntu-latest | New CI test.yml | Yes (standard) | — | — |

**Missing dependencies with no fallback:** None that block Phase 23 execution.

**Missing dependencies with fallback:** langchain 1.2 is not in the core env — correct behavior; the `core` CI job must not install it.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (via uv) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/llm/ -q` |
| Full suite (core) | `uv run pytest tests/ --ignore=tests/llm/ -q` |
| Full suite (llm) | `uv run pytest tests/llm/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-01 | Core install has zero LLM imports; `require_llm_deps()` raises with hint when absent | unit | `uv run pytest tests/llm/test_require_llm_deps.py -x` | No — Wave 0 |
| CORE-01 | Core 252-test suite passes without extras | regression | `uv run pytest tests/ --ignore=tests/llm/ -q` | Partially (existing tests) |
| CORE-02 | `build_from_workflow` produces correct keys and topology | unit | `uv run pytest tests/llm/test_context_builder_workflow.py -x` | No — Wave 0 |
| CORE-02 | `build_from_diff` produces correct keys and categories | unit | `uv run pytest tests/llm/test_context_builder_diff.py -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/llm/ -q`
- **Per wave merge:** `uv run pytest tests/ --ignore=tests/llm/ -q && uv run pytest tests/llm/ -q` (with extras)
- **Phase gate:** Both suites green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/llm/__init__.py` — empty init to make subdirectory a package
- [ ] `tests/llm/test_require_llm_deps.py` — covers CORE-01 (require_llm_deps raises/passes correctly)
- [ ] `tests/llm/test_context_builder_workflow.py` — covers CORE-02 (build_from_workflow output shape)
- [ ] `tests/llm/test_context_builder_diff.py` — covers CORE-02 (build_from_diff output shape)

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 23 |
|-----------|-------------------|
| Release workflow triggers on `v*` tag push, not branch push | No impact — Phase 23 adds a separate `test.yml` workflow, not `release.yml` |
| `npm ci --legacy-peer-deps` required for frontend builds | No impact — Phase 23 is pure Python, no frontend changes |
| 4-part version format for pyivf-make_version | No impact — Phase 23 does not change the release process |
| `permissions: contents: write` on release job | No impact — test.yml jobs need no such permissions |

---

## Sources

### Primary (HIGH confidence)
- Verified from source code: `src/alteryx_diff/models/workflow.py` — exact fields on `WorkflowDoc`, `AlteryxNode`, `AlteryxConnection`
- Verified from source code: `src/alteryx_diff/models/diff.py` — exact fields on `DiffResult`, `NodeDiff`, `EdgeDiff`
- Verified from source code: `pyproject.toml` — confirmed `[project.optional-dependencies]` absent, `[dependency-groups]` used for dev, `uv_build` backend, `[tool.mypy] strict = true, ignore_missing_imports = false`
- `.planning/research/STACK.md` — langchain 1.2.14 PyPI-verified, uv optional-deps syntax, `require_llm_deps()` pattern
- `.planning/research/ARCHITECTURE.md` — ContextBuilder interface, optional import guard pattern, mypy TYPE_CHECKING pattern

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md` — uv optional deps behavior (verified against uv 0.10.10 official docs link in STACK.md)
- Python `pytest.importorskip` — standard pytest API, documented behavior

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified from pyproject.toml and installed packages
- Architecture: HIGH — model fields verified from source; patterns from STACK.md/ARCHITECTURE.md cross-referenced with working source code (`_graph_builder.py`)
- Pitfalls: HIGH for Pitfalls 1-7 — all derived from direct source inspection (WorkflowDoc has no `.name`, ToolID is NewType, field_diffs is tuple, etc.)

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (langchain/langgraph move fast — re-verify if delayed more than 30 days)

---

## RESEARCH COMPLETE
