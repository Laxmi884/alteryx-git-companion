---
phase: 24-documentation-graph-docrenderer-ollama
verified: 2026-04-04T23:50:00Z
status: human_needed
score: 8/9 must-haves verified
re_verification: false
human_verification:
  - test: "Start a local Ollama instance with a model (e.g. llama3), then run: uv run python -c \"import asyncio; from langchain_ollama import ChatOllama; from alteryx_diff.llm.doc_graph import generate_documentation; llm = ChatOllama(model='llama3'); ctx = {'workflow_name': 'TestWF', 'tool_count': 1, 'tools': [{'tool_id': 1, 'tool_type': 'DbFileInput', 'config': {}}], 'connections': [], 'topology': {'connections': [], 'source_tools': [1], 'sink_tools': [1], 'branch_points': []}}; doc = asyncio.run(generate_documentation(ctx, llm)); print(doc.workflow_name)\""
    expected: "Pipeline completes and prints 'TestWF' (or similar workflow name) with no API key required. No cloud provider errors raised."
    why_human: "Requires a locally running Ollama instance — cannot be verified programmatically without the external service. EVAL-01 specifies offline/air-gapped execution; automated tests use a mock LLM, not a real Ollama endpoint."
---

# Phase 24: DocumentationGraph + DocRenderer + Ollama Verification Report

**Phase Goal:** A LangGraph 4-node pipeline generates structured workflow documentation from ContextBuilder output, a DocRenderer writes it to Markdown and HTML fragment, and a local Ollama model can be used as the LLM backend for offline execution.
**Verified:** 2026-04-04T23:50:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `await doc_graph.ainvoke(initial_state)` completes the 4-node pipeline (analyze_topology, annotate_tools, risk_scan, assemble_doc) and returns a validated WorkflowDocumentation with single automatic retry on ValidationError | VERIFIED | `doc_graph.py` implements all 4 nodes wired linearly; `generate_documentation` retries on `ValidationError`; `test_retry_on_validation_error` and `test_retry_exhausted_raises` pass |
| 2 | `DocRenderer.to_markdown(doc)` produces a standalone `.md` file; `DocRenderer.to_html_fragment(doc)` produces an HTML `<section>` fragment — both renderable without errors | VERIFIED | `doc_renderer.py` implements both methods with Jinja2 templates; `DocRenderer` importable without LLM extras; all 8 `test_doc_renderer.py` tests pass |
| 3 | Passing ChatOllama as the LLM backend runs the pipeline to completion without any cloud API key | ? UNCERTAIN | Provider-agnostic via `BaseChatModel` injection confirmed with mock LLM (`test_provider_agnostic` passes); `langchain-ollama~=1.0` declared in `[llm]` extras; end-to-end run against live Ollama requires human verification |

**Score:** 8/9 must-haves verified (1 requires human)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/alteryx_diff/llm/models.py` | WorkflowDocumentation + ToolNote Pydantic models | VERIFIED | 19 lines, exports `WorkflowDocumentation` (5 fields, no `assumptions`) and `ToolNote` (3 fields) |
| `src/alteryx_diff/llm/doc_graph.py` | build_doc_graph factory + generate_documentation + DocState | VERIFIED | 260 lines, all three exports present; `DocState` TypedDict with 6 fields |
| `src/alteryx_diff/renderers/doc_renderer.py` | DocRenderer with to_markdown, to_html_fragment, write_markdown | VERIFIED | 116 lines, `TYPE_CHECKING` guard protects LLM import, `autoescape=True` for HTML |
| `tests/llm/conftest.py` | mock_llm fixture + sample_workflow_documentation helper | VERIFIED | `sample_workflow_documentation()` and `mock_llm` fixture present with correct shape |
| `tests/llm/test_models.py` | Unit tests for WorkflowDocumentation | VERIFIED | 6 tests, all pass |
| `tests/llm/test_doc_graph.py` | Unit tests for pipeline execution | VERIFIED | 7 tests, all pass |
| `tests/llm/test_doc_renderer.py` | Unit tests for DocRenderer | VERIFIED | 8 tests, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/alteryx_diff/llm/doc_graph.py` | `src/alteryx_diff/llm/models.py` | `from alteryx_diff.llm.models import WorkflowDocumentation` + `WorkflowDocumentation.model_validate_json` | WIRED | Lines 18 and 254/259 confirm import and usage in validate path |
| `src/alteryx_diff/llm/doc_graph.py` | `langgraph.graph` | `from langgraph.graph import END, START, StateGraph` + `StateGraph(DocState)` | WIRED | Lines 52 and 205 inside `build_doc_graph`; lazy import preserves testability |
| `src/alteryx_diff/llm/context_builder.py` | `src/alteryx_diff/normalizer/_strip.py` | `from alteryx_diff.normalizer._strip import strip_noise` + `strip_noise(node.config)` | WIRED | Line 14 (import) and line 61 (usage in `build_from_workflow` tools comprehension) |
| `src/alteryx_diff/renderers/doc_renderer.py` | `src/alteryx_diff/llm/models.py` | `TYPE_CHECKING` guard only | WIRED (correctly isolated) | Import is inside `if TYPE_CHECKING:` block (line 15-16); runtime uses string annotation `"WorkflowDocumentation"`; confirmed importable without `[llm]` extras |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `doc_graph.py::generate_documentation` | `WorkflowDocumentation` returned | LLM `with_structured_output(WorkflowDocumentation).ainvoke` in `assemble_doc` node, fed by `context`, `topology_notes`, `tool_annotations`, `risk_notes` state keys | Yes (all state keys populated by prior nodes before `assemble_doc`) | FLOWING |
| `doc_renderer.py::to_markdown` | Markdown string | Jinja2 template renders `doc.workflow_name`, `doc.intent`, `doc.data_flow`, `doc.tool_notes`, `doc.risks` from passed `WorkflowDocumentation` | Yes (directly from Pydantic model fields) | FLOWING |
| `doc_renderer.py::to_html_fragment` | HTML string | Same Jinja2 approach as `to_markdown` with `autoescape=True` env | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 21 Phase-24 tests pass | `uv run --extra llm pytest tests/llm/test_models.py tests/llm/test_doc_graph.py tests/llm/test_doc_renderer.py -q` | `21 passed in 0.35s` | PASS |
| DocRenderer importable without LLM extras | `python3 -c "from alteryx_diff.renderers.doc_renderer import DocRenderer; print('OK')"` | `OK — importable without LLM extras` | PASS |
| strip_noise wired in context_builder | `grep "strip_noise" src/alteryx_diff/llm/context_builder.py` | Lines 14 (import) and 61 (usage) found | PASS |
| langchain-openai declared in pyproject.toml | `grep "langchain-openai" pyproject.toml` | `"langchain-openai~=0.3"` at line 38 | PASS |
| Ollama live end-to-end run | Requires running Ollama instance | Not tested | ? SKIP — routed to human |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CORE-03 | 24-01, 24-02 | DocumentationGraph (LangGraph ~1.1) runs 4-node pipeline with single-retry on ValidationError | SATISFIED | `build_doc_graph` + `generate_documentation` fully implemented; `StateGraph(DocState)` with 4 nodes; retry logic at lines 255-259 of `doc_graph.py`; 7 pipeline tests pass |
| CORE-04 | 24-03 | DocRenderer renders WorkflowDoc to standalone Markdown `.md` and HTML fragment embeddable in diff report | SATISFIED | `to_markdown`, `to_html_fragment`, `write_markdown` all implemented with Jinja2; `<section class="workflow-doc">` confirmed; HTML escaping confirmed; 8 renderer tests pass |
| EVAL-01 | 24-01, 24-02 | User can configure doc generation to use local Ollama model for offline/air-gapped execution | PARTIALLY SATISFIED (automated) / ? NEEDS HUMAN | `langchain-ollama~=1.0` in `[llm]` extras; `build_doc_graph(llm: BaseChatModel)` accepts any provider; `test_provider_agnostic` passes with mock; live Ollama run unverified |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/alteryx_diff/llm/doc_graph.py` | 122-124 | `except Exception: annotations = json.dumps([])` silent fallback in `annotate_tools` | Info | Deliberate robustness deviation documented in 24-02-SUMMARY.md; `assemble_doc` receives context directly to compensate; not a stub |

No stubs, TODO comments, placeholder returns, or empty implementations found in any Phase 24 artifact.

### Human Verification Required

#### 1. Ollama Live End-to-End Run (EVAL-01)

**Test:** Start a local Ollama instance with any model (e.g. `llama3` or `mistral`), then run:
```
uv run python -c "
import asyncio
from langchain_ollama import ChatOllama
from alteryx_diff.llm.doc_graph import generate_documentation

llm = ChatOllama(model='llama3')
ctx = {
    'workflow_name': 'TestWF',
    'tool_count': 1,
    'tools': [{'tool_id': 1, 'tool_type': 'DbFileInput', 'config': {}}],
    'connections': [],
    'topology': {'connections': [], 'source_tools': [1], 'sink_tools': [1], 'branch_points': []}
}
doc = asyncio.run(generate_documentation(ctx, llm))
print(doc.workflow_name)
print(doc.intent[:80])
"
```
**Expected:** Pipeline completes, prints workflow name and intent. No cloud API key or network error. No `APIConnectionError` or `AuthenticationError`.
**Why human:** Requires a locally running Ollama instance — the automated test suite uses a `MagicMock` LLM, not a real Ollama endpoint. EVAL-01 specifically targets offline/air-gapped execution; this can only be confirmed against a real Ollama process.

### Gaps Summary

No automated gaps. The single open item is human verification of the live Ollama integration (EVAL-01 Success Criterion 3). All code-level evidence for provider-agnosticism is present: `BaseChatModel` interface, `langchain-ollama` dependency, `test_provider_agnostic` passing — but the offline execution guarantee cannot be confirmed without a real Ollama instance.

---

_Verified: 2026-04-04T23:50:00Z_
_Verifier: Claude (gsd-verifier)_
