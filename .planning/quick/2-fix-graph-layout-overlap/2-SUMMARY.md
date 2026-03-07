# Quick Task 2 Summary: Fix graph node overlap and layout clutter

**Date:** 2026-03-07
**Commit:** b9667e2

## What was done

Three changes in `src/alteryx_diff/renderers/_graph_builder.py`:

1. **Filter ToolContainer nodes** — Added `CONTAINER_TYPE` constant and a `continue` guard in `build_digraph`. Containers have no data connections so they appeared as isolated floating nodes.

2. **Shorten labels** — Changed `label=node.tool_type` to `label=f"{short_label}\n({tool_id})"` where `short_label = node.tool_type.split(".")[-1]`. Full plugin path still shown in tooltip.

3. **Increase LAYOUT_SCALE** — Changed 800 → 2000 so nodes in the same hierarchical layer have more vertical separation.

## Result

- 105 tests pass (no regressions)
- Graph shows only data-flow nodes, no container clutter
- Node labels are compact and readable
- Same-layer nodes no longer overlap
