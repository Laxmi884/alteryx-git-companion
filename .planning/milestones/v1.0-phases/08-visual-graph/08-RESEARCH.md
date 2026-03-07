# Phase 8: Visual Graph - Research

**Researched:** 2026-03-06
**Domain:** Python graph visualization — pyvis / NetworkX / D3.js; self-contained inline HTML; interactive click/hover panels
**Confidence:** HIGH (stack verified; pyvis CDN issue confirmed from official source; NetworkX API confirmed from official docs)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Node labels & information density
- Tool name only is always visible on the node (no tool type, no ID)
- Change type communicated by color only — no text badge or subtitle on the node
- An inline legend is embedded in the graph panel itself (green = added, red = removed, yellow = modified, blue = connection change, neutral = unchanged)
- Tool type is accessible via hover tooltip (not on the node face)

#### Hover tooltip
- Hovering a node shows: tool type + change type + count of changed config fields
- Applies to changed nodes; for unchanged nodes, no hover behavior (nodes not interactive)

#### Diff panel UX
- Clicking a changed node opens a slide-in side panel from the right
- Graph remains visible while the panel is open
- Panel contents: config key-value diff only — just the changed fields, two-column before/after format
- Closing: click anywhere outside the panel or press Escape
- Clicking a different node while a panel is open replaces panel contents (implicit switch)

#### Unchanged node treatment
- Unchanged nodes are muted / de-emphasized (lighter gray color)
- A "Show only changes" toggle button is present in the graph controls
- When unchanged nodes are hidden, their connected edges are also hidden
- Unchanged nodes are not clickable — no interaction on click

#### In-browser controls
- Zoom (scroll/pinch) + fit-to-screen button only
- No per-change-type filter checkboxes — the unchanged-toggle is sufficient
- Layout (hierarchical vs canvas) is baked in at report generation via CLI flag; no in-browser layout switch
- No search/highlight input

### Claude's Discretion
- Exact node sizing and font size
- Side panel width and animation style
- Fit-to-screen button placement within the graph panel
- Visual style of the muted/gray treatment for unchanged nodes
- How to handle the tooltip position relative to node

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GRPH-01 | Report embeds an interactive graph rendering tools as nodes and connections as directed edges | Custom D3.js/vis-network template embedded via Jinja2; no pyvis file write needed |
| GRPH-02 | Hierarchical left-to-right auto-layout (topological sort) by default; `--canvas-layout` flag uses Alteryx canvas X/Y coordinates | NetworkX `topological_generations` + `multipartite_layout(align='vertical')` for default; raw `AlteryxNode.x`/`y` for canvas mode |
| GRPH-03 | Nodes color-coded: green=added, red=removed, yellow=modified, blue=connection change; unchanged = neutral | Color constants set as node attributes during DiGraph construction; transferred to renderer |
| GRPH-04 | Hover or click a graph node to display inline config diff without page reload | DIFF_DATA JSON embedded in `<script>` tag (same pattern as HTML report); JS reads it on click |
</phase_requirements>

---

## Summary

Phase 8 adds an interactive workflow topology graph to the existing self-contained HTML report. The core technical challenge is embedding a fully-offline graph visualization (no CDN) in HTML with interactive click/hover behavior driven by the already-present `DIFF_DATA` JSON pattern established in Phase 7.

The spike plan (08-01) exists because pyvis 0.3.2 has a confirmed, unfixed Bootstrap CDN leak in `cdn_resources='in_line'` mode (GitHub issue #228, PR #201 still open as of 2026). The Bootstrap `<link>` and `<script>` tags are hardcoded in pyvis's Jinja2 template and are emitted regardless of `cdn_resources` setting. This violates REPT-04 / GRPH-01 self-contained requirement. The spike must quantify whether a regex post-processing workaround is viable or whether a custom vis-network Jinja2 template is required.

**Recommendation from evidence:** Use a custom Jinja2 template with vis-network's standalone UMD bundle vendored and inlined as a `<script>` block — the same pattern as Phase 7's embedded JS/CSS. This completely avoids the pyvis CDN leak problem, requires no post-processing, and aligns with the project's established "inline everything" approach. NetworkX is already a runtime dependency and handles DiGraph construction plus layout coordinate computation entirely in Python before any HTML is generated.

**Primary recommendation:** Implement a `GraphRenderer` class using a custom Jinja2 template with vis-network standalone inlined. Follow the exact renderer pattern from `HTMLRenderer` (Phase 7). Use pyvis only if the spike proves the Bootstrap CDN leak is cleanly removable with a one-line regex and no other CDN references remain.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | >=3.6 (already in deps: 3.6.1) | DiGraph construction, `topological_generations`, `multipartite_layout`, cycle detection | Already a runtime dependency; `topological_generations` + `multipartite_layout(align='vertical')` is the documented NetworkX pattern for hierarchical left-to-right DAG layout |
| jinja2 | >=3.1.6 (already in deps) | Jinja2 template for graph HTML embedding | Already used by HTMLRenderer; GraphRenderer follows identical renderer pattern |
| vis-network | 9.1.4 (standalone UMD, vendored inline) | Browser-side graph rendering: nodes, edges, zoom, pan, click/hover events | Used by pyvis internally; mature, no-physics fixed-position mode proven at 500+ nodes; standalone UMD bundle can be inlined directly into the Jinja2 template |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyvis | 0.3.2 (spike/dev only) | Potentially used to generate HTML then strip CDN tags | Only if spike in 08-01 shows the regex workaround is a clean one-liner and no additional CDN references remain |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| vis-network (inlined) | D3.js v7 | D3 requires custom force-layout and interaction code; vis-network provides click, hover, zoom, pan, fixed-position mode out of the box. For a static diff report, vis-network's built-in interaction model wins. |
| Custom Jinja2 template | pyvis generate_html() + post-processing | pyvis CDN leak is unfixed in 0.3.2; post-processing adds fragility. Custom template has zero CDN by construction. |
| networkx multipartite_layout | graphviz dot layout | graphviz is a system binary not in pyproject.toml; adds install complexity. NetworkX pure-Python layout is sufficient for 500-node display. |

**Installation:**

No new runtime dependencies are needed. networkx and jinja2 are already runtime deps. The vis-network standalone UMD bundle is vendored into `src/alteryx_diff/static/vis-network.min.js` and read via `importlib.resources` at renderer instantiation. No `pip install` step for the browser library.

---

## Architecture Patterns

### Recommended Project Structure

```
src/alteryx_diff/
├── renderers/
│   ├── __init__.py           # re-export GraphRenderer alongside HTMLRenderer
│   ├── html_renderer.py      # existing Phase 7 renderer (unchanged in Phase 8)
│   ├── graph_renderer.py     # NEW: GraphRenderer class
│   └── _graph_builder.py     # NEW: build_digraph(), compute_positions() helpers
├── static/
│   └── vis-network.min.js    # NEW: vendored vis-network standalone UMD bundle
tests/
├── fixtures/
│   └── graph.py              # NEW: DiffResult fixtures for graph tests (ToolIDs 801+)
└── test_graph_renderer.py    # NEW: graph rendering tests
```

No new packages or directories beyond `static/`. GraphRenderer follows the exact same renderer pattern established by JSONRenderer and HTMLRenderer in Phases 6 and 7.

### Pattern 1: DiGraph Construction from DiffResult

**What:** Build a `networkx.DiGraph` from `DiffResult` plus the original `WorkflowDoc` connections, assigning `diff_status`, `color`, and `title` node attributes.

**When to use:** At render time inside `GraphRenderer.render()`.

**Example:**
```python
# Source: NetworkX official docs + project DiffResult model
import networkx as nx
from alteryx_diff.models import DiffResult
from alteryx_diff.models.workflow import AlteryxConnection

COLOR_MAP = {
    "added":      "#28a745",  # green
    "removed":    "#dc3545",  # red
    "modified":   "#ffc107",  # yellow/amber
    "connection": "#007bff",  # blue
    "unchanged":  "#adb5bd",  # neutral gray
}

def build_digraph(
    result: DiffResult,
    all_connections: tuple[AlteryxConnection, ...],
    all_nodes_by_id: dict[int, str],  # tool_id -> tool_type
) -> nx.DiGraph:
    G: nx.DiGraph = nx.DiGraph()

    added_ids = {int(n.tool_id) for n in result.added_nodes}
    removed_ids = {int(n.tool_id) for n in result.removed_nodes}
    modified_ids = {int(nd.tool_id) for nd in result.modified_nodes}
    conn_changed_ids = (
        {int(e.src_tool) for e in result.edge_diffs}
        | {int(e.dst_tool) for e in result.edge_diffs}
    )

    for tool_id, tool_type in all_nodes_by_id.items():
        if tool_id in added_ids:
            status = "added"
        elif tool_id in removed_ids:
            status = "removed"
        elif tool_id in modified_ids:
            status = "modified"
        elif tool_id in conn_changed_ids:
            status = "connection"
        else:
            status = "unchanged"
        G.add_node(
            tool_id,
            label=tool_type,
            color=COLOR_MAP[status],
            status=status,
            title=tool_type,  # vis-network tooltip on hover
        )

    for conn in all_connections:
        G.add_edge(int(conn.src_tool), int(conn.dst_tool))
    return G
```

### Pattern 2: Hierarchical Left-to-Right Layout via Topological Sort

**What:** Use `networkx.topological_generations` to assign layer depths, then `multipartite_layout(align='vertical')` to get normalized x/y positions suitable for vis-network.

**When to use:** Default layout mode (when `--canvas-layout` is NOT set).

**Cycle caveat:** Alteryx workflows can contain feedback loops (cycles). `topological_generations` raises `NetworkXUnfeasible` on cyclic graphs. Strategy: detect and temporarily remove back-edges for layout, then re-add them for rendering.

**Example:**
```python
# Source: https://networkx.org/documentation/stable/auto_examples/graph/plot_dag_layout.html
import networkx as nx

LAYOUT_SCALE = 800  # pixel scale for vis-network viewport

def hierarchical_positions(G: nx.DiGraph) -> dict[int, tuple[float, float]]:
    """Compute left-to-right hierarchical positions via topological sort.
    Handles cycles by temporarily removing back-edges before layout.
    Returns {tool_id: (x_pixels, y_pixels)}.
    """
    dag = G.copy()
    removed_back_edges: list[tuple[int, int]] = []
    while not nx.is_directed_acyclic_graph(dag):
        cycle = list(nx.find_cycle(dag))
        back_edge = cycle[-1][:2]
        dag.remove_edge(*back_edge)
        removed_back_edges.append(back_edge)

    for layer, nodes in enumerate(nx.topological_generations(dag)):
        for node in nodes:
            dag.nodes[node]["layer"] = layer

    # align='vertical' => layers are vertical columns left-to-right
    raw_pos = nx.multipartite_layout(dag, subset_key="layer", align="vertical")
    # raw_pos values are numpy arrays [x, y] in range [-1, 1]
    return {
        int(node): (float(coords[0]) * LAYOUT_SCALE, float(coords[1]) * LAYOUT_SCALE)
        for node, coords in raw_pos.items()
    }
```

### Pattern 3: Canvas-Layout Mode (--canvas-layout)

**What:** Position nodes directly at Alteryx canvas X/Y coordinates stored in `AlteryxNode.x` and `AlteryxNode.y`.

**When to use:** When `--canvas-layout` flag is passed. Use new workflow positions for added/modified nodes, old workflow positions for removed nodes.

**Example:**
```python
# Source: project AlteryxNode model (models/workflow.py)
def canvas_positions(
    nodes_old: tuple[AlteryxNode, ...],
    nodes_new: tuple[AlteryxNode, ...],
) -> dict[int, tuple[float, float]]:
    pos: dict[int, tuple[float, float]] = {}
    for node in nodes_old:
        pos[int(node.tool_id)] = (node.x, node.y)
    for node in nodes_new:  # new overrides old (covers modified + added)
        pos[int(node.tool_id)] = (node.x, node.y)
    return pos
```

### Pattern 4: vis-network Inline Embedding Pattern

**What:** Vendor vis-network's standalone UMD minified JS into `src/alteryx_diff/static/vis-network.min.js`. Read at renderer instantiation via `importlib.resources` and inject into Jinja2 template as a `<script>` block.

**When to use:** Always — ensures GRPH-01 / REPT-04 self-contained requirement with zero CDN references.

**Vendoring steps (one-time, done during spike 08-01):**
1. Download: `curl -L https://unpkg.com/vis-network@9.1.4/standalone/umd/vis-network.min.js -o src/alteryx_diff/static/vis-network.min.js`
2. Add `static/` to package data in `pyproject.toml` under `[tool.setuptools.package-data]` or equivalent uv_build config
3. Read via `importlib.resources.files("alteryx_diff").joinpath("static/vis-network.min.js").read_text()`

**Template injection:**
```python
# In graph_renderer.py
import importlib.resources as pkg_resources

class GraphRenderer:
    _VIS_JS: str = pkg_resources.files("alteryx_diff") \
        .joinpath("static/vis-network.min.js").read_text(encoding="utf-8")
```

### Pattern 5: DIFF_DATA JSON + Interactive Panel (Browser-Side)

**What:** Reuse the existing `DIFF_DATA` JSON-in-script-tag pattern from Phase 7. The graph section reads from the same `<script id="diff-data">` tag already embedded by HTMLRenderer.

**When to use:** Node click and hover interactions in the graph section.

**JavaScript pattern (vanilla JS, no framework — matches Phase 7 convention):**
```javascript
// Source: Phase 7 html_renderer.py DIFF_DATA pattern
var DIFF_DATA = JSON.parse(document.getElementById('diff-data').textContent);

// Build fast lookup: tool_id (number) -> {category, data}
var TOOL_INDEX = {};
['added', 'removed', 'modified'].forEach(function(cat) {
    (DIFF_DATA[cat] || []).forEach(function(item) {
        TOOL_INDEX[item.tool_id] = { category: cat, data: item };
    });
});

// vis-network click handler
network.on('click', function(params) {
    if (params.nodes.length === 0) {
        closeSidePanel();
        return;
    }
    var nodeId = params.nodes[0];  // integer
    var entry = TOOL_INDEX[nodeId];
    if (!entry) return;  // unchanged node - no panel
    openSidePanel(nodeId, entry);
});
```

**Side panel with safe DOM construction (no innerHTML — matches Phase 7 buildDetail pattern):**
```javascript
function openSidePanel(nodeId, entry) {
    var panel = document.getElementById('diff-panel');
    // Clear previous content using safe DOM method
    while (panel.firstChild) { panel.removeChild(panel.firstChild); }
    buildPanelContent(panel, entry);
    panel.classList.add('open');
}

function buildPanelContent(panel, entry) {
    // Use document.createElement / textContent for all content — no innerHTML
    // Matches the buildDetail() pattern in Phase 7 html_renderer.py
    var data = entry.data;
    if (entry.category === 'modified') {
        data.field_diffs.forEach(function(fd) {
            var row = document.createElement('div');
            row.className = 'field-row';
            var nameEl = document.createElement('div');
            nameEl.className = 'field-name';
            nameEl.textContent = fd.field;
            row.appendChild(nameEl);
            panel.appendChild(row);
        });
    }
}
```

### Pattern 6: "Show Only Changes" Toggle + Fit-to-Screen

```javascript
// vis-network DataSet update approach — hide/show by updating node.hidden property
var nodesDataset = new vis.DataSet(GRAPH_NODES);
var edgesDataset = new vis.DataSet(GRAPH_EDGES);
var showOnlyChanges = false;

document.getElementById('toggle-changes').addEventListener('click', function() {
    showOnlyChanges = !showOnlyChanges;
    var hiddenIds = new Set(
        showOnlyChanges
        ? GRAPH_NODES.filter(function(n) { return n.status === 'unchanged'; })
                     .map(function(n) { return n.id; })
        : []
    );
    nodesDataset.update(GRAPH_NODES.map(function(n) {
        return { id: n.id, hidden: hiddenIds.has(n.id) };
    }));
    edgesDataset.update(GRAPH_EDGES.map(function(e) {
        return { id: e.id, hidden: hiddenIds.has(e.from) || hiddenIds.has(e.to) };
    }));
});

// Fit-to-screen button
document.getElementById('fit-btn').addEventListener('click', function() {
    network.fit({ animation: true });
});
```

### Anti-Patterns to Avoid

- **Using pyvis without verifying CDN strip:** pyvis 0.3.2 emits Bootstrap CDN `<link>` and `<script>` tags unconditionally in `cdn_resources='in_line'` mode. The existing `test_render_self_contained()` test checks for `cdn.` in output and will fail.
- **Enabling vis-network physics:** Physics simulation causes browser hang with 500+ nodes. Always set `physics: { enabled: false }` and pass pre-computed positions.
- **Using `topological_sort` directly:** Use `topological_generations` — it groups nodes into layers for `multipartite_layout`. `topological_sort` returns a flat sequence with no layer information.
- **Calling `multipartite_layout` with `align='horizontal'`:** This is incorrect for left-to-right layout. Use `align='vertical'` (default) — layers are vertical columns arranged left-to-right.
- **Assuming Alteryx workflows are acyclic:** Some workflows have feedback connections. Guard `topological_generations` with `nx.is_directed_acyclic_graph` check.
- **Building a separate HTML file for the graph:** The graph must be embedded inline in the same HTML report as a fragment (`<div>` + `<style>` + `<script>`), not a standalone `<html>` document.
- **Using innerHTML for panel content:** Phase 7 uses `createElement`/`textContent` for all dynamic content. Maintain this pattern to avoid XSS.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hierarchical DAG layout algorithm | Custom Sugiyama or layered layout from scratch | `nx.topological_generations` + `nx.multipartite_layout` | NetworkX already in runtime deps; correct column positions in 2 function calls |
| DAG cycle detection | Manual DFS | `nx.find_cycle` + `nx.is_directed_acyclic_graph` | NetworkX API; one-liner; handles all edge cases |
| Browser graph rendering | SVG/canvas drawing from scratch | vis-network standalone UMD (vendored inline) | vis-network provides node/edge rendering, zoom, pan, click/hover events, fixed-position mode, HTML-labeled nodes |
| Node click data lookup | Second HTTP request or re-parsing | DIFF_DATA already in `<script id="diff-data">` tag | Phase 7 pattern — reuse the same embedded JSON; zero extra data transfer |
| node-to-layer assignment | Manual BFS | `nx.topological_generations` generator | Returns frozensets of nodes per layer; plug directly into `multipartite_layout` |

**Key insight:** NetworkX handles all graph topology in Python at render time. The browser receives pre-computed `nodes[]` and `edges[]` arrays with pixel positions — zero layout computation in the browser.

---

## Common Pitfalls

### Pitfall 1: pyvis Bootstrap CDN Leak

**What goes wrong:** Output contains `https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/...` `<link>` and `<script>` tags even with `cdn_resources='in_line'`. The existing `test_render_self_contained()` test checks `assert "cdn." not in html` and will fail.

**Why it happens:** pyvis 0.3.2 Jinja2 template hardcodes Bootstrap CDN references unconditionally. PR #201 fixing this has been open since December 2022 and is not merged as of March 2026.

**How to avoid:** Use a custom Jinja2 template with vis-network inlined directly. If the spike chooses pyvis, post-process the output with a targeted regex to remove exactly the two Bootstrap tags — then verify no other CDN references remain.

**Warning signs:** `assert "cdn." not in html` failure; browser DevTools shows network requests on offline machine.

### Pitfall 2: Physics Simulation with 500+ Nodes

**What goes wrong:** Browser tab hangs for 10-30 seconds or freezes when vis-network starts physics stabilization.

**Why it happens:** vis-network default configuration enables physics simulation. With 500 nodes, stabilization converges slowly.

**How to avoid:** Set `physics: { enabled: false }` in vis-network options object. Pass explicit `x`/`y` coordinates in every node object. vis-network renders instantly when physics is off and positions are provided.

**Warning signs:** Browser spinning indicator; `stabilizationProgress` events firing; `network.stabilize()` blocking the main thread.

### Pitfall 3: Cyclic Workflows Breaking Topological Sort

**What goes wrong:** `nx.topological_generations(G)` raises `networkx.exception.NetworkXUnfeasible: Graph contains a cycle` on feedback-connected Alteryx workflows.

**Why it happens:** Alteryx supports iterative macros and feedback connections that create cycles in the DiGraph.

**How to avoid:** Check `nx.is_directed_acyclic_graph(G)` before calling `topological_generations`. If False, use `nx.find_cycle` in a loop to remove back-edges for layout computation, then re-add them to the `edges` array sent to vis-network.

**Warning signs:** `NetworkXUnfeasible` exception in tests or at runtime.

### Pitfall 4: multipartite_layout Axis Confusion

**What goes wrong:** Calling `nx.multipartite_layout(G, subset_key="layer")` with `align='horizontal'` places layers from top-to-bottom, not left-to-right.

**Why it happens:** The `align` parameter controls within-column node arrangement. `align='vertical'` (the default) produces layers as vertical columns ordered left-to-right — which IS the desired hierarchical layout.

**How to avoid:** Use `align='vertical'` (default). Validate that nodes in layer 0 have smaller x-values than nodes in layer 1.

**Warning signs:** All nodes appear in a single horizontal row; positions all share the same y-value.

### Pitfall 5: vis-network Node/Edge ID Type Mismatch

**What goes wrong:** Click event `params.nodes[0]` returns an integer; `TOOL_INDEX[nodeId]` returns `undefined` because keys were stored as strings.

**Why it happens:** JSON object keys in JavaScript are always strings; `TOOL_INDEX["701"]` is not the same as `TOOL_INDEX[701]`.

**How to avoid:** Store TOOL_INDEX with integer keys: `TOOL_INDEX[item.tool_id]` where `item.tool_id` is a number in the JSON. Or explicitly coerce: `TOOL_INDEX[String(nodeId)]` if storing as strings. Choose one convention and apply consistently.

**Warning signs:** Click on a node produces no panel; `TOOL_INDEX[nodeId]` is `undefined` despite the node being in DIFF_DATA.

### Pitfall 6: GraphRenderer Producing Standalone HTML (Double html/body Tags)

**What goes wrong:** If GraphRenderer generates a complete HTML document and HTMLRenderer embeds it, the output contains nested `<html>/<body>` tags — invalid HTML that breaks rendering.

**Why it happens:** Following pyvis's full-document output pattern naively.

**How to avoid:** GraphRenderer produces an HTML fragment: one `<div id="graph-container">`, one `<style>` block, and one `<script>` block. HTMLRenderer's Jinja2 template includes `{{ graph_html | safe }}` at the designated position. The fragment shares the same DIFF_DATA script tag already present in the page.

**Warning signs:** Browser inspector shows duplicate `<html>` tags; graph panel appears outside the main container.

---

## Code Examples

### vis-network Initialization (Physics Off, Fixed Positions)

```javascript
// Source: https://visjs.github.io/vis-network/docs/network/physics.html
var options = {
    physics: { enabled: false },
    nodes: {
        shape: "box",
        font: { size: 12 },
        borderWidth: 1
    },
    edges: {
        arrows: { to: { enabled: true } },
        smooth: { enabled: false }
    },
    interaction: {
        zoomView: true,
        dragView: true,
        hover: true
    }
};
var container = document.getElementById("graph-container");
var data = {
    nodes: new vis.DataSet(GRAPH_NODES),
    edges: new vis.DataSet(GRAPH_EDGES)
};
var network = new vis.Network(container, data, options);
network.fit();  // auto-scale viewport to fit all nodes
```

### Nodes Array Structure Passed from Python to Template

```python
# In graph_renderer.py — Python side
nodes_json = [
    {
        "id": tool_id,            # integer — must match edge from/to
        "label": tool_type,       # visible node text
        "color": color_hex,       # e.g. "#28a745"
        "status": status,         # "added"/"removed"/"modified"/"connection"/"unchanged"
        "title": tooltip_text,    # vis-network tooltip on hover
        "x": pos_x,               # pre-computed float pixel coordinate
        "y": pos_y,               # pre-computed float pixel coordinate
        "fixed": True,            # vis-network: prevent physics from moving this node
    }
    for tool_id, (pos_x, pos_y) in positions.items()
]
edges_json = [
    {
        "id": f"{src}-{dst}",
        "from": src,   # integer tool_id
        "to": dst,     # integer tool_id
    }
    for src, dst in G.edges()
]
```

### Slide-In Panel CSS Pattern

```css
/* In graph_renderer.py Jinja2 template inline style block */
#diff-panel {
    position: fixed;
    top: 0; right: -400px;
    width: 380px; height: 100%;
    background: #fff;
    border-left: 1px solid #dee2e6;
    box-shadow: -2px 0 8px rgba(0,0,0,0.1);
    overflow-y: auto;
    transition: right 0.2s ease;
    z-index: 1000;
    padding: 16px;
}
#diff-panel.open { right: 0; }
#graph-overlay {
    display: none;
    position: fixed; inset: 0;
    z-index: 999;
}
#diff-panel.open + #graph-overlay { display: block; }
```

### Escape Key + Outside Click Close Pattern

```javascript
// Safe event listeners — no innerHTML
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeSidePanel();
});
document.getElementById('graph-overlay').addEventListener('click', function() {
    closeSidePanel();
});
function closeSidePanel() {
    document.getElementById('diff-panel').classList.remove('open');
}
```

### importlib.resources for Vendored vis-network Bundle

```python
# Source: Python stdlib importlib.resources (Python 3.9+ API)
import importlib.resources as pkg_resources

# At class level (loaded once, not per-render)
_VIS_JS: str = (
    pkg_resources.files("alteryx_diff")
    .joinpath("static/vis-network.min.js")
    .read_text(encoding="utf-8")
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pyvis `show(filename)` writes HTML to disk | `generate_html()` returns string without file write | pyvis ~2022 | Enables embedding without temp files; CDN leak remains unfixed |
| pyvis full HTML document output | Custom Jinja2 fragment + vis-network UMD inline | Best practice 2024+ for air-gapped use | Complete CDN control; no post-processing |
| vis-network physics layout | Physics disabled + pre-computed Python positions | Always available in vis-network | Required for 500+ node performance |
| `nx.topological_sort` flat list | `nx.topological_generations` layer groups | NetworkX 2.6+ | Enables direct `multipartite_layout` usage for hierarchical display |
| pyvis `from_nx()` auto-conversion | Manual DiGraph construction with explicit attributes | Always available | Explicit color/status attributes; no reliance on pyvis attribute transfer behavior |

**Deprecated/outdated:**
- pyvis `show(filename)` method: writes to disk and opens browser — not usable for inline embedding.
- pyvis `local=True` parameter in `write_html()`: removed in favor of `cdn_resources` class parameter.
- vis-network physics stabilization for layout: correct for exploratory force-directed graphs; wrong for static diff reports with pre-computed positions.

---

## Open Questions

1. **Exact scope of pyvis CDN references beyond Bootstrap**
   - What we know: The confirmed CDN leak is the two Bootstrap tags (CSS + JS). vis-network JS/CSS are inlined when `cdn_resources='in_line'`.
   - What's unclear: Whether pyvis 0.3.2 emits any other CDN references (e.g., tom-select, other libraries) in `in_line` mode.
   - Recommendation: During spike 08-01, grep the actual pyvis-generated HTML for ALL occurrences of `https://` within `<link`/`<script src` tags. Count them. If exactly 2 (Bootstrap CSS + Bootstrap JS), the regex workaround is viable. If more, use custom template.

2. **vis-network standalone min.js file size in generated HTML**
   - What we know: The standalone directory is ~7MB total; exact min.js size not confirmed.
   - What's unclear: Actual size impact on HTML report file; whether this matters for the use case.
   - Recommendation: Measure during spike 08-01. Document the resulting HTML report size. If > 3MB, note it in the 08-01 output but proceed — self-contained air-gapped use requires it.

3. **Node color priority when a node is both modified and connection-changed**
   - What we know: A node can appear in both `result.modified_nodes` and `result.edge_diffs`.
   - What's unclear: Which color takes priority?
   - Recommendation: Use `modified > connection > unchanged`. Modified config is the more specific and actionable signal. Added/removed supersede all others.

4. **Canvas layout coordinate normalization**
   - What we know: Alteryx canvas coordinates are arbitrary floats (e.g., X=1200, Y=3500).
   - What's unclear: Whether vis-network handles large absolute coordinates natively without distortion.
   - Recommendation: Pass raw coordinates; call `network.fit()` after render. vis-network handles arbitrary coordinate ranges; fit() auto-scales the viewport.

---

## Sources

### Primary (HIGH confidence)
- NetworkX 3.6.1 official docs — topological_generations, multipartite_layout, find_cycle, DAG layout example: https://networkx.org/documentation/stable/auto_examples/graph/plot_dag_layout.html
- NetworkX 3.6.1 multipartite_layout reference: https://networkx.org/documentation/stable/reference/generated/networkx.drawing.layout.multipartite_layout.html
- vis-network official docs — physics.enabled option: https://visjs.github.io/vis-network/docs/network/physics.html
- pyvis official source — generate_html(), cdn_resources parameter: https://pyvis.readthedocs.io/en/latest/_modules/pyvis/network.html

### Secondary (MEDIUM confidence)
- GitHub WestHealth/pyvis issue #228 — CDN leak confirmed in 0.3.2 (reported May 2023, still open): https://github.com/WestHealth/pyvis/issues/228
- GitHub WestHealth/pyvis PR #201 — Bootstrap CDN fix not merged as of 2026: https://github.com/WestHealth/pyvis/pull/201
- pyvis tutorial — from_nx(), node attributes, toggle_physics(): https://pyvis.readthedocs.io/en/latest/tutorial.html
- unpkg vis-network 9.1.4 standalone directory — ~7MB total directory size: https://app.unpkg.com/vis-network@9.1.4/files/standalone

### Tertiary (LOW confidence)
- vis-network standalone min.js exact file size in KB — not verified from official source; must be measured during spike 08-01

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — networkx and jinja2 confirmed already in runtime deps; vis-network CDN issue confirmed from official GitHub issue; NetworkX topological layout API confirmed from official docs
- Architecture: HIGH — follows established renderer pattern from Phase 6/7; DIFF_DATA reuse pattern confirmed from Phase 7 code; vis-network fixed-position and physics-off API confirmed from official docs
- Pitfalls: HIGH (CDN leak verified from official sources; physics and cycle handling from API docs) / MEDIUM (axis confusion, type mismatch — from API docs and project code patterns)

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (pyvis CDN bug unlikely to be fixed; NetworkX API stable; vis-network 9.x API stable)
