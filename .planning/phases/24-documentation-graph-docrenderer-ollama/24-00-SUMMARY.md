---
phase: 24-documentation-graph-docrenderer-ollama
plan: "00"
subsystem: llm-tests
tags: [tdd, red-phase, test-stubs, langchain, langgraph]
dependency_graph:
  requires: []
  provides: [test-api-contract-models, test-api-contract-doc-graph, test-api-contract-doc-renderer]
  affects: [24-01, 24-02, 24-03]
tech_stack:
  added: []
  patterns: [pytest.importorskip-skip-pattern, tdd-red-phase]
key_files:
  created:
    - tests/llm/__init__.py
    - tests/llm/test_models.py
    - tests/llm/test_doc_graph.py
    - tests/llm/test_doc_renderer.py
  modified: []
decisions: []
metrics:
  duration: "2 minutes"
  completed: "2026-04-04T23:37:11Z"
  tasks_completed: 1
  files_changed: 4
---

# Phase 24 Plan 00: Wave 0 Test Stubs Summary

RED-phase test stubs for WorkflowDocumentation Pydantic models, DocumentationGraph LangGraph pipeline, and DocRenderer rendering — establishing the test API contract before any implementation.

## What Was Built

Three test stub files under `tests/llm/` establishing the Phase 24 test API contract:

1. **`tests/llm/test_models.py`** — 5 stubs for `WorkflowDocumentation` and `ToolNote` Pydantic models: field validation, correct data acceptance, invalid data rejection, and absence of excluded fields.

2. **`tests/llm/test_doc_graph.py`** — 5 stubs for the `DocumentationGraph` LangGraph pipeline: compiled graph return type, 4-node topology verification, `generate_documentation` return type, retry-on-validation-error behavior, and provider-agnostic LLM interface.

3. **`tests/llm/test_doc_renderer.py`** — 7 stubs for `DocRenderer`: Markdown rendering with all content sections, HTML fragment rendering (section element, all sections present), file write behavior, and importability without LangChain installed.

All files follow the Phase 23 `pytest.importorskip("langchain_core")` pattern — stubs skip gracefully without `[llm]` extras, and fail with "stub — implement in Plan NN" when extras are present.

## Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create failing test stubs for WorkflowDocumentation, DocumentationGraph, and DocRenderer | 0e94b33 | tests/llm/__init__.py, tests/llm/test_models.py, tests/llm/test_doc_graph.py, tests/llm/test_doc_renderer.py |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — this plan's purpose IS to create stubs. The stubs are intentional and will be implemented in Plans 01 (models), 02 (doc_graph), and 03 (doc_renderer).

## Self-Check: PASSED

Files verified:
- FOUND: tests/llm/__init__.py
- FOUND: tests/llm/test_models.py
- FOUND: tests/llm/test_doc_graph.py
- FOUND: tests/llm/test_doc_renderer.py

Commits verified:
- FOUND: 0e94b33 (test(24-00): add failing test stubs)
