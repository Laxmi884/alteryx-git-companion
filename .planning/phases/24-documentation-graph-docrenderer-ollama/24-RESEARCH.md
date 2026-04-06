# Phase 24: DocumentationGraph + DocRenderer + Ollama - Research

**Researched:** 2026-04-04
**Domain:** LangGraph pipeline, Pydantic structured output, DocRenderer, LLM provider injection
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Output Model**
- D-01: Output model is `WorkflowDocumentation` (Pydantic `BaseModel`) — NOT `WorkflowDoc` (existing frozen dataclass in `alteryx_diff.models.workflow`)
- D-02: `WorkflowDocumentation` structure:
  ```python
  class ToolNote(BaseModel):
      tool_id: int
      tool_type: str
      role: str              # one sentence: what this tool does in context

  class WorkflowDocumentation(BaseModel):
      workflow_name: str
      intent: str            # 2-3 sentences: what the workflow accomplishes
      data_flow: str         # prose: how data moves source-to-sink
      tool_notes: list[ToolNote]
      risks: list[str]       # production concerns
  ```
- D-03: `assumptions` field explicitly excluded (hallucination risk)
- D-04: `tool_notes` is a structured list (not prose)
- D-05: `data_flow` is prose (not structured)
- D-06: `risks` is a flat `list[str]`

**Pipeline Topology**
- D-07: Linear 4-node: `analyze_topology → annotate_tools → risk_scan → assemble_doc`. No fan-out.
- D-08: Fan-out via `Send` API explicitly rejected for Phase 24
- D-09: LangGraph state type: `TypedDict` only
- D-10: Single automatic retry on `ValidationError` in `generate_documentation()` convenience wrapper

**Config Field Strategy**
- D-11: `ContextBuilder.build_from_workflow` calls `strip_noise(node.config)` for each tool
- D-12: `strip_noise` handles GUID/timestamp/path noise; structural noise (Plugin DLL names, EngineSettings, Annotation keys) tolerated
- D-13: `build_from_diff` unchanged; only `build_from_workflow` tool config path updated

**LLM Injection Pattern**
- D-14: Factory function pattern (not class):
  ```python
  def build_doc_graph(llm: BaseChatModel) -> CompiledStateGraph: ...
  async def generate_documentation(context: dict, llm: BaseChatModel) -> WorkflowDocumentation: ...
  ```
- D-15: Ollama: caller passes `ChatOllama(model="llama3")` — no special adapter
- D-16: OpenRouter: caller passes `ChatOpenAI(model="...", base_url="https://openrouter.ai/api/v1", api_key=...)`
- D-17: Add `langchain-openai~=0.3` to `[project.optional-dependencies] llm` in `pyproject.toml`
- D-18: Factory function is provider-agnostic — any `BaseChatModel` works

### Claude's Discretion

- LangGraph `DocState` TypedDict field names and exact intermediate state structure
- Prompt wording for each of the 4 nodes
- Whether `build_doc_graph` is in `doc_graph.py` or split across files
- `DocRenderer` Markdown template format (section headers, table vs list for tool_notes)
- HTML fragment structure (a `<section>` element per ARCHITECTURE.md pattern)
- mypy/TYPE_CHECKING guards for optional `langchain` imports inside the llm subpackage
- Test fixture design for LangGraph tests (mock LLM vs `pytest.importorskip`)

### Deferred Ideas (OUT OF SCOPE)

- Per-tool config curation allowlist (deferred to Phase 27 RAGAS evaluation)
- Fan-out `annotate_tools` via LangGraph Send API
- `assumptions` field in `WorkflowDocumentation`
- LangSmith tracing
</user_constraints>

---

## Summary

Phase 24 builds on the Phase 23 LLM foundation (import guard, ContextBuilder, CI two-job setup) to implement the core documentation pipeline. The three deliverables are: (1) `WorkflowDocumentation` + `ToolNote` Pydantic models in a new `src/alteryx_diff/llm/models.py`; (2) the LangGraph `DocumentationGraph` in `src/alteryx_diff/llm/doc_graph.py` with a provider-agnostic `build_doc_graph(llm)` factory and `generate_documentation()` convenience wrapper; (3) `DocRenderer` in `src/alteryx_diff/renderers/doc_renderer.py` that renders `WorkflowDocumentation` to Markdown and HTML fragment.

The Phase 23 infrastructure is already verified working: `langchain 1.2.15`, `langgraph 1.1.x`, `langchain-ollama 1.0.1` are installed via `uv sync --extra llm`; the `require_llm_deps()` guard and CI two-job pattern are in place; 11 LLM tests pass. One small fix needed in `ContextBuilder.build_from_workflow` to call `strip_noise(node.config)` per D-11.

A key discovery from environment probing: the `CompiledGraph` import path shown in `ARCHITECTURE.md` (`from langgraph.graph.graph import CompiledGraph`) does NOT exist in langgraph 1.1. The correct type is `CompiledStateGraph` imported from `langgraph.graph.state`. The return type annotation for `build_doc_graph` should use `CompiledStateGraph` or `TYPE_CHECKING`-gated annotation.

**Primary recommendation:** Implement in four tasks: (1) `WorkflowDocumentation` models; (2) `strip_noise` update to `ContextBuilder`; (3) `DocumentationGraph` pipeline; (4) `DocRenderer` + tests.

---

## Standard Stack

### Core (all already installed via `[llm]` extras from Phase 23)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain | `~=1.2` (installed: 1.2.15) | `BaseChatModel`, `with_structured_output`, LCEL | Confirmed current stable as of April 2026 |
| langgraph | `~=1.1` (installed: 1.1.x) | `StateGraph`, `START`/`END`, `ainvoke` | Locked in Phase 23 |
| langchain-ollama | `~=1.0` (installed: 1.0.1) | `ChatOllama` for local/offline execution | Locked in Phase 23 |
| pydantic | v2 (transitive) | `WorkflowDocumentation`/`ToolNote` output models | Already in project |

### New Addition

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| langchain-openai | `~=0.3` | `ChatOpenAI` for OpenRouter + OpenAI-compatible endpoints | D-17: add to `[llm]` extras in pyproject.toml |

**Note:** `langchain-openai` is already present in the venv (pulled transitively), but is NOT declared in `pyproject.toml` `[llm]` extras. Per D-17, it must be explicitly added.

**Version verification (verified 2026-04-04):**
```
langchain==1.2.15 (PyPI: 1.2.14 was listed, but 1.2.15 is installed)
langgraph: 1.1.x (verified via import + StateGraph instantiation)
langchain-ollama==1.0.1
langchain-openai: installed transitively, ~=0.3 pin appropriate
```

**No additional install required for Phase 24 core work** — all deps already present via `uv sync --extra llm`.

## Architecture Patterns

### File Layout for Phase 24

```
src/alteryx_diff/
├── llm/
│   ├── __init__.py            # Phase 23 — require_llm_deps() (no changes)
│   ├── context_builder.py     # Phase 23 — update build_from_workflow (strip_noise)
│   ├── models.py              # NEW: WorkflowDocumentation + ToolNote Pydantic models
│   └── doc_graph.py           # NEW: build_doc_graph(), generate_documentation()
├── renderers/
│   ├── html_renderer.py       # Phase 22 — no changes
│   └── doc_renderer.py        # NEW: DocRenderer.to_markdown() / .to_html_fragment()
tests/
└── llm/
    ├── __init__.py            # Phase 23
    ├── test_context_builder.py # Phase 23 — add strip_noise test
    ├── test_require_llm_deps.py # Phase 23
    └── test_doc_graph.py       # NEW: unit tests with mock LLM
    └── test_doc_renderer.py    # NEW: tests for DocRenderer
```

### Pattern 1: DocState TypedDict (linear 4-node)

The `StateGraph` state must be `TypedDict` — verified in langgraph 1.1. Pydantic `BaseModel` is NOT supported for state.

```python
# src/alteryx_diff/llm/doc_graph.py
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

from langchain_core.language_models import BaseChatModel


class DocState(TypedDict):
    context: dict                  # ContextBuilder output dict
    topology_notes: str            # analyze_topology output
    tool_annotations: str          # annotate_tools output (serialized JSON of tool notes)
    risk_notes: str                # risk_scan output
    raw_doc_json: str              # assemble_doc output — raw JSON string for validation
    validation_error: str          # retry context; empty string on first pass
```

### Pattern 2: Async node functions + build_doc_graph factory

```python
# Source: verified via uv run --extra llm python -c "..." (2026-04-04)
from langgraph.graph import StateGraph, START, END

def build_doc_graph(llm: BaseChatModel) -> "CompiledStateGraph":
    # llm captured in closure by each node via inner async functions
    async def analyze_topology(state: DocState) -> dict:
        # Pure context analysis: no LLM call in this node
        # Read state["context"]["topology"] to build structured summary
        return {"topology_notes": "...", "tool_annotations": "", "risk_notes": "", "raw_doc_json": "", "validation_error": ""}

    async def annotate_tools(state: DocState) -> dict:
        # Single LLM call for all tool notes as a batch
        structured_llm = llm.with_structured_output(
            schema_for_tool_annotations,   # dict schema or Pydantic model
            method="json_schema",
        )
        result = await structured_llm.ainvoke([...])
        return {"tool_annotations": json.dumps(result)}

    async def risk_scan(state: DocState) -> dict:
        result = await llm.ainvoke([...])
        return {"risk_notes": result.content}

    async def assemble_doc(state: DocState) -> dict:
        structured_llm = llm.with_structured_output(WorkflowDocumentation, method="json_schema")
        result = await structured_llm.ainvoke([...])
        return {"raw_doc_json": result.model_dump_json()}

    builder = StateGraph(DocState)
    builder.add_node("analyze_topology", analyze_topology)
    builder.add_node("annotate_tools", annotate_tools)
    builder.add_node("risk_scan", risk_scan)
    builder.add_node("assemble_doc", assemble_doc)
    builder.add_edge(START, "analyze_topology")
    builder.add_edge("analyze_topology", "annotate_tools")
    builder.add_edge("annotate_tools", "risk_scan")
    builder.add_edge("risk_scan", "assemble_doc")
    builder.add_edge("assemble_doc", END)
    return builder.compile()
```

### Pattern 3: generate_documentation with single-retry

```python
# Source: D-10 from CONTEXT.md; ValidationError pattern verified
async def generate_documentation(
    context: dict,
    llm: BaseChatModel,
) -> WorkflowDocumentation:
    graph = build_doc_graph(llm)
    initial_state: DocState = {
        "context": context,
        "topology_notes": "",
        "tool_annotations": "",
        "risk_notes": "",
        "raw_doc_json": "",
        "validation_error": "",
    }
    state = await graph.ainvoke(initial_state)
    try:
        return WorkflowDocumentation.model_validate_json(state["raw_doc_json"])
    except ValidationError as e:
        # Single retry: re-invoke with validation error appended to state
        retry_state = {**initial_state, "validation_error": str(e)}
        state = await graph.ainvoke(retry_state)
        return WorkflowDocumentation.model_validate_json(state["raw_doc_json"])
```

### Pattern 4: DocRenderer (stateless class, follows html_renderer.py convention)

```python
# src/alteryx_diff/renderers/doc_renderer.py
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alteryx_diff.llm.models import WorkflowDocumentation


class DocRenderer:
    """Renders WorkflowDocumentation to Markdown or HTML fragment.

    Stateless — follows same renderer protocol as HTMLRenderer.
    No LLM imports at module level (WorkflowDocumentation is TYPE_CHECKING only).
    """

    def to_markdown(self, doc: "WorkflowDocumentation") -> str:
        """Standalone .md file for `alteryx-diff document` CLI."""
        ...

    def to_html_fragment(self, doc: "WorkflowDocumentation") -> str:
        """<section> fragment for embedding in diff report."""
        ...

    def write_markdown(self, doc: "WorkflowDocumentation", output_path: Path) -> Path:
        content = self.to_markdown(doc)
        output_path.write_text(content, encoding="utf-8")
        return output_path
```

**Critical note:** `DocRenderer` lives in `src/alteryx_diff/renderers/` which is in the core package. It must NOT import from `alteryx_diff.llm.models` at module top level — that would break the core import guard. Use `TYPE_CHECKING` guard for the annotation and accept a plain `WorkflowDocumentation` instance at runtime. At runtime, the caller that already has `[llm]` installed will pass the object; the renderer just calls `.intent`, `.data_flow`, `.tool_notes`, `.risks` on it.

### Pattern 5: strip_noise integration in ContextBuilder (D-11/D-13)

```python
# Update to src/alteryx_diff/llm/context_builder.py (build_from_workflow only)
from alteryx_diff.normalizer._strip import strip_noise

# In build_from_workflow, change the tools list comprehension:
tools = [
    {
        "tool_id": int(node.tool_id),
        "tool_type": node.tool_type,
        "config": strip_noise(node.config),  # D-11: was node.config directly
    }
    for node in doc.nodes
]
```

### Anti-Patterns to Avoid

- **`from langgraph.graph.graph import CompiledGraph`:** This module path does NOT exist in langgraph 1.1. Use `from langgraph.graph.state import CompiledStateGraph` for type annotations, or omit the return type annotation and use `TYPE_CHECKING` guard.
- **Pydantic BaseModel as StateGraph state:** Not supported in langgraph 1.x. State must be `TypedDict`.
- **Top-level import of `langchain` in `doc_renderer.py`:** The renderer is in the core package. A top-level LLM import breaks the 251-test suite for users without `[llm]` extras.
- **`asyncio.run()` inside an async function:** Raises `RuntimeError: This event loop is already running`. The `ainvoke` call is `await`-ed directly inside `generate_documentation`.
- **Forgetting to initialize all TypedDict keys on first invoke:** LangGraph 1.1 requires all state keys to be present in the initial dict passed to `ainvoke`. Missing keys raise `KeyError` inside node functions.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured JSON output from LLM | Custom JSON parsing / regex extraction | `llm.with_structured_output(WorkflowDocumentation, method="json_schema")` | Handles schema enforcement, tool-calling fallback, retry on parse error internally |
| Provider-agnostic LLM calls | `if isinstance(llm, ChatOllama)` dispatch | `BaseChatModel.ainvoke([messages])` — polymorphic | All `BaseChatModel` subclasses share the same interface |
| Markdown rendering of structured data | Custom f-string template | Jinja2 `Environment` (already in project, used by HTMLRenderer) | Autoescaping, whitespace control, consistent with existing patterns |
| Token budget checking | `len(str(context)) / 4` approximation | `from langchain_core.messages.utils import count_tokens_approximately` | Verified available; handles message structure correctly |

**Key insight:** `with_structured_output(method="json_schema")` is the canonical pattern for Ollama and any provider that supports JSON schema constraints. Using it eliminates custom parsing entirely. The `include_raw=True` variant provides the raw `AIMessage` for debugging when `parsing_error` is set.

---

## Common Pitfalls

### Pitfall 1: Wrong CompiledGraph Import Path
**What goes wrong:** `from langgraph.graph.graph import CompiledGraph` raises `ModuleNotFoundError` at runtime.
**Why it happens:** ARCHITECTURE.md uses this path, but langgraph 1.1 restructured module layout. The compiled state graph type is `CompiledStateGraph` from `langgraph.graph.state`.
**How to avoid:** Use `from langgraph.graph.state import CompiledStateGraph` for the return type annotation on `build_doc_graph`. Or use `TYPE_CHECKING` guard entirely and annotate as string literal `"CompiledStateGraph"`.
**Verified:** `from langgraph.graph.state import CompiledStateGraph` imports successfully in the project venv.

### Pitfall 2: Incomplete TypedDict Initial State
**What goes wrong:** `KeyError: 'topology_notes'` when a node attempts `state["topology_notes"]` on the first invocation.
**Why it happens:** LangGraph 1.1 does not auto-fill missing TypedDict keys with defaults. Unlike dataclasses, TypedDict has no default values.
**How to avoid:** Always pass all TypedDict keys in the initial state dict to `ainvoke`. `generate_documentation` must initialize every field.
**Warning signs:** `KeyError` in node function body on first call.

### Pitfall 3: Top-Level LLM Import in DocRenderer
**What goes wrong:** `import alteryx_diff` fails for users without `[llm]` extras because `doc_renderer.py` has `from alteryx_diff.llm.models import WorkflowDocumentation` at module top.
**Why it happens:** `DocRenderer` is in `src/alteryx_diff/renderers/` — a core package. The core package cannot have hard LLM imports.
**How to avoid:** Use `TYPE_CHECKING` guard for `WorkflowDocumentation` import. The runtime duck-typing of Pydantic model attributes (`doc.intent`, `doc.tool_notes`, etc.) requires no import — Python does attribute lookup dynamically.

### Pitfall 4: Retry Appending State Without Re-initializing
**What goes wrong:** On retry, the previous intermediate state (topology_notes, tool_annotations, etc.) is passed through unchanged, causing the assemble_doc node to use stale data.
**Why it happens:** LangGraph nodes only update the keys they return — other keys persist from the prior run. A retry with `{**initial_state, "validation_error": str(e)}` correctly re-initializes all intermediate fields to empty strings so nodes re-compute them.
**How to avoid:** Always spread `initial_state` as the base for retry state, then overlay `validation_error`. Do not pass the previous `state` dict as the retry input.

### Pitfall 5: mypy strict mode and optional LLM types
**What goes wrong:** `mypy --strict` fails on `doc_graph.py` because `langchain_core` and `langgraph` imports are guarded (in `TYPE_CHECKING` or try/except) — mypy can't infer types.
**Why it happens:** `ignore_missing_imports = true` for `langchain.*` and `langgraph.*` is already in `pyproject.toml`, but strict mode still flags unresolved types inside the function bodies.
**How to avoid:** Add `# type: ignore[...]` where needed, or use `TYPE_CHECKING` guard for all LLM type annotations. The existing `pyproject.toml` mypy overrides already cover `langchain.*`, `langgraph.*`, `langchain_ollama.*` — no new mypy config needed.

### Pitfall 6: DocRenderer Type Annotation for `WorkflowDocumentation`
**What goes wrong:** Linter/mypy complains about unresolved `WorkflowDocumentation` in DocRenderer method signatures.
**Why it happens:** The type is gated under `TYPE_CHECKING` but the method signatures use it as a runtime annotation.
**How to avoid:** Use `from __future__ import annotations` at the top of `doc_renderer.py` — this defers all annotations to strings, so `TYPE_CHECKING`-gated imports work correctly with mypy's `ignore_missing_imports` override.

---

## Code Examples

### WorkflowDocumentation model

```python
# Source: CONTEXT.md D-02 (locked decision)
# src/alteryx_diff/llm/models.py
from __future__ import annotations

from pydantic import BaseModel, Field


class ToolNote(BaseModel):
    tool_id: int
    tool_type: str
    role: str = Field(description="One sentence: what this tool does in context")


class WorkflowDocumentation(BaseModel):
    workflow_name: str
    intent: str = Field(description="2-3 sentences: what the workflow accomplishes")
    data_flow: str = Field(description="Prose: how data moves source-to-sink")
    tool_notes: list[ToolNote]
    risks: list[str] = Field(description="Production concerns: data quality, config gotchas")
```

### DocState TypedDict

```python
# Source: STACK.md verified LangGraph pattern + D-09
from typing_extensions import TypedDict

class DocState(TypedDict):
    context: dict          # ContextBuilder output
    topology_notes: str    # analyze_topology output
    tool_annotations: str  # annotate_tools output (JSON string)
    risk_notes: str        # risk_scan output
    raw_doc_json: str      # assemble_doc output — JSON string of WorkflowDocumentation
    validation_error: str  # empty on first pass; str(ValidationError) on retry
```

### Async ainvoke (verified working)

```python
# Source: verified in project venv (2026-04-04)
result: DocState = await graph.ainvoke({
    "context": context_dict,
    "topology_notes": "",
    "tool_annotations": "",
    "risk_notes": "",
    "raw_doc_json": "",
    "validation_error": "",
})
```

### ChatOllama with structured output

```python
# Source: STACK.md + verified via import check (2026-04-04)
from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseChatModel

llm: BaseChatModel = ChatOllama(model="llama3", temperature=0)
structured_llm = llm.with_structured_output(
    WorkflowDocumentation,
    method="json_schema",  # recommended for Ollama
)
result: WorkflowDocumentation = await structured_llm.ainvoke(messages)
```

### OpenRouter usage (provider-agnostic, no special adapter)

```python
# Source: CONTEXT.md D-16
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="mistralai/mistral-7b-instruct",
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-...",
)
# Same generate_documentation() call — no changes needed
doc = await generate_documentation(context, llm)
```

### DocRenderer Markdown template (recommended structure)

```markdown
# {workflow_name}

## Intent
{intent}

## Data Flow
{data_flow}

## Tool Inventory
| Tool ID | Type | Role |
|---------|------|------|
| {tool_id} | {tool_type} | {role} |

## Production Risks
- {risk_1}
- {risk_2}
```

### DocRenderer HTML fragment (recommended structure)

```html
<section class="workflow-doc" id="workflow-doc">
  <h2>{workflow_name}</h2>
  <h3>Intent</h3>
  <p>{intent}</p>
  <h3>Data Flow</h3>
  <p>{data_flow}</p>
  <h3>Tool Inventory</h3>
  <table>...</table>
  <h3>Production Risks</h3>
  <ul>...</ul>
</section>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `from langgraph.graph.graph import CompiledGraph` | `from langgraph.graph.state import CompiledStateGraph` | langgraph 1.x | ARCHITECTURE.md is stale on this import |
| Pydantic BaseModel as StateGraph state | TypedDict only for StateGraph state | langchain 1.x | Pydantic models are for LLM *output*, not graph state |
| `langchain~=0.3` pins | `langchain~=1.2` (1.2.15 current) | Released Nov 2025, stable April 2026 | PROJECT.md key decisions note is stale — use STACK.md |
| `langchain_community` for Ollama | `langchain_ollama` as dedicated package | ~2024 | `langchain-ollama 1.0.1` is the correct dependency; `langchain-community` should not be used for Ollama |

**Deprecated/outdated patterns in ARCHITECTURE.md (do not use):**
- Fan-out `annotate_tools` via `Send` API: rejected by D-08
- `langchain~=0.3` version pin: stale, replaced by `~=1.2`
- `from langgraph.graph.graph import CompiledGraph`: module doesn't exist in 1.1

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | yes | 3.12.4 (host); 3.13.x (.venv) | — |
| uv | Package management | yes | 0.10.10 | — |
| langchain | Pipeline | yes (via `--extra llm`) | 1.2.15 | — |
| langgraph | StateGraph | yes (via `--extra llm`) | 1.1.x | — |
| langchain-ollama | ChatOllama | yes (via `--extra llm`) | 1.0.1 | — |
| langchain-openai | OpenRouter/ChatOpenAI | yes (transitively, NOT declared) | ~0.3 | Must declare in pyproject.toml [llm] extras per D-17 |
| Ollama binary | Running local models | yes | 0.18.2 | Model must be pulled separately (`ollama pull llama3`) |
| pydantic v2 | WorkflowDocumentation model | yes (transitive) | 2.x | — |

**Missing dependencies with no fallback:**
- None — all required deps are installed.

**Action items:**
- `langchain-openai~=0.3` must be added to `pyproject.toml` `[project.optional-dependencies] llm` (D-17). Currently present transitively but not declared.
- Ollama `llama3` model must be pulled by user separately — not bundled. Document in tests.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run --extra llm pytest tests/llm/ -q` |
| Full suite command | `uv run --extra llm pytest tests/ -q` (skips llm tests without extras) |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-03 | DocumentationGraph 4-node pipeline runs | unit (mock LLM) | `uv run --extra llm pytest tests/llm/test_doc_graph.py -x` | No — Wave 0 |
| CORE-03 | `generate_documentation()` returns `WorkflowDocumentation` | unit (mock LLM) | `uv run --extra llm pytest tests/llm/test_doc_graph.py::test_generate_documentation -x` | No — Wave 0 |
| CORE-03 | Single-retry on ValidationError | unit (mock LLM that returns invalid JSON first) | `uv run --extra llm pytest tests/llm/test_doc_graph.py::test_retry_on_validation_error -x` | No — Wave 0 |
| CORE-03 | Provider-agnostic: any `BaseChatModel` works | unit (FakeLLM or MagicMock) | `uv run --extra llm pytest tests/llm/test_doc_graph.py::test_provider_agnostic -x` | No — Wave 0 |
| CORE-04 | `DocRenderer.to_markdown()` returns non-empty string | unit | `uv run --extra llm pytest tests/llm/test_doc_renderer.py::test_to_markdown -x` | No — Wave 0 |
| CORE-04 | `DocRenderer.to_html_fragment()` contains `<section>` tag | unit | `uv run --extra llm pytest tests/llm/test_doc_renderer.py::test_to_html_fragment -x` | No — Wave 0 |
| CORE-04 | `DocRenderer.write_markdown()` writes file | unit | `uv run --extra llm pytest tests/llm/test_doc_renderer.py::test_write_markdown -x` | No — Wave 0 |
| EVAL-01 | `ChatOllama` passes through `generate_documentation()` without error | unit (mock via `ainvoke` mock) | `uv run --extra llm pytest tests/llm/test_doc_graph.py::test_ollama_llm -x` | No — Wave 0 |
| D-11 | `build_from_workflow` applies `strip_noise` to tool config | unit | `uv run --extra llm pytest tests/llm/test_context_builder.py::test_build_from_workflow_strip_noise -x` | No — Wave 0 |

### Mock LLM Strategy (Claude's Discretion)

Use `langchain_core.language_models.fake.FakeListChatModel` (ships with langchain-core) or `MagicMock` with `AsyncMock` for `ainvoke`. Recommended: create a simple `FakeLLM` fixture in `tests/llm/conftest.py` that returns a pre-baked `WorkflowDocumentation` JSON string from `ainvoke`.

```python
# tests/llm/conftest.py
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_llm():
    """Mock BaseChatModel that returns a valid WorkflowDocumentation JSON."""
    llm = MagicMock()
    # Make with_structured_output return a mock that has ainvoke
    structured = MagicMock()
    structured.ainvoke = AsyncMock(return_value=sample_workflow_documentation())
    llm.with_structured_output = MagicMock(return_value=structured)
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="topology notes"))
    return llm
```

### Sampling Rate

- **Per task commit:** `uv run --extra llm pytest tests/llm/ -q`
- **Per wave merge:** `uv run pytest tests/ -q && uv run --extra llm pytest tests/llm/ -q`
- **Phase gate:** Both suites green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/llm/test_doc_graph.py` — covers CORE-03, EVAL-01
- [ ] `tests/llm/test_doc_renderer.py` — covers CORE-04
- [ ] `tests/llm/conftest.py` — shared `mock_llm` fixture + `sample_workflow_documentation` helper
- [ ] `tests/llm/test_context_builder.py::test_build_from_workflow_strip_noise` — new test case in existing file (covers D-11)

---

## Project Constraints (from CLAUDE.md)

- Release workflow: triggered by `v*` tag push from any branch; builds `AlterxyGitCompanion.exe` on Windows runner
- `npm ci --legacy-peer-deps` for frontend (Vite 8 / @tailwindcss/vite peer conflict)
- PyInstaller version format: `X.Y.Z.W` (four numeric parts)
- `permissions: contents: write` required on CI job for release uploads
- **Phase 24 is Python-only (no frontend changes)** — CLAUDE.md CI quirks do not affect this phase

---

## Open Questions

1. **`assemble_doc` node: use `with_structured_output` directly on full `WorkflowDocumentation`, or parse raw text?**
   - What we know: `with_structured_output(WorkflowDocumentation, method="json_schema")` is verified to work with ChatOllama
   - What's unclear: for large workflows (many tool_notes), the schema may exceed some models' JSON schema constraint window
   - Recommendation: use `with_structured_output` directly; if tool_notes exceed ~30 items, truncate in `annotate_tools` node (ARCHITECTURE.md suggests 50-tool cap in ContextBuilder)

2. **`annotate_tools` node: structured output or free-text then parse?**
   - What we know: D-04 says `tool_notes` is a structured list; a single LLM call for all tools is sufficient (D-08 rejects fan-out)
   - What's unclear: passing `list[ToolNote]` as the output schema for an intermediate node vs. passing all tool annotations as a JSON string in `DocState["tool_annotations"]`
   - Recommendation: use intermediate state field `tool_annotations: str` (serialized JSON), then pass to `assemble_doc` which constructs the final `WorkflowDocumentation` with validated `tool_notes`

3. **How should `validation_error` modify the retry prompts?**
   - What we know: D-10 says "appends the validation error to state context on retry"
   - What's unclear: each node's prompt vs. just `assemble_doc`'s prompt
   - Recommendation: only `assemble_doc` checks `state["validation_error"]`; other nodes re-run identically on retry (their intermediate state is reset by `generate_documentation`'s retry initialization)

---

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` — confirmed library versions, LangGraph StateGraph pattern, structured output, Ollama integration
- `.planning/research/ARCHITECTURE.md` — component map, build order, interface signatures (note: CompiledGraph import path stale — see Pitfall 1)
- `.planning/phases/24-documentation-graph-docrenderer-ollama/24-CONTEXT.md` — all locked decisions D-01 through D-18
- `.planning/phases/23-llm-foundation/23-CONTEXT.md` — Phase 23 locked decisions (D-01 through D-13)
- Environment probe (2026-04-04): `uv run --extra llm python -c "..."` — verified all imports, ainvoke pattern, CompiledStateGraph path

### Secondary (MEDIUM confidence)
- `src/alteryx_diff/llm/context_builder.py` — actual Phase 23 implementation, confirms D-11 change needed
- `src/alteryx_diff/renderers/html_renderer.py` — DocRenderer pattern to follow (Jinja2, stateless class, render method)
- `src/alteryx_diff/normalizer/_strip.py` — `strip_noise()` signature confirmed; safe to call on `node.config`

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via environment probe and PyPI in STACK.md
- Architecture: HIGH — LangGraph patterns verified via `uv run --extra llm` execution; TypedDict constraint and ainvoke confirmed
- Pitfalls: HIGH — CompiledGraph import path tested and confirmed wrong; top-level import pitfall verified via test suite structure
- DocRenderer: HIGH — follows established HTMLRenderer pattern; Jinja2 already in project

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days — langchain/langgraph are relatively stable at 1.x)
