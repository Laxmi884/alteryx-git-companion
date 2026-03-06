---
phase: 08-visual-graph
plan: "01"
subsystem: rendering
tags: [vis-network, networkx, graph, digraph, layout, package-data, importlib-resources]

# Dependency graph
requires:
  - phase: 05-diff-engine
    provides: "DiffResult, NodeDiff, EdgeDiff types consumed by build_digraph()"
  - phase: 01-scaffold-and-data-models
    provides: "AlteryxNode, AlteryxConnection, ToolID types"
provides:
  - "vis-network 9.1.4 standalone UMD bundle (702KB) at src/alteryx_diff/static/vis-network.min.js"
  - "build_digraph(): DiffResult -> nx.DiGraph[int] with diff_status node attributes"
  - "hierarchical_positions(): topological layout with cycle back-edge removal"
  - "canvas_positions(): raw Alteryx X/Y coords keyed by tool_id"
  - "load_vis_js(): importlib.resources loader with filesystem fallback"
affects:
  - 08-visual-graph-plan-02  # GraphRenderer uses all four functions

# Tech tracking
tech-stack:
  added:
    - "vis-network 9.1.4 (vendored UMD bundle, no npm dependency)"
  patterns:
    - "Vendored JS bundle in src/alteryx_diff/static/ with [tool.uv_build] package-data config"
    - "importlib.resources primary + filesystem fallback for package data access"
    - "networkx.* mypy override added (no stubs, follows deepdiff pattern)"

key-files:
  created:
    - "src/alteryx_diff/static/vis-network.min.js"
    - "src/alteryx_diff/renderers/_graph_builder.py"
  modified:
    - "pyproject.toml"

key-decisions:
  - "[08-01]: vis-network 9.1.4 vendored as standalone UMD bundle (702KB) — no npm/CDN dependency, single-file HTML output remains self-contained"
  - "[08-01]: networkx.* mypy override added to pyproject.toml — networkx has no type stubs; follows same pattern as deepdiff override (ignore_missing_imports)"
  - "[08-01]: load_vis_js() uses importlib.resources with filesystem fallback — editable installs and built packages both work without code change"
  - "[08-01]: COLOR_MAP is a module-level constant in _graph_builder.py — single source of truth for diff status colors used by both Python (graph builder) and JS template (Plan 02)"
  - "[08-01]: LAYOUT_SCALE = 800 — pixel scale factor for multipartite_layout output to vis-network viewport coordinates"

patterns-established:
  - "Static asset vendoring: bundle goes in src/alteryx_diff/static/, declared in [tool.uv_build] package-data"
  - "Graph builder is a pure data layer: no rendering logic, no Jinja2 — all consumed by graph_renderer.py in Plan 02"
  - "Cycle handling pattern: iterative back-edge removal via nx.find_cycle() before topological_generations()"

requirements-completed:
  - GRPH-02
  - GRPH-03

# Metrics
duration: 4min
completed: 2026-03-06
---

# Phase 8 Plan 01: Visual Graph — Bundle and Graph Builder Summary

**vis-network 9.1.4 UMD bundle vendored (702KB) and DiGraph data-layer implemented with hierarchical layout, canvas position mapping, and importlib.resources loader**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-06T20:04:34Z
- **Completed:** 2026-03-06T20:08:08Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Vendored vis-network 9.1.4 standalone UMD bundle (702,055 bytes) to `src/alteryx_diff/static/` and configured `[tool.uv_build]` package-data in `pyproject.toml`
- Implemented `build_digraph()` mapping DiffResult to `nx.DiGraph[int]` with priority-ordered diff status (added > removed > modified > connection > unchanged) and COLOR_MAP node attributes
- Implemented `hierarchical_positions()` with DAG cycle back-edge removal, topological layer assignment, and LAYOUT_SCALE-normalized multipartite layout
- Implemented `canvas_positions()` returning raw Alteryx X/Y coordinates (new overrides old for added/modified nodes)
- Implemented `load_vis_js()` with importlib.resources primary path and filesystem fallback for development environments
- All four functions pass ruff + mypy --strict; imports verified clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Vendor vis-network UMD bundle and configure package data** - `9628dc7` (chore)
2. **Task 2: Implement _graph_builder.py** - `890adda` (feat)

## Files Created/Modified

- `src/alteryx_diff/static/vis-network.min.js` - vis-network 9.1.4 standalone UMD bundle (702KB), accessible via importlib.resources
- `src/alteryx_diff/renderers/_graph_builder.py` - DiGraph construction + hierarchical/canvas position helpers + vis-network JS loader
- `pyproject.toml` - Added `[tool.uv_build] package-data` for static/*.js and `[[tool.mypy.overrides]]` for networkx.* (no stubs)

## Decisions Made

- networkx has no type stubs in Python ecosystem; added `[[tool.mypy.overrides]] module = ["networkx.*"] ignore_missing_imports = true` to pyproject.toml following the same pattern used for deepdiff
- vis-network vendored as standalone UMD (not ESM or CommonJS) — standalone bundles have no external dependencies, enabling inline embedding in single-file HTML output
- ruff-format auto-reformatted `_graph_builder.py` during pre-commit (line length adjustment on `raw_pos` assignment); staged and committed the reformatted version as part of the same task commit

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added networkx.* mypy override to pyproject.toml**
- **Found during:** Task 2 (_graph_builder.py implementation)
- **Issue:** networkx has no type stubs; mypy --strict reports `[import-untyped]` error, blocking mypy compliance
- **Fix:** Added `[[tool.mypy.overrides]] module = ["networkx.*"] ignore_missing_imports = true` to pyproject.toml, following existing deepdiff pattern
- **Files modified:** `pyproject.toml`
- **Verification:** `venv/bin/mypy src/alteryx_diff/renderers/_graph_builder.py` → "Success: no issues found"
- **Committed in:** `890adda` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical config)
**Impact on plan:** Necessary for mypy --strict compliance. No scope creep — deepdiff already had this pattern, networkx needed the same treatment.

## Issues Encountered

- ruff-format reformatted `_graph_builder.py` during pre-commit hook run, requiring re-staging and re-committing. The reformatted version is identical in behavior (only whitespace adjusted on the `raw_pos` line).

## User Setup Required

None — no external service configuration required. vis-network is vendored; no CDN or npm needed.

## Next Phase Readiness

- Plan 02 (GraphRenderer): all four helper functions are callable and verified — `build_digraph()`, `hierarchical_positions()`, `canvas_positions()`, `load_vis_js()` are ready to be consumed by `graph_renderer.py`
- COLOR_MAP constants are in `_graph_builder.py` — Plan 02 template can reference them or duplicate for JS-side coloring
- No blockers

## Self-Check: PASSED

- FOUND: src/alteryx_diff/static/vis-network.min.js
- FOUND: src/alteryx_diff/renderers/_graph_builder.py
- FOUND: .planning/phases/08-visual-graph/08-01-SUMMARY.md
- FOUND commit: 9628dc7 (chore: vendor vis-network bundle)
- FOUND commit: 890adda (feat: _graph_builder.py)

---
*Phase: 08-visual-graph*
*Completed: 2026-03-06*
