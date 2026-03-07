# Quick Task 2: Fix graph node overlap and layout clutter

## Problem

After fixing container parsing, the graph showed all nodes but had:
1. ToolContainer nodes appearing as isolated, unconnected nodes (they're visual groupings)
2. Nodes overlapping at the same hierarchical layer (LAYOUT_SCALE=800 too small for 20+ nodes)
3. Labels showing full plugin paths (e.g. "AlteryxBasePluginsGui.Filter.Filter") making nodes very wide

## Fix

**File:** `src/alteryx_diff/renderers/_graph_builder.py`

1. Add `CONTAINER_TYPE` constant and skip containers in `build_digraph`
2. Shorten labels: `node.tool_type.split(".")[-1]` + tool ID (e.g. "Filter (10)")
3. Increase `LAYOUT_SCALE` from 800 to 2000
