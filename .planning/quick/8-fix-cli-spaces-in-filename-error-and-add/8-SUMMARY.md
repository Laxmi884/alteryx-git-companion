---
phase: quick-8
plan: 8
subsystem: cli, parser, pipeline
tags: [cli, parser, pipeline, filter, yxwz, help-text]
dependency_graph:
  requires: []
  provides: [filter_ui_tools parameter chain, --no-filter-ui-tools CLI flag, .yxwz help text]
  affects: [cli.py, parser.py, pipeline/pipeline.py]
tech_stack:
  added: []
  patterns: [keyword-only bool defaults for filtering, typer bool option with --no- prefix]
key_files:
  created: []
  modified:
    - src/alteryx_diff/cli.py
    - src/alteryx_diff/parser.py
    - src/alteryx_diff/pipeline/pipeline.py
decisions:
  - Typer bool option default=True with --no-filter-ui-tools flag name maps correctly to filter_ui_tools=False when flag used
  - filter_ui_tools guard placed immediately after plugin string extraction, before position/config reads — avoids unnecessary attribute access on filtered nodes
  - Help string split across multiple string literals to stay within ruff 88-char line limit
metrics:
  duration: "3 min"
  completed_date: "2026-03-09"
  tasks_completed: 2
  files_modified: 3
---

# Quick Task 8: Fix CLI spaces-in-filename error and add UI tool filtering

**One-liner:** Thread `filter_ui_tools: bool = True` through `_tree_to_workflow`, `_parse_one`, `parse()`, `DiffRequest`, and `run()`, then expose `--no-filter-ui-tools` flag in CLI with updated `.yxwz` help text.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Thread filter_ui_tools through parser and pipeline | 72637bc | parser.py, pipeline/pipeline.py |
| 2 | Add --no-filter-ui-tools flag and update CLI help text | ec3ba04 | cli.py |

## Changes Made

### parser.py

- `_tree_to_workflow()` — added `filter_ui_tools: bool = True` keyword-only parameter. Guard `if filter_ui_tools and plugin.startswith("AlteryxGuiToolkit."): continue` placed before position/config reads for efficiency.
- `_parse_one()` — added `filter_ui_tools: bool = True` keyword-only parameter, passed through to `_tree_to_workflow()`.
- `parse()` — added `filter_ui_tools: bool = True` keyword-only parameter with updated docstring, passed to both `_parse_one()` calls.

### pipeline/pipeline.py

- `DiffRequest` dataclass — added `filter_ui_tools: bool = True` field (consistent with `frozen=True, kw_only=True, slots=True` pattern).
- `run()` — passes `filter_ui_tools=request.filter_ui_tools` to `parse()`. Updated docstring to describe the new field.

### cli.py

- `workflow_a` help: "Baseline .yxmd or .yxwz file (quote paths that contain spaces)"
- `workflow_b` help: "Changed .yxmd or .yxwz file (quote paths that contain spaces)"
- Command docstring updated to mention `.yxwz` and provide a shell quoting example.
- New `--no-filter-ui-tools` flag added (typer bool option, default True) after `canvas_layout`.
- Both `DiffRequest(...)` call sites updated with `filter_ui_tools=filter_ui_tools`.

## Verification

```
105 passed, 1 xfailed in 0.78s
```

CLI `--help` shows updated argument descriptions, `.yxwz` support, space-quoting guidance, and `--no-filter-ui-tools` flag.

Smoke test: comparing `examples/RISK_Creation of TU Cohorts.yxwz` against `examples/RISK_Creation of TU Cohorts_03MAR26.yxmd` exits 0 (no differences found with default filter active).

## Deviations from Plan

**1. [Rule 2 - Lint] Fixed ruff E501 line-too-long in help string**
- **Found during:** Task 2 commit (pre-commit hook)
- **Issue:** Help string lines for `--no-filter-ui-tools` exceeded 88-char limit
- **Fix:** Split string literal across three shorter string segments
- **Files modified:** src/alteryx_diff/cli.py
- **Commit:** ec3ba04 (included in task commit after fix)

## Self-Check

Files confirmed present:
- FOUND: src/alteryx_diff/cli.py
- FOUND: src/alteryx_diff/parser.py
- FOUND: src/alteryx_diff/pipeline/pipeline.py

Commits confirmed: 72637bc, ec3ba04

## Self-Check: PASSED
