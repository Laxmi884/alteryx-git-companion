---
phase: quick-7
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/alteryx_diff/renderers/_graph_builder.py
  - src/alteryx_diff/renderers/graph_renderer.py
autonomous: true
requirements:
  - QUICK-7
must_haves:
  truths:
    - "Added nodes are visibly green in the graph (not pale tint)"
    - "Removed nodes are visibly red in the graph (not pale tint)"
    - "Modified nodes are visibly amber/yellow in the graph (not pale tint)"
    - "Connection-change nodes are visibly blue in the graph (not pale tint)"
    - "Unchanged nodes retain a neutral gray background"
    - "Legend dots in graph controls match the new node background colors"
    - "All existing graph renderer tests still pass"
  artifacts:
    - path: "src/alteryx_diff/renderers/_graph_builder.py"
      provides: "COLOR_MAP and BORDER_COLOR_MAP constants with darker values"
    - path: "src/alteryx_diff/renderers/graph_renderer.py"
      provides: "Updated legend dot colors matching new COLOR_MAP"
  key_links:
    - from: "src/alteryx_diff/renderers/_graph_builder.py"
      to: "src/alteryx_diff/renderers/graph_renderer.py"
      via: "COLOR_MAP import used in test_node_colors_match_diff_status"
      pattern: "COLOR_MAP"
---

<objective>
Darken the graph node background colors so diff status is visually obvious at a glance, and ensure the connection-change status has a distinct, saturated color that clearly communicates "something changed in connections."

Purpose: Current pale pastel backgrounds (#d1fae5, #fee2e2 etc.) are nearly invisible, especially in light mode. Users need to scan the graph and immediately identify changed nodes without squinting at subtle tints.
Output: Updated COLOR_MAP with richer backgrounds, matching BORDER_COLOR_MAP adjustments, and synced legend dots in the template.
</objective>

<execution_context>
@/Users/laxmikantmukkawar/.claude/get-shit-done/workflows/execute-plan.md
@/Users/laxmikantmukkawar/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Darken COLOR_MAP backgrounds and update connection color</name>
  <files>src/alteryx_diff/renderers/_graph_builder.py</files>
  <action>
    Update the COLOR_MAP and BORDER_COLOR_MAP constants in _graph_builder.py with richer, darker values. The new colors must be clearly distinguishable while readable with dark text (#1e293b font set in the template options).

    Replace COLOR_MAP with these saturated values:
    - "added":      "#6ee7b7"   (emerald-300 — rich green, clearly "new")
    - "removed":    "#fca5a5"   (red-300 — clear red, clearly "deleted")
    - "modified":   "#fcd34d"   (amber-300 — warm yellow, clearly "changed")
    - "connection": "#93c5fd"   (blue-300 — clear blue, clearly "wired differently")
    - "unchanged":  "#e2e8f0"   (slate-200 — neutral gray, clearly "no change")

    Replace BORDER_COLOR_MAP with these deeper values that complement the backgrounds:
    - "added":      "#059669"   (keep — emerald-600, good contrast)
    - "removed":    "#dc2626"   (keep — red-600, good contrast)
    - "modified":   "#b45309"   (amber-700 — slightly deeper for contrast on #fcd34d)
    - "connection": "#1d4ed8"   (blue-700 — deeper blue for contrast on #93c5fd)
    - "unchanged":  "#94a3b8"   (slate-400 — keep)

    These are direct constant replacements only. No logic changes.
  </action>
  <verify>
    <automated>cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && python -c "from alteryx_diff.renderers._graph_builder import COLOR_MAP, BORDER_COLOR_MAP; assert COLOR_MAP['added'] == '#6ee7b7'; assert COLOR_MAP['connection'] == '#93c5fd'; print('COLOR_MAP OK')"</automated>
  </verify>
  <done>COLOR_MAP["added"] == "#6ee7b7", COLOR_MAP["connection"] == "#93c5fd"; all other statuses updated to matching richer values</done>
</task>

<task type="auto">
  <name>Task 2: Sync legend dot colors in graph template and run tests</name>
  <files>src/alteryx_diff/renderers/graph_renderer.py</files>
  <action>
    The legend in _GRAPH_FRAGMENT_TEMPLATE uses hardcoded hex colors for the dot spans. Update them to match the new COLOR_MAP backgrounds from Task 1 so the legend accurately reflects what users see on graph nodes.

    Locate the five legend span elements with inline background styles (around line 35-39 of the template string) and replace:
    - Added dot:       background:#059669  ->  background:#6ee7b7
    - Removed dot:     background:#dc2626  ->  background:#fca5a5
    - Modified dot:    background:#d97706  ->  background:#fcd34d
    - Connection dot:  background:#2563eb  ->  background:#93c5fd
    - Unchanged dot:   background:#cbd5e1  ->  background:#e2e8f0

    Also update the dot border colors (add border: 1px solid [BORDER_COLOR] to each dot span) so the legend dots have the same border treatment as graph nodes:
    - Added:      border:1px solid #059669
    - Removed:    border:1px solid #dc2626
    - Modified:   border:1px solid #b45309
    - Connection: border:1px solid #1d4ed8
    - Unchanged:  border:1px solid #94a3b8

    After editing, run the full graph renderer test suite to confirm no regressions.
  </action>
  <verify>
    <automated>cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && uv run pytest tests/test_graph_renderer.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>All 7 graph renderer tests pass; legend dots display #6ee7b7 for added, #fca5a5 for removed, #fcd34d for modified, #93c5fd for connection, #e2e8f0 for unchanged</done>
</task>

</tasks>

<verification>
Run full test suite to catch any unexpected breakage:

```
cd /Users/laxmikantmukkawar/Documents/Projects/alteryx_diff && uv run pytest -x -q 2>&1 | tail -10
```

Expected: all tests pass (105+ passing, 0 failures).
</verification>

<success_criteria>
- COLOR_MAP backgrounds are rich saturated values, not pale pastels
- Connection-change nodes display a clearly distinct blue (#93c5fd background, #1d4ed8 border)
- Legend dots in graph controls match new node background colors exactly
- All existing tests pass without modification
</success_criteria>

<output>
After completion, create `.planning/quick/7-make-graph-colors-darker-and-add-color-f/7-SUMMARY.md`
</output>
