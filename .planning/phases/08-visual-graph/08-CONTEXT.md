# Phase 8: Visual Graph - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Embed an interactive workflow topology graph in the self-contained HTML report. Nodes represent tools, edges represent connections, color-coded by change type. Hover/click reveals inline config diffs. No external CDN dependencies. Layout is set at generation time (hierarchical default or `--canvas-layout`).

</domain>

<decisions>
## Implementation Decisions

### Node labels & information density
- Tool name only is always visible on the node (no tool type, no ID)
- Change type communicated by color only — no text badge or subtitle on the node
- An inline legend is embedded in the graph panel itself (green = added, red = removed, yellow = modified, blue = connection change, neutral = unchanged)
- Tool type is accessible via hover tooltip (not on the node face)

### Hover tooltip
- Hovering a node shows: tool type + change type + count of changed config fields
- Applies to changed nodes; for unchanged nodes, no hover behavior (nodes not interactive)

### Diff panel UX
- Clicking a changed node opens a slide-in side panel from the right
- Graph remains visible while the panel is open
- Panel contents: config key-value diff only — just the changed fields, two-column before/after format
- Closing: click anywhere outside the panel or press Escape
- Clicking a different node while a panel is open replaces panel contents (implicit switch)

### Unchanged node treatment
- Unchanged nodes are muted / de-emphasized (lighter gray color)
- A "Show only changes" toggle button is present in the graph controls
- When unchanged nodes are hidden, their connected edges are also hidden
- Unchanged nodes are not clickable — no interaction on click

### In-browser controls
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

</decisions>

<specifics>
## Specific Ideas

- No specific product references mentioned — open to standard approaches for graph styling
- The diff panel should feel like it belongs in the same visual language as the rest of the HTML report

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-visual-graph*
*Context gathered: 2026-03-06*
