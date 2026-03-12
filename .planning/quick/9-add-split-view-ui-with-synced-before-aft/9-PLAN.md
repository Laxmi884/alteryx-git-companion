---
phase: quick-9
plan: 9
type: execute
wave: 1
depends_on: []
files_modified:
  - src/alteryx_diff/renderers/graph_renderer.py
  - src/alteryx_diff/renderers/_graph_builder.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "Graph section shows Split View by default with three columns: left (old graph), center (scrollable change panel), right (new graph)"
    - "Overlay View button restores the current single merged graph behavior exactly as it exists today"
    - "View preference persists in localStorage across page loads"
    - "Both split-view graphs use canvas positions (Alteryx X/Y coordinates)"
    - "Removed nodes appear as ghost/faint outlines on the right (new) graph; added nodes appear as ghost/faint outlines on the left (old) graph"
    - "Panning or zooming one split-view graph syncs the other graph's viewport"
    - "Clicking a change row in the center panel pans both graphs to that node and briefly highlights it"
    - "Dark/light theme applies to all new elements consistently"
  artifacts:
    - path: "src/alteryx_diff/renderers/graph_renderer.py"
      provides: "Updated _GRAPH_FRAGMENT_TEMPLATE with split/overlay toggle and two vis-network instances; updated render() to pass nodes_old_json and nodes_new_json"
      contains: "split-view-left, split-view-right, split-change-rows, overlay-view"
    - path: "src/alteryx_diff/renderers/_graph_builder.py"
      provides: "build_split_node_list() helper returning (old_vis_nodes, new_vis_nodes) with ghost nodes included"
      exports: ["build_split_node_list"]
  key_links:
    - from: "graph_renderer.py render()"
      to: "_graph_builder.build_split_node_list()"
      via: "Python call, returns (old_vis_nodes, new_vis_nodes) as serialized via json.dumps"
    - from: "JS networkLeft / networkRight instances"
      to: "vis.DataSet(NODES_OLD) / vis.DataSet(NODES_NEW)"
      via: "Template variables nodes_old_json | safe and nodes_new_json | safe"
    - from: "JS networkLeft.on('dragEnd') and networkLeft.on('zoom')"
      to: "networkRight.moveTo()"
      via: "Sync handler inside initSplitNetworks(); symmetric for right->left"
    - from: "center panel change rows onclick"
      to: "networkLeft.moveTo() + networkRight.moveTo()"
      via: "focusNode(toolId) JS function"
---

<objective>
Replace the single-graph-only layout in the diff report with a Split View (default) / Overlay View (existing) toggle. Split View shows old and new workflow graphs side-by-side with synchronized pan/zoom and a center change panel. Overlay View preserves the current merged graph behavior unchanged.

Purpose: Reviewers can spatially compare where nodes were before and after, instantly see what was added/removed at a glance, and click change rows to navigate both graphs simultaneously.
Output: Updated graph_renderer.py (new template + Python data prep) and _graph_builder.py (ghost-node helper).
</objective>

<execution_context>
@/Users/laxmikantmukkawar/.claude/get-shit-done/workflows/execute-plan.md
@/Users/laxmikantmukkawar/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/alteryx_diff/renderers/graph_renderer.py
@src/alteryx_diff/renderers/_graph_builder.py
@src/alteryx_diff/renderers/html_renderer.py

<interfaces>
<!-- Key types the executor needs. Extracted from codebase. No exploration needed. -->

AlteryxNode (from models/workflow.py, inferred from usage in graph_renderer.py):
  tool_id: int | str      -- cast to int() throughout codebase
  tool_type: str          -- e.g. "AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect"
  x: float                -- Alteryx canvas X coordinate
  y: float                -- Alteryx canvas Y coordinate
  config: dict[str, Any]

DiffResult (from models/diff.py):
  added_nodes: tuple[AlteryxNode, ...]
  removed_nodes: tuple[AlteryxNode, ...]
  modified_nodes: tuple[NodeDiff, ...]   -- NodeDiff has .tool_id and .field_diffs
  edge_diffs: tuple[EdgeDiff, ...]

Existing _graph_builder.py public API:
  build_digraph(result, all_connections, all_nodes) -> nx.DiGraph[int]
  canvas_positions(nodes_old, nodes_new) -> dict[int, tuple[float, float]]
  hierarchical_positions(G) -> dict[int, tuple[float, float]]
  load_vis_js() -> str
  COLOR_MAP: dict[str, str]          -- status -> hex background color
  BORDER_COLOR_MAP: dict[str, str]   -- status -> hex border color
  CONTAINER_TYPE: str                -- ToolContainer tool_type string (skip these)

GraphRenderer.render() current signature (unchanged by this plan):
  render(self, result, all_connections, nodes_old, nodes_new, *, canvas_layout=False) -> str
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add build_split_node_list() to _graph_builder.py</name>
  <files>src/alteryx_diff/renderers/_graph_builder.py</files>
  <action>
Append a new public function `build_split_node_list` at the bottom of _graph_builder.py (after `load_vis_js`). Also update the module docstring Public API list to include it. Do NOT modify any existing functions — this is additive only.

Function signature:
```python
def build_split_node_list(
    result: DiffResult,
    nodes_old: tuple[AlteryxNode, ...],
    nodes_new: tuple[AlteryxNode, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
```

Docstring: "Build two separate vis-network node lists for split view. Returns (old_vis_nodes, new_vis_nodes). Left graph contains real old nodes plus ghost placeholders for added nodes. Right graph contains real new nodes plus ghost placeholders for removed nodes. Ghost nodes use opacity:0.25 and borderDashes:[4,4]."

Implementation:

Step 1 — Build ID sets:
  added_ids = {int(n.tool_id) for n in result.added_nodes}
  removed_ids = {int(n.tool_id) for n in result.removed_nodes}
  modified_ids = {int(nd.tool_id) for nd in result.modified_nodes}
  new_pos_lookup = {int(n.tool_id): (n.x, n.y) for n in nodes_new}
  old_pos_lookup = {int(n.tool_id): (n.x, n.y) for n in nodes_old}

Step 2 — Build left (old) node list:
  For each node in nodes_old, skip CONTAINER_TYPE.
  Determine status:
    "removed" if tool_id in removed_ids
    "modified" if tool_id in modified_ids
    "unchanged" otherwise
  Build node dict:
    {"id": tool_id, "label": short_label + "\n(" + str(tool_id) + ")",
     "x": node.x, "y": node.y, "fixed": False, "status": status,
     "color": {"background": COLOR_MAP[status], "border": BORDER_COLOR_MAP[status],
               "highlight": {"background": COLOR_MAP[status], "border": BORDER_COLOR_MAP[status]}},
     "title": node.tool_type + " | " + status}

  Then for each added node in result.added_nodes (skip CONTAINER_TYPE tool_type):
    pos = new_pos_lookup.get(int(n.tool_id), (0.0, 0.0))
    short_label = n.tool_type.split(".")[-1]
    Append ghost node dict:
      {"id": int(n.tool_id), "label": short_label + "\n(" + str(int(n.tool_id)) + ")",
       "x": pos[0], "y": pos[1], "fixed": False, "status": "ghost_added",
       "opacity": 0.25, "borderDashes": [4, 4],
       "color": {"background": "#d1fae5", "border": "#6ee7b7"},
       "title": n.tool_type + " | added (in new workflow)"}

Step 3 — Build right (new) node list:
  For each node in nodes_new, skip CONTAINER_TYPE.
  Determine status:
    "added" if tool_id in added_ids
    "modified" if tool_id in modified_ids
    "unchanged" otherwise
  Build node dict with same structure as left side (real x, y from node).

  Then for each removed node in result.removed_nodes (skip CONTAINER_TYPE tool_type):
    pos = old_pos_lookup.get(int(n.tool_id), (0.0, 0.0))
    short_label = n.tool_type.split(".")[-1]
    Append ghost node dict:
      {"id": int(n.tool_id), "label": short_label + "\n(" + str(int(n.tool_id)) + ")",
       "x": pos[0], "y": pos[1], "fixed": False, "status": "ghost_removed",
       "opacity": 0.25, "borderDashes": [4, 4],
       "color": {"background": "#fee2e2", "border": "#fca5a5"},
       "title": n.tool_type + " | removed (was in old workflow)"}

Step 4 — Return (old_vis_nodes, new_vis_nodes).

Type hint for return value: tuple[list[dict[str, Any]], list[dict[str, Any]]]
  </action>
  <verify>
```bash
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && uv run python -c "from alteryx_diff.renderers._graph_builder import build_split_node_list; print('import OK')"
```
Must print "import OK". Then:
```bash
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && uv run ruff check src/alteryx_diff/renderers/_graph_builder.py && uv run mypy src/alteryx_diff/renderers/_graph_builder.py --strict && echo "lint OK"
```
Must print "lint OK" with no new errors.
  </verify>
  <done>build_split_node_list is importable and passes ruff + mypy strict checks on _graph_builder.py.</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite graph_renderer.py with split/overlay toggle UI</name>
  <files>src/alteryx_diff/renderers/graph_renderer.py</files>
  <action>
Replace `_GRAPH_FRAGMENT_TEMPLATE` in graph_renderer.py and update `GraphRenderer.render()`. The `# ruff: noqa: E501` pragma at the top already suppresses line-length warnings.

CRITICAL: The overlay-view section (step 5 below) must be an exact structural copy of the current template's graph-controls, graph-container, diff-panel, and graph-overlay divs. Do not simplify or omit any existing overlay behavior. The existing pytest suite exercises the overlay path and will catch regressions.

--- Python changes in render() ---

Add `build_split_node_list` to the existing import from `_graph_builder`:
  from alteryx_diff.renderers._graph_builder import (
      build_digraph, build_split_node_list, canvas_positions, hierarchical_positions, load_vis_js,
  )

Inside render(), after computing positions, call:
  old_vis_nodes, new_vis_nodes = build_split_node_list(result, nodes_old, nodes_new)

Pass to template.render():
  nodes_old_json=json.dumps(old_vis_nodes)   -- new
  nodes_new_json=json.dumps(new_vis_nodes)   -- new
  Keep all existing kwargs: nodes_json, edges_json, vis_js.

--- Template structure (replace _GRAPH_FRAGMENT_TEMPLATE entirely) ---

The new template has these top-level sections inside <section id="graph-section">:

1. HEADING: <h2>Workflow Graph</h2>

2. VIEW TOGGLE BAR:
   <div id="graph-view-toggle"> with two buttons:
     <button id="btn-split" onclick="switchView('split')">Split View</button>
     <button id="btn-overlay" onclick="switchView('overlay')">Overlay View</button>
   Style the active button blue (#3b82f6, white text), inactive transparent.

3. SPLIT VIEW CONTAINER: <div id="split-view" style="display:flex;...height:600px;...">
   Three children:
   a. Left column (flex:1): header "Before" + <div id="split-view-left"> for vis-network
   b. Center column (fixed width 280px): sticky header "Changes" + <div id="split-change-rows">
      The center panel change rows are built entirely with DOM methods (createElement,
      appendChild, textContent) in JS — NOT with any direct HTML string assignment.
   c. Right column (flex:1): header "After" + <div id="split-view-right"> for vis-network

4. SPLIT CONTROLS: <div id="split-controls"> with "Fit Both" button and legend dots.

5. OVERLAY VIEW CONTAINER: <div id="overlay-view" style="display:none;">
   Contains the existing graph-controls div, graph-container div, diff-panel div,
   and graph-overlay div — identical structure to the current template.

6. STYLE BLOCK: Extend the existing CSS with:
   - Dark mode rules for split-view-left and split-view-right backgrounds.
   - .split-change-row class (flex row, padding, hover state, border-bottom).
   - .split-change-badge class (small colored circle).
   - Responsive @media rule: at max-width 800px, split-view goes flex-direction:column.
   - Button active/inactive state via CSS class toggling (not inline style mutation).

7. SCRIPT BLOCK: Single IIFE containing three logical sections in order:

   SECTION A — Shared data (declare once at top of IIFE):
     var GRAPH_NODES = {{ nodes_json | safe }};
     var GRAPH_EDGES = {{ edges_json | safe }};
     var NODES_OLD = {{ nodes_old_json | safe }};
     var NODES_NEW = {{ nodes_new_json | safe }};
     var DIFF_DATA = JSON.parse(document.getElementById('diff-data').textContent);
     var TOOL_INDEX = {};  -- build same as current code

   SECTION B — Overlay network (identical to current code):
     var nodesDataset, edgesDataset, network (all scoped to IIFE);
     All existing functions: isDark, applyThemeColors, show-only-changes toggle,
     fit button, fullscreen button, click handler, openSidePanel, closeSidePanel,
     buildPanelContent, formatVal, escape key handler, overlay click handler.
     The MutationObserver callback now also calls applyThemeColorsToSplit() after
     calling applyThemeColors() (applyThemeColorsToSplit defined later but hoisted).

   SECTION C — Split network + view switcher:

     Variables:
       var networkLeft = null, networkRight = null;
       var syncingViewport = false;

     function initSplitNetworks():
       Guard: if (networkLeft) return;
       Get leftContainer and rightContainer by ID.
       Build leftNodeIds = Set of IDs where status is NOT 'ghost_added'.
       Build rightNodeIds = Set of IDs where status is NOT 'ghost_removed'.
       Filter GRAPH_EDGES to leftEdges (both from/to in leftNodeIds).
       Filter GRAPH_EDGES to rightEdges (both from/to in rightNodeIds).
       Create networkLeft = new vis.Network(leftContainer, {nodes: new vis.DataSet(NODES_OLD), edges: new vis.DataSet(leftEdges)}, SPLIT_OPTIONS).
       Create networkRight = new vis.Network(rightContainer, {nodes: new vis.DataSet(NODES_NEW), edges: new vis.DataSet(rightEdges)}, SPLIT_OPTIONS).
       Call networkLeft.fit() and networkRight.fit().
       Register sync listeners:
         networkLeft.on('dragEnd', syncLeftToRight);
         networkLeft.on('zoom', syncLeftToRight);
         networkRight.on('dragEnd', syncRightToLeft);
         networkRight.on('zoom', syncRightToLeft);
       Call applyThemeColorsToSplit().

     function syncLeftToRight():
       if (syncingViewport) return;
       syncingViewport = true;
       networkRight.moveTo({position: networkLeft.getViewPosition(), scale: networkLeft.getScale(), animation: false});
       syncingViewport = false;

     function syncRightToLeft():
       if (syncingViewport) return;
       syncingViewport = true;
       networkLeft.moveTo({position: networkRight.getViewPosition(), scale: networkRight.getScale(), animation: false});
       syncingViewport = false;

     var SPLIT_OPTIONS = { physics:{enabled:false}, nodes:{shape:'box', borderWidth:1, margin:{top:6,right:10,bottom:6,left:10}, font:{size:12,face:'system-ui,-apple-system,sans-serif'}, shapeProperties:{borderRadius:6}}, edges:{arrows:{to:{enabled:true,scaleFactor:0.6}}, smooth:{enabled:true,type:'cubicBezier',forceDirection:'horizontal',roundness:0.4}, color:{color:'#94a3b8'}, width:1.2}, interaction:{zoomView:true, dragView:true, hover:true} };

     function applyThemeColorsToSplit():
       if (!networkLeft) return;
       var palette = isDark() ? DARK_COLORS : LIGHT_COLORS;
       Update non-ghost nodes in networkLeft.body.data.nodes and networkRight.body.data.nodes
       using palette[n.status] where status is not 'ghost_added' or 'ghost_removed'.

     function focusNode(toolId):
       var pos = null;
       Try networkLeft.getPosition(toolId), catch silently.
       If null, try networkRight.getPosition(toolId), catch silently.
       If pos found, call moveTo on both networks with scale:1.2 and smooth animation.

     function buildCenterPanel():
       Get container = document.getElementById('split-change-rows').
       Build array of {cat, item} from DIFF_DATA['added'], DIFF_DATA['removed'], DIFF_DATA['modified'].
       If empty: create a div with textContent "No changes." and append to container.
       Otherwise for each entry:
         Create row div with class "split-change-row".
         Set data-tool-id attribute.
         Create badge span with class "split-change-badge", set background color via style.background.
         Create label span with textContent = shortType + " (" + tool_id + ")".
         Create category span with textContent = cat.
         Append badge, label, catTag to row using appendChild.
         Add click listener that calls focusNode(item.tool_id).
         Append row to container using appendChild.
       -- All DOM construction uses createElement + appendChild + textContent only.
          No direct HTML string assignment is used anywhere.

     Call buildCenterPanel() immediately.

     View switcher:
       var currentView = localStorage.getItem('alteryx-diff-view') || 'split';

       function switchView(view):
         currentView = view;
         localStorage.setItem('alteryx-diff-view', view);
         if (view === 'split'):
           Show split-view (display:flex), show split-controls (display:flex).
           Hide overlay-view (display:none).
           Mark btn-split active, btn-overlay inactive via classList.
           Call initSplitNetworks().
           setTimeout 50ms: call networkLeft.redraw() and networkRight.redraw() if not null.
         else:
           Hide split-view (display:none), hide split-controls (display:none).
           Show overlay-view (display:block).
           Mark btn-overlay active, btn-split inactive via classList.
           setTimeout 50ms: call network.fit({animation:false}) if not null.

       Call switchView(currentView) at end of IIFE to initialize on load.

  </action>
  <verify>
Run import check:
```bash
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && uv run python -c "
from alteryx_diff.renderers.graph_renderer import GraphRenderer
import inspect
src = inspect.getsource(GraphRenderer.render)
assert 'nodes_old_json' in src
assert 'nodes_new_json' in src
assert 'build_split_node_list' in src
print('render() API check OK')
"
```

Run full test suite:
```bash
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && uv run pytest tests/ -x -q 2>&1 | tail -20
```
All existing tests must pass (zero regressions).

Run ruff on both modified files:
```bash
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && uv run ruff check src/alteryx_diff/renderers/graph_renderer.py src/alteryx_diff/renderers/_graph_builder.py && echo "ruff OK"
```

Spot-check generated HTML structure by generating a report with any two .yxmd files from the examples/ folder (or workflow.yxmd and workflow2.yxmd in the project root if examples lack a second file). Confirm the output HTML contains all of the following strings:
  - "split-view-left"
  - "split-view-right"
  - "split-change-rows"
  - "switchView"
  - "NODES_OLD"
  - "NODES_NEW"

Edge-presence assertion (use a workflow pair known to have connections — e.g., workflow.yxmd vs workflow2.yxmd). Generate HTML output and assert that GRAPH_EDGES in the rendered source contains at least one edge object, confirming the edge array threaded into NODES_OLD/NODES_NEW filtering is non-empty:
```bash
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && uv run python -c "
import subprocess, sys
result = subprocess.run(
    ['uv', 'run', 'alteryx-diff', 'workflow.yxmd', 'workflow2.yxmd', '--output', '/tmp/split_check.html'],
    capture_output=True, text=True
)
html = open('/tmp/split_check.html').read()
assert 'split-change-rows' in html, 'split-change-rows ID missing'
idx = html.find('var GRAPH_EDGES =')
assert idx != -1, 'GRAPH_EDGES missing'
edges_snippet = html[idx:idx+200]
assert '{' in edges_snippet or '[' in edges_snippet, 'GRAPH_EDGES appears empty'
print('edge-presence check OK')
" 2>&1
```
If workflow.yxmd and workflow2.yxmd are identical (no connections), use any differing pair from examples/ instead; the assertion only needs at least one from/to edge object present.
  </verify>
  <done>
- All existing pytest tests pass with zero regressions.
- ruff passes on both modified files with no new errors.
- Generated HTML contains split-view and overlay-view containers plus all required JS variables and the "split-change-rows" center panel ID.
- Edge-presence assertion confirms GRAPH_EDGES is non-empty in a report generated from a workflow pair with connections.
- Visually: Split View is default, center panel renders change rows, Overlay View restores current merged graph.
  </done>
</task>

</tasks>

<verification>
1. `from alteryx_diff.renderers._graph_builder import build_split_node_list` imports without error.
2. `uv run pytest tests/ -x -q` passes all tests (zero regressions).
3. Generated HTML contains: id="split-view-left", id="split-view-right", id="split-change-rows", var NODES_OLD, var NODES_NEW, function switchView.
4. `uv run ruff check src/alteryx_diff/renderers/` passes with no new errors.
5. View toggle persists in localStorage ('alteryx-diff-view' key).
6. GRAPH_EDGES in generated HTML is non-empty when run against a workflow pair with known connections.
</verification>

<success_criteria>
- Split View is the default when opening the report.
- Two vis-network instances render old and new workflow graphs side-by-side using Alteryx canvas coordinates (nodes_old X/Y for left, nodes_new X/Y for right).
- Ghost nodes (borderDashes, opacity 0.25) appear on the opposite graph to show spatial context for added/removed nodes.
- Panning or zooming one graph syncs the other via moveTo() with syncingViewport guard to prevent infinite recursion.
- Center panel (id="split-change-rows") lists all added, removed, and modified nodes; clicking a row calls focusNode() to pan both graphs.
- Overlay View button restores exact current behavior (single merged graph, slide-in side panel on click, show-only-changes toggle, fullscreen toggle).
- View preference persists in localStorage under key 'alteryx-diff-view'.
- Dark/light theme applies correctly to all new split-view elements.
- All 105+ existing tests continue to pass.
</success_criteria>

<output>
After completion, create `.planning/quick/9-add-split-view-ui-with-synced-before-aft/9-SUMMARY.md` with what was built, key decisions, and any deviations from the plan.
</output>
