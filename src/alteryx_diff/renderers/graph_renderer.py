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
    build_split_node_list,
    canvas_positions,
    hierarchical_positions,
    load_vis_js,
)

_GRAPH_FRAGMENT_TEMPLATE = """<section id="graph-section">
<h2>Workflow Graph</h2>

<div id="graph-view-toggle" style="display:flex;gap:8px;margin-bottom:10px;">
  <button id="btn-split" class="view-toggle-btn" onclick="switchView('split')">Split View</button>
  <button id="btn-overlay" class="view-toggle-btn" onclick="switchView('overlay')">Overlay View</button>
</div>

<div id="split-view" style="display:flex;height:600px;gap:0;border:1px solid #dee2e6;border-radius:4px;overflow:hidden;">
  <div style="flex:1;display:flex;flex-direction:column;min-width:0;">
    <div style="padding:6px 10px;font-weight:600;font-size:0.85em;background:#f1f5f9;border-bottom:1px solid #dee2e6;border-right:1px solid #dee2e6;">Before</div>
    <div id="split-view-left" style="flex:1;height:100%;background:#f8fafc;"></div>
  </div>
  <div style="width:280px;display:flex;flex-direction:column;border-left:1px solid #dee2e6;border-right:1px solid #dee2e6;">
    <div style="padding:6px 10px;font-weight:600;font-size:0.85em;background:#f1f5f9;border-bottom:1px solid #dee2e6;position:sticky;top:0;z-index:1;">Changes</div>
    <div id="split-change-rows" style="flex:1;overflow-y:auto;padding:4px 0;"></div>
  </div>
  <div style="flex:1;display:flex;flex-direction:column;min-width:0;">
    <div style="padding:6px 10px;font-weight:600;font-size:0.85em;background:#f1f5f9;border-bottom:1px solid #dee2e6;">After</div>
    <div id="split-view-right" style="flex:1;height:100%;background:#f8fafc;"></div>
  </div>
</div>

<div id="split-controls" style="display:flex;gap:8px;align-items:center;padding:8px 0;margin-top:4px;">
  <button id="fit-both-btn" class="ctrl-btn" onclick="if(networkLeft)networkLeft.fit();if(networkRight)networkRight.fit();">Fit Both</button>
  <button id="split-fullscreen-btn" class="ctrl-btn">Fullscreen</button>
  <span style="font-size:0.8em;color:#64748b;">
    <span style="display:inline-block;width:12px;height:12px;background:#6ee7b7;border:1px solid #059669;border-radius:50%;margin-right:3px;"></span>Added
    <span style="display:inline-block;width:12px;height:12px;background:#fca5a5;border:1px solid #dc2626;border-radius:50%;margin:0 3px;"></span>Removed
    <span style="display:inline-block;width:12px;height:12px;background:#fcd34d;border:1px solid #b45309;border-radius:50%;margin:0 3px;"></span>Modified
    <span style="display:inline-block;width:12px;height:12px;background:#e2e8f0;border:1px solid #94a3b8;border-radius:50%;margin:0 3px;"></span>Unchanged
  </span>
</div>

<div id="diff-panel" style="position:fixed;top:0;right:-420px;width:400px;height:100%;background:#fff;border-left:1px solid #dee2e6;box-shadow:-2px 0 8px rgba(0,0,0,0.1);overflow-y:auto;transition:right 0.2s ease;z-index:1000;padding:16px;box-sizing:border-box;border-radius:8px 0 0 8px;"></div>
<div id="graph-overlay" style="display:none;position:fixed;inset:0;z-index:999;"></div>

<div id="overlay-view" style="display:none;">
  <div id="graph-controls" style="margin-bottom:8px;display:flex;gap:8px;align-items:center;padding:8px 0;">
    <button id="fit-btn" class="ctrl-btn">Fit to Screen</button>
    <button id="fullscreen-btn" class="ctrl-btn">Fullscreen</button>
    <button id="toggle-changes" class="ctrl-btn">Show Only Changes</button>
    <span style="font-size:0.8em;color:#64748b;">
      <span data-legend="added" style="display:inline-block;width:12px;height:12px;background:#6ee7b7;border:1px solid #059669;border-radius:50%;margin-right:3px;"></span>Added
      <span data-legend="removed" style="display:inline-block;width:12px;height:12px;background:#fca5a5;border:1px solid #dc2626;border-radius:50%;margin:0 3px;"></span>Removed
      <span data-legend="modified" style="display:inline-block;width:12px;height:12px;background:#fcd34d;border:1px solid #b45309;border-radius:50%;margin:0 3px;"></span>Modified
      <span data-legend="connection" style="display:inline-block;width:12px;height:12px;background:#93c5fd;border:1px solid #1d4ed8;border-radius:50%;margin:0 3px;"></span>Connection change
      <span data-legend="unchanged" style="display:inline-block;width:12px;height:12px;background:#e2e8f0;border:1px solid #94a3b8;border-radius:50%;margin:0 3px;"></span>Unchanged
    </span>
  </div>
  <div id="graph-container" style="width:100%;height:620px;border:1px solid #dee2e6;border-radius:4px;background:#f8fafc;position:relative;"></div>
</div>

<style>
.view-toggle-btn { padding:6px 16px; border:1px solid #cbd5e1; border-radius:4px; cursor:pointer; font-size:0.88em; background:transparent; }
.view-toggle-btn.active { background:#3b82f6; color:#fff; border-color:#3b82f6; }
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
#graph-section:fullscreen { background: #f8fafc; padding: 12px; box-sizing: border-box; height: 100vh; display: flex; flex-direction: column; }
#graph-section:fullscreen #graph-view-toggle { flex-shrink: 0; }
#graph-section:fullscreen #split-view { flex: 1; height: auto !important; min-height: 0; }
#graph-section:fullscreen #split-controls { flex-shrink: 0; display: flex !important; }
#graph-section:fullscreen #graph-container { height: calc(100vh - 120px); }
.split-change-row { display:flex; align-items:center; gap:6px; padding:6px 10px; border-bottom:1px solid #f1f5f9; cursor:pointer; font-size:0.82em; }
.split-change-row:hover { background:#f8fafc; }
.split-change-badge { display:inline-block; width:10px; height:10px; border-radius:50%; flex-shrink:0; }
@media (max-width: 800px) {
  #split-view { flex-direction: column; height: auto; }
  #split-view > div { width: 100% !important; }
}
@media (prefers-color-scheme: dark) {
  #graph-section:fullscreen { background: #0f172a; }
  #graph-section:fullscreen #split-view { border-color: #334155 !important; }
  #graph-container { background: #0f172a !important; border-color: #334155 !important; }
  #diff-panel { background: #1e293b !important; border-color: #334155 !important; color: #e2e8f0 !important; }
  .panel-title { border-color: #334155 !important; color: #e2e8f0; }
  .panel-field-name { color: #94a3b8 !important; }
  .panel-before { background: #2d1518 !important; }
  .panel-after { background: #132318 !important; }
  .value-mono { color: #e2e8f0; }
  #split-view-left { background: #0f172a !important; }
  #split-view-right { background: #0f172a !important; }
  #split-change-rows { background: #1e293b; color: #e2e8f0; }
  .split-change-row { border-bottom-color: #334155; }
  .split-change-row:hover { background: #334155; }
}
[data-theme=dark] #graph-section:fullscreen { background: #0f172a; }
[data-theme=dark] #graph-container { background: #0f172a !important; border-color: #334155 !important; }
[data-theme=dark] #diff-panel { background: #1e293b !important; border-color: #334155 !important; color: #e2e8f0 !important; }
[data-theme=dark] .panel-title { border-color: #334155 !important; color: #e2e8f0; }
[data-theme=dark] .panel-field-name { color: #94a3b8 !important; }
[data-theme=dark] .panel-before { background: #2d1518 !important; }
[data-theme=dark] .panel-after { background: #132318 !important; }
[data-theme=dark] .value-mono { color: #e2e8f0; }
[data-theme=dark] #split-view-left { background: #0f172a !important; }
[data-theme=dark] #split-view-right { background: #0f172a !important; }
[data-theme=dark] #split-change-rows { background: #1e293b; color: #e2e8f0; }
[data-theme=dark] .split-change-row { border-bottom-color: #334155; }
[data-theme=dark] .split-change-row:hover { background: #334155; }
[data-theme=light] #graph-container { background: #f8fafc !important; border-color: #dee2e6 !important; }
[data-theme=light] #diff-panel { background: #fff !important; border-color: #dee2e6 !important; color: inherit !important; }
[data-theme=light] #split-view-left { background: #f8fafc !important; }
[data-theme=light] #split-view-right { background: #f8fafc !important; }
</style>
<script>
(function() {
{{ vis_js | safe }}

// ── Section A: Shared data ────────────────────────────────────────────────
var GRAPH_NODES = {{ nodes_json | safe }};
var GRAPH_EDGES = {{ edges_json | safe }};
var NODES_OLD = {{ nodes_old_json | safe }};
var NODES_NEW = {{ nodes_new_json | safe }};
var DIFF_DATA = JSON.parse(document.getElementById('diff-data').textContent);

// Build fast lookup: integer tool_id -> {category, data}
var TOOL_INDEX = {};
['added','removed','modified'].forEach(function(cat) {
  (DIFF_DATA[cat] || []).forEach(function(item) {
    TOOL_INDEX[item.tool_id] = {category: cat, data: item};
  });
});

// ── Section B: Overlay network (single merged graph) ──────────────────────
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

// ── Dark mode adaptive colors ─────────────────────────────────────────────
var LIGHT_COLORS = {
  added:      {background: '#6ee7b7', border: '#059669'},
  removed:    {background: '#fca5a5', border: '#dc2626'},
  modified:   {background: '#fcd34d', border: '#b45309'},
  connection: {background: '#93c5fd', border: '#1d4ed8'},
  unchanged:  {background: '#e2e8f0', border: '#94a3b8'}
};
var DARK_COLORS = {
  added:      {background: '#059669', border: '#065f46'},
  removed:    {background: '#dc2626', border: '#991b1b'},
  modified:   {background: '#d97706', border: '#92400e'},
  connection: {background: '#2563eb', border: '#1e40af'},
  unchanged:  {background: '#334155', border: '#475569'}
};

function isDark() {
  var t = document.documentElement.getAttribute('data-theme');
  if (t === 'dark') return true;
  if (t === 'light') return false;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function applyThemeColors() {
  var dark = isDark();
  var palette = dark ? DARK_COLORS : LIGHT_COLORS;
  var fontLight = '#ffffff';
  var fontDark  = '#1e293b';
  var fontMuted = '#cbd5e1';
  nodesDataset.update(GRAPH_NODES.map(function(n) {
    var c = palette[n.status];
    var fontColor = dark ? (n.status === 'unchanged' ? fontMuted : fontLight) : fontDark;
    return {id: n.id, color: {background: c.background, border: c.border, highlight: {background: c.background, border: c.border}, hover: {background: c.background, border: c.border}}, font: {color: fontColor}};
  }));
  // Sync legend dots
  document.querySelectorAll('[data-legend]').forEach(function(dot) {
    var c = palette[dot.getAttribute('data-legend')];
    if (c) { dot.style.background = c.background; dot.style.borderColor = c.border; }
  });
  applyThemeColorsToSplit();
}

applyThemeColors();
new MutationObserver(function(ms) {
  ms.forEach(function(m) { if (m.attributeName === 'data-theme') applyThemeColors(); });
}).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
    if (!document.documentElement.hasAttribute('data-theme')) applyThemeColors();
  });
}
// ─────────────────────────────────────────────────────────────────────────

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

// Fullscreen toggle (overlay view)
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

// Fullscreen toggle (split view)
document.getElementById('split-fullscreen-btn').addEventListener('click', function() {
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
    var splitBtn = document.getElementById('split-fullscreen-btn');
    if (splitBtn) splitBtn.textContent = 'Fullscreen';
    network.fit({animation: false});
    if (networkLeft) networkLeft.fit({animation: false});
    if (networkRight) networkRight.fit({animation: false});
  } else {
    setTimeout(function() {
      if (networkLeft) networkLeft.fit({animation: false});
      if (networkRight) networkRight.fit({animation: false});
    }, 100);
  }
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

// ── Section C: Split network + view switcher ──────────────────────────────
var networkLeft = null, networkRight = null;
var syncingViewport = false;

var SPLIT_OPTIONS = {
  physics: {enabled: false},
  nodes: {shape: 'box', borderWidth: 1, margin: {top: 6, right: 10, bottom: 6, left: 10}, font: {size: 12, face: 'system-ui,-apple-system,sans-serif'}, shapeProperties: {borderRadius: 6}},
  edges: {arrows: {to: {enabled: true, scaleFactor: 0.6}}, smooth: {enabled: true, type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.4}, color: {color: '#94a3b8'}, width: 1.2},
  interaction: {zoomView: true, dragView: true, hover: true}
};

function initSplitNetworks() {
  if (networkLeft) return;
  var leftContainer = document.getElementById('split-view-left');
  var rightContainer = document.getElementById('split-view-right');

  // Build ID sets for filtering edges
  var leftNodeIds = new Set(NODES_OLD.filter(function(n) { return n.status !== 'ghost_added'; }).map(function(n) { return n.id; }));
  var rightNodeIds = new Set(NODES_NEW.filter(function(n) { return n.status !== 'ghost_removed'; }).map(function(n) { return n.id; }));

  var leftEdges = GRAPH_EDGES.filter(function(e) { return leftNodeIds.has(e.from) && leftNodeIds.has(e.to); });
  var rightEdges = GRAPH_EDGES.filter(function(e) { return rightNodeIds.has(e.from) && rightNodeIds.has(e.to); });

  networkLeft = new vis.Network(leftContainer, {nodes: new vis.DataSet(NODES_OLD), edges: new vis.DataSet(leftEdges)}, SPLIT_OPTIONS);
  networkRight = new vis.Network(rightContainer, {nodes: new vis.DataSet(NODES_NEW), edges: new vis.DataSet(rightEdges)}, SPLIT_OPTIONS);

  networkLeft.fit();
  networkRight.fit();

  networkLeft.on('dragEnd', syncLeftToRight);
  networkLeft.on('zoom', syncLeftToRight);
  networkRight.on('dragEnd', syncRightToLeft);
  networkRight.on('zoom', syncRightToLeft);

  function onSplitNodeClick(params) {
    if (params.nodes.length === 0) { closeSidePanel(); return; }
    var nodeId = params.nodes[0];
    var entry = TOOL_INDEX[nodeId];
    if (!entry) return;
    openSidePanel(nodeId, entry);
  }
  networkLeft.on('click', onSplitNodeClick);
  networkRight.on('click', onSplitNodeClick);

  applyThemeColorsToSplit();
}

function syncLeftToRight() {
  if (syncingViewport) return;
  syncingViewport = true;
  networkRight.moveTo({position: networkLeft.getViewPosition(), scale: networkLeft.getScale(), animation: false});
  syncingViewport = false;
}

function syncRightToLeft() {
  if (syncingViewport) return;
  syncingViewport = true;
  networkLeft.moveTo({position: networkRight.getViewPosition(), scale: networkRight.getScale(), animation: false});
  syncingViewport = false;
}

function applyThemeColorsToSplit() {
  if (!networkLeft) return;
  var palette = isDark() ? DARK_COLORS : LIGHT_COLORS;
  var ghostStatuses = {'ghost_added': true, 'ghost_removed': true};
  [
    {net: networkLeft, nodes: NODES_OLD},
    {net: networkRight, nodes: NODES_NEW}
  ].forEach(function(pair) {
    var updates = [];
    pair.nodes.forEach(function(n) {
      if (ghostStatuses[n.status]) return;
      var c = palette[n.status];
      if (c) {
        updates.push({id: n.id, color: {background: c.background, border: c.border, highlight: {background: c.background, border: c.border}}});
      }
    });
    if (updates.length > 0) {
      pair.net.body.data.nodes.update(updates);
    }
  });
}

function focusNode(toolId) {
  var pos = null;
  try { pos = networkLeft.getPosition(toolId); } catch(e) { pos = null; }
  if (!pos) {
    try { pos = networkRight.getPosition(toolId); } catch(e) { pos = null; }
  }
  if (pos) {
    var moveOpts = {position: pos, scale: 1.2, animation: {duration: 300, easingFunction: 'easeInOutQuad'}};
    networkLeft.moveTo(moveOpts);
    networkRight.moveTo(moveOpts);
  }
}

function buildCenterPanel() {
  var container = document.getElementById('split-change-rows');
  var BADGE_COLORS = {added: '#6ee7b7', removed: '#fca5a5', modified: '#fcd34d'};
  var entries = [];
  ['added', 'removed', 'modified'].forEach(function(cat) {
    (DIFF_DATA[cat] || []).forEach(function(item) {
      entries.push({cat: cat, item: item});
    });
  });
  if (entries.length === 0) {
    var empty = document.createElement('div');
    empty.style.padding = '12px 10px';
    empty.style.color = '#64748b';
    empty.style.fontSize = '0.85em';
    empty.textContent = 'No changes.';
    container.appendChild(empty);
    return;
  }
  entries.forEach(function(e) {
    var item = e.item;
    var cat = e.cat;
    var row = document.createElement('div');
    row.className = 'split-change-row';
    row.setAttribute('data-tool-id', item.tool_id);

    var badge = document.createElement('span');
    badge.className = 'split-change-badge';
    badge.style.background = BADGE_COLORS[cat] || '#e2e8f0';

    var shortType = (item.tool_type || '').split('.').pop();
    var label = document.createElement('span');
    label.style.flex = '1';
    label.textContent = shortType + ' (' + item.tool_id + ')';

    var catTag = document.createElement('span');
    catTag.style.fontSize = '0.78em';
    catTag.style.color = '#64748b';
    catTag.textContent = cat;

    row.appendChild(badge);
    row.appendChild(label);
    row.appendChild(catTag);
    row.addEventListener('click', function() { focusNode(item.tool_id); });
    container.appendChild(row);
  });
}

buildCenterPanel();

// View switcher
var currentView = localStorage.getItem('alteryx-diff-view') || 'split';

function switchView(view) {
  currentView = view;
  localStorage.setItem('alteryx-diff-view', view);
  var splitView = document.getElementById('split-view');
  var splitControls = document.getElementById('split-controls');
  var overlayView = document.getElementById('overlay-view');
  var btnSplit = document.getElementById('btn-split');
  var btnOverlay = document.getElementById('btn-overlay');
  if (view === 'split') {
    splitView.style.display = 'flex';
    splitControls.style.display = 'flex';
    overlayView.style.display = 'none';
    btnSplit.classList.add('active');
    btnOverlay.classList.remove('active');
    requestAnimationFrame(function() {
      initSplitNetworks();
      requestAnimationFrame(function() {
        if (networkLeft) { networkLeft.redraw(); networkLeft.fit({animation: false}); }
        if (networkRight) { networkRight.redraw(); networkRight.fit({animation: false}); }
      });
    });
  } else {
    splitView.style.display = 'none';
    splitControls.style.display = 'none';
    overlayView.style.display = 'block';
    btnOverlay.classList.add('active');
    btnSplit.classList.remove('active');
    setTimeout(function() {
      if (network) network.fit({animation: false});
    }, 50);
  }
}

switchView(currentView);

})();
</script>
</section>
"""


class GraphRenderer:
    """Render a DiffResult as an interactive vis-network graph HTML fragment.

    Produces: <section id="graph-section"> containing:
        - Split View (default): two vis-network canvases side-by-side with
          synchronized pan/zoom and a center change panel
        - Overlay View: single merged graph with slide-in diff panel (existing behavior)
        - inline <style> for all UI elements
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
                "fixed": False,
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

        # Build split view node lists
        old_vis_nodes, new_vis_nodes = build_split_node_list(
            result, nodes_old, nodes_new
        )

        # Load vendored vis-network JS
        vis_js = load_vis_js()

        # Render fragment via Jinja2 — nodes/edges passed as pre-serialized JSON strings
        env = Environment(autoescape=True)  # noqa: S701
        env.policies["json.dumps_kwargs"] = {"ensure_ascii": False}
        template = env.from_string(_GRAPH_FRAGMENT_TEMPLATE)
        return template.render(
            nodes_json=json.dumps(nodes_json),
            edges_json=json.dumps(edges_json),
            nodes_old_json=json.dumps(old_vis_nodes),
            nodes_new_json=json.dumps(new_vis_nodes),
            vis_js=vis_js,
        )
