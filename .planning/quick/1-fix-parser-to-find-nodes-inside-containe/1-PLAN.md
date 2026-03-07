# Quick Task 1: Fix parser to find nodes inside containers in yxmd workflows

## Problem

The parser used `root.findall("Nodes/Node")` which only finds **direct children** of `<Nodes>`. When a workflow uses ToolContainer nodes, the actual tool nodes are nested under `<ChildNodes>` and were never parsed.

This caused:
- All nodes inside containers missing from the graph
- All connections silently dropped (graph builder skips edges where either endpoint isn't in the graph)
- Report showing 0 tools / 0 connections for container-heavy workflows

## Fix

**File:** `src/alteryx_diff/parser.py` line 142

Change `root.findall("Nodes/Node")` → `root.findall("Nodes//Node")`

The `//` XPath operator performs recursive descent, finding `<Node>` elements at any depth within `<Nodes>` — including those nested inside `<ChildNodes>` of container nodes.

## Tasks

1. **Apply one-line fix** in `parser.py` — change `/` to `//` in findall path
2. **Verify** — run tests (105 pass), regenerate review.html, check JSON output shows child nodes
