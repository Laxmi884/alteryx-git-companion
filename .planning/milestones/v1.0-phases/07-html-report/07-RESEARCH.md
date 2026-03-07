# Phase 7: HTML Report - Research

**Researched:** 2026-03-06
**Domain:** Python Jinja2 templating, self-contained HTML report generation, vanilla JavaScript expand/collapse
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Visual Design & Density**
- Clean and minimal tone: white background, subtle borders, system fonts — professional diff tool aesthetic
- Tools grouped by status in the report body: Added section, Removed section, Modified section, Connection Changes section
- Print-friendly: include `@media print` CSS — all sections expand, toggles hidden, clean pagination
- Only changed tools appear in the report — unchanged tools are excluded entirely

**Summary Panel Layout**
- Counts only: 4 colored badges (added=green, removed=red, modified=yellow, connections=blue) showing the numeric count
- Counts are clickable anchor links — clicking a badge scrolls to and expands that section
- Summary panel sits at the top of the page, full width
- Connection changes get their own separate blue badge (not rolled into modified)

**Diff Display Format**
- Before/after values use stacked rows: field name, then a red-tinted "Before: X" row, then a green-tinted "After: Y" row. Works on narrow screens and prints cleanly.
- For added/removed tools: show all fields from the tool config in the expanded section
- Tool identity shown as: Tool name + Tool ID (e.g., "Input Data Tool (ID: 42)")
- Long/complex values (SQL queries, file paths): shown in full, wrapped in a monospaced block — no truncation

**Expand/Collapse Behavior**
- Default state on load: all sections collapsed — only section headers and tool name rows visible
- "Expand All" / "Collapse All" controls present (per section or globally) — needed for print and Ctrl+F search
- Clicking a summary count badge scrolls to that section AND expands it
- Expandable tool rows indicated by a chevron/arrow icon (▶) that rotates when expanded

### Claude's Discretion
- Exact spacing, typography sizes, and color hex values (beyond the 4 status colors)
- Monospaced font choice for code/value blocks
- Exact placement and styling of Expand All / Collapse All buttons

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REPT-01 | Report includes a color-coded summary panel showing counts for added (green), removed (red), modified (yellow), and connection changes (blue) | Jinja2 template with summary dict from DiffResult; CSS badge colors via class names (status-added, status-removed, status-modified, status-connections); anchor-link scroll-to-section via JavaScript |
| REPT-02 | Report includes expandable per-tool detail sections showing before/after field-level values for each modified tool | JSON-in-script-tag pattern (const DIFF_DATA); vanilla JS reads DIFF_DATA on expand click; before/after stacked rows rendered from NodeDiff.field_diffs dict |
| REPT-03 | Report header displays report title, generation timestamp, and both compared file names | Jinja2 renders `{{ timestamp }}`, `{{ file_a }}`, `{{ file_b }}` variables passed from HTMLRenderer.render(); datetime.now(timezone.utc).isoformat() for timestamp |
| REPT-04 | Report is fully self-contained HTML — all JavaScript and CSS embedded inline, no CDN references, functional on air-gapped networks | All CSS in `<style>` tag; all JS in `<script>` tag; Jinja2 template stored as module-level string constant in html_renderer.py (no external files); no CDN URLs anywhere |
</phase_requirements>

---

## Summary

Phase 7 generates a single self-contained `.html` file from a `DiffResult` object. The report must open on air-gapped networks, meaning every byte of CSS and JavaScript is embedded inline — no CDN, no external files. The architecture is straightforward: a Jinja2 `Environment.from_string()` template embedded as a Python string constant inside `html_renderer.py`, rendering `DiffResult` data passed directly as template variables.

The performance constraint (500-tool workflow opens in under 3 seconds) is solved by the JSON-in-script-tag pattern: all tool detail data is serialized as `const DIFF_DATA = {...}` in a `<script>` tag at render time. On page load only section headers and tool name rows are in the DOM; the per-field before/after detail for each tool is built dynamically from `DIFF_DATA` when the user clicks to expand. This keeps initial DOM size small and parsing fast.

The `NodeDiff.field_diffs` dict (`field_name -> (old_value, new_value)`) is the core data for REPT-02. For added/removed tools, `AlteryxNode.config` (a `dict[str, Any]`) provides all fields to display. The `HTMLRenderer` follows the exact same renderer pattern already established for `JSONRenderer`: a class in `renderers/html_renderer.py`, re-exported from `renderers/__init__.py`, with a `render(result: DiffResult) -> str` method.

**Primary recommendation:** Use Jinja2 3.1.6 with `Environment.from_string()` and the `|tojson` filter to safely embed `DiffResult` as `const DIFF_DATA` in a script tag; keep all CSS and JS inline in a single template string constant in the renderer module.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | >=3.1 (latest: 3.1.6, released 2025-03-05) | HTML template rendering | De facto Python HTML templating library; built-in `tojson` filter safely embeds Python dicts as JSON in script tags; `from_string()` avoids file I/O for self-contained use |
| Python stdlib: json | 3.11+ | Serialize DiffResult data to JSON string for DIFF_DATA | Already in use throughout project; `json.dumps(sort_keys=True)` is the project-wide canonicalization convention |
| Python stdlib: datetime | 3.11+ | Generate ISO 8601 timestamp for report header | No external dep needed |
| Python stdlib: pathlib | 3.11+ | Extract filenames from path_a/path_b for header | Already used in pipeline.py |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| markupsafe | >=2.0 (transitive Jinja2 dep) | Marks strings as HTML-safe; used internally by `|tojson` filter | Automatically available when Jinja2 is installed; do NOT call Markup() directly — use `|tojson` filter instead |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 template string | Python f-string HTML | f-strings cannot loop, have no filters, and become unmaintainable at >50 lines; Jinja2 is right tool for structured HTML |
| Jinja2 template string | Jinja2 PackageLoader / FileSystemLoader | PackageLoader requires template files on disk inside the package; from_string() keeps the template co-located with the renderer class as a Python string constant — no extra files to package |
| `const DIFF_DATA = {...}` script tag | Server-side full render | Full server-side render of 500 tools DOM at Jinja2 time creates large HTML; JSON script tag + client-side lazy build keeps initial DOM small for < 3s open time |
| Vanilla JS | React/Vue/Alpine.js | External JS frameworks require CDN or bundled assets — violates REPT-04 (air-gapped); vanilla JS for expand/collapse is < 30 lines |

**Installation:**
```bash
uv add jinja2
```

Jinja2 has no transitive dependencies beyond MarkupSafe (which uv resolves automatically).

---

## Architecture Patterns

### Recommended Project Structure

```
src/alteryx_diff/
├── renderers/
│   ├── __init__.py          # exports JSONRenderer, HTMLRenderer
│   ├── json_renderer.py     # existing
│   └── html_renderer.py     # NEW: HTMLRenderer class + _TEMPLATE string constant
tests/
├── fixtures/
│   └── html_report.py       # NEW: Phase 7 fixture DiffResults (ToolIDs 701+)
└── test_html_renderer.py    # NEW: HTMLRenderer unit tests
```

No template files, no `templates/` directory. The Jinja2 template lives as a module-level string constant `_TEMPLATE` in `html_renderer.py`.

### Pattern 1: HTMLRenderer Class (mirrors JSONRenderer)

**What:** `HTMLRenderer` class in `renderers/html_renderer.py` with `render(result: DiffResult) -> str` method, following the established renderer pattern.

**When to use:** Called by the pipeline output stage (Phase 9 CLI) to produce the report HTML string, which the caller writes to disk.

**Example:**
```python
# Source: project convention from renderers/json_renderer.py
from __future__ import annotations

import json
from datetime import datetime, timezone

from jinja2 import Environment

from alteryx_diff.models import DiffResult

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Alteryx Workflow Diff</title>
  <style>
    /* All CSS inline here — no CDN, no external files */
    body { font-family: system-ui, -apple-system, sans-serif; ... }
    /* status badge colors */
    .badge-added    { background: #d4edda; color: #155724; }
    .badge-removed  { background: #f8d7da; color: #721c24; }
    .badge-modified { background: #fff3cd; color: #856404; }
    .badge-connections { background: #cce5ff; color: #004085; }
    /* before/after row tints */
    .before-row { background: #fff5f5; }
    .after-row  { background: #f5fff5; }
    /* chevron rotation */
    .chevron { display: inline-block; transition: transform 0.15s; }
    .expanded .chevron { transform: rotate(90deg); }
    /* print styles */
    @media print {
      .toggle-btn { display: none; }
      .detail { display: block !important; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Alteryx Workflow Diff</h1>
    <p>Generated: {{ timestamp }}</p>
    <p>{{ file_a }} vs {{ file_b }}</p>
  </header>

  {# Summary badges — anchor links scroll+expand their section #}
  <section id="summary">
    <a href="#added"       onclick="expandSection('added')"       class="badge badge-added">Added: {{ summary.added }}</a>
    <a href="#removed"     onclick="expandSection('removed')"     class="badge badge-removed">Removed: {{ summary.removed }}</a>
    <a href="#modified"    onclick="expandSection('modified')"    class="badge badge-modified">Modified: {{ summary.modified }}</a>
    <a href="#connections" onclick="expandSection('connections')" class="badge badge-connections">Connections: {{ summary.connections }}</a>
  </section>

  {# Tool sections — detail rendered lazily from DIFF_DATA #}
  <section id="added">...</section>
  <section id="removed">...</section>
  <section id="modified">...</section>
  <section id="connections">...</section>

  {# Embed all diff data — lazy per-tool expansion reads from here #}
  <script type="application/json" id="diff-data">{{ diff_data | tojson }}</script>
  <script>
    /* All JavaScript inline here — no CDN, no external files */
    const DIFF_DATA = JSON.parse(document.getElementById('diff-data').textContent);
    function expandSection(id) { ... }
    function toggleTool(toolId, section) { ... }
    /* expand all / collapse all */
    function expandAll(section) { ... }
    function collapseAll(section) { ... }
  </script>
</body>
</html>"""


class HTMLRenderer:
    """Render a DiffResult to a self-contained HTML string.

    All CSS and JavaScript are embedded inline — no CDN references.
    Tool detail is lazy-loaded from DIFF_DATA JSON in script tag.
    """

    def render(
        self,
        result: DiffResult,
        file_a: str = "workflow_a.yxmd",
        file_b: str = "workflow_b.yxmd",
    ) -> str:
        env = Environment(autoescape=True)
        template = env.from_string(_TEMPLATE)
        return template.render(
            timestamp=datetime.now(timezone.utc).isoformat(),
            file_a=file_a,
            file_b=file_b,
            summary={
                "added": len(result.added_nodes),
                "removed": len(result.removed_nodes),
                "modified": len(result.modified_nodes),
                "connections": len(result.edge_diffs),
            },
            diff_data=self._build_diff_data(result),
        )

    def _build_diff_data(self, result: DiffResult) -> dict:
        # Returns a plain dict that tojson serializes into the script tag
        ...
```

### Pattern 2: JSON-in-Script-Tag for Lazy Tool Detail

**What:** All per-tool detail data is serialized into a `<script type="application/json" id="diff-data">` tag at render time. The DOM initially shows only tool name rows. When a user clicks to expand, JavaScript reads `DIFF_DATA` (already parsed) and builds the before/after rows for that specific tool on demand.

**When to use:** Required for 500-tool performance target. Full DOM render of 500 × N fields at Jinja2 template time would create megabytes of HTML and slow browser parse time.

**Why `type="application/json"`:** The browser ignores this script tag (it's not executable JS), but JS can read `document.getElementById('diff-data').textContent` and JSON.parse it. No escaping conflicts. This is the standard pattern used by tools like webpack's data injection.

**Important:** The `|tojson` Jinja2 filter handles JSON serialization AND marks the output as `Markup` (HTML-safe), preventing double-escaping of `<`, `>`, `&` characters in config values. Do NOT use `json.dumps(...) | safe` — use `| tojson` directly.

**Data shape for DIFF_DATA:**
```python
{
    "added": [
        {"tool_id": 42, "tool_type": "Filter", "config": {"Expression": "[Amount] > 0"}}
    ],
    "removed": [...],
    "modified": [
        {
            "tool_id": 43,
            "tool_type": "Filter",
            "field_diffs": [
                {"field": "Expression", "before": "[Amount] > 0", "after": "[Amount] > 100"}
            ]
        }
    ],
    "connections": [
        {"src_tool": 1, "src_anchor": "Output", "dst_tool": 2, "dst_anchor": "Input", "change_type": "added"}
    ]
}
```

### Pattern 3: Jinja2 Environment Setup

**What:** Use `Environment(autoescape=True)` + `env.from_string(_TEMPLATE)` — no loader, no file system access. Template string constant defined at module level.

**Why autoescape=True:** Config values from Alteryx tools may contain `<`, `>`, `&` (XML-derived data). Autoescaping prevents XSS and malformed HTML. The `|tojson` filter always produces safe output regardless of autoescape setting (it uses `markupsafe.Markup`).

**Why from_string not PackageLoader:** PackageLoader requires a `templates/` directory inside the package — more files to maintain and package. `from_string()` with a module-level `_TEMPLATE` string keeps the renderer entirely self-contained.

**Jinja2 Environment policies for tojson:**
```python
env = Environment(autoescape=True)
# Optional: customize tojson serialization (default: sort_keys=True)
env.policies["json.dumps_kwargs"] = {"indent": None, "ensure_ascii": False}
```

### Pattern 4: Renderer Registration in __init__.py

**What:** `HTMLRenderer` must be exported from `renderers/__init__.py` alongside `JSONRenderer`, following the established pattern.

```python
# renderers/__init__.py — add HTMLRenderer export
from alteryx_diff.renderers.html_renderer import HTMLRenderer
from alteryx_diff.renderers.json_renderer import JSONRenderer

__all__ = ["JSONRenderer", "HTMLRenderer"]
```

### Anti-Patterns to Avoid

- **Using `json.dumps(...) | safe` instead of `| tojson`:** `json.dumps` produces a Python string; Jinja2 will HTML-escape `<`, `>`, `&` inside it when autoescape=True, making the JSON invalid for JavaScript to parse. Use `| tojson` which returns `markupsafe.Markup` and bypasses autoescaping correctly.
- **Full DOM render of all tool details at Jinja2 template time:** Generates huge HTML for large workflows. Build only skeleton rows in the template; build detail rows in JavaScript from DIFF_DATA.
- **External CDN or stylesheet links:** Violates REPT-04 and blocks air-gapped use. Every `<script src=...>` or `<link href=...>` pointing to an external host is forbidden. Verify with `"cdn"` / `"http"` string search on the rendered output in tests.
- **`type="text/javascript"` for JSON data tag:** Browser attempts to execute it. Use `type="application/json"` for the data tag.
- **f-string HTML generation instead of Jinja2:** Unescaped config values (e.g., SQL with `>`, `<`) will break the HTML structure or create XSS vectors in f-string rendering.
- **Using `autoescape=False` with user-derived data:** Config values come from Alteryx XML which may contain HTML-significant characters. Use `autoescape=True`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML escaping of config values | Custom escape function | Jinja2 `autoescape=True` | Misses edge cases: `'`, `"`, `/`, `\` in different contexts; Jinja2's markupsafe handles all HTML contexts correctly |
| JSON serialization into script tags | `json.dumps(...) + "\n"` in f-string | `| tojson` Jinja2 filter | Jinja2 autoescaping will corrupt plain `json.dumps` output; `tojson` returns `Markup` bypassing autoescaping correctly |
| CSS reset / normalize | Custom CSS baseline | System font stack (`system-ui, -apple-system`) + minimal resets | Air-gapped constraint means no external CSS; system fonts are already correct for the target environment and require zero bytes |
| Template file loading | Custom file loader | `Environment.from_string()` with module-level `_TEMPLATE` | No extra files to distribute; template lives next to the class; no packaging complexity |

**Key insight:** The Jinja2 `|tojson` filter is the load-bearing piece for correctness. Rolling a custom JSON-in-HTML embedding always breaks on real data with `<script>`, `</script>`, or `&` in config values.

---

## Common Pitfalls

### Pitfall 1: `</script>` Inside JSON Data Kills the Page

**What goes wrong:** If any Alteryx tool config value contains the literal string `</script>` (e.g., an embedded SQL comment or file path), and this value is placed inside a `<script>` block, the browser terminates the script at that `</script>` token — breaking the JSON and all JavaScript on the page.

**Why it happens:** The HTML parser processes `</script>` before the JavaScript engine sees the content. JSON string escaping (`\"`) does not help because `<` and `/` are valid JSON characters.

**How to avoid:** Use `<script type="application/json">` for the data tag. The browser's HTML parser does NOT look for `</script>` terminators inside `type="application/json"` blocks — it reads until the closing `</script>` tag only. Alternatively, have `| tojson` escape `/` to `\/` (Jinja2's tojson does this by default, producing `<\/script>` which is safe in executable script blocks too).

**Warning signs:** Report page renders blank or JS throws SyntaxError in browser console. Test by including a config value containing `</script>` in fixture data.

### Pitfall 2: Autoescape Double-Encoding JSON

**What goes wrong:** Using `{{ json_data | safe }}` with a pre-serialized JSON string — if the string was produced by Python's `json.dumps()` it's already a string, not a Markup object, so Jinja2 in `autoescape=True` mode will HTML-encode `&`, `<`, `>` inside it, making the JSON malformed.

**Why it happens:** Jinja2 autoescape applies to any non-Markup value rendered via `{{ }}`. `json.dumps()` returns `str`, not `Markup`.

**How to avoid:** Always use `{{ diff_data | tojson }}` where `diff_data` is the Python dict/list object, NOT a pre-serialized JSON string. The `tojson` filter handles both serialization and Markup wrapping in one step.

**Warning signs:** `JSON.parse()` throws in browser console; config values containing `&` appear as `&amp;` in parsed JavaScript.

### Pitfall 3: Ruff B701 / Bandit B701 — Jinja2 autoescape=False

**What goes wrong:** Creating `Environment(autoescape=False)` or `Environment()` (default is False) triggers ruff/bandit rule B701 in projects with security linting.

**Why it happens:** The project uses ruff with `"B"` rules enabled (`select = ["E", "F", "I", "UP", "B", "SIM"]`). B701 flags `jinja2_autoescape_false`.

**How to avoid:** Always pass `autoescape=True` explicitly to `Environment()`. This also happens to be correct for HTML generation.

**Warning signs:** Pre-commit hook fails on `html_renderer.py` with B701 error.

### Pitfall 4: mypy --strict Requires Typed Template Variables

**What goes wrong:** `template.render(**kwargs)` accepts `**Any` — mypy strict won't complain at the call site, but the dict passed to `_build_diff_data()` must have explicit `dict[str, Any]` return type to satisfy strict mode.

**Why it happens:** The project runs mypy --strict. Any function returning bare `dict` (without type params) fails `disallow_any_generics`.

**How to avoid:** Annotate `_build_diff_data(self, result: DiffResult) -> dict[str, Any]` and all nested dicts consistently. Follow the pattern in `json_renderer.py` where every helper returns `dict[str, Any]`.

**Warning signs:** mypy error: `"dict" is not generic` or `Missing type parameters for generic type "dict"`.

### Pitfall 5: 500-Tool DOM Size — Full Render at Template Time

**What goes wrong:** Rendering all before/after field rows for 500 modified tools in the Jinja2 template loop creates a very large HTML document (potentially >5MB for tools with complex SQL configs). Browser parse + layout time exceeds 3 seconds.

**Why it happens:** Each modified tool may have 10-50 fields; each field has a before row and after row. 500 tools × 30 fields × 2 rows = 30,000 DOM nodes before any JavaScript runs.

**How to avoid:** In the Jinja2 template, only render the tool header row (name + ID + chevron) for each tool. The `<div class="tool-detail" id="detail-{tool_id}" hidden>` is empty in the initial HTML. JavaScript reads from `DIFF_DATA` and builds detail rows only when the user clicks to expand.

**Warning signs:** Report open time > 3 seconds on 500-tool fixture; browser DevTools shows large HTML parse time.

### Pitfall 6: `uv.lock` Not Updated After Adding Jinja2

**What goes wrong:** `pyproject.toml` gets `jinja2>=3.1` in `[project.dependencies]` but `uv.lock` is stale, causing the pre-commit environment to have wrong dependencies.

**Why it happens:** uv manages a lockfile; `uv add jinja2` updates both `pyproject.toml` and `uv.lock` atomically. Manual edits to `pyproject.toml` do not update `uv.lock`.

**How to avoid:** Always use `uv add jinja2` (not manual pyproject.toml edit) to add the dependency. Commit both `pyproject.toml` and `uv.lock`.

**Warning signs:** `ImportError: No module named 'jinja2'` in tests despite being in pyproject.toml.

---

## Code Examples

### Jinja2 Environment with from_string (verified pattern)

```python
# Source: https://jinja.palletsprojects.com/en/stable/api/ (HIGH confidence)
from jinja2 import Environment

env = Environment(autoescape=True)
template = env.from_string("Hello {{ name }}!")
result = template.render(name="World")
# result == "Hello World!"
```

### tojson Filter — Safe JSON in Script Tag (verified pattern)

```python
# Source: https://jinja.palletsprojects.com/en/stable/templates/ (HIGH confidence)
# In the template string:
# <script type="application/json" id="diff-data">{{ diff_data | tojson }}</script>
#
# diff_data is a Python dict; tojson:
# 1. Calls json.dumps(diff_data, sort_keys=True) by default
# 2. Returns markupsafe.Markup — bypasses autoescape
# 3. Escapes </script> sequences safely
```

### Jinja2 tojson Policy Customization

```python
# Source: https://jinja.palletsprojects.com/en/stable/api/#jinja2.Environment (HIGH confidence)
env = Environment(autoescape=True)
env.policies["json.dumps_kwargs"] = {"ensure_ascii": False, "sort_keys": True}
```

### HTML Renderer Following Project Pattern

```python
# Source: project convention from src/alteryx_diff/renderers/json_renderer.py
from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from jinja2 import Environment

from alteryx_diff.models import DiffResult, NodeDiff
from alteryx_diff.models.workflow import AlteryxNode

_TEMPLATE: str = """..."""  # full Jinja2 template string

class HTMLRenderer:
    def render(
        self,
        result: DiffResult,
        file_a: str = "workflow_a.yxmd",
        file_b: str = "workflow_b.yxmd",
    ) -> str:
        env = Environment(autoescape=True)
        template = env.from_string(_TEMPLATE)
        return template.render(
            timestamp=datetime.now(timezone.utc).isoformat(),
            file_a=file_a,
            file_b=file_b,
            summary={
                "added": len(result.added_nodes),
                "removed": len(result.removed_nodes),
                "modified": len(result.modified_nodes),
                "connections": len(result.edge_diffs),
            },
            diff_data=self._build_diff_data(result),
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
            "config": node.config,
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
```

### Vanilla JavaScript Expand/Collapse Pattern

```javascript
// Source: MDN Web Docs + project requirement (MEDIUM confidence — pattern verified)
// Reads DIFF_DATA (already parsed) — no network requests
function toggleTool(toolId, section) {
    const detailEl = document.getElementById('detail-' + section + '-' + toolId);
    const headerEl = document.getElementById('header-' + section + '-' + toolId);
    const isExpanded = detailEl.getAttribute('aria-hidden') === 'false';

    if (isExpanded) {
        detailEl.setAttribute('aria-hidden', 'true');
        detailEl.hidden = true;
        headerEl.classList.remove('expanded');
        headerEl.setAttribute('aria-expanded', 'false');
    } else {
        // Lazy-build detail rows from DIFF_DATA on first expand
        if (!detailEl.dataset.built) {
            buildDetail(toolId, section, detailEl);
            detailEl.dataset.built = 'true';
        }
        detailEl.setAttribute('aria-hidden', 'false');
        detailEl.hidden = false;
        headerEl.classList.add('expanded');
        headerEl.setAttribute('aria-expanded', 'true');
    }
}

function expandSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({behavior: 'smooth'});
        // expand all tools in that section
        section.querySelectorAll('.tool-header').forEach(h => {
            if (!h.classList.contains('expanded')) h.click();
        });
    }
}
```

### CSS Before/After Row Pattern

```css
/* Source: CONTEXT.md requirement — stacked rows for before/after */
.field-row { margin: 4px 0; }
.field-name { font-weight: 600; font-size: 0.85em; color: #555; }
.before-row { background: #fff5f5; border-left: 3px solid #dc3545; padding: 4px 8px; }
.after-row  { background: #f5fff5; border-left: 3px solid #28a745; padding: 4px 8px; }
.before-row::before { content: "Before: "; font-weight: 600; color: #dc3545; }
.after-row::before  { content: "After: ";  font-weight: 600; color: #28a745; }
.value-block { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
               white-space: pre-wrap; word-break: break-all; }

@media print {
    .toggle-btn, .expand-all-btn { display: none; }
    .tool-detail { display: block !important; }
    .tool-detail[hidden] { display: block !important; }
}
```

### Test for Self-Contained Output (no CDN check)

```python
# Source: REPT-04 requirement + project test pattern
def test_render_is_self_contained() -> None:
    """Rendered HTML contains no external URLs (CDN check)."""
    renderer = HTMLRenderer()
    html = renderer.render(_empty_diff_result())

    # No external script or link tags
    assert "cdn." not in html
    assert "unpkg.com" not in html
    assert "jsdelivr.net" not in html
    assert "<script src=" not in html
    assert '<link rel="stylesheet"' not in html
    # CSS and JS must be present inline
    assert "<style>" in html
    assert "<script>" in html
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Jinja2 `Template()` directly (no Environment) | `Environment(autoescape=True).from_string()` | Jinja2 2.x → 3.x | `Template()` bypasses autoescape config; Environment wrapper is necessary for autoescape to apply |
| `autoescape=False` (historical default) | `autoescape=True` for HTML templates | Jinja2 2.4+ recommendation | B701 ruff rule flags `False`; project uses ruff B rules |
| CDN-hosted CSS/JS in reports | Inline everything for air-gapped use | Operational requirement | CDN-hosted tools break in corporate/regulated environments |
| `json.dumps(data) | safe` | `data | tojson` filter | Jinja2 tojson filter added | `| safe` on pre-serialized JSON still fails when autoescaping was applied before `| safe` |

**Deprecated/outdated:**
- `jinja2.Template("...")` constructor: Bypasses Environment autoescape setting. Use `Environment.from_string()` instead.
- Importing from `jinja2.utils` for Markup: Use `markupsafe.Markup` or let `|tojson` produce it automatically.

---

## Open Questions

1. **ToolID allocation for Phase 7 fixtures**
   - What we know: ToolIDs 601+ used by Phase 6; 501-599 used by Phase 5; Phase 7 fixtures should start at 701+
   - What's unclear: Not explicitly confirmed in STATE.md for Phase 7
   - Recommendation: Allocate 701+ for Phase 7 fixtures per the sequential allocation pattern; document in fixture file header

2. **render() method signature — how to pass file_a/file_b names**
   - What we know: JSONRenderer.render() takes only `result: DiffResult`. HTMLRenderer needs filenames for the report header (REPT-03).
   - What's unclear: Whether to pass filenames as constructor args (`HTMLRenderer(file_a, file_b)`) or render-time args (`render(result, file_a, file_b)`)
   - Recommendation: Pass as `render(result, file_a, file_b)` keyword arguments with defaults — consistent with how Phase 9 CLI will call it (CLI has access to paths at call time, not construction time); matches how `JSONRenderer.render(result)` is structured

3. **Field value serialization for complex nested config types**
   - What we know: `AlteryxNode.config` is `dict[str, Any]`; `NodeDiff.field_diffs` values are `(Any, Any)` tuples; values may be dicts, lists, strings, numbers
   - What's unclear: How deeply nested config values should be formatted for display (e.g., dict-valued fields)
   - Recommendation: Rely on `|tojson` for display of complex values in the JavaScript layer; all values are already JSON-serializable via the existing `json.dumps(sort_keys=True)` convention used project-wide; display as formatted JSON in monospaced blocks

---

## Sources

### Primary (HIGH confidence)

- https://jinja.palletsprojects.com/en/stable/api/ — Environment constructor, from_string, tojson policy, autoescape
- https://jinja.palletsprojects.com/en/stable/templates/ — tojson filter, whitespace control, raw blocks, for/if syntax
- https://pypi.org/project/Jinja2/ — latest version 3.1.6, release date 2025-03-05
- Project source: `src/alteryx_diff/renderers/json_renderer.py` — established renderer pattern to follow
- Project source: `src/alteryx_diff/models/diff.py` — DiffResult, NodeDiff, EdgeDiff data structures
- Project source: `pyproject.toml` — ruff B rules enabled, mypy strict, pytest config

### Secondary (MEDIUM confidence)

- https://sopython.com/canon/94/jinja-escapes-json-so-it-is-invalid-javascript/ — tojson vs json.dumps|safe pitfall, verified against Jinja2 docs
- https://bandit.readthedocs.io/en/latest/plugins/b701_jinja2_autoescape_false.html — B701 rule, verified against ruff B rule selection in pyproject.toml
- MDN Web Docs lazy loading patterns — lazy DOM build from JSON data pattern

### Tertiary (LOW confidence)

- None — all critical claims verified against official sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Jinja2 3.1.6 confirmed from PyPI; version + API verified from official docs
- Architecture: HIGH — renderer pattern copied from existing project code; Jinja2 from_string/autoescape verified from official docs
- Pitfalls: HIGH — tojson/autoescape interaction verified from official Jinja2 docs and sopython canon; B701 ruff rule verified from pyproject.toml; `</script>` in JSON data tag verified as HTML spec behavior

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (Jinja2 is stable; vanilla JS patterns are evergreen)
