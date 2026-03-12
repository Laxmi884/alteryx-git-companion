---
phase: quick-4
plan: 4
type: execute
wave: 1
depends_on: []
files_modified:
  - src/alteryx_diff/renderers/html_renderer.py
  - src/alteryx_diff/renderers/graph_renderer.py
  - tests/test_html_renderer.py
  - tests/test_graph_renderer.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Dark mode applies automatically via prefers-color-scheme media query — no user interaction needed"
    - "Graph nodes are draggable (fixed: false) so users can reorganize the layout"
    - "A fullscreen button expands the graph container to fill the viewport"
    - "All 105+ existing tests still pass after changes"
  artifacts:
    - path: "src/alteryx_diff/renderers/html_renderer.py"
      provides: "HTML template with dark mode CSS variables"
      contains: "prefers-color-scheme"
    - path: "src/alteryx_diff/renderers/graph_renderer.py"
      provides: "Graph fragment with draggable nodes and fullscreen toggle"
      contains: "fixed.*false"
  key_links:
    - from: "html_renderer.py _TEMPLATE"
      to: "graph_renderer.py _GRAPH_FRAGMENT_TEMPLATE"
      via: "{{ graph_html | safe }} injection"
      pattern: "graph_html"
    - from: "_GRAPH_FRAGMENT_TEMPLATE"
      to: "vis-network options"
      via: "fixed: false on each node entry"
      pattern: "fixed.*false"
---

<objective>
Add dark mode support, draggable graph nodes, and a fullscreen graph toggle to the HTML diff report.

Purpose: Users view this report in both light and dark OS themes; graph nodes with fixed=True prevent reorganization after layout; no fullscreen path exists for large workflows.
Output: Updated html_renderer.py (dark mode CSS) and graph_renderer.py (draggable nodes + fullscreen button + JS).
</objective>

<execution_context>
@/Users/laxmikantmukkawar/.claude/get-shit-done/workflows/execute-plan.md
@/Users/laxmikantmukkawar/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/3-improve-graph-visualization-for-modern-u/3-SUMMARY.md

<interfaces>
<!-- Key patterns the executor needs. Extracted from current source. -->

From src/alteryx_diff/renderers/html_renderer.py:
- _TEMPLATE is a triple-quoted string inside the module — all CSS is inline in a <style> block
- Current body background: #fff, color: #212529
- The template uses Jinja2 autoescape=True; graph_html injected via {{ graph_html | safe }}

From src/alteryx_diff/renderers/graph_renderer.py:
- _GRAPH_FRAGMENT_TEMPLATE is a triple-quoted string
- Node entries built in GraphRenderer.render() with "fixed": True — this prevents dragging
- vis-network options object has physics: {enabled: false}
- Graph container: height:620px, background:#f8fafc
- Controls div contains: Fit to Screen, Show Only Changes buttons

From src/alteryx_diff/renderers/_graph_builder.py:
- COLOR_MAP soft tints: added #d1fae5, removed #fee2e2, modified #fef3c7, connection #dbeafe, unchanged #f1f5f9
- BORDER_COLOR_MAP accents: added #059669, removed #dc2626, modified #d97706, connection #2563eb, unchanged #cbd5e1

Graph node format in nodes_json list:
{
  "id": node_id,
  "label": label,
  "color": {"background": ..., "border": ..., "highlight": {...}},
  "status": status,
  "title": title,
  "x": px,
  "y": py,
  "fixed": True   # <-- must become False for draggable
}
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add dark mode CSS to HTML report template</name>
  <files>src/alteryx_diff/renderers/html_renderer.py, tests/test_html_renderer.py</files>
  <action>
In html_renderer.py, update the `_TEMPLATE` string's `<style>` block to use CSS custom properties (variables) for theme-sensitive colors, then add a `@media (prefers-color-scheme: dark)` block that overrides them. Do NOT add JavaScript theme toggles — OS-level automatic switching only.

CSS variable scheme (light defaults, dark overrides):
```css
/* Light defaults */
:root {
  --bg: #fff;
  --text: #212529;
  --text-muted: #666;
  --border: #dee2e6;
  --row-bg: #f8f9fa;
  --row-hover: #e9ecef;
  --detail-bg: #fff;
  --field-label: #555;
  --before-bg: #fff5f5;
  --after-bg: #f5fff5;
  --btn-bg: #fff;
  --btn-text: #475569;
  --btn-border: #cbd5e1;
  --btn-hover-bg: #f1f5f9;
  --btn-hover-border: #94a3b8;
  --section-border: #eee;
  --empty-color: #888;
  --badge-added-bg: #d4edda; --badge-added-text: #155724; --badge-added-border: #c3e6cb;
  --badge-removed-bg: #f8d7da; --badge-removed-text: #721c24; --badge-removed-border: #f5c6cb;
  --badge-modified-bg: #fff3cd; --badge-modified-text: #856404; --badge-modified-border: #ffeeba;
  --badge-conn-bg: #cce5ff; --badge-conn-text: #004085; --badge-conn-border: #b8daff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f172a;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --border: #334155;
    --row-bg: #1e293b;
    --row-hover: #273449;
    --detail-bg: #131f31;
    --field-label: #94a3b8;
    --before-bg: #2d1518;
    --after-bg: #132318;
    --btn-bg: #1e293b;
    --btn-text: #94a3b8;
    --btn-border: #475569;
    --btn-hover-bg: #273449;
    --btn-hover-border: #64748b;
    --section-border: #334155;
    --empty-color: #64748b;
    --badge-added-bg: #052e16; --badge-added-text: #86efac; --badge-added-border: #166534;
    --badge-removed-bg: #2d1515; --badge-removed-text: #fca5a5; --badge-removed-border: #7f1d1d;
    --badge-modified-bg: #1c1506; --badge-modified-text: #fcd34d; --badge-modified-border: #78350f;
    --badge-conn-bg: #0c1a3a; --badge-conn-text: #93c5fd; --badge-conn-border: #1e3a5f;
  }
}
```

Replace all hardcoded color values in the CSS rules with the corresponding CSS variables. Keep the monospace font stack for `.value-block` unchanged. Keep `@media print` rule unchanged.

Replace in CSS rules:
- `background: #fff` → `background: var(--bg)` (body)
- `color: #212529` → `color: var(--text)` (body)
- `color: #666` (header p) → `color: var(--text-muted)`
- `border-bottom: 1px solid #dee2e6` (header) → `border-bottom: 1px solid var(--border)`
- Badge background/color/border → use `--badge-*` variables
- `border-bottom: 2px solid #eee` (h2) → `border-bottom: 2px solid var(--section-border)`
- `.tool-row background: #f8f9fa` → `var(--row-bg)`, `border: 1px solid #e9ecef` → `var(--border)`
- `.tool-row:hover background: #e9ecef` → `var(--row-hover)`
- `.tool-detail background: #fff` → `var(--detail-bg)`, border → `var(--border)`
- `.field-name color: #555` → `var(--field-label)`
- `.ctrl-btn background/color/border` → `--btn-*` variables
- `.empty color: #888` → `var(--empty-color)`

Also update the governance metadata section inline styles to use the same variables where possible (color:#888 → var(--text-muted), color:#555 → var(--field-label), border-top:1px solid #dee2e6 → var(--border)).

Tests: test_html_renderer.py checks for presence of `id="diff-data"` tag and JSON structure. No color assertions exist — tests should still pass. Run `pytest tests/test_html_renderer.py -x -q` to verify.
  </action>
  <verify>
    <automated>cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && python -m pytest tests/test_html_renderer.py tests/test_graph_renderer.py -x -q</automated>
  </verify>
  <done>_TEMPLATE contains `prefers-color-scheme: dark` and CSS custom properties. All html_renderer and graph_renderer tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Draggable graph nodes and fullscreen graph toggle</name>
  <files>src/alteryx_diff/renderers/graph_renderer.py, tests/test_graph_renderer.py</files>
  <action>
Two changes to graph_renderer.py:

**1. Make nodes draggable**

In `GraphRenderer.render()`, the node dict currently has `"fixed": True`. Change it to `"fixed": False`. This single change allows vis-network drag after the initial layout. Physics stays disabled (`physics: {enabled: false}` in options) — nodes stay where dropped, no simulation.

Change in the `entry` dict construction (around line 291):
```python
entry: dict[str, Any] = {
    ...
    "fixed": False,   # was True — allow user drag after layout
}
```

**2. Add fullscreen button to graph controls**

In `_GRAPH_FRAGMENT_TEMPLATE`, add a fullscreen button to the `#graph-controls` div:
```html
<button id="fullscreen-btn" class="ctrl-btn">Fullscreen</button>
```
Place it after the `fit-btn` button, before the `toggle-changes` button.

Add fullscreen CSS to the `<style>` block in the graph fragment (after the existing rules):
```css
#graph-section:fullscreen { background: #f8fafc; padding: 12px; }
#graph-section:fullscreen #graph-container { height: calc(100vh - 80px); }
@media (prefers-color-scheme: dark) {
  #graph-section:fullscreen { background: #0f172a; }
}
```

Add fullscreen JS (inside the IIFE, after the `fit-btn` listener):
```javascript
// Fullscreen toggle
document.getElementById('fullscreen-btn').addEventListener('click', function() {
  var section = document.getElementById('graph-section');
  if (!document.fullscreenElement) {
    section.requestFullscreen().catch(function() {});
    this.textContent = 'Exit Fullscreen';
  } else {
    document.exitFullscreen();
    this.textContent = 'Fullscreen';
  }
});
document.addEventListener('fullscreenchange', function() {
  if (!document.fullscreenElement) {
    var btn = document.getElementById('fullscreen-btn');
    if (btn) btn.textContent = 'Fullscreen';
    network.fit({animation: false});
  }
});
```

Also add dark mode support for the graph fragment. Add a `@media (prefers-color-scheme: dark)` block to the `<style>` in `_GRAPH_FRAGMENT_TEMPLATE`:
```css
@media (prefers-color-scheme: dark) {
  #graph-container { background: #0f172a !important; border-color: #334155 !important; }
  #diff-panel { background: #1e293b !important; border-color: #334155 !important; color: #e2e8f0 !important; }
  .panel-title { border-color: #334155 !important; color: #e2e8f0; }
  .panel-field-name { color: #94a3b8 !important; }
  .panel-before { background: #2d1518 !important; }
  .panel-after { background: #132318 !important; }
  .value-mono { color: #e2e8f0; }
}
```

Tests: test_graph_renderer.py has `test_node_colors_match_diff_status` which checks `color["background"]` against COLOR_MAP — this still works since color dict format is unchanged. The `"fixed"` field is not currently asserted in tests. Run full suite to verify.
  </action>
  <verify>
    <automated>cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && python -m pytest tests/ -x -q 2>&1 | tail -10</automated>
  </verify>
  <done>"fixed": False in GraphRenderer.render(), fullscreen button exists in _GRAPH_FRAGMENT_TEMPLATE, dark mode CSS in graph fragment, all 105+ tests pass.</done>
</task>

</tasks>

<verification>
Run full test suite after both tasks:
```bash
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && python -m pytest tests/ -q
```
Expected: 105 passed, 1 xfailed (pre-existing xfail on GUID test).

Also verify the diff_report.html can be regenerated:
```bash
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && python -m alteryx_diff workflow.yxmd workflow2.yxmd --output diff_report.html 2>/dev/null || echo "CLI check — only verifying no import errors"
python -c "from alteryx_diff.renderers import HTMLRenderer, GraphRenderer; print('imports OK')"
```
</verification>

<success_criteria>
- _TEMPLATE in html_renderer.py uses CSS custom properties and has `@media (prefers-color-scheme: dark)` block
- _GRAPH_FRAGMENT_TEMPLATE in graph_renderer.py has fullscreen button, fullscreen JS, dark mode CSS
- GraphRenderer.render() sets `"fixed": False` on all nodes
- All 105+ existing tests pass, 0 regressions
- `python -c "from alteryx_diff.renderers import HTMLRenderer, GraphRenderer"` exits 0
</success_criteria>

<output>
After completion, create `.planning/quick/4-modernize-diff-report-ui-ux-with-dark-mo/4-SUMMARY.md`
</output>
