---
phase: quick-3
plan: 3
type: execute
wave: 1
depends_on: []
files_modified:
  - src/alteryx_diff/renderers/_graph_builder.py
  - src/alteryx_diff/renderers/graph_renderer.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Graph nodes are visually distinct by diff status with modern, accessible colors"
    - "Node shape uses rounded corners and is large enough to read comfortably"
    - "Changed nodes (added/removed/modified) have a visible accent border"
    - "Graph canvas is taller and uses a light off-white background"
    - "Control buttons look polished with hover states and clear spacing"
    - "Edges are curved and have directional visual weight"
    - "Legend swatches are circular pills matching new color scheme"
  artifacts:
    - path: "src/alteryx_diff/renderers/_graph_builder.py"
      provides: "Updated COLOR_MAP and node borderColor/borderWidth attributes"
    - path: "src/alteryx_diff/renderers/graph_renderer.py"
      provides: "Updated vis-network options, CSS, and graph container height"
  key_links:
    - from: "_graph_builder.py COLOR_MAP"
      to: "graph_renderer.py legend swatches"
      via: "hardcoded color strings must match in both files"
---

<objective>
Upgrade the graph section of the HTML diff report with modern UI/UX treatment: refined color palette, better node shapes, polished control buttons, taller canvas, and curved edges.

Purpose: The current graph uses flat Bootstrap-4 colors, small 500px canvas, and plain box nodes. Reviewers spend more time squinting at the graph than reading diffs.
Output: Updated graph_renderer.py and _graph_builder.py producing a visually improved graph fragment.
</objective>

<execution_context>
@/Users/laxmikantmukkawar/.claude/get-shit-done/workflows/execute-plan.md
@/Users/laxmikantmukkawar/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/alteryx_diff/renderers/_graph_builder.py
@src/alteryx_diff/renderers/graph_renderer.py
@tests/test_graph_renderer.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update COLOR_MAP and node attributes in _graph_builder.py</name>
  <files>src/alteryx_diff/renderers/_graph_builder.py</files>
  <action>
Replace COLOR_MAP with a modern, accessible palette. Add a BORDER_COLOR_MAP dict alongside it for accent borders on changed nodes.

New COLOR_MAP (background fill):
- "added":       "#d1fae5"   (soft emerald tint)
- "removed":     "#fee2e2"   (soft rose tint)
- "modified":    "#fef3c7"   (soft amber tint)
- "connection":  "#dbeafe"   (soft blue tint)
- "unchanged":   "#f1f5f9"   (slate-50)

New BORDER_COLOR_MAP (border accent, darker shade of fill):
- "added":       "#059669"   (emerald-600)
- "removed":     "#dc2626"   (red-600)
- "modified":    "#d97706"   (amber-600)
- "connection":  "#2563eb"   (blue-600)
- "unchanged":   "#cbd5e1"   (slate-300)

In build_digraph(), when calling G.add_node(), add two new attributes:
- borderColor=BORDER_COLOR_MAP[status]
- borderWidth=3 if status != "unchanged" else 1

The node `color` attribute must become a dict for vis-network to accept both fill and border:
  color={"background": COLOR_MAP[status], "border": BORDER_COLOR_MAP[status], "highlight": {"background": COLOR_MAP[status], "border": BORDER_COLOR_MAP[status]}}

Remove the standalone borderColor/borderWidth keys; they are now embedded in the color dict.

Keep CONTAINER_TYPE, LAYOUT_SCALE, and all function signatures unchanged. All 8 graph renderer tests must still pass.
  </action>
  <verify>
    <automated>/Users/laxmikantmukkawar/.cache/uv/archive-v0/bkiNW9PCUPjqEK-u4PtHi/uv-0.8.12.data/scripts/uv run pytest tests/test_graph_renderer.py -q</automated>
  </verify>
  <done>8 tests pass; COLOR_MAP uses soft tint palette; color dicts include background+border keys</done>
</task>

<task type="auto">
  <name>Task 2: Modernize graph fragment CSS, vis-network options, and controls in graph_renderer.py</name>
  <files>src/alteryx_diff/renderers/graph_renderer.py</files>
  <action>
Edit the _GRAPH_FRAGMENT_TEMPLATE string in graph_renderer.py. Make these specific changes:

1. **Graph container height**: Change `height:500px` to `height:620px`. Add `background:#f8fafc` (off-white, not stark white).

2. **vis-network options dict** (in the JS `options` variable):
   Replace the current options with:
   ```js
   var options = {
     physics: {enabled: false},
     nodes: {
       shape: 'box',
       borderWidth: 1,
       borderWidthSelected: 3,
       margin: {top: 8, right: 12, bottom: 8, left: 12},
       font: {size: 13, face: 'system-ui, -apple-system, sans-serif', color: '#1e293b'},
       shapeProperties: {borderRadius: 6},
       shadow: {enabled: false}
     },
     edges: {
       arrows: {to: {enabled: true, scaleFactor: 0.7, type: 'arrow'}},
       smooth: {enabled: true, type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.4},
       color: {color: '#94a3b8', highlight: '#475569', hover: '#475569'},
       width: 1.5,
       hoverWidth: 2.5,
       selectionWidth: 2.5
     },
     interaction: {zoomView: true, dragView: true, hover: true, tooltipDelay: 200, hideEdgesOnDrag: false}
   };
   ```

3. **Legend swatches**: Change the `border-radius:2px` to `border-radius:50%` on every legend `span` swatch element, and update the background colors to match the new BORDER_COLOR_MAP values:
   - Added swatch: `#059669`
   - Removed swatch: `#dc2626`
   - Modified swatch: `#d97706`
   - Connection swatch: `#2563eb`
   - Unchanged swatch: `#cbd5e1`

4. **Control buttons CSS**: Replace the existing `.ctrl-btn` style in `html_renderer.py`'s _TEMPLATE with:
   ```css
   .ctrl-btn { font-size: 0.8em; padding: 4px 10px; cursor: pointer; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; color: #475569; font-weight: 500; transition: background 0.15s, border-color 0.15s; }
   .ctrl-btn:hover { background: #f1f5f9; border-color: #94a3b8; }
   ```
   Note: `.ctrl-btn` is defined in `html_renderer.py`'s `_TEMPLATE` `<style>` block (line 40), NOT in graph_renderer.py. Update it there.

5. **graph-controls bar** (in graph_renderer.py): Add `padding:8px 0` and change the separator `color:#555` to `color:#64748b`.

6. **diff-panel border radius**: Change `border-radius` on `#diff-panel` from implicit 0 to `border-radius:8px 0 0 8px`.

All 8 existing tests in test_graph_renderer.py must still pass. The changes are CSS/JS string updates — no Python logic changes.
  </action>
  <verify>
    <automated>/Users/laxmikantmukkawar/.cache/uv/archive-v0/bkiNW9PCUPjqEK-u4PtHi/uv-0.8.12.data/scripts/uv run pytest tests/test_graph_renderer.py tests/test_html_renderer.py -q</automated>
  </verify>
  <done>All 15 tests pass (8 graph + 7 html); graph container is 620px with off-white background; vis-network uses cubicBezier edges; legend swatches are circular with border-accent colors; ctrl-btn has hover state</done>
</task>

</tasks>

<verification>
Run full test suite to confirm no regressions:
/Users/laxmikantmukkawar/.cache/uv/archive-v0/bkiNW9PCUPjqEK-u4PtHi/uv-0.8.12.data/scripts/uv run pytest -q

Expected: 105 tests pass (same baseline as v1.0 milestone).

Manually open diff_report.html in a browser (if available) to visually confirm:
- Nodes use soft tinted fills with darker accent borders on changed nodes
- Edges curve between nodes
- Container is taller with off-white background
- Buttons have visible hover state
</verification>

<success_criteria>
- 105 tests pass with no regressions
- COLOR_MAP uses soft tint palette (#d1fae5 / #fee2e2 / #fef3c7 / #dbeafe / #f1f5f9)
- Node color dicts include background + border keys (vis-network format)
- Graph container height is 620px
- Edges use cubicBezier smooth mode
- Legend swatches are circular (border-radius: 50%) with border-accent colors
</success_criteria>

<output>
After completion, create `.planning/quick/3-improve-graph-visualization-for-modern-u/3-SUMMARY.md`
</output>
