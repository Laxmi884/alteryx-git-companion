# ruff: noqa: E501
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from jinja2 import Environment

from alteryx_diff.models import DiffResult, NodeDiff
from alteryx_diff.models.diff import EdgeDiff
from alteryx_diff.models.workflow import AlteryxNode

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Alteryx Workflow Diff Report</title>
<style>
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
body { margin: 0; padding: 16px; background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.container { max-width: 960px; margin: 0 auto; }
.badge { display: inline-block; padding: 6px 14px; border-radius: 4px; font-weight: 600; font-size: 1.1em; text-decoration: none; cursor: pointer; margin: 4px; }
.badge-added { background: var(--badge-added-bg); color: var(--badge-added-text); border: 1px solid var(--badge-added-border); }
.badge-removed { background: var(--badge-removed-bg); color: var(--badge-removed-text); border: 1px solid var(--badge-removed-border); }
.badge-modified { background: var(--badge-modified-bg); color: var(--badge-modified-text); border: 1px solid var(--badge-modified-border); }
.badge-connections { background: var(--badge-conn-bg); color: var(--badge-conn-text); border: 1px solid var(--badge-conn-border); }
h2 { font-size: 1.1em; font-weight: 600; margin: 24px 0 8px; border-bottom: 2px solid var(--section-border); padding-bottom: 4px; display: flex; align-items: center; gap: 8px; }
.tool-row { display: flex; align-items: center; padding: 8px 12px; border: 1px solid var(--border); border-radius: 4px; margin: 4px 0; cursor: pointer; background: var(--row-bg); user-select: none; }
.tool-row:hover { background: var(--row-hover); }
.chevron { display: inline-block; transition: transform 0.15s; margin-right: 8px; font-style: normal; }
.tool-row.expanded .chevron { transform: rotate(90deg); }
.tool-detail { padding: 8px 12px 8px 36px; border: 1px solid var(--border); border-top: none; border-radius: 0 0 4px 4px; background: var(--detail-bg); }
.field-row { margin: 6px 0; }
.field-name { font-weight: 600; font-size: 0.85em; color: var(--field-label); margin-bottom: 2px; }
.before-row { background: var(--before-bg); border-left: 3px solid #dc3545; padding: 4px 8px; margin: 2px 0; }
.after-row { background: var(--after-bg); border-left: 3px solid #28a745; padding: 4px 8px; margin: 2px 0; }
.before-label { font-weight: 600; color: #dc3545; }
.after-label { font-weight: 600; color: #28a745; }
.value-block { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; white-space: pre-wrap; word-break: break-all; font-size: 0.9em; }
.ctrl-btn { font-size: 0.8em; padding: 4px 10px; cursor: pointer; border: 1px solid var(--btn-border); border-radius: 6px; background: var(--btn-bg); color: var(--btn-text); font-weight: 500; transition: background 0.15s, border-color 0.15s; }
.ctrl-btn:hover { background: var(--btn-hover-bg); border-color: var(--btn-hover-border); }
.empty { color: var(--empty-color); font-style: italic; }
header { border-bottom: 1px solid var(--border); margin-bottom: 20px; padding-bottom: 12px; }
header h1 { font-size: 1.5em; margin: 0 0 4px; }
header p { margin: 2px 0; color: var(--text-muted); font-size: 0.9em; }
@media print { .ctrl-btn { display: none; } .tool-detail { display: block !important; } }
</style>
</head>
<body>
<div class="container">
<header>
  <h1>Alteryx Workflow Diff Report</h1>
  <p>Generated: {{ timestamp }}</p>
  <p>{{ file_a }} vs {{ file_b }}</p>
</header>
<section id="summary">
  <a href="#added" onclick="expandSection('added'); return true;" class="badge badge-added">Added: {{ summary.added }}</a>
  <a href="#removed" onclick="expandSection('removed'); return true;" class="badge badge-removed">Removed: {{ summary.removed }}</a>
  <a href="#modified" onclick="expandSection('modified'); return true;" class="badge badge-modified">Modified: {{ summary.modified }}</a>
  <a href="#connections" onclick="expandSection('connections'); return true;" class="badge badge-connections">Connections: {{ summary.connections }}</a>
</section>
<section>
  <h2 id="added">
    Added Tools
    <button class="ctrl-btn" onclick="expandAll('added')">Expand All</button>
    <button class="ctrl-btn" onclick="collapseAll('added')">Collapse All</button>
  </h2>
  {% for tool in diff_data.added %}
  <div class="tool-row" id="row-added-{{ tool.tool_id }}"
       onclick="toggleTool({{ tool.tool_id }}, 'added')">
    <span class="chevron">&#9654;</span>
    {{ tool.tool_type }} (ID: {{ tool.tool_id }})
  </div>
  <div class="tool-detail" id="detail-added-{{ tool.tool_id }}" hidden></div>
  {% else %}
  <p class="empty">No added tools.</p>
  {% endfor %}
</section>
<section>
  <h2 id="removed">
    Removed Tools
    <button class="ctrl-btn" onclick="expandAll('removed')">Expand All</button>
    <button class="ctrl-btn" onclick="collapseAll('removed')">Collapse All</button>
  </h2>
  {% for tool in diff_data.removed %}
  <div class="tool-row" id="row-removed-{{ tool.tool_id }}"
       onclick="toggleTool({{ tool.tool_id }}, 'removed')">
    <span class="chevron">&#9654;</span>
    {{ tool.tool_type }} (ID: {{ tool.tool_id }})
  </div>
  <div class="tool-detail" id="detail-removed-{{ tool.tool_id }}" hidden></div>
  {% else %}
  <p class="empty">No removed tools.</p>
  {% endfor %}
</section>
<section>
  <h2 id="modified">
    Modified Tools
    <button class="ctrl-btn" onclick="expandAll('modified')">Expand All</button>
    <button class="ctrl-btn" onclick="collapseAll('modified')">Collapse All</button>
  </h2>
  {% for tool in diff_data.modified %}
  <div class="tool-row" id="row-modified-{{ tool.tool_id }}"
       onclick="toggleTool({{ tool.tool_id }}, 'modified')">
    <span class="chevron">&#9654;</span>
    {{ tool.tool_type }} (ID: {{ tool.tool_id }})
  </div>
  <div class="tool-detail" id="detail-modified-{{ tool.tool_id }}" hidden></div>
  {% else %}
  <p class="empty">No modified tools.</p>
  {% endfor %}
</section>
<section>
  <h2 id="connections">
    Connection Changes
    <button class="ctrl-btn" onclick="expandAll('connections')">Expand All</button>
    <button class="ctrl-btn" onclick="collapseAll('connections')">Collapse All</button>
  </h2>
  {% for e in diff_data.connections %}
  <div class="tool-row" id="row-connections-{{ loop.index }}"
       onclick="toggleTool({{ loop.index }}, 'connections')">
    <span class="chevron">&#9654;</span>
    {{ e.src_tool }}:{{ e.src_anchor }} to {{ e.dst_tool }}:{{ e.dst_anchor }}
  </div>
  <div class="tool-detail" id="detail-connections-{{ loop.index }}" hidden></div>
  {% else %}
  <p class="empty">No connection changes.</p>
  {% endfor %}
</section>
<script type="application/json" id="diff-data">{{ diff_data | tojson }}</script>
{{ graph_html | safe }}
{% if metadata %}
<details id="governance" style="margin-top:32px;border-top:1px solid var(--border);padding-top:12px;">
  <summary style="cursor:pointer;color:var(--text-muted);font-size:0.85em;padding:4px 0;user-select:none;">
    Governance Metadata (ALCOA+)
  </summary>
  <div style="font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:0.82em;padding:8px 0;color:var(--field-label);line-height:1.8;">
    <div><strong>File A:</strong> {{ metadata.file_a }}</div>
    <div><strong>SHA-256 A:</strong> {{ metadata.sha256_a }}</div>
    <div><strong>File B:</strong> {{ metadata.file_b }}</div>
    <div><strong>SHA-256 B:</strong> {{ metadata.sha256_b }}</div>
    <div><strong>Generated:</strong> {{ metadata.generated_at }}</div>
  </div>
</details>
{% endif %}
<script>
var DIFF_DATA = JSON.parse(document.getElementById('diff-data').textContent);

function expandSection(sectionId) {
    var section = document.getElementById(sectionId);
    if (!section) return;
    section.scrollIntoView({behavior: 'smooth'});
    var rows = section.querySelectorAll('.tool-row');
    for (var i = 0; i < rows.length; i++) {
        if (!rows[i].classList.contains('expanded')) rows[i].click();
    }
}

function toggleTool(toolId, section) {
    var detailEl = document.getElementById('detail-' + section + '-' + toolId);
    var rowEl = document.getElementById('row-' + section + '-' + toolId);
    if (!detailEl || !rowEl) return;
    var isExpanded = rowEl.classList.contains('expanded');
    if (isExpanded) {
        detailEl.hidden = true;
        rowEl.classList.remove('expanded');
    } else {
        if (!detailEl.dataset.built) {
            buildDetail(toolId, section, detailEl);
            detailEl.dataset.built = 'true';
        }
        detailEl.hidden = false;
        rowEl.classList.add('expanded');
    }
}

function buildDetail(toolId, section, container) {
    var sectionData = DIFF_DATA[section];
    var tool = null;
    for (var i = 0; i < sectionData.length; i++) {
        if (sectionData[i].tool_id === toolId) { tool = sectionData[i]; break; }
    }
    if (!tool) return;
    var frag = document.createDocumentFragment();
    if (section === 'modified') {
        tool.field_diffs.forEach(function(fd) {
            var row = document.createElement('div');
            row.className = 'field-row';
            var nameEl = document.createElement('div');
            nameEl.className = 'field-name';
            nameEl.textContent = fd.field;
            var beforeRow = document.createElement('div');
            beforeRow.className = 'before-row';
            var beforeLabel = document.createElement('span');
            beforeLabel.className = 'before-label';
            beforeLabel.textContent = 'Before: ';
            var beforeVal = document.createElement('span');
            beforeVal.className = 'value-block';
            beforeVal.textContent = formatVal(fd.before);
            beforeRow.appendChild(beforeLabel);
            beforeRow.appendChild(beforeVal);
            var afterRow = document.createElement('div');
            afterRow.className = 'after-row';
            var afterLabel = document.createElement('span');
            afterLabel.className = 'after-label';
            afterLabel.textContent = 'After: ';
            var afterVal = document.createElement('span');
            afterVal.className = 'value-block';
            afterVal.textContent = formatVal(fd.after);
            afterRow.appendChild(afterLabel);
            afterRow.appendChild(afterVal);
            row.appendChild(nameEl);
            row.appendChild(beforeRow);
            row.appendChild(afterRow);
            frag.appendChild(row);
        });
    } else if (section === 'added' || section === 'removed') {
        var config = tool.config;
        Object.keys(config).forEach(function(k) {
            var row = document.createElement('div');
            row.className = 'field-row';
            var nameEl = document.createElement('div');
            nameEl.className = 'field-name';
            nameEl.textContent = k;
            var valEl = document.createElement('div');
            valEl.className = 'value-block';
            valEl.textContent = formatVal(config[k]);
            row.appendChild(nameEl);
            row.appendChild(valEl);
            frag.appendChild(row);
        });
    } else if (section === 'connections') {
        var row = document.createElement('div');
        row.className = 'field-row';
        var valEl = document.createElement('span');
        valEl.className = 'value-block';
        valEl.textContent = tool.src_tool + ':' + tool.src_anchor + ' -> ' + tool.dst_tool + ':' + tool.dst_anchor + ' (' + tool.change_type + ')';
        row.appendChild(valEl);
        frag.appendChild(row);
    }
    container.appendChild(frag);
}

function formatVal(v) {
    if (v === null || v === undefined) return 'null';
    if (typeof v === 'object') return JSON.stringify(v, null, 2);
    return String(v);
}

function expandAll(sectionId) {
    var section = document.getElementById(sectionId);
    if (!section) return;
    var rows = section.querySelectorAll('.tool-row');
    for (var i = 0; i < rows.length; i++) {
        if (!rows[i].classList.contains('expanded')) rows[i].click();
    }
}

function collapseAll(sectionId) {
    var section = document.getElementById(sectionId);
    if (!section) return;
    var rows = section.querySelectorAll('.tool-row.expanded');
    for (var i = 0; i < rows.length; i++) { rows[i].click(); }
}
</script>
</div>
</body>
</html>
"""


class HTMLRenderer:
    """Render a DiffResult to a self-contained HTML string.

    All CSS and JavaScript are embedded inline — no CDN references.
    Tool detail is lazy-loaded from DIFF_DATA JSON in script tag.
    Follows the renderer pattern established by JSONRenderer.
    """

    def render(
        self,
        result: DiffResult,
        file_a: str = "workflow_a.yxmd",
        file_b: str = "workflow_b.yxmd",
        *,
        graph_html: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Render result to a self-contained HTML string.

        Args:
            result: The diff output to render.
            file_a: Display name for the baseline workflow file.
            file_b: Display name for the changed workflow file.
            graph_html: Optional HTML fragment from GraphRenderer to embed in the
                report. When non-empty, the interactive vis-network graph section
                is inserted before the closing container div. Defaults to "".
            metadata: Optional governance metadata dict for ALCOA+ compliance footer.
                When provided, a collapsible ``<details id="governance">`` section is
                appended with file paths, SHA-256 digests, and generation timestamp.
                When ``None`` (default), the footer is omitted — zero regression risk
                for existing callers.

        Returns:
            A self-contained HTML string with all CSS and JavaScript inline.
        """
        # autoescape=True required — avoids ruff B701
        env = Environment(autoescape=True)
        env.policies["json.dumps_kwargs"] = {"ensure_ascii": False, "sort_keys": True}
        template = env.from_string(_TEMPLATE)
        return template.render(
            timestamp=datetime.now(UTC).isoformat(),
            file_a=file_a,
            file_b=file_b,
            summary={
                "added": len(result.added_nodes),
                "removed": len(result.removed_nodes),
                "modified": len(result.modified_nodes),
                "connections": len(result.edge_diffs),
            },
            diff_data=self._build_diff_data(result),
            graph_html=graph_html,
            metadata=metadata,
        )

    def _build_diff_data(self, result: DiffResult) -> dict[str, Any]:
        return {
            "added": [self._node_to_dict(n) for n in result.added_nodes],
            "removed": [self._node_to_dict(n) for n in result.removed_nodes],
            "modified": [self._node_diff_to_dict(nd) for nd in result.modified_nodes],
            "connections": [self._edge_to_dict(e) for e in result.edge_diffs],
        }

    def _node_to_dict(self, node: AlteryxNode) -> dict[str, Any]:
        return {
            "tool_id": int(node.tool_id),
            "tool_type": node.tool_type,
            "config": dict(node.config),
        }

    def _node_diff_to_dict(self, nd: NodeDiff) -> dict[str, Any]:
        return {
            "tool_id": int(nd.tool_id),
            "tool_type": nd.old_node.tool_type,
            "field_diffs": [
                {"field": k, "before": v[0], "after": v[1]}
                for k, v in nd.field_diffs.items()
            ],
        }

    def _edge_to_dict(self, e: EdgeDiff) -> dict[str, Any]:
        return {
            "tool_id": int(e.src_tool),
            "src_tool": int(e.src_tool),
            "src_anchor": str(e.src_anchor),
            "dst_tool": int(e.dst_tool),
            "dst_anchor": str(e.dst_anchor),
            "change_type": e.change_type,
        }
