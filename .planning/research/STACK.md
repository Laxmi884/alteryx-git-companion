# Stack Research — LLM Documentation (April 2026)

**Project:** Alteryx Git Companion v1.2 — LLM-powered workflow documentation
**Researched:** 2026-04-02
**Confidence:** MEDIUM-HIGH (versions verified from PyPI; API patterns cross-referenced across multiple sources)

> This document supplements the original STACK.md (v1.0 XML diff stack) with LLM-specific additions for the v1.2 milestone.

---

## CRITICAL VERSION ALERT

The PROJECT.md Key Decisions table states `langchain~=0.3 + langgraph~=1.1` with the rationale "langchain>=1.2 does not exist." **This is incorrect as of April 2026.** The current production-stable version is `langchain==1.2.14`. See the Confirmed Library Versions section below.

**Action required:** The version pin in pyproject.toml should target `langchain~=1.2`, not `langchain~=0.3`. The PROJECT.md Key Decisions rationale note is stale and should be updated.

---

## Confirmed Library Versions

| Library | Current Version | Release Date | Source |
|---------|----------------|--------------|--------|
| langchain | **1.2.14** | Mar 31, 2026 | PyPI |
| langchain-core | **1.2.24** | Apr 1, 2026 | PyPI |
| langchain-community | **0.4.1** | 2026 | PyPI |
| langgraph | **1.1.4** | Mar 31, 2026 | PyPI |
| langchain-ollama | **1.0.1** | Dec 12, 2025 | PyPI |
| ragas | **0.4.3** | Jan 13, 2026 | PyPI |

**Confidence:** HIGH — all versions fetched directly from PyPI pages.

**Sources:**
- https://pypi.org/project/langchain/
- https://pypi.org/project/langgraph/
- https://pypi.org/project/langchain-ollama/
- https://pypi.org/project/ragas/

---

## Recommended LLM Stack

| Technology | Version Pin | Purpose | Why |
|------------|-------------|---------|-----|
| langchain | `~=1.2` | Core LLM abstraction layer (chat models, LCEL chains, structured output) | Stable production release (1.0 milestone shipped late 2025); `with_structured_output` still present on `BaseChatModel`; LCEL pipe operator retained |
| langchain-core | `~=1.2` (transitive) | Base interfaces (Runnable, BaseChatModel, messages) | Pulled in by langchain; pin major only |
| langgraph | `~=1.1` | `DocumentationGraph` StateGraph pipeline | 1.1.4 is current stable; `StateGraph` + `START`/`END` API is unchanged from 1.0 to 1.1 |
| langchain-ollama | `~=1.0` | Offline/air-gapped LLM execution via local Ollama | 1.0.1 supports `with_structured_output` with `method='json_schema'` (default since 0.3); good Pydantic v2 support |
| ragas | `~=0.4` | Faithfulness evaluation harness | 0.4.3 current; use `SingleTurnSample` + `EvaluationDataset` API (legacy `evaluate()` call deprecated in 0.4, removed in 1.0) |
| tiktoken | `>=0.7` | Token budget estimation for non-Ollama providers | Lightweight; used by langchain-core internally |

**What NOT to add:**
- `langchain-openai` — only add if/when cloud provider integration is scoped. Not needed for Ollama-only v1.2.
- `langchain-classic` — the backward-compat shim for old 0.3 patterns. Do not depend on this; use 1.x native patterns.
- `langsmith` — tracing/observability SDK; out of scope for v1.2.

---

## LangGraph StateGraph Pattern

**Confidence:** HIGH — verified against official LangGraph docs (https://docs.langchain.com/oss/python/langgraph/graph-api) which returned working code.

This is the exact import and pattern for a linear 4-node `DocumentationGraph` using `langgraph>=1.0`:

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

# --- State definition (TypedDict only — Pydantic models NOT supported in v1.x StateGraph) ---
class DocumentationState(TypedDict):
    context: str            # Built by ContextBuilder, passed in at invoke() time
    topology_notes: str     # Output of analyze_topology node
    tool_annotations: str   # Output of annotate_tools node
    risk_notes: str         # Output of risk_scan node
    final_doc: str          # Output of assemble_doc node

# --- Node functions (each receives full state, returns partial update dict) ---
def analyze_topology(state: DocumentationState) -> dict:
    # Call LLM here, return partial state update
    return {"topology_notes": "..."}

def annotate_tools(state: DocumentationState) -> dict:
    return {"tool_annotations": "..."}

def risk_scan(state: DocumentationState) -> dict:
    return {"risk_notes": "..."}

def assemble_doc(state: DocumentationState) -> dict:
    return {"final_doc": "..."}

# --- Build and compile ---
builder = StateGraph(DocumentationState)

builder.add_node("analyze_topology", analyze_topology)
builder.add_node("annotate_tools", annotate_tools)
builder.add_node("risk_scan", risk_scan)
builder.add_node("assemble_doc", assemble_doc)

builder.add_edge(START, "analyze_topology")
builder.add_edge("analyze_topology", "annotate_tools")
builder.add_edge("annotate_tools", "risk_scan")
builder.add_edge("risk_scan", "assemble_doc")
builder.add_edge("assemble_doc", END)

graph = builder.compile()

# --- Invoke ---
result = graph.invoke({"context": "<ContextBuilder output here>"})
final_markdown = result["final_doc"]
```

**Key constraints:**
- State must be `TypedDict`. Pydantic `BaseModel` is NOT supported for `StateGraph` state in langchain 1.x — this is a breaking change from some pre-1.0 patterns. Use `TypedDict` for graph state; use Pydantic for structured LLM output.
- `.compile()` is mandatory before `.invoke()`.
- Nodes return partial dicts; LangGraph merges them into the state.
- For async: use `await graph.ainvoke(...)` (all nodes become `async def`).

---

## Structured Output Pattern

**Confidence:** HIGH — verified from reference docs and confirmed active in March 2026 usage reports.

`with_structured_output` is still the canonical pattern in langchain 1.2.x. It exists on `BaseChatModel` in `langchain-core`. The `create_agent` abstraction is for agent loops; for a linear pipeline like `DocumentationGraph`, use `with_structured_output` directly.

```python
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama

# --- Define output schema with Pydantic v2 ---
class WorkflowSummary(BaseModel):
    """Structured summary of an Alteryx workflow."""
    purpose: str = Field(description="One-sentence description of what this workflow does")
    input_sources: list[str] = Field(description="Data sources consumed by this workflow")
    output_targets: list[str] = Field(description="Data targets produced by this workflow")
    tool_count: int = Field(description="Total number of tools in the workflow")
    risk_flags: list[str] = Field(description="Potential data quality or logic risks, if any")

# --- Bind structured output to model ---
model = ChatOllama(model="llama3.1", temperature=0)
structured_model = model.with_structured_output(WorkflowSummary)

# Basic invocation
result: WorkflowSummary = structured_model.invoke(
    "Analyze this workflow context and produce a structured summary:\n\n{context}"
)
print(result.purpose)   # dot-access on Pydantic model

# --- With retry on ValidationError (PROJECT.md: single-retry pattern) ---
from langchain_core.exceptions import OutputParserException

structured_model_with_raw = model.with_structured_output(
    WorkflowSummary,
    include_raw=True,   # Returns {"raw": AIMessage, "parsed": WorkflowSummary, "parsing_error": ...}
)

raw_result = structured_model_with_raw.invoke("...")
if raw_result["parsing_error"]:
    # Single retry with explicit JSON instruction in prompt
    result = structured_model.invoke("Return valid JSON matching the schema. " + "...")
else:
    result = raw_result["parsed"]
```

**Pydantic v2 specifics:** `BaseModel` from `pydantic` works directly. No `v1` compat shim needed. `Field(description=...)` populates the JSON schema `description` field which Ollama passes to the model.

---

## Ollama Integration

**Confidence:** HIGH — verified from `langchain-ollama` reference docs and PyPI.

### Basic setup

```python
from langchain_ollama import ChatOllama

# For structured output, use json_schema method (default since langchain-ollama 0.3.0)
model = ChatOllama(
    model="llama3.1",       # or "llama3.2", "mistral", "deepseek-r1:14b"
    temperature=0,          # Required for deterministic structured output
    # method defaults to 'json_schema' in 1.0.x — do not override unless debugging
)
```

### Structured output with ChatOllama

The `with_structured_output` signature on `ChatOllama`:

```python
ChatOllama.with_structured_output(
    schema: dict | type,
    *,
    method: Literal['function_calling', 'json_mode', 'json_schema'] = 'json_schema',
    include_raw: bool = False,
)
```

`json_schema` is the recommended default. Ollama passes the Pydantic schema directly to the model as a format constraint, making structured output highly reliable even with models that don't support tool calling.

### Known issues and limitations

| Issue | Severity | Mitigation |
|-------|----------|------------|
| Not all models support tool calling | Medium | Use `method='json_schema'` (default) instead of `function_calling` |
| `json_mode` requires schema in prompt too | Medium | Use `json_schema` method to avoid this; `json_schema` does NOT require manual prompt engineering |
| Output is null when function calling fails | High | Always set `method='json_schema'` explicitly if you hit null outputs |
| Ollama must be running locally | Low | Document setup requirement; not bundled in the exe |
| Token limit differences by model | Low | Use token budget guard before invoking |

**Recommendation:** Pin `method='json_schema'` explicitly in code even though it is the default. Prevents silent regression if default changes.

---

## RAGAS for Factual Grounding

**Confidence:** MEDIUM — API patterns verified from PyPI and docs search; exact 0.4 API confirmed from multiple sources but full reference docs returned 403.

### What RAGAS provides

RAGAS 0.4.3 includes these metrics relevant to the grounding requirement:

| Metric | What it measures | Requires vector store? |
|--------|-----------------|----------------------|
| `Faithfulness` | Are all claims in the LLM response inferable from the provided context? Score 0-1. | No — only needs response + retrieved_contexts |
| `FactualCorrectness` | Factual accuracy against a reference answer | No — needs response + reference |
| `LLMContextRecall` | Did the LLM use all relevant context? | No — needs response + context |

### Usage pattern without a vector store

The grounding harness for v1.2 needs to check that the LLM's documentation output is faithful to the `ContextBuilder` output. This is a pure faithfulness check — no retrieval step involved.

```python
from ragas import evaluate
from ragas.metrics import Faithfulness
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from langchain_ollama import ChatOllama
from ragas.llms import LangchainLLMWrapper

# --- Build samples from generated docs ---
# context_str = ContextBuilder output (what we gave the LLM)
# generated_doc = LLM output (what we want to evaluate)

sample = SingleTurnSample(
    user_input="Document this Alteryx workflow",   # The prompt sent to the LLM
    response=generated_doc,                        # The LLM's output
    retrieved_contexts=[context_str],              # The ContextBuilder output used as context
)

dataset = EvaluationDataset(samples=[sample])

# --- Use local Ollama as evaluator LLM (avoids cloud dependency) ---
evaluator_llm = LangchainLLMWrapper(
    ChatOllama(model="llama3.1", temperature=0)
)

# --- Run evaluation ---
results = evaluate(
    dataset=dataset,
    metrics=[Faithfulness()],
    llm=evaluator_llm,
)

faithfulness_score = results["faithfulness"]  # float 0.0 to 1.0
# Threshold for v1.2: reject if faithfulness_score < 0.8
```

### API deprecation note

The older `SingleTurnSample.single_turn_ascore()` method is deprecated in ragas 0.4 and removed in 1.0. Use the `evaluate()` function with `EvaluationDataset` as shown above.

---

## Optional Dependency Pattern (uv)

**Confidence:** HIGH — verified against uv official docs (https://docs.astral.sh/uv/concepts/projects/dependencies/).

### pyproject.toml syntax

```toml
[project]
name = "alteryx-diff"
version = "1.2.0"
requires-python = ">=3.11"
dependencies = [
    # Core dependencies (always installed)
    "lxml>=6.0.2",
    "networkx>=3.6.1",
    "typer>=0.24.1",
    "jinja2>=3.1.6",
    "deepdiff>=8.6.1",
    "scipy>=1.17.1",
    "fastapi>=0.115",
    "pystray",
    "keyring",
]

[project.optional-dependencies]
llm = [
    "langchain~=1.2",
    "langchain-core~=1.2",
    "langgraph~=1.1",
    "langchain-ollama~=1.0",
    "ragas~=0.4",
    "tiktoken>=0.7",
]

[tool.uv]
dev-dependencies = [
    "pytest>=9.0.2",
    "pytest-cov",
    "ruff",
    "mypy",
]
```

### Sync commands

```bash
# Core only (no LLM deps):
uv sync

# Core + LLM deps:
uv sync --extra llm

# Install from PyPI (end-user):
pip install alteryx-diff           # core only
pip install "alteryx-diff[llm]"    # with LLM features
```

### Key gotchas

1. **Conflicting optional deps:** If two extras have conflicting requirements, uv's resolver will fail unless you declare them with `[tool.uv.conflicts]`. For v1.2 there is only one extra (`llm`), so no conflict handling needed.

2. **Optional deps appear in published metadata:** They are NOT local-only. When the package is published to PyPI, the `[llm]` extra is advertised as a public extra. This is correct behavior for an installable package.

3. **Dev dependencies are separate from optional deps:** Do NOT put pytest or ruff in `[project.optional-dependencies]`. Dev deps belong in `[tool.uv.dev-dependencies]` or `[dependency-groups]`. Using `[project.optional-dependencies]` for dev tools causes them to appear in published package metadata.

4. **Guard in code:** The `alteryx_diff/llm/` module must guard imports behind `try/except ImportError` so that the core CLI exits gracefully when LLM deps are not installed:

```python
try:
    from langchain_ollama import ChatOllama
    from langgraph.graph import StateGraph
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
```

---

## Token Budget Management

**Confidence:** MEDIUM — `count_tokens_approximately` function verified from LangChain reference docs; tiktoken usage pattern is widely established.

### Recommended approach: two-tier

**Tier 1 — Fast pre-check (no model call):** Use `langchain_core.messages.utils.count_tokens_approximately` for a quick budget check before invoking the LLM. This avoids a network call and is sufficient for guard-railing.

```python
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately

def check_token_budget(messages: list, max_tokens: int = 8000) -> bool:
    """Return True if messages are within budget."""
    estimated = count_tokens_approximately(messages)
    return estimated <= max_tokens

# Usage before LLM call:
messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=context_str),
]
if not check_token_budget(messages, max_tokens=6000):
    # Truncate context_str before proceeding
    raise ValueError(f"Context too large: ~{count_tokens_approximately(messages)} tokens")
```

**Function signature:**
```python
count_tokens_approximately(
    messages: Iterable[MessageLikeRepresentation],
    *,
    chars_per_token: float = 4.0,          # Conservative estimate
    extra_tokens_per_message: float = 3.0,
    count_name: bool = True,
    tokens_per_image: int = 85,
    use_usage_metadata_scaling: bool = False,
    tools: list | None = None,
) -> int
```

Returns an `int` — approximate token count. The `chars_per_token=4.0` default is conservative (slightly overestimates). For Ollama/Llama3, this is a reasonable approximation.

**Tier 2 — Accurate count (model-specific, only if needed):** Use `tiktoken` directly for OpenAI-compatible models. For Ollama/Llama3, tiktoken with `o200k_base` encoding is a reasonable approximation but may differ by 1–3 tokens per message due to Llama's custom special tokens.

```python
import tiktoken

def count_tokens_tiktoken(text: str, model: str = "gpt-4o") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))
```

**Recommendation for v1.2:** Use `count_tokens_approximately` for the `ContextBuilder` budget guard (the `ContextBuilder`'s job is to keep context under the limit). Do not add tiktoken as a hard dependency unless a cloud provider integration is added later.

---

## What NOT to Add

| Library | Why Excluded | If Needed Later |
|---------|-------------|-----------------|
| `openai` / `langchain-openai` | Cloud provider; out of scope for offline-first v1.2 | Add as separate optional extra `[project.optional-dependencies] openai = [...]` |
| `anthropic` / `langchain-anthropic` | Same as above | Same pattern |
| `langsmith` | Tracing/observability SDK; adds external API dependency; out of scope | Add to dev extras only if adopting LangSmith for evaluation |
| `langchain-classic` | Backward-compat shim for pre-1.0 patterns; indicates code using deprecated APIs | Use native 1.x patterns instead |
| `chromadb` / `faiss-cpu` | Vector stores; RAGAS does NOT require them for faithfulness evaluation | Only if retrieval-augmented features are added |
| `sentence-transformers` | Embedding models; not needed for text-only doc generation | Only if semantic search over workflow history is added |
| `celery` / `redis` | Task queues; doc generation is synchronous in v1.2 | If async job queue is added in v1.3+ |
| `pydantic-settings` | Config management; langchain 1.x uses it internally but no need to expose it | Only if adding complex config surface |

**Core principle:** The `[llm]` optional group should be installable in an air-gapped environment given a local PyPI mirror or pre-downloaded wheels, because the exe targets air-gapped corporate Alteryx environments. Avoid any dependency that phones home on import or requires external API keys to function.

---

## Migration Notes: langchain 0.3 → 1.2

If any implementation was started against `langchain~=0.3`, these are the changes needed:

| Change Area | Old (0.3) | New (1.2) | Impact |
|-------------|-----------|-----------|--------|
| StateGraph state type | Could use Pydantic BaseModel | Must use `TypedDict` | Rewrite state class |
| `with_structured_output` | Existed on BaseChatModel | Still exists on BaseChatModel | No change needed |
| LCEL pipe operator `\|` | Supported | Still supported | No change needed |
| Legacy chains (LLMChain etc.) | In `langchain` package | Moved to `langchain-classic` | Avoid; use LCEL instead |
| Python version | `>=3.9` | `>=3.10` | Project already requires `>=3.11`, no impact |
| `create_agent` | N/A | New abstraction for agent loops | Not relevant for linear pipeline |

---

## Sources

- langchain PyPI — https://pypi.org/project/langchain/ (version 1.2.14, Mar 31, 2026)
- langchain-core PyPI — https://pypi.org/project/langchain-core/
- langgraph PyPI — https://pypi.org/project/langgraph/ (version 1.1.4, Mar 31, 2026)
- langchain-ollama PyPI — https://pypi.org/project/langchain-ollama/ (version 1.0.1, Dec 12, 2025)
- ragas PyPI — https://pypi.org/project/ragas/ (version 0.4.3, Jan 13, 2026)
- LangGraph Graph API docs — https://docs.langchain.com/oss/python/langgraph/graph-api
- ChatOllama.with_structured_output reference — https://reference.langchain.com/python/langchain-ollama/chat_models/ChatOllama/with_structured_output
- count_tokens_approximately reference — https://reference.langchain.com/python/langchain-core/messages/utils/count_tokens_approximately
- LangChain v1 migration guide — https://docs.langchain.com/oss/python/migrate/langchain-v1
- LangChain 1.0 GA announcement — https://changelog.langchain.com/announcements/langchain-1-0-now-generally-available
- uv optional dependencies docs — https://docs.astral.sh/uv/concepts/projects/dependencies/
- Ollama structured outputs — https://ollama.com/blog/structured-outputs
- RAGAS faithfulness docs — https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/
- RAGAS evaluation guide — https://docs.ragas.io/en/stable/getstarted/rag_eval/
- tiktoken token counting — https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb

---

*Stack research for: Alteryx Git Companion v1.2 — LLM Documentation Generation*
*Researched: 2026-04-02*
