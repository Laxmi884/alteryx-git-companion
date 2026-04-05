---
phase: 25
plan: 02
subsystem: cli
tags: [cli, document, llm, multi-command, typer, testing]
dependency_graph:
  requires: [25-01, 23-01, 24-01, 24-02]
  provides: [document-subcommand, parse_one-api, _resolve_llm-helper, _resolve_model_string-helper]
  affects: [cli.py, parser.py, test_cli.py]
tech_stack:
  added: []
  patterns: [deferred-llm-imports, CORE-01-compliance, multi-command-typer, sys-modules-mock]
key_files:
  created:
    - tests/llm/test_cli_document.py
  modified:
    - src/alteryx_diff/parser.py
    - src/alteryx_diff/cli.py
    - tests/test_cli.py
decisions:
  - Patched generate_documentation at source (alteryx_diff.llm.doc_graph) not at cli module due to deferred import inside document() function body
  - Used sys.modules injection for langchain_ollama mock to handle environments without langchain_ollama installed
  - Tasks 2 and 3 committed together as specified since adding document() converts app from single to multi-command mode
metrics:
  duration: 341s
  completed: 2026-04-05
  tasks_completed: 4
  files_modified: 4
---

# Phase 25 Plan 02: `document` Subcommand + Multi-Command Typer Regression Fix Summary

**One-liner:** Added `alteryx-diff document` subcommand with LLM provider dispatch and `_resolve_llm()` helper, fixed all 12 CLI tests for multi-command Typer mode, and added 6 new acceptance tests for CLI-01.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Add public `parse_one()` to parser.py | 835066b | src/alteryx_diff/parser.py |
| 2+3 | Add `document` subcommand + update test_cli.py for multi-command | 17a9754 | src/alteryx_diff/cli.py, tests/test_cli.py |
| 4 | New tests/llm/test_cli_document.py | 88f8e2a | tests/llm/test_cli_document.py |

## What Was Built

- **`parse_one()` public API** in `parser.py`: delegates to `_parse_one()`, added to `__all__`
- **`_resolve_model_string()`** helper: D-04 fallback chain (`--model` → `ACD_LLM_MODEL` env → config_store → error)
- **`_resolve_llm()`** helper: provider dispatch supporting ollama, openai, openrouter with deferred LangChain imports
- **`document` subcommand**: full workflow — `require_llm_deps()` guard → file validation → model resolution → parse → LLM pipeline → DocRenderer → Markdown output
- **Multi-command Typer fix**: all 12 existing `runner.invoke(app, [...])` calls updated to `["diff", ...]` prefix
- **6 new tests** in `tests/llm/test_cli_document.py` covering CLI-01 acceptance criteria

## Verification Results

```
tests/test_cli.py: 12 passed
tests/llm/test_cli_document.py: 6 passed
tests/llm/test_require_llm_deps.py: 3 passed
tests/llm/: 41 passed total (no regressions)
```

Registered commands confirmed: `['diff', 'document']`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Patched generate_documentation at source module, not cli module**
- **Found during:** Task 4 test execution
- **Issue:** `generate_documentation` is imported inside `document()` function body for CORE-01 compliance; `patch("alteryx_diff.cli.generate_documentation", ...)` raised `AttributeError` since the name doesn't exist at module level
- **Fix:** Changed patch target to `alteryx_diff.llm.doc_graph.generate_documentation` (the source location)
- **Files modified:** tests/llm/test_cli_document.py
- **Commit:** 88f8e2a

**2. [Rule 1 - Bug] Used sys.modules injection for ChatOllama mock**
- **Found during:** Task 4 test execution
- **Issue:** `langchain_ollama` is not installed in the test environment; `patch("langchain_ollama.ChatOllama", ...)` raised `ModuleNotFoundError`
- **Fix:** Used `patch.dict(sys.modules, {"langchain_ollama": mock_ollama_module})` to inject a mock module
- **Files modified:** tests/llm/test_cli_document.py
- **Commit:** 88f8e2a

## Known Stubs

None — all functionality is fully wired. The `document` command executes the complete pipeline end-to-end.

## Self-Check: PASSED
