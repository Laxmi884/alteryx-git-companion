# Phase 7: HTML Report - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate a self-contained HTML file that governance reviewers open in a browser to inspect color-coded diffs of Alteryx workflow tool configurations. No internet connection required, no software to install. The report visualizes DiffResult data — added, removed, modified tools, and connection changes.

</domain>

<decisions>
## Implementation Decisions

### Visual Design & Density
- Clean and minimal tone: white background, subtle borders, system fonts — professional diff tool aesthetic
- Tools grouped by status in the report body: Added section, Removed section, Modified section, Connection Changes section
- Print-friendly: include `@media print` CSS — all sections expand, toggles hidden, clean pagination
- Only changed tools appear in the report — unchanged tools are excluded entirely

### Summary Panel Layout
- Counts only: 4 colored badges (added=green, removed=red, modified=yellow, connections=blue) showing the numeric count
- Counts are clickable anchor links — clicking a badge scrolls to and expands that section
- Summary panel sits at the top of the page, full width
- Connection changes get their own separate blue badge (not rolled into modified)

### Diff Display Format
- Before/after values use stacked rows: field name, then a red-tinted "Before: X" row, then a green-tinted "After: Y" row. Works on narrow screens and prints cleanly.
- For added/removed tools: show all fields from the tool config in the expanded section
- Tool identity shown as: Tool name + Tool ID (e.g., "Input Data Tool (ID: 42)")
- Long/complex values (SQL queries, file paths): shown in full, wrapped in a monospaced block — no truncation

### Expand/Collapse Behavior
- Default state on load: all sections collapsed — only section headers and tool name rows visible
- "Expand All" / "Collapse All" controls present (per section or globally) — needed for print and Ctrl+F search
- Clicking a summary count badge scrolls to that section AND expands it
- Expandable tool rows indicated by a chevron/arrow icon (▶) that rotates when expanded

### Claude's Discretion
- Exact spacing, typography sizes, and color hex values (beyond the 4 status colors)
- Monospaced font choice for code/value blocks
- Exact placement and styling of Expand All / Collapse All buttons

</decisions>

<specifics>
## Specific Ideas

- Success criteria specifies JSON-in-script-tag pattern: embed DiffResult as `const DIFF_DATA = {...}` in a `<script>` tag for lazy per-tool expansion
- All CSS and JavaScript must be embedded inline — zero CDN references
- 500-tool workflow must open in under 3 seconds

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-html-report*
*Context gathered: 2026-03-06*
