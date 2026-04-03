# Architecture Research — LLM Documentation (April 2026)

**Researched:** 2026-04-02
**Confidence:** MEDIUM-HIGH (LangGraph patterns from official docs + community; FastAPI patterns HIGH from official docs)

---

## Component Map

### New Components

| Component | Path | Responsibility |
|-----------|------|---------------|
| `ContextBuilder` | `src/alteryx_diff/llm/context_builder.py` | Transforms `WorkflowDoc`/`DiffResult` dataclasses into token-efficient JSON dicts for LLM consumption. No raw XML ever reaches the LLM. |
| `DocumentationGraph` | `src/alteryx_diff/llm/doc_graph.py` | LangGraph compiled graph: `analyze_topology → annotate_tools → risk_scan → assemble_doc`. Returns `WorkflowDoc` Pydantic model. |
| `DocRenderer` | `src/alteryx_diff/renderers/doc_renderer.py` | Renders `WorkflowDoc` to Markdown (standalone) or HTML fragment (embedded in diff report). Follows same renderer protocol as `HTMLRenderer`. |
| `llm/__init__.py` | `src/alteryx_diff/llm/__init__.py` | Optional-import guard. Raises `ImportError` with install hint if `[llm]` extras absent. |
| `LLM router` | `app/routers/llm.py` | FastAPI router: `POST /api/llm/document` triggers background doc generation; `GET /api/llm/progress/{job_id}` streams SSE progress. |
| `RAGAS harness` | `tests/eval/ragas_eval.py` | Faithfulness + factual grounding evaluation. Not part of the main package; dev-only. |

### Modified Components

| Component | Path | Change |
|-----------|------|--------|
| `cli.py` | `src/alteryx_diff/cli.py` | Add `document` subcommand via `app.add_typer(document_app, name="document")`. |
| `pipeline/pipeline.py` | `src/alteryx_diff/pipeline/pipeline.py` | No change to `pipeline.run()`. The LLM layer consumes `DiffResult` as input — it does not modify the pipeline. |
| `history.py` router | `app/routers/history.py` | Add optional `?doc=true` query param that triggers background doc generation alongside the existing diff response. |
| `pyproject.toml` | `pyproject.toml` | Add `[project.optional-dependencies] llm = [...]` group with `langchain~=0.3`, `langgraph~=1.1`, `langchain-openai`, `langchain-community` (Ollama). |

---

## Data Flow

```
WorkflowDoc / DiffResult
        |
        v
  ContextBuilder.build()
        |  (structured JSON dict, no raw XML)
        v
  DocumentationGraph.ainvoke(state)
  +-----------------------------------------+
  |  analyze_topology  (sync-safe, fast)    |
  |         |                               |
  |         v                               |
  |  annotate_tools  (fan-out via Send API) |
  |  [tool_1] [tool_2] ... [tool_N]         |
  |         | (Semaphore: max 5 concurrent) |
  |         v  reducer merges annotations   |
  |  risk_scan  (single LLM call)           |
  |         |                               |
  |  assemble_doc  (single LLM call)        |
  +-----------------------------------------+
        |
        v
  WorkflowDoc  (Pydantic model, Python-validated)
        |
        +---> DocRenderer.to_markdown()  -->  docs/workflow.md
        +---> DocRenderer.to_html_fragment()  -->  embedded in diff HTML
```

---

## LangGraph Async Pattern

**Confidence:** MEDIUM (ainvoke pattern confirmed via official docs mirror and community; exact v1.1 signature consistent across sources)

### State Definition

```python
# src/alteryx_diff/llm/doc_graph.py
from typing import Annotated, TypedDict
from langgraph.graph import START, END, StateGraph
from langgraph.types import Send
import operator

class DocState(TypedDict):
    context: dict                          # built by ContextBuilder
    topology_summary: str                  # from analyze_topology
    tool_annotations: Annotated[list[dict], operator.add]  # reducer: append
    risk_notes: str
    assembled_doc: str

class ToolAnnotationState(TypedDict):
    """Private state for a single annotate_tools worker."""
    tool_context: dict
    annotation: str
```

### Node Definitions (Async)

```python
import asyncio
from langchain_core.language_models import BaseChatModel

_semaphore = asyncio.Semaphore(5)  # module-level; max 5 concurrent LLM calls

async def analyze_topology(state: DocState) -> dict:
    # No LLM call -- pure Python analysis of context dict
    summary = _build_topology_summary(state["context"])
    return {"topology_summary": summary}

async def annotate_single_tool(state: ToolAnnotationState) -> dict:
    """Worker node. Called once per tool via Send API."""
    async with _semaphore:
        result = await llm.ainvoke([...])
    return {"tool_annotations": [{"tool_id": state["tool_context"]["id"],
                                   "annotation": result.content}]}

def fan_out_tools(state: DocState) -> list[Send]:
    """Conditional edge: emit one Send per tool."""
    return [
        Send("annotate_single_tool", {"tool_context": tool})
        for tool in state["context"]["tools"]
    ]

async def risk_scan(state: DocState) -> dict:
    result = await llm.ainvoke([...])
    return {"risk_notes": result.content}

async def assemble_doc(state: DocState) -> dict:
    result = await llm.ainvoke([...])
    return {"assembled_doc": result.content}
```

### Graph Compilation

```python
def build_doc_graph(llm: BaseChatModel) -> CompiledGraph:
    builder = StateGraph(DocState)
    builder.add_node("analyze_topology", analyze_topology)
    builder.add_node("annotate_single_tool", annotate_single_tool)
    builder.add_node("risk_scan", risk_scan)
    builder.add_node("assemble_doc", assemble_doc)

    builder.add_edge(START, "analyze_topology")
    builder.add_conditional_edges("analyze_topology", fan_out_tools, ["annotate_single_tool"])
    builder.add_edge("annotate_single_tool", "risk_scan")
    builder.add_edge("risk_scan", "assemble_doc")
    builder.add_edge("assemble_doc", END)

    return builder.compile()
```

### Async Invocation (canonical call)

```python
# Confirmed pattern: await graph.ainvoke(initial_state)
result: DocState = await doc_graph.ainvoke({
    "context": context_builder.build(workflow_doc),
    "topology_summary": "",
    "tool_annotations": [],
    "risk_notes": "",
    "assembled_doc": "",
})
```

**Key facts (HIGH confidence):**
- `ainvoke()` is the async counterpart to `invoke()`. Both accept `(state, config=None)`.
- Node functions must be `async def` to avoid blocking the event loop during LLM calls.
- `astream()` is available for token-level streaming from the graph directly.

---

## FastAPI Integration

### Non-Blocking HTML Response

The existing `pipeline.run()` is synchronous (CPU-bound XML parsing + diffing). LangGraph graph invocations are async. These are separate concerns and must be handled differently.

**Pattern A: Sync pipeline from async endpoint (use `run_in_threadpool`)**

```python
# app/routers/history.py
from starlette.concurrency import run_in_threadpool
from alteryx_diff.pipeline import pipeline

@router.get("/api/history/{sha}/diff")
async def get_diff(sha: str):
    # Offload sync pipeline.run() to thread pool -- does NOT block event loop
    diff_result = await run_in_threadpool(pipeline.run, DiffRequest(...))
    html = HTMLRenderer().render(diff_result)
    return HTMLResponse(html)
```

**Why `run_in_threadpool` over `run_in_executor`:**
- `run_in_threadpool` (from `starlette.concurrency`) is the FastAPI-idiomatic choice.
- It uses the default executor, requires no manual executor setup, and is integrated with FastAPI's design.
- Reserve `asyncio.get_running_loop().run_in_executor(pool, ...)` only if you need a `ProcessPoolExecutor` for CPU-bound work with separate processes.

**Pattern B: Async LangGraph graph from async endpoint (direct await)**

```python
@router.post("/api/llm/document")
async def start_doc_generation(request: DocRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    sse_queues[job_id] = asyncio.Queue()
    background_tasks.add_task(_run_doc_graph, job_id, request)
    return {"job_id": job_id}

async def _run_doc_graph(job_id: str, request: DocRequest):
    queue = sse_queues[job_id]
    try:
        result = await doc_graph.ainvoke({...})
        await queue.put({"step": "complete", "doc": result["assembled_doc"]})
    except Exception as e:
        await queue.put({"step": "error", "message": str(e)})
```

**Do NOT use `asyncio.run()` inside an async endpoint.** `asyncio.run()` creates a new event loop and raises `RuntimeError: This event loop is already running` inside FastAPI's async context.

### SSE Streaming for LLM Output

The project already uses SSE for the file watcher (`app/routers/watch.py`). Apply the same queue-based pattern for LLM progress.

**Two-endpoint pattern (proven for LLM streaming):**

```python
# app/routers/llm.py
import asyncio
import uuid
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
import json

router = APIRouter()
_active_jobs: dict[str, asyncio.Queue] = {}

@router.post("/api/llm/document")
async def start_doc(background_tasks: BackgroundTasks, sha: str, workflow_path: str):
    """Returns immediately with job_id. Client then opens SSE stream."""
    job_id = str(uuid.uuid4())
    _active_jobs[job_id] = asyncio.Queue()
    background_tasks.add_task(_generate_doc, job_id, sha, workflow_path)
    return {"job_id": job_id}

@router.get("/api/llm/progress/{job_id}")
async def stream_progress(job_id: str):
    """SSE endpoint -- streams progress until 'complete' or 'error'."""
    async def event_gen():
        if job_id not in _active_jobs:
            yield f'data: {json.dumps({"step": "error", "message": "job not found"})}\n\n'
            return
        queue = _active_jobs[job_id]
        while True:
            msg = await queue.get()
            yield f'data: {json.dumps(msg)}\n\n'
            if msg.get("step") in ("complete", "error"):
                _active_jobs.pop(job_id, None)
                break

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache",
                                       "X-Accel-Buffering": "no"})

async def _generate_doc(job_id: str, sha: str, workflow_path: str):
    queue = _active_jobs.get(job_id)
    if not queue:
        return
    try:
        await queue.put({"step": "analyzing", "progress": 10})
        context = context_builder.build(...)
        await queue.put({"step": "annotating_tools", "progress": 30})
        result = await doc_graph.ainvoke({"context": context, ...})
        await queue.put({"step": "complete", "progress": 100, "doc": result["assembled_doc"]})
    except Exception as e:
        await queue.put({"step": "error", "message": str(e)})
```

**Client-side (React/TypeScript):**

```typescript
const es = new EventSource(`/api/llm/progress/${jobId}`);
es.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.step === "complete") { es.close(); setDoc(msg.doc); }
  else if (msg.step === "error") { es.close(); setError(msg.message); }
  else { setProgress(msg.progress); }
};
```

**Important nuance:** When combining `BackgroundTasks` + `StreamingResponse`, FastAPI closes the connection only after the background task completes, not after the streaming generator exhausts. The two-endpoint queue pattern avoids this: the client opens the SSE endpoint independently, and the background task pushes to the queue without being coupled to the HTTP response lifecycle.

---

## CLI Integration

**Typer subcommand pattern (official docs, HIGH confidence):**

```python
# src/alteryx_diff/cli.py  (existing file -- minimal change)
import typer
from alteryx_diff.cli_document import document_app  # new module

app = typer.Typer(name="alteryx-diff")
app.add_typer(document_app, name="document")  # adds `alteryx-diff document`

@app.command()
def diff(
    base: Path = typer.Argument(..., help="Base .yxmd file"),
    head: Path = typer.Argument(..., help="Head .yxmd file"),
    ...
):
    ...
```

```python
# src/alteryx_diff/cli_document.py  (new file)
import typer
from pathlib import Path

document_app = typer.Typer(help="Generate LLM documentation for a workflow.")

@document_app.command()
def workflow(
    path: Path = typer.Argument(..., help="Path to .yxmd workflow file"),
    output: Path = typer.Option(None, "--output", "-o", help="Output .md path"),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m"),
    ollama: bool = typer.Option(False, "--ollama", help="Use local Ollama model"),
):
    """Generate developer documentation for a single workflow."""
    from alteryx_diff.llm import require_llm_deps  # late import
    require_llm_deps()
    ...
```

This produces:
- `alteryx-diff diff base.yxmd head.yxmd` (existing, unchanged)
- `alteryx-diff document workflow.yxmd` (new)

**Key:** `app.add_typer(document_app, name="document")` groups all document subcommands under `document`. The `name` parameter sets the CLI command group name. If `name` is omitted, commands are flattened to the top level (avoid this).

---

## Parallel Annotation with Rate Limiting

### Send API + asyncio.Semaphore Pattern

LangGraph's `Send` API enables map-reduce: fan-out over a list (one `Send` per tool), with a reducer on the receiving state key to aggregate results. `max_concurrency` in the invocation config provides a first layer of concurrency control. `asyncio.Semaphore` inside each worker node provides a second, finer-grained layer for LLM API rate limits.

```python
# Semaphore: module-level singleton, shared across all worker invocations
_llm_semaphore = asyncio.Semaphore(5)  # max 5 simultaneous LLM calls

async def annotate_single_tool(state: ToolAnnotationState) -> dict:
    """LangGraph worker node. Invoked once per tool by Send API."""
    async with _llm_semaphore:
        # Only 5 of these run concurrently regardless of how many tools exist
        result = await llm.ainvoke([
            SystemMessage("Annotate this Alteryx tool concisely."),
            HumanMessage(json.dumps(state["tool_context"])),
        ])
    return {"tool_annotations": [
        {"tool_id": state["tool_context"]["id"], "text": result.content}
    ]}

def fan_out_to_tools(state: DocState) -> list[Send]:
    """Conditional edge function: creates one Send per tool."""
    return [
        Send("annotate_single_tool", {"tool_context": tool})
        for tool in state["context"]["tools"]
    ]
```

```python
# Graph construction -- conditional_edges from analyze_topology
builder.add_conditional_edges(
    "analyze_topology",
    fan_out_to_tools,
    ["annotate_single_tool"],  # destination node names the edge can target
)
```

```python
# Invocation with graph-level concurrency cap (belt-and-suspenders)
result = await doc_graph.ainvoke(
    initial_state,
    config={"max_concurrency": 10},  # LangGraph internal cap
)
```

**State reducer for fan-in:**

```python
from typing import Annotated
import operator

class DocState(TypedDict):
    tool_annotations: Annotated[list[dict], operator.add]  # append, not overwrite
```

`operator.add` as the reducer means each worker's `{"tool_annotations": [...]}` return is appended to the list rather than replacing it. This is the correct LangGraph pattern for fan-out aggregation.

**Two-layer rate limiting strategy:**
1. `config={"max_concurrency": N}` — LangGraph-level cap on total concurrent node executions.
2. `asyncio.Semaphore(5)` — LLM API-level cap inside the node; protects against bursts from multiple graph runs sharing the same process.

**LangGraph does NOT natively rate-limit LLM API calls.** You must implement `asyncio.Semaphore` yourself inside the node function. `max_concurrency` in the config limits concurrent node execution at the graph level, not the API call level within nodes.

---

## Optional Import Pattern

**Pattern (HIGH confidence — established Python community standard):**

```python
# src/alteryx_diff/llm/__init__.py

def require_llm_deps() -> None:
    """
    Call at the entry point of any LLM feature.
    Raises ImportError with a helpful install hint if [llm] extras are missing.
    """
    missing = []
    try:
        import langchain  # noqa: F401
    except ImportError:
        missing.append("langchain~=0.3")
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

```python
# Usage in CLI (late import -- not at module top level)
@document_app.command()
def workflow(path: Path, ...):
    from alteryx_diff.llm import require_llm_deps
    require_llm_deps()  # Fails fast with a clear message before any work
    from alteryx_diff.llm.doc_graph import build_doc_graph
    ...
```

```python
# Usage in FastAPI router (lazy check at startup)
try:
    from alteryx_diff.llm import require_llm_deps
    require_llm_deps()
    _llm_available = True
except ImportError:
    _llm_available = False

@router.post("/api/llm/document")
async def start_doc(...):
    if not _llm_available:
        raise HTTPException(503, "LLM features not installed. Add [llm] extras.")
    ...
```

**Rules:**
- Never import from `alteryx_diff.llm.*` at module top level in CLI or FastAPI app startup.
- Always guard with `require_llm_deps()` before any use.
- Use `TYPE_CHECKING` guard if type annotations reference LLM types.

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from alteryx_diff.llm.doc_graph import DocumentationGraph
```

---

## Git Commit Strategy for Generated Docs

**Recommendation: Separate follow-up commit (MEDIUM confidence)**

Generated `docs/workflow.md` should be committed in a dedicated follow-up commit, not in the same commit as the `.yxmd` workflow file. Reasons:

1. **Semantic separation:** The `.yxmd` commit represents a human intent (a workflow save). The doc commit is machine-generated output. Mixing them obscures the commit graph.
2. **Auditability:** Separate commits allow the doc commit to carry `[generated]` or a conventional commit type (`docs(llm): ...`), making it filterable in `git log`.
3. **Regeneration:** If the LLM model changes or the doc is regenerated, the diff is clean — it touches only the `docs/` file.
4. **Rollback safety:** Reverting a workflow save does not accidentally revert auto-generated docs.

**Implementation in companion app:**

```
Commit 1 (user action — synchronous):
  src/workflows/workflow.yxmd        <- human save via "Save Version"
  message: "feat: save workflow.yxmd"

Commit 2 (app-generated — async, after LLM completes):
  docs/workflow.md                   <- LLM-generated
  message: "docs(llm): auto-document workflow.yxmd [generated]"
```

The companion app should:
- Trigger doc generation in the background after a save.
- Commit `docs/workflow.md` as a separate commit once generation completes.
- Skip doc commit if generation fails (non-blocking; save must always succeed).

**Note on "generated files should not be committed" principle:** This applies to build artifacts (`.pyc`, dist bundles). Human-readable documentation that adds governance value IS the product of the LLM feature and is committed intentionally. The `[generated]` tag in the commit message makes provenance clear.

---

## Build Order

Dependencies flow in one direction. Build inner modules first.

```
Layer 0 (no internal deps):
  src/alteryx_diff/llm/__init__.py          (import guard only)
  src/alteryx_diff/llm/context_builder.py   (depends only on existing models)

Layer 1 (depends on Layer 0):
  src/alteryx_diff/llm/doc_graph.py         (depends on context_builder + LangGraph)
  src/alteryx_diff/renderers/doc_renderer.py (depends on WorkflowDoc model)

Layer 2 (depends on Layers 0-1):
  src/alteryx_diff/cli_document.py          (depends on doc_graph + doc_renderer)
  app/routers/llm.py                        (depends on doc_graph + SSE pattern)

Layer 3 (integration):
  src/alteryx_diff/cli.py                   (add_typer for document_app)
  app/main.py                               (include llm router)
  app/frontend/                             (SSE client + progress UI)

Layer 4 (eval, last):
  tests/eval/ragas_eval.py                  (depends on everything above)
```

**Dependency graph:**

```
pyproject.toml [llm] extras
       |
       +-- langchain~=0.3
       +-- langgraph~=1.1
       +-- langchain-community (Ollama)
              |
              v
  llm/__init__.py (require_llm_deps guard)
              |
              v
  llm/context_builder.py ---- models/ (WorkflowDoc, DiffResult)
              |
              v
  llm/doc_graph.py ----------- LangGraph StateGraph + Send + Semaphore
              |
       +------+------+
       v             v
  cli_document.py  app/routers/llm.py
       |             |
       v             v
  cli.py          app/main.py
  (add_typer)     (include_router)
```

---

## Key Interface Signatures

### ContextBuilder

```python
# src/alteryx_diff/llm/context_builder.py
from dataclasses import dataclass
from alteryx_diff.models import WorkflowDoc, DiffResult

@dataclass
class ContextBuilder:
    """
    Transforms structured Python objects into token-efficient dicts
    suitable for LLM consumption. Raw XML never crosses this boundary.
    """
    max_tools: int = 50           # cap for annotation fan-out
    include_positions: bool = False

    def build_from_workflow(self, doc: WorkflowDoc) -> dict:
        """For `alteryx-diff document` -- single workflow intent doc."""
        return {
            "workflow_name": doc.name,
            "tool_count": len(doc.tools),
            "tools": [self._serialize_tool(t) for t in doc.tools[:self.max_tools]],
            "connections": self._serialize_connections(doc.connections),
            "topology": self._infer_topology(doc),
        }

    def build_from_diff(self, result: DiffResult) -> dict:
        """For `alteryx-diff diff --doc` -- change narrative."""
        return {
            "summary": {
                "added": len(result.added_tools),
                "removed": len(result.removed_tools),
                "modified": len(result.modified_tools),
            },
            "changes": [self._serialize_change(c) for c in result.changes],
        }

    def _serialize_tool(self, tool) -> dict:
        """Use Pydantic model_dump() if tool is a Pydantic model,
           otherwise custom dict projection to exclude XML noise."""
        if hasattr(tool, "model_dump"):
            return tool.model_dump(exclude={"raw_xml", "position"})
        return {"id": tool.tool_id, "type": tool.tool_type, "config": tool.config}
```

### DocumentationGraph

```python
# src/alteryx_diff/llm/doc_graph.py
from langchain_core.language_models import BaseChatModel
from langgraph.graph.graph import CompiledGraph

def build_doc_graph(llm: BaseChatModel) -> CompiledGraph:
    """
    Returns a compiled LangGraph graph.
    Caller must: result = await graph.ainvoke(initial_state)
    """
    ...

async def generate_documentation(
    context: dict,
    llm: BaseChatModel,
) -> WorkflowDoc:
    """
    Convenience wrapper. Builds graph, invokes, validates output.
    Raises ValidationError if assembled doc fails Pydantic validation.
    Single retry on ValidationError (per v1.2 key decision).
    """
    graph = build_doc_graph(llm)
    state = await graph.ainvoke({"context": context, ...})
    try:
        return WorkflowDoc.model_validate_json(state["assembled_doc"])
    except ValidationError as e:
        # Single retry with error context appended to state
        state = await graph.ainvoke({
            "context": context,
            "validation_error": str(e),
            ...
        })
        return WorkflowDoc.model_validate_json(state["assembled_doc"])
```

### DocRenderer

```python
# src/alteryx_diff/renderers/doc_renderer.py
from pathlib import Path
from alteryx_diff.models import WorkflowDoc

class DocRenderer:
    """
    Renders WorkflowDoc to output formats.
    Stateless; follows same renderer protocol as HTMLRenderer.
    """

    def to_markdown(self, doc: WorkflowDoc) -> str:
        """Standalone .md file output for `alteryx-diff document` CLI."""
        ...

    def to_html_fragment(self, doc: WorkflowDoc) -> str:
        """HTML <section> fragment for embedding in diff report."""
        ...

    def write_markdown(self, doc: WorkflowDoc, output_path: Path) -> Path:
        """Writes .md and returns path. Used by CLI."""
        content = self.to_markdown(doc)
        output_path.write_text(content, encoding="utf-8")
        return output_path
```

---

## Sources

- LangGraph async execution (mirror): https://www.baihezi.com/mirrors/langgraph/how-tos/async/index.html
- LangGraph Send API (DEV.to): https://dev.to/sreeni5018/leveraging-langgraphs-send-api-for-dynamic-and-parallel-workflow-execution-4pgd
- LangGraph parallelization (Medium): https://medium.com/codetodeploy/built-with-langgraph-11-parallelization-efa2ccdba2e0
- LangGraph map-reduce (Medium): https://medium.com/@astropomeai/implementing-map-reduce-with-langgraph-creating-flexible-branches-for-parallel-execution-b6dc44327c0e
- LangGraph Send API (Medium): https://medium.com/ai-engineering-bootcamp/map-reduce-with-the-send-api-in-langgraph-29b92078b47d
- FastAPI run_in_threadpool vs run_in_executor: https://sentry.io/answers/fastapi-difference-between-run-in-executor-and-run-in-threadpool/
- FastAPI SSE + background tasks (DEV.to): https://dev.to/zachary62/build-an-llm-web-app-in-python-from-scratch-part-4-fastapi-background-tasks-sse-21g4
- FastAPI concurrency (official): https://fastapi.tiangolo.com/async/
- Typer subcommands (official): https://typer.tiangolo.com/tutorial/subcommands/add-typer/
- Pydantic serialization (official): https://docs.pydantic.dev/latest/concepts/serialization/
- Conventional Commits: https://www.conventionalcommits.org/en/v1.0.0/
- Optional imports (Python Discuss): https://discuss.python.org/t/optional-imports-for-optional-dependencies/104760
