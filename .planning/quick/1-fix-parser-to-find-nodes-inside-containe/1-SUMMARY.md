# Quick Task 1 Summary: Fix parser to find nodes inside containers

**Date:** 2026-03-07
**Commit:** b30bb25

## What was done

Fixed a one-line bug in `src/alteryx_diff/parser.py` where `root.findall("Nodes/Node")` only found direct children of `<Nodes>`, missing all tool nodes nested inside ToolContainer `<ChildNodes>` elements.

**Change:** `root.findall("Nodes/Node")` → `root.findall("Nodes//Node")`

## Root cause

Alteryx workflows with containers use this XML structure:
```xml
<Nodes>
  <Node ToolID="24">  <!-- ToolContainer -->
    <ChildNodes>
      <Node ToolID="1">  <!-- actual tool — was being skipped -->
      <Node ToolID="2">  <!-- actual tool — was being skipped -->
    </ChildNodes>
  </Node>
</Nodes>
```

The `/` XPath separator only descends one level. The `//` separator recurses into all descendants.

## Result

- 105 tests pass (no regressions)
- Nodes inside containers now appear in graph and diff report
- Connections between those nodes now render correctly
