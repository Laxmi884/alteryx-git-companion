# Phase 5: Diff Engine - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Given two matched WorkflowDocs (output of Phase 4 node matcher), compute all functional differences — node additions, removals, field-level config modifications with before/after values, and edge changes. Returns a `DiffResult` data structure consumed by downstream reporting phases. Creating reports, displaying output, or formatting diffs for humans are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Modification reporting depth
- Report changes at full nested paths (e.g., `filter.expression`), not just top-level config keys
- String/expression fields are compared as opaque strings — no semantic parsing or normalization
- Unchanged fields are completely omitted from NodeDiff output — only changed fields appear
- List fields are treated as atomic values: if any element differs, the whole list is before/after (no element-level list diff)

### Edge rewiring classification
- No explicit "rewiring" category — rewiring is represented as one removed edge + one added edge (symmetric difference)
- Edge identity (4-tuple) uses normalized/matched tool names from Phase 4, not raw XML names
- Anchor renames are treated as remove + add (same src/dst tools with different anchors = different edge)
- When a tool is removed, all its edges are automatically classified as removed — no separate orphaned edge category

### DiffResult data model
- `DiffResult` is a Python dataclass
- `NodeDiff` (for modified nodes) carries: `tool_name` + `field_diffs` (list of `{path, before, after}`) — no full config snapshot
- `added_nodes` and `removed_nodes` store the full node configuration for downstream use
- `DiffResult` exposes an `is_empty` property (True when no additions, removals, modifications, or edge diffs)

### Null / missing field handling
- Config key present in one workflow but absent in the other → treated as modification with `None` (before=value, after=None or vice versa)
- No distinction between explicit null (key present, value null) and absent key — both treated as `None`
- Fields to exclude from comparison: Claude determines exclusion list based on field semantics (e.g., display-only fields like position, layout metadata, internal rendering hints)
- If node configs fail to compare (corrupt/unparseable value): raise an exception — fail loudly, do not silently emit an error entry

### Claude's Discretion
- Exact exclusion list for non-functional config fields (position, display metadata, etc.)
- Internal structure of `FieldDiff` (whether path is a string or list of segments)
- How to handle DeepDiff output format conversion to the `field_diffs` schema
- Rewiring detection heuristic (if Claude determines it adds value as an optional annotation)

</decisions>

<specifics>
## Specific Ideas

- No specific references — open to standard approaches using DeepDiff for field-level diffing
- The `is_empty` property makes the "functionally identical workflows produce empty result" success criterion explicit and readable

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-diff-engine*
*Context gathered: 2026-03-03*
