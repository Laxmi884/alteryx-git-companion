---
phase: quick-4
plan: 4
subsystem: renderers
tags: [dark-mode, css-variables, graph, fullscreen, draggable, ui-ux]
dependency_graph:
  requires: []
  provides: [dark-mode-css, draggable-graph-nodes, fullscreen-graph-toggle]
  affects: [html_renderer, graph_renderer]
tech_stack:
  added: []
  patterns: [css-custom-properties, prefers-color-scheme, fullscreen-api]
key_files:
  created: []
  modified:
    - src/alteryx_diff/renderers/html_renderer.py
    - src/alteryx_diff/renderers/graph_renderer.py
decisions:
  - "CSS custom properties used for all theme-sensitive colors — no JS theme toggle, OS-level switching only via prefers-color-scheme media query"
  - "fixed: False on nodes keeps physics disabled but allows drag-to-reposition after initial layout"
  - "Fullscreen targets #graph-section element (not just the canvas) so controls stay visible in fullscreen mode"
  - "Dark mode added to graph fragment as standalone media query — independent from html_renderer.py variables since the fragment has no access to :root"
metrics:
  duration: 3 min
  completed: "2026-03-07"
  tasks_completed: 2
  files_modified: 2
---

# Phase quick-4 Plan 4: Modernize Diff Report UI/UX with Dark Mode Summary

**One-liner:** Dark mode via CSS custom properties + prefers-color-scheme, draggable vis-network nodes, and a fullscreen API toggle for the graph section.

## What Was Built

Added automatic dark mode support to the HTML diff report and graph fragment, made graph nodes draggable after initial layout, and introduced a fullscreen button for large-workflow inspection.

### Task 1: Add dark mode CSS to HTML report template

- Added `:root` CSS custom property block with 20+ design tokens covering background, text, border, badge, button, and row colors
- Added `@media (prefers-color-scheme: dark)` override block with deep-navy dark palette
- Replaced all hardcoded color values (`#fff`, `#212529`, `#dee2e6`, badge colors, button colors, row colors, etc.) with corresponding `var(--*)` references
- Updated governance metadata `<details>` section inline styles to use CSS variables (`var(--border)`, `var(--text-muted)`, `var(--field-label)`)
- All 15 html_renderer and graph_renderer tests pass without modification

### Task 2: Draggable graph nodes and fullscreen graph toggle

- Changed `"fixed": True` to `"fixed": False` in `GraphRenderer.render()` node entry dict — vis-network physics remains disabled, nodes stay where dropped
- Added `<button id="fullscreen-btn" class="ctrl-btn">Fullscreen</button>` to `#graph-controls` between fit-btn and toggle-changes
- Added fullscreen CSS: `#graph-section:fullscreen` rules set background and expand `#graph-container` to `calc(100vh - 80px)`
- Added fullscreen JS: click handler calls `requestFullscreen()` / `exitFullscreen()` and updates button text; `fullscreenchange` event resets text and calls `network.fit()` on exit
- Added `@media (prefers-color-scheme: dark)` block to graph fragment `<style>` covering `#graph-container`, `#diff-panel`, `.panel-title`, `.panel-field-name`, `.panel-before`, `.panel-after`, `.value-mono`
- Full test suite: 105 passed, 1 xfailed — zero regressions

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Verification

- [x] `_TEMPLATE` in `html_renderer.py` uses CSS custom properties and has `@media (prefers-color-scheme: dark)` block
- [x] `_GRAPH_FRAGMENT_TEMPLATE` in `graph_renderer.py` has fullscreen button, fullscreen JS, dark mode CSS
- [x] `GraphRenderer.render()` sets `"fixed": False` on all nodes
- [x] All 105 existing tests pass, 1 xfailed (pre-existing), 0 regressions
- [x] `python -c "from alteryx_diff.renderers import HTMLRenderer, GraphRenderer"` exits 0

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | ad7d0cf | feat(quick-4): add dark mode CSS to HTML report template |
| 2 | e1697dd | feat(quick-4): add draggable nodes, fullscreen toggle, and dark mode to graph |

## Self-Check: PASSED
