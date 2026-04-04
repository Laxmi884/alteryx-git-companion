---
phase: 24-documentation-graph-docrenderer-ollama
plan: "01"
subsystem: llm
tags: [pydantic, models, context-builder, strip-noise, test-infrastructure]
dependency_graph:
  requires: [24-00]
  provides: [WorkflowDocumentation, ToolNote, mock_llm fixture, strip_noise wiring]
  affects: [24-02, 24-03]
tech_stack:
  added: [langchain-openai~=0.3]
  patterns: [Pydantic BaseModel output schema, pytest.importorskip guard, TDD RED-GREEN]
key_files:
  created:
    - src/alteryx_diff/llm/models.py
    - tests/llm/conftest.py
    - tests/llm/test_models.py
  modified:
    - src/alteryx_diff/llm/context_builder.py
    - tests/llm/test_context_builder.py
    - pyproject.toml
decisions:
  - WorkflowDocumentation has exactly 5 fields (no assumptions field) per D-03
  - strip_noise applied only in build_from_workflow, not build_from_diff
  - mock_llm.with_structured_output returns a chain whose ainvoke returns WorkflowDocumentation instance
metrics:
  duration: "~2.5 minutes"
  completed: "2026-04-04"
  tasks_completed: 2
  files_changed: 6
---

# Phase 24 Plan 01: Workflow Documentation Models and Context Builder Update Summary

WorkflowDocumentation + ToolNote Pydantic output models with strip_noise wiring in ContextBuilder and shared mock_llm test fixture for Plans 02 and 03.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Create WorkflowDocumentation model + update pyproject.toml + test infrastructure | 7e3f94f | models.py, conftest.py, test_models.py, pyproject.toml |
| 2 | Update ContextBuilder.build_from_workflow to apply strip_noise + add test | c1aee07 | context_builder.py, test_context_builder.py |

## What Was Built

### Task 1: WorkflowDocumentation Pydantic Model + Test Infrastructure

Created `src/alteryx_diff/llm/models.py` with:
- `ToolNote(BaseModel)`: 3 fields — `tool_id: int`, `tool_type: str`, `role: str`
- `WorkflowDocumentation(BaseModel)`: 5 fields — `workflow_name`, `intent`, `data_flow`, `tool_notes: list[ToolNote]`, `risks: list[str]`
- No `assumptions` field (per D-03)

Updated `pyproject.toml`:
- Added `langchain-openai~=0.3` to `[llm]` extras
- Added `langchain_openai.*` to mypy overrides module list

Created `tests/llm/conftest.py` with:
- `sample_workflow_documentation()`: returns a realistic 3-tool (Input/Filter/Output) WorkflowDocumentation with 2 risks
- `mock_llm` pytest fixture: MagicMock with `ainvoke` (AsyncMock returning content string) and `with_structured_output` (returns chain whose `ainvoke` returns WorkflowDocumentation)
- `sample_context` pytest fixture: matching ContextBuilder.build_from_workflow output shape

Created `tests/llm/test_models.py` with 6 tests behind `pytest.importorskip("langchain")` guard.

### Task 2: ContextBuilder strip_noise Integration

Updated `src/alteryx_diff/llm/context_builder.py`:
- Added `from alteryx_diff.normalizer._strip import strip_noise` import
- Changed `"config": node.config` to `"config": strip_noise(node.config)` in `build_from_workflow` tools list comprehension
- `build_from_diff` is unchanged

Added `test_build_from_workflow_strip_noise` to `tests/llm/test_context_builder.py`:
- Creates WorkflowDoc with ISO8601 timestamp in tool config
- Asserts the timestamp is replaced with `__TIMESTAMP__` sentinel after `build_from_workflow`

## Verification Results

- `uv run --extra llm pytest tests/llm/ -x -q`: **18 passed**
- Core test suite (excluding pre-existing failures): **237 passed, 1 xfailed**
- Pre-existing failures confirmed NOT caused by this plan:
  - `tests/test_cli.py`: `CliRunner.__init__()` got unexpected `mix_stderr` argument (typer API change)
  - `tests/test_remote.py::test_post_push_success` and `test_push_repo_deleted` (2 pre-existing failures)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data is wired from real Pydantic models and fixtures.

## Self-Check: PASSED

Files confirmed present:
- `/Users/laxmikantmukkawar/Documents/Projects/alteryx_diff/src/alteryx_diff/llm/models.py` — FOUND
- `/Users/laxmikantmukkawar/Documents/Projects/alteryx_diff/tests/llm/conftest.py` — FOUND
- `/Users/laxmikantmukkawar/Documents/Projects/alteryx_diff/tests/llm/test_models.py` — FOUND

Commits confirmed present:
- `7e3f94f` — FOUND (feat(24-01): add WorkflowDocumentation model...)
- `c1aee07` — FOUND (feat(24-01): apply strip_noise to tool configs...)
