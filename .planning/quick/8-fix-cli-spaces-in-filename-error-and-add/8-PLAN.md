---
phase: quick-8
plan: 8
type: execute
wave: 1
depends_on: []
files_modified:
  - src/alteryx_diff/cli.py
  - src/alteryx_diff/parser.py
  - src/alteryx_diff/pipeline/pipeline.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "CLI help text mentions .yxwz support and that paths with spaces must be quoted"
    - "workflow_a/workflow_b argument help strings say 'Baseline .yxmd or .yxwz file' / 'Changed .yxmd or .yxwz file'"
    - "Comparing a .yxwz App against a .yxmd omits AlteryxGuiToolkit.* nodes by default"
    - "--no-filter-ui-tools flag re-includes AlteryxGuiToolkit.* nodes when specified"
    - "All existing tests continue to pass"
  artifacts:
    - path: "src/alteryx_diff/cli.py"
      provides: "Updated help text and --no-filter-ui-tools flag"
    - path: "src/alteryx_diff/parser.py"
      provides: "filter_ui_tools param in _tree_to_workflow, _parse_one, parse"
    - path: "src/alteryx_diff/pipeline/pipeline.py"
      provides: "filter_ui_tools threaded through DiffRequest and run()"
  key_links:
    - from: "cli.py --no-filter-ui-tools flag"
      to: "pipeline.run(filter_ui_tools=...)"
      via: "DiffRequest.filter_ui_tools field"
    - from: "pipeline.run()"
      to: "parser.parse(filter_ui_tools=...)"
      via: "parse() call with kwarg"
    - from: "parser._tree_to_workflow()"
      to: "AlteryxGuiToolkit.* nodes"
      via: "plugin.startswith('AlteryxGuiToolkit.') skip guard"
---

<objective>
Fix two issues in the alteryx_diff CLI tool: (1) update help text to document .yxwz support and
the requirement to quote paths with spaces; (2) add UI tool filtering that skips AlteryxGuiToolkit.*
nodes when comparing .yxwz Apps against .yxmd workflows (default on, opt-out via flag).

Purpose: Eliminate spurious added/removed node noise from app interface tools, and surface clear
guidance so users know to quote space-containing paths.
Output: Updated cli.py, parser.py, pipeline.py with new flag, filter logic, and help text.
</objective>

<execution_context>
@/Users/laxmikantmukkawar/.claude/get-shit-done/workflows/execute-plan.md
@/Users/laxmikantmukkawar/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

<interfaces>
<!-- Current signatures the executor will modify. Extracted from codebase. -->

From src/alteryx_diff/parser.py:
```python
def parse(path_a: pathlib.Path, path_b: pathlib.Path) -> tuple[WorkflowDoc, WorkflowDoc]: ...
def _parse_one(path: pathlib.Path) -> WorkflowDoc: ...
def _tree_to_workflow(tree: etree._ElementTree[etree._Element], filepath: str) -> WorkflowDoc: ...
```

From src/alteryx_diff/pipeline/pipeline.py:
```python
@dataclass(frozen=True, kw_only=True, slots=True)
class DiffRequest:
    path_a: pathlib.Path
    path_b: pathlib.Path

def run(request: DiffRequest, *, include_positions: bool = False) -> DiffResponse: ...
```

From src/alteryx_diff/cli.py:
```python
@app.command()
def diff(
    workflow_a: pathlib.Path = typer.Argument(..., help="Baseline .yxmd file"),
    workflow_b: pathlib.Path = typer.Argument(..., help="Changed .yxmd file"),
    ...
) -> None:
    """Compare two Alteryx .yxmd workflow files and report differences."""
    ...
    response = run(DiffRequest(path_a=workflow_a, path_b=workflow_b), include_positions=include_positions)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Thread filter_ui_tools through parser and pipeline</name>
  <files>src/alteryx_diff/parser.py, src/alteryx_diff/pipeline/pipeline.py</files>
  <action>
**parser.py — three changes:**

1. Add `filter_ui_tools: bool = True` parameter to `_tree_to_workflow()`. After computing `plugin`
   (line ~149), add this guard immediately before `nodes_list.append(...)`:
   ```python
   if filter_ui_tools and plugin.startswith("AlteryxGuiToolkit."):
       continue
   ```

2. Add `filter_ui_tools: bool = True` parameter to `_parse_one()`. Pass it through to
   `_tree_to_workflow(tree, filepath=str(path), filter_ui_tools=filter_ui_tools)`.

3. Add `filter_ui_tools: bool = True` parameter to `parse()`. Update the docstring to mention
   the new parameter. Pass it through: `_parse_one(path_a, filter_ui_tools=filter_ui_tools)` and
   `_parse_one(path_b, filter_ui_tools=filter_ui_tools)`.

**pipeline/pipeline.py — two changes:**

1. Add `filter_ui_tools: bool = True` field to `DiffRequest` dataclass (after `path_b`).
   The dataclass uses `frozen=True, kw_only=True, slots=True` — just add the field with a default.

2. In `run()`, pass `filter_ui_tools` from the request to `parse()`:
   ```python
   doc_a, doc_b = parse(request.path_a, request.path_b, filter_ui_tools=request.filter_ui_tools)
   ```
   Also update the `run()` docstring to mention `filter_ui_tools` in `DiffRequest`.
  </action>
  <verify>
    <automated>cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && python -m pytest tests/ -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>All existing tests pass; parse() and run() accept filter_ui_tools; AlteryxGuiToolkit.* nodes are skipped by default.</done>
</task>

<task type="auto">
  <name>Task 2: Add --no-filter-ui-tools flag and update CLI help text</name>
  <files>src/alteryx_diff/cli.py</files>
  <action>
**Four changes to cli.py:**

1. Update the `workflow_a` help string from `"Baseline .yxmd file"` to
   `"Baseline .yxmd or .yxwz file (quote paths that contain spaces)"`.

2. Update the `workflow_b` help string from `"Changed .yxmd file"` to
   `"Changed .yxmd or .yxwz file (quote paths that contain spaces)"`.

3. Update the command docstring from:
   `"""Compare two Alteryx .yxmd workflow files and report differences."""`
   to:
   `"""Compare two Alteryx .yxmd or .yxwz workflow/app files and report differences.\n\n    Paths that contain spaces must be quoted in the shell, e.g.:\n\n      alteryx-diff "My Workflow A.yxmd" "My Workflow B.yxmd"\n    """`

4. Add a new `filter_ui_tools` parameter after `canvas_layout`:
   ```python
   filter_ui_tools: bool = typer.Option(  # noqa: B008
       True,
       "--no-filter-ui-tools",
       help=(
           "Include AlteryxGuiToolkit.* app interface nodes (Tab, TextBox, Action, etc.)"
           " that are filtered by default when comparing .yxwz apps against .yxmd workflows"
       ),
   )
   ```
   Note: Typer maps `--no-filter-ui-tools` as the flag to set a bool option to False when the
   default is True. The parameter name stays `filter_ui_tools`.

5. Thread `filter_ui_tools` into the two `DiffRequest(...)` call sites (both branches of the
   `quiet or json_output` condition):
   ```python
   DiffRequest(path_a=workflow_a, path_b=workflow_b, filter_ui_tools=filter_ui_tools)
   ```
  </action>
  <verify>
    <automated>cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && python -m alteryx_diff.cli diff --help 2>&1 && python -m pytest tests/ -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>
    `--help` shows updated argument descriptions mentioning .yxwz and space-quoting; `--no-filter-ui-tools` flag appears in help; all tests pass.
  </done>
</task>

</tasks>

<verification>
```bash
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff
# All tests pass
python -m pytest tests/ -x -q

# Help text shows .yxwz and space-quoting guidance
python -m alteryx_diff.cli diff --help

# Smoke: filter active (default) — app file vs workflow file
python -m alteryx_diff.cli diff \
  "examples/RISK_Creation of TU Cohorts.yxwz" \
  "examples/RISK_Creation of TU Cohorts_03MAR26.yxmd" \
  -o /tmp/test_filtered.html && echo "Exit 0 or 1 OK"
```
</verification>

<success_criteria>
- `workflow_a` help: "Baseline .yxmd or .yxwz file (quote paths that contain spaces)"
- `workflow_b` help: "Changed .yxmd or .yxwz file (quote paths that contain spaces)"
- Command docstring mentions quoting paths with spaces, with shell example
- `--no-filter-ui-tools` flag present in `--help` output
- `DiffRequest` has `filter_ui_tools: bool = True` field
- `parse()` and `_parse_one()` and `_tree_to_workflow()` each accept `filter_ui_tools: bool = True`
- AlteryxGuiToolkit.* nodes skipped by default; included with `--no-filter-ui-tools`
- All existing tests continue to pass (`pytest tests/ -x -q` exits 0)
</success_criteria>

<output>
After completion, create `.planning/quick/8-fix-cli-spaces-in-filename-error-and-add/8-SUMMARY.md`
</output>
