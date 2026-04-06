---
phase: 24-documentation-graph-docrenderer-ollama
plan: "02"
subsystem: llm
tags: [langgraph, documentation-pipeline, structured-output, provider-agnostic, tdd]
dependency_graph:
  requires: [24-00, 24-01]
  provides: [doc_graph.py, generate_documentation, build_doc_graph, DocState]
  affects: [24-03, 24-04, 25-cli]
tech_stack:
  added: []
  patterns: [LangGraph StateGraph linear 4-node pipeline, closure-captured llm in node functions, TypedDict for graph state, single-retry on ValidationError]
key_files:
  created:
    - src/alteryx_diff/llm/doc_graph.py
    - tests/llm/test_doc_graph.py
  modified: []
decisions:
  - "DocState uses TypedDict with 6 fields per D-09; analyze_topology is pure Python (no LLM call)"
  - "validate-then-retry pattern: WorkflowDocumentation.model_validate_json on raw_doc_json; retry_state spreads initial_state + validation_error per D-10/Pitfall 4"
  - "asyncio.run() used in tests instead of pytest.mark.asyncio (pytest-asyncio not available)"
  - "annotate_tools uses with_structured_output(list[ToolNote]) with fallback to empty list on exception"
metrics:
  duration_minutes: 7
  completed_date: "2026-04-04"
  tasks_completed: 1
  files_created: 2
  files_modified: 0
---

# Phase 24 Plan 02: DocumentationGraph Pipeline Summary

**One-liner:** LangGraph 4-node linear documentation pipeline (analyze_topology, annotate_tools, risk_scan, assemble_doc) with provider-agnostic BaseChatModel injection and single-retry on Pydantic ValidationError.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 RED | Failing tests for DocumentationGraph pipeline (7 tests) | 7fb4786 |
| 1 GREEN | Implement doc_graph.py with build_doc_graph + generate_documentation | f029f7e |

## What Was Built

### `src/alteryx_diff/llm/doc_graph.py`

- `DocState(TypedDict)` — 6-field state: `context`, `topology_notes`, `tool_annotations`, `risk_notes`, `raw_doc_json`, `validation_error`
- `build_doc_graph(llm: BaseChatModel) -> CompiledStateGraph` — factory function with 4 async nodes wired linearly via `StateGraph(DocState)`
  - `analyze_topology`: pure Python, no LLM call; reads `state["context"]["topology"]` and builds a structured text summary
  - `annotate_tools`: single LLM call via `with_structured_output(list[ToolNote], method="json_schema")`; fallback to empty list on exception
  - `risk_scan`: single LLM call via `ainvoke(messages)`; stores raw content in `risk_notes`
  - `assemble_doc`: single LLM call via `with_structured_output(WorkflowDocumentation, method="json_schema")`; appends `validation_error` to system message on retry
- `generate_documentation(context, llm) -> WorkflowDocumentation` — async convenience wrapper; first attempt + single-retry on `ValidationError` (retry_state spreads `initial_state` + `validation_error` to re-run all nodes fresh)

### `tests/llm/test_doc_graph.py`

7 tests, all passing:
1. `test_build_doc_graph_returns_compiled` — graph has ainvoke method
2. `test_generate_documentation_returns_model` — returns WorkflowDocumentation with all fields
3. `test_generate_documentation_workflow_name` — workflow_name matches context
4. `test_pipeline_calls_llm` — LLM actually invoked during pipeline
5. `test_retry_on_validation_error` — single retry succeeds when second call returns valid doc
6. `test_retry_exhausted_raises` — ValidationError raised when both attempts fail
7. `test_provider_agnostic` — works with any mock meeting BaseChatModel contract

## Verification

```
uv run --extra llm pytest tests/llm/test_doc_graph.py -x -q  → 7 passed
uv run --extra llm pytest tests/llm/ -x -q                   → 33 passed
uv run pytest tests/ --ignore=tests/llm/ --ignore=tests/test_cli.py → 183 passed, 1 xfailed
```

Core suite pre-existing failures (not caused by this plan):
- `tests/test_cli.py`: `TypeError: CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'` — pre-existing
- `tests/test_remote.py::test_post_push_success` — pre-existing failure unrelated to LLM pipeline

## Deviations from Plan

### Implementation Deviations

**1. [Rule 2 - Auto-adaptation] asyncio.run() instead of @pytest.mark.asyncio**
- **Found during:** Task 1 (RED phase)
- **Issue:** `pytest-asyncio` is not installed; `@pytest.mark.asyncio` produced `PytestUnknownMarkWarning` and test collection errors
- **Fix:** Used `asyncio.run()` pattern directly inside sync test functions — consistent with existing pattern in `tests/test_watch.py`
- **Files modified:** `tests/llm/test_doc_graph.py`

**2. [Rule 2 - Robustness] Exception fallback in annotate_tools**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `with_structured_output(list[ToolNote])` may fail with some providers that don't support list schema; this would abort the pipeline rather than degrading gracefully
- **Fix:** Wrapped annotate_tools LLM call in try/except with fallback to empty list; assemble_doc receives full context to compensate
- **Files modified:** `src/alteryx_diff/llm/doc_graph.py`

## Known Stubs

None — all exported functions are fully implemented.

## Self-Check: PASSED

- [x] `src/alteryx_diff/llm/doc_graph.py` exists and contains `DocState`, `build_doc_graph`, `generate_documentation`
- [x] `tests/llm/test_doc_graph.py` exists with 7 test functions
- [x] Commit `7fb4786` (RED) exists
- [x] Commit `f029f7e` (GREEN) exists
- [x] All 7 tests pass
- [x] Full LLM suite (33 tests) passes
- [x] Core suite unaffected (pre-existing failures verified pre-date this plan)
