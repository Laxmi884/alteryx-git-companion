# HTML Diff Report Visual Redesign — Design Spec

**Date:** 2026-03-27
**Branch:** `refactor/html-report`
**Status:** Approved

---

## Goal

Transform the Alteryx Workflow Diff Report from a plain functional layout into a visually stunning, modern developer-grade report. Audience: developers, data analysts, business users, and QA/validation teams.

---

## Architecture

### Constraint: Self-contained, zero CDN
All CSS, JS, and fonts remain embedded inline. No external dependencies. Report works offline.

### Files changed
- `src/alteryx_diff/renderers/html_renderer.py` — main report template (`_TEMPLATE` string)
- `src/alteryx_diff/renderers/graph_renderer.py` — graph fragment template (`_GRAPH_FRAGMENT_TEMPLATE` string)

### What does NOT change
- `HTMLRenderer` Python class — no signature changes
- `GraphRenderer` Python class — no signature changes
- Jinja2 template variables (`{{ summary.added }}`, `{{ diff_data | tojson }}`, `{{ graph_html | safe }}`, `{{ metadata }}`, etc.)
- vis-network JS logic (split/overlay views, click handlers, `applyThemeColors()`, node color palette)
- Governance metadata footer structure
- Dark/light toggle behaviour and `localStorage` persistence

### Key structural change
Dark mode is the **default** theme (instead of light). Light is the secondary toggle state. The `setTheme()` JS function and `localStorage` key remain identical.

---

## Visual Design System

### Color tokens (CSS custom properties)

| Token | Dark value | Light value |
|---|---|---|
| `--bg` | `#0f172a` | `#ffffff` |
| `--surface` | `#1e293b` | `#f8f9fb` |
| `--surface-2` | `#131f31` | `#f1f5f9` |
| `--border` | `#1e3a5f` | `#e2e8f0` |
| `--border-subtle` | `#334155` | `#f1f5f9` |
| `--text` | `#e2e8f0` | `#0f172a` |
| `--text-muted` | `#64748b` | `#64748b` |
| `--accent-added` | `#57ef92` | `#16a34a` |
| `--accent-added-bg` | `#052e16` | `#f0fdf4` |
| `--accent-added-border` | `#166534` | `#bbf7d0` |
| `--accent-removed` | `#f87171` | `#dc2626` |
| `--accent-removed-bg` | `#2d1515` | `#fef2f2` |
| `--accent-removed-border` | `#7f1d1d` | `#fecaca` |
| `--accent-modified` | `#fbbf24` | `#d97706` |
| `--accent-modified-bg` | `#1c1506` | `#fffbeb` |
| `--accent-modified-border` | `#78350f` | `#fde68a` |
| `--accent-conn` | `#60a5fa` | `#2563eb` |
| `--accent-conn-bg` | `#0c1a3a` | `#eff6ff` |
| `--accent-conn-border` | `#1e3a5f` | `#bfdbfe` |

### Typography
- **UI text:** `Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- **Code/values/diffs:** `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`
- **Base size:** `14px`
- **Muted labels:** `11px`, uppercase, `1px` letter-spacing
- **Title:** `18px`, Semi Bold weight (`600`)
- **Stat count:** `32px`, Bold weight (`700`)

### Spacing & shape
- Container max-width: `960px`, centered
- Horizontal padding: `32px`
- Section gaps: `24px`
- Row gaps: `8px`
- Card/row border radius: `8px`
- Transition: `0.15s ease` on hover/expand

---

## Components

### Header
- Full-width dark bar (`--bg`), bottom border (`--border`)
- **Left:** 8px green pulse dot + title (18px Semi Bold, `--text`) + meta line (file A → file B · timestamp, `--text-muted`, 12px)
- **Right:** theme toggle pill — moon icon + "Dark" label, ghost style with `--surface` bg and `--border` stroke; clicking toggles dark↔light

### Summary Stat Cards (replaces flat badge row)
- 4 equal-width cards in a `display:flex` row, `12px` gap
- Each card: `--accent-*-bg` fill, `1px --accent-*-border` border, `8px` radius, `16px` padding
- **Top row:** uppercase label (11px, `1px` letter-spacing, `--accent-*` color at 70% opacity) + small colored dot (right-aligned, 6px)
- **Count:** 32px Bold, `--accent-*` color
- Click behaviour unchanged — jumps to section and expands all rows

### Section Headers
- `3px` left accent bar (color = section accent), section name (14px Semi Bold, `--text`), count pill (`--accent-*-bg` + border)
- **Right:** `Expand All` / `Collapse All` ghost buttons — `--surface` bg, `--border` stroke, `--text-muted` label, `6px` radius
- Bottom border `--border-subtle`

### Tool Rows (collapsed)
- `--surface` bg, `1px --border` border, `8px` radius, `8px` vertical margin
- **Left:** `▶` chevron (rotates 90° when expanded) + tool type name + ID pill
- **Right:** field-count badge for modified ("3 fields"), change-type badge for added/removed/connections
- **Hover:** background `#273449`

### Expanded Detail Panel (modified tools)
- `--surface-2` bg, top border removed, bottom radius only (visually attached to row above)
- Each changed field:
  - Field label: 11px uppercase `--text-muted`
  - **Before row:** `3px --accent-removed` left border, `--accent-removed-bg` fill, "Before:" label + monospace value
  - **After row:** `3px --accent-added` left border, `--accent-added-bg` fill, "After:" label + monospace value

### Added / Removed Tool Detail Panel
- Same structure as expanded panel but single-column: field name + monospace value (no before/after split)

### Connection Detail Panel
- Single line: `src_tool:src_anchor → dst_tool:dst_anchor (change_type)` in monospace

### Graph Section
- **Section header:** matches all other section headers (accent bar + title + count + buttons)
- **View toggle:** `Split View` / `Overlay View` as ghost pill buttons; active state: `--accent-conn` bg, white text
- **Graph containers:** `--surface` bg, `--border` border, `8px` radius
- **Split view "Changes" panel:** `--surface` bg, `--border` separators, `--text` labels
- **Slide-out diff panel:** `--surface` bg, `--border` left edge, matches expanded detail panel style
- **Remove** all inline `style=""` attributes and `!important` overrides from `_GRAPH_FRAGMENT_TEMPLATE` — replace with CSS variable references
- vis-network JS logic and node color palettes (`LIGHT_COLORS`, `DARK_COLORS`) are **unchanged**

### Governance Footer
- `<details>` element, `--surface` bg, `--border` top edge, `12px` padding
- `<summary>` label: 12px, `--text-muted`
- Metadata rows: monospace 12px, `--text-muted`, `1.8` line-height

---

## Behaviour (unchanged)
- Theme toggle persists to `localStorage` key `alteryx-diff-theme`; on load restores saved preference or falls back to OS preference
- Default theme when no saved preference and no OS preference: **dark**
- Tool detail panels lazy-built on first expand (existing `buildDetail()` JS)
- `expandAll()` / `collapseAll()` per section
- Summary card click → scroll to section + expand all rows
- Print: `@media print` hides buttons, forces all details open
- Governance `<details>` open/close is native browser behaviour

---

## Out of Scope
- Changes to Python class interfaces or method signatures
- Changes to vis-network JS graph logic or node colour computation
- Adding new data fields to the diff output
- CDN references of any kind
