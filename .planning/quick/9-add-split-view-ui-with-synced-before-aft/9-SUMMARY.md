---
phase: quick-9
plan: 9
subsystem: renderers
tags: [split-view, vis-network, graph, ui, sync]
dependency_graph:
  requires: []
  provides: [split-view-graph, overlay-view-graph, ghost-nodes, center-change-panel]
  affects: [graph_renderer.py, _graph_builder.py, diff_report.html]
tech_stack:
  added: []
  patterns: [split-view-toggle, synchronized-viewport, ghost-nodes, localStorage-persistence]
key_files:
  created: []
  modified:
    - src/alteryx_diff/renderers/_graph_builder.py
    - src/alteryx_diff/renderers/graph_renderer.py
decisions:
  - "Ghost nodes use new/old position coords respectively so spatial context is accurate even when workflows differ significantly"
  - "syncingViewport boolean guard prevents infinite recursion between left/right pan sync handlers"
  - "center panel uses createElement+appendChild exclusively (no innerHTML) for XSS safety"
  - "Overlay View keeps exact current JS structure unchanged inside #overlay-view div"
  - "applyThemeColorsToSplit() called from applyThemeColors() so theme changes propagate consistently"
metrics:
  duration: 5 min
  completed: "2026-03-10"
  tasks: 2
  files: 2
---

# Quick Task 9: Add Split View UI with Synced Before/After Graphs

Split View (default) / Overlay View toggle for the diff report graph section — two vis-network instances side-by-side with synchronized pan/zoom, ghost nodes for spatial context, and a center change panel that navigates both graphs on click.

## What Was Built

**Task 1: build_split_node_list() helper (_graph_builder.py)**

Added a new public function `build_split_node_list()` to `_graph_builder.py` that builds two separate vis-network node lists for the split view. The left graph (old) contains real old nodes with status-colored backgrounds plus ghost placeholders (opacity 0.25, borderDashes [4,4]) for added nodes positioned at their new-workflow coordinates. The right graph (new) mirrors this with real new nodes plus ghost placeholders for removed nodes at their old-workflow coordinates.

**Task 2: Split/Overlay toggle UI (graph_renderer.py)**

Rewrote `_GRAPH_FRAGMENT_TEMPLATE` entirely and updated `GraphRenderer.render()`:

- View toggle bar with `btn-split` and `btn-overlay` buttons; active state via CSS class `.active` (blue #3b82f6)
- `#split-view`: three-column flex layout — left (flex:1 Before graph), center (280px change panel), right (flex:1 After graph)
- `#split-change-rows`: center panel built via DOM methods only (createElement/appendChild/textContent); clicking a row calls `focusNode()` to pan both graphs
- `#split-controls`: "Fit Both" button and legend dots
- `#overlay-view`: wraps exact existing graph-controls, graph-container, diff-panel, graph-overlay structure unchanged
- Synchronized viewport via `syncLeftToRight()`/`syncRightToLeft()` with `syncingViewport` guard
- `applyThemeColorsToSplit()` updates non-ghost nodes on both networks when theme changes
- View preference persists in `localStorage` under key `'alteryx-diff-view'`
- Split View is the default (`localStorage.getItem('alteryx-diff-view') || 'split'`)
- Responsive: `@media (max-width: 800px)` switches split-view to column layout
- Dark/light theme CSS rules added for split-view-left, split-view-right, split-change-rows

Python changes in `render()`:
- Added `build_split_node_list` to the import from `_graph_builder`
- Calls `build_split_node_list(result, nodes_old, nodes_new)` after computing positions
- Passes `nodes_old_json` and `nodes_new_json` as new template variables

## Verification Results

- `from alteryx_diff.renderers._graph_builder import build_split_node_list` imports without error
- `pytest tests/ -x -q`: 105 passed, 1 xfailed (zero regressions)
- `ruff check src/alteryx_diff/renderers/`: all checks passed
- Generated HTML contains: `split-view-left`, `split-view-right`, `split-change-rows`, `switchView`, `NODES_OLD`, `NODES_NEW`
- `localStorage` key `alteryx-diff-view` present in generated HTML
- Edge-presence assertion: `GRAPH_EDGES` non-empty in report from workflow.yxmd vs workflow2.yxmd (4 changes detected)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `src/alteryx_diff/renderers/_graph_builder.py`: FOUND
- `src/alteryx_diff/renderers/graph_renderer.py`: FOUND
- Task 1 commit 20a3732: FOUND
- Task 2 commit 2f20f8e: FOUND
- 105 tests passing: CONFIRMED
