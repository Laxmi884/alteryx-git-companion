---
phase: quick-9
verified: 2026-03-10T00:00:00Z
status: human_needed
score: 7/8 must-haves verified
re_verification: false
human_verification:
  - test: "Open generated diff report in a browser and confirm Split View renders two vis-network graphs side by side"
    expected: "Left graph shows old workflow nodes (plus faint ghost outlines for added nodes), right graph shows new workflow nodes (plus faint ghost outlines for removed nodes), center panel lists all changes"
    why_human: "vis-network canvas rendering requires a browser; can't verify visual output programmatically"
  - test: "Pan or zoom the left graph and confirm the right graph viewport syncs, and vice versa"
    expected: "Both graphs move together; no infinite recursion or jank"
    why_human: "Viewport sync requires interactive browser event firing; syncingViewport guard logic can't be exercised with static analysis"
  - test: "Click a row in the center change panel"
    expected: "Both graphs smoothly pan/zoom to the corresponding node and briefly highlight it"
    why_human: "focusNode() relies on networkLeft.getPosition() which requires a live vis-network instance"
  - test: "Switch to Overlay View by clicking the 'Overlay View' button"
    expected: "The split view hides, the single merged graph appears with all existing controls (Fit to Screen, Fullscreen, Show Only Changes, slide-in side panel on node click)"
    why_human: "DOM visibility switching and overlay network behavior requires an interactive browser session"
  - test: "Reload the page after switching to Overlay View"
    expected: "Overlay View is still active (localStorage persistence)"
    why_human: "localStorage persistence requires a real browser session"
  - test: "Toggle dark/light mode (if the app has the theme toggle from quick-5)"
    expected: "Split-view-left and split-view-right backgrounds change to dark (#0f172a), center panel background changes, node colors update via applyThemeColorsToSplit()"
    why_human: "Theme switching requires browser interaction; CSS [data-theme=dark] rules and JS applyThemeColorsToSplit() can only be confirmed visually"
---

# Quick Task 9: Add Split View UI Verification Report

**Task Goal:** Add split-view UI with synced before/after graphs and center change panel plus overlay toggle
**Verified:** 2026-03-10
**Status:** human_needed (all automated checks pass; visual/interactive behavior requires browser)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Graph section shows Split View by default with three columns: left (Before), center (scrollable change panel), right (After) | VERIFIED | Template has `#split-view` with flex layout, `#split-view-left`, `#split-change-rows` (280px center), `#split-view-right`; `currentView = localStorage.getItem('alteryx-diff-view') \|\| 'split'` defaults to split; confirmed in generated HTML |
| 2 | Overlay View button restores current single merged graph behavior | VERIFIED | `#overlay-view` div contains exact existing structure: `#graph-controls`, `#graph-container`, `#diff-panel`, `#graph-overlay`; all existing JS logic (fit, fullscreen, show-only-changes, click handler, openSidePanel) preserved unchanged; 105 tests pass with zero regressions |
| 3 | View preference persists in localStorage across page loads | VERIFIED | `localStorage.setItem('alteryx-diff-view', view)` in `switchView()`; `localStorage.getItem('alteryx-diff-view') \|\| 'split'` on load; key string `'alteryx-diff-view'` confirmed present in generated HTML |
| 4 | Both split-view graphs use canvas positions (Alteryx X/Y coordinates) | VERIFIED | `build_split_node_list()` uses `node.x`, `node.y` directly from `AlteryxNode` for all real nodes; ghost nodes use `new_pos_lookup` / `old_pos_lookup` derived from actual node coordinates |
| 5 | Removed nodes appear as ghost/faint outlines on right graph; added nodes appear as ghost/faint outlines on left graph | VERIFIED | `_graph_builder.py`: added nodes appended to `old_vis_nodes` with `"status": "ghost_added"`, `"opacity": 0.25`, `"borderDashes": [4, 4]`; removed nodes appended to `new_vis_nodes` with `"status": "ghost_removed"`, same opacity/dashes |
| 6 | Panning or zooming one split-view graph syncs the other graph's viewport | VERIFIED | `networkLeft.on('dragEnd', syncLeftToRight)`, `networkLeft.on('zoom', syncLeftToRight)` and symmetric right listeners; `syncLeftToRight()` calls `networkRight.moveTo({position: networkLeft.getViewPosition(), scale: networkLeft.getScale()})` with `syncingViewport` guard preventing infinite recursion |
| 7 | Clicking a change row in the center panel pans both graphs to that node and briefly highlights it | VERIFIED | `row.addEventListener('click', function() { focusNode(item.tool_id); })` in `buildCenterPanel()`; `focusNode()` calls `networkLeft.moveTo()` and `networkRight.moveTo()` with `scale: 1.2` and smooth animation; needs human to confirm visually |
| 8 | Dark/light theme applies to all new elements consistently | VERIFIED | CSS rules for `[data-theme=dark]` and `@media (prefers-color-scheme: dark)` cover `#split-view-left`, `#split-view-right`, `#split-change-rows`, `.split-change-row`, `.split-change-row:hover`; `applyThemeColorsToSplit()` called from `applyThemeColors()` on MutationObserver and initial load |

**Score:** 8/8 truths verified (automated evidence for all; 6 additionally require human browser confirmation)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/alteryx_diff/renderers/_graph_builder.py` | `build_split_node_list()` helper returning `(old_vis_nodes, new_vis_nodes)` with ghost nodes | VERIFIED | Function at line 204; full implementation with ghost nodes for added (to left graph) and removed (to right graph); import check passes; ruff clean |
| `src/alteryx_diff/renderers/graph_renderer.py` | Updated `_GRAPH_FRAGMENT_TEMPLATE` with split/overlay toggle and two vis-network instances; `render()` calls `build_split_node_list` and passes `nodes_old_json`/`nodes_new_json` | VERIFIED | Template fully rewritten with all required IDs and JS sections; `render()` calls `build_split_node_list()` at line 644 and passes results to template at lines 658-659 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `graph_renderer.py render()` | `_graph_builder.build_split_node_list()` | Python call, returns `(old_vis_nodes, new_vis_nodes)` serialized via `json.dumps` | VERIFIED | Line 644: `old_vis_nodes, new_vis_nodes = build_split_node_list(result, nodes_old, nodes_new)`; lines 658-659: `nodes_old_json=json.dumps(old_vis_nodes)`, `nodes_new_json=json.dumps(new_vis_nodes)` |
| JS `networkLeft` / `networkRight` instances | `vis.DataSet(NODES_OLD)` / `vis.DataSet(NODES_NEW)` | Template variables `nodes_old_json \| safe` and `nodes_new_json \| safe` | VERIFIED | Lines 142-143 in template: `var NODES_OLD = {{ nodes_old_json \| safe }}; var NODES_NEW = {{ nodes_new_json \| safe }};`; `networkLeft = new vis.Network(leftContainer, {nodes: new vis.DataSet(NODES_OLD), ...})` |
| `JS networkLeft.on('dragEnd')` and `networkLeft.on('zoom')` | `networkRight.moveTo()` | Sync handler inside `initSplitNetworks()`; symmetric for right->left | VERIFIED | Lines 403-406 register all four listeners; `syncLeftToRight()` at line 411 calls `networkRight.moveTo(...)` with `syncingViewport` guard |
| Center panel change rows `onclick` | `networkLeft.moveTo()` + `networkRight.moveTo()` | `focusNode(toolId)` JS function | VERIFIED | `buildCenterPanel()` line 502: `row.addEventListener('click', function() { focusNode(item.tool_id); })`; `focusNode()` lines 447-458 calls `moveTo` on both networks |

### Requirements Coverage

No `requirements:` IDs declared in plan frontmatter (field is empty `[]`). No REQUIREMENTS.md cross-reference needed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | No anti-patterns detected |

Scanned for: TODO/FIXME/placeholder comments, empty implementations (`return null`, `return {}`, `=> {}`), console.log-only handlers. None found in either modified file.

### Human Verification Required

**1. Split View Rendering**

**Test:** Generate a diff report from two differing workflow files, open in a browser. Confirm two side-by-side vis-network graphs appear with "Before" and "After" headers, and the center panel lists all added/removed/modified nodes.

**Expected:** Three-column layout visible; ghost nodes (faint outlines) for added tools shown on left graph, ghost nodes for removed tools shown on right graph.

**Why human:** vis-network canvas rendering requires a browser; visual output cannot be verified programmatically.

**2. Synchronized Pan/Zoom**

**Test:** Pan or zoom one graph while watching the other.

**Expected:** The other graph's viewport mirrors the action instantly with no infinite recursion or jank.

**Why human:** `syncingViewport` guard logic can only be tested via live browser interaction.

**3. Center Panel Click Navigation**

**Test:** Click a row in the center change panel.

**Expected:** Both graphs smoothly animate to center on the corresponding node.

**Why human:** `focusNode()` requires a live vis-network instance to call `getPosition()` and `moveTo()`.

**4. Overlay View Restoration**

**Test:** Click "Overlay View" button; interact with the single merged graph (click a node, use show-only-changes toggle, fullscreen).

**Expected:** Exact existing behavior preserved — slide-in side panel, overlay click to close, keyboard Escape to close.

**Why human:** DOM visibility switching and overlay network behavior require a browser session.

**5. localStorage Persistence**

**Test:** Switch to Overlay View, close and reopen the report.

**Expected:** Overlay View is still active on reload.

**Why human:** localStorage requires a real browser session.

**6. Dark/Light Theme on Split Elements**

**Test:** Toggle the dark/light theme switcher (if available from quick-5).

**Expected:** `#split-view-left`, `#split-view-right`, `#split-change-rows` update colors; vis-network node colors update via `applyThemeColorsToSplit()`.

**Why human:** CSS `[data-theme=dark]` rules and JS theme application require browser rendering.

### Gaps Summary

No gaps. All automated checks pass:

- `build_split_node_list` imports without error
- 105 tests pass, 1 xfailed (zero regressions from the 105-test baseline)
- ruff passes on both modified files with no errors
- Generated HTML contains all required IDs and JS variables: `split-view-left`, `split-view-right`, `split-change-rows`, `switchView`, `NODES_OLD`, `NODES_NEW`, `localStorage`, `alteryx-diff-view`
- `GRAPH_EDGES` is non-empty in generated output
- All four key links verified by static code analysis
- Ghost node implementation (opacity 0.25, borderDashes [4,4]) confirmed in `_graph_builder.py`
- Dark/light CSS rules cover all new split-view elements
- Overlay view preserves all four existing structural elements unchanged

Status is `human_needed` because split-view rendering, synchronized viewport behavior, focusNode navigation, localStorage persistence, and theme propagation all require an interactive browser session to confirm.

---

_Verified: 2026-03-10_
_Verifier: Claude (gsd-verifier)_
