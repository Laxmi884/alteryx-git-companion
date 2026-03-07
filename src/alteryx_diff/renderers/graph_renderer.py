# ruff: noqa: E501
"""Interactive vis-network graph HTML fragment renderer.

GraphRenderer.render() produces a self-contained HTML fragment (not a full
document) that is embedded into the full report by HTMLRenderer via the
``{{ graph_html | safe }}`` template placeholder.

vis-network standalone UMD is inlined — zero CDN references.
Physics is disabled; positions are pre-computed in Python.
"""

from __future__ import annotations

import json
from typing import Any

from jinja2 import Environment

from alteryx_diff.models import DiffResult
from alteryx_diff.models.workflow import AlteryxConnection, AlteryxNode
from alteryx_diff.renderers._graph_builder import (
    build_digraph,
    canvas_positions,
    hierarchical_positions,
    load_vis_js,
)

_GRAPH_FRAGMENT_TEMPLATE = """<section id="graph-section">
<h2>Workflow Graph</h2>
<div id="graph-controls" style="margin-bottom:8px;display:flex;gap:8px;align-items:center;padding:8px 0;">
  <button id="fit-btn" class="ctrl-btn">Fit to Screen</button>
  <button id="toggle-changes" class="ctrl-btn">Show Only Changes</button>
  <span style="font-size:0.8em;color:#64748b;">
    <span style="display:inline-block;width:12px;height:12px;background:#059669;border-radius:50%;margin-right:3px;"></span>Added
    <span style="display:inline-block;width:12px;height:12px;background:#dc2626;border-radius:50%;margin:0 3px;"></span>Removed
    <span style="display:inline-block;width:12px;height:12px;background:#d97706;border-radius:50%;margin:0 3px;"></span>Modified
    <span style="display:inline-block;width:12px;height:12px;background:#2563eb;border-radius:50%;margin:0 3px;"></span>Connection change
    <span style="display:inline-block;width:12px;height:12px;background:#cbd5e1;border-radius:50%;margin:0 3px;"></span>Unchanged
  </span>
</div>
<div id="graph-container" style="width:100%;height:620px;border:1px solid #dee2e6;border-radius:4px;background:#f8fafc;position:relative;"></div>
<div id="diff-panel" style="position:fixed;top:0;right:-420px;width:400px;height:100%;background:#fff;border-left:1px solid #dee2e6;box-shadow:-2px 0 8px rgba(0,0,0,0.1);overflow-y:auto;transition:right 0.2s ease;z-index:1000;padding:16px;box-sizing:border-box;border-radius:8px 0 0 8px;"></div>
<div id="graph-overlay" style="display:none;position:fixed;inset:0;z-index:999;"></div>
<style>
#diff-panel.open { right: 0 !important; }
#diff-panel.open ~ #graph-overlay { display: block !important; }
.panel-title { font-size:1em; font-weight:600; margin:0 0 12px; border-bottom:2px solid #eee; padding-bottom:8px; }
.panel-field-row { margin:8px 0; }
.panel-field-name { font-weight:600; font-size:0.82em; color:#555; margin-bottom:3px; }
.panel-before { background:#fff5f5; border-left:3px solid #dc3545; padding:4px 8px; margin:2px 0; }
.panel-after  { background:#f5fff5; border-left:3px solid #28a745; padding:4px 8px; margin:2px 0; }
.panel-before-label { font-weight:600; color:#dc3545; }
.panel-after-label  { font-weight:600; color:#28a745; }
.value-mono { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; white-space:pre-wrap; word-break:break-all; font-size:0.88em; }
</style>
<script>
(function() {
{{ vis_js | safe }}

var GRAPH_NODES = {{ nodes_json | safe }};
var GRAPH_EDGES = {{ edges_json | safe }};
var DIFF_DATA = JSON.parse(document.getElementById('diff-data').textContent);

// Build fast lookup: integer tool_id -> {category, data}
var TOOL_INDEX = {};
['added','removed','modified'].forEach(function(cat) {
  (DIFF_DATA[cat] || []).forEach(function(item) {
    TOOL_INDEX[item.tool_id] = {category: cat, data: item};
  });
});

var nodesDataset = new vis.DataSet(GRAPH_NODES);
var edgesDataset = new vis.DataSet(GRAPH_EDGES);

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

var container = document.getElementById('graph-container');
var network = new vis.Network(container, {nodes: nodesDataset, edges: edgesDataset}, options);
network.fit();

// Show-only-changes toggle
var showOnlyChanges = false;
document.getElementById('toggle-changes').addEventListener('click', function() {
  showOnlyChanges = !showOnlyChanges;
  this.textContent = showOnlyChanges ? 'Show All Nodes' : 'Show Only Changes';
  var hiddenIds = new Set(
    showOnlyChanges
      ? GRAPH_NODES.filter(function(n) { return n.status === 'unchanged'; }).map(function(n) { return n.id; })
      : []
  );
  nodesDataset.update(GRAPH_NODES.map(function(n) {
    return {id: n.id, hidden: hiddenIds.has(n.id)};
  }));
  edgesDataset.update(GRAPH_EDGES.map(function(e) {
    return {id: e.id, hidden: hiddenIds.has(e.from) || hiddenIds.has(e.to)};
  }));
});

// Fit-to-screen
document.getElementById('fit-btn').addEventListener('click', function() {
  network.fit({animation: true});
});

// Click handler
network.on('click', function(params) {
  if (params.nodes.length === 0) {
    closeSidePanel();
    return;
  }
  var nodeId = params.nodes[0];  // integer
  var entry = TOOL_INDEX[nodeId];
  if (!entry) return;  // unchanged node — no panel
  openSidePanel(nodeId, entry);
});

// Hover tooltip — vis-network handles via node.title attribute automatically

// Panel open/close
function openSidePanel(nodeId, entry) {
  var panel = document.getElementById('diff-panel');
  while (panel.firstChild) { panel.removeChild(panel.firstChild); }
  buildPanelContent(panel, entry);
  panel.classList.add('open');
}

function closeSidePanel() {
  document.getElementById('diff-panel').classList.remove('open');
}

function buildPanelContent(panel, entry) {
  var titleEl = document.createElement('div');
  titleEl.className = 'panel-title';
  titleEl.textContent = entry.data.tool_type + ' (ID: ' + entry.data.tool_id + ') \u2014 ' + entry.category;
  panel.appendChild(titleEl);
  if (entry.category === 'modified') {
    entry.data.field_diffs.forEach(function(fd) {
      var row = document.createElement('div');
      row.className = 'panel-field-row';
      var nameEl = document.createElement('div');
      nameEl.className = 'panel-field-name';
      nameEl.textContent = fd.field;
      var beforeRow = document.createElement('div');
      beforeRow.className = 'panel-before';
      var beforeLabel = document.createElement('span');
      beforeLabel.className = 'panel-before-label';
      beforeLabel.textContent = 'Before: ';
      var beforeVal = document.createElement('span');
      beforeVal.className = 'value-mono';
      beforeVal.textContent = formatVal(fd.before);
      beforeRow.appendChild(beforeLabel);
      beforeRow.appendChild(beforeVal);
      var afterRow = document.createElement('div');
      afterRow.className = 'panel-after';
      var afterLabel = document.createElement('span');
      afterLabel.className = 'panel-after-label';
      afterLabel.textContent = 'After: ';
      var afterVal = document.createElement('span');
      afterVal.className = 'value-mono';
      afterVal.textContent = formatVal(fd.after);
      afterRow.appendChild(afterLabel);
      afterRow.appendChild(afterVal);
      row.appendChild(nameEl);
      row.appendChild(beforeRow);
      row.appendChild(afterRow);
      panel.appendChild(row);
    });
  } else {
    var config = entry.data.config || {};
    Object.keys(config).forEach(function(k) {
      var row = document.createElement('div');
      row.className = 'panel-field-row';
      var nameEl = document.createElement('div');
      nameEl.className = 'panel-field-name';
      nameEl.textContent = k;
      var valEl = document.createElement('div');
      valEl.className = 'value-mono';
      valEl.textContent = formatVal(config[k]);
      row.appendChild(nameEl);
      row.appendChild(valEl);
      panel.appendChild(row);
    });
  }
}

function formatVal(v) {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'object') return JSON.stringify(v, null, 2);
  return String(v);
}

// Escape key and overlay click
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeSidePanel();
});
document.getElementById('graph-overlay').addEventListener('click', function() {
  closeSidePanel();
});

})();
</script>
</section>
"""


class GraphRenderer:
    """Render a DiffResult as an interactive vis-network graph HTML fragment.

    Produces: <section id="graph-section"> containing:
        - <div id="graph-container"> for vis-network canvas
        - inline <style> for the slide-in diff panel
        - inline <script> with vis-network UMD embedded + graph logic

    Fragment is embedded by HTMLRenderer via ``{{ graph_html | safe }}``.
    vis-network standalone UMD is inlined — zero CDN references.
    Physics is disabled; positions are pre-computed in Python.
    """

    def render(
        self,
        result: DiffResult,
        all_connections: tuple[AlteryxConnection, ...],
        nodes_old: tuple[AlteryxNode, ...],
        nodes_new: tuple[AlteryxNode, ...],
        *,
        canvas_layout: bool = False,
    ) -> str:
        """Render a DiffResult as a self-contained HTML fragment with vis-network.

        Args:
            result: The diff output with added/removed/modified nodes and edge diffs.
            all_connections: Combined connections from both old and new workflows.
            nodes_old: Nodes from the baseline (old) workflow.
            nodes_new: Nodes from the changed (new) workflow.
            canvas_layout: If True, use raw Alteryx X/Y canvas coordinates instead
                of the hierarchical topological layout.

        Returns:
            An HTML fragment string (no <html>/<head>/<body> tags) containing
            a <section id="graph-section"> with the interactive vis-network graph.
        """
        # Deduplicate nodes: old first, new overrides (adds/modified take new position)
        nodes_map: dict[int, AlteryxNode] = {}
        for n in nodes_old:
            nodes_map[int(n.tool_id)] = n
        for n in nodes_new:
            nodes_map[int(n.tool_id)] = n
        all_nodes_tuple = tuple(nodes_map.values())

        # Build directed graph with diff status attributes
        G = build_digraph(result, all_connections, all_nodes_tuple)

        # Compute layout positions
        if canvas_layout:
            positions = canvas_positions(nodes_old, nodes_new)
        else:
            positions = hierarchical_positions(G)

        # Build field counts for modified node tooltips
        field_counts: dict[int, int] = {
            int(nd.tool_id): len(nd.field_diffs) for nd in result.modified_nodes
        }

        # Build nodes list with pre-computed positions
        nodes_json: list[dict[str, Any]] = []
        for node_id, (px, py) in positions.items():
            attrs = G.nodes[node_id]
            label: str = attrs["label"]
            status: str = attrs["status"]
            title: str = attrs["title"]
            entry: dict[str, Any] = {
                "id": node_id,
                "label": label,
                "color": attrs["color"],
                "status": status,
                "title": title,
                "x": px,
                "y": py,
                "fixed": True,
            }
            nodes_json.append(entry)

        # Enrich tooltip for modified nodes with field change count
        for entry in nodes_json:
            if entry["status"] == "modified":
                count = field_counts.get(int(entry["id"]), 0)
                entry["title"] = (
                    f"{entry['label']} | modified | {count} field(s) changed"
                )

        # Build edges list
        edges_json: list[dict[str, Any]] = [
            {"id": f"{src}-{dst}", "from": src, "to": dst} for src, dst in G.edges()
        ]

        # Load vendored vis-network JS
        vis_js = load_vis_js()

        # Render fragment via Jinja2 — nodes/edges passed as pre-serialized JSON strings
        env = Environment(autoescape=True)  # noqa: S701
        env.policies["json.dumps_kwargs"] = {"ensure_ascii": False}
        template = env.from_string(_GRAPH_FRAGMENT_TEMPLATE)
        return template.render(
            nodes_json=json.dumps(nodes_json),
            edges_json=json.dumps(edges_json),
            vis_js=vis_js,
        )
