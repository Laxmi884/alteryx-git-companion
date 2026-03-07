# Phase 4: Node Matcher - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement a two-pass node matching algorithm that correctly pairs tool instances between two workflow versions — even when Alteryx regenerates all ToolIDs. Pass 1: exact ToolID lookup. Pass 2: Hungarian algorithm fallback on unmatched leftovers. Output: matched pairs, unmatched-old (removals), unmatched-new (additions). Diff computation and report rendering are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Cost function weighting
- Tool type is a hard block: a cost matrix is built per-type — only same-type tools are compared against each other. Cross-type pairs never appear in the matrix.
- Within same-type: type match is guaranteed (enforced at construction), so cost is computed from position proximity + config hash similarity only.
- Exact sub-weights between position and config hash: Claude's discretion.
- Position proximity uses normalized canvas distance — normalize (x, y) by workflow canvas bounds so absolute pixel scale doesn't skew results for large vs small workflows.

### Threshold + rejection behavior
- Threshold is hardcoded at 0.8 (no configurable parameter).
- After Hungarian assigns pairs, any pair with cost > 0.8 is rejected: the old node goes to removals, the new node goes to additions.
- Threshold applies at the pair level (per assigned pair, not per-tool independently).
- No low-confidence annotation — rejected pairs are simply unmatched. Callers do not see ambiguous matches.

### Matcher output contract
- Function signature: accepts `list[NormalizedNode]` (old) and `list[NormalizedNode]` (new) — Phase 3 output is the direct input. Matcher never touches raw XML.
- Returns a named tuple or dataclass: `MatchResult(matched: list[tuple[NormalizedNode, NormalizedNode]], removed: list[NormalizedNode], added: list[NormalizedNode])`.
- Each matched pair contains the full `(old_node, new_node)` NormalizedNode objects — no ID-only tuples.
- No `match_source` annotation. Which pass produced a match is an internal implementation detail, not surfaced to callers.

### Partial regeneration handling
- Pass 1 consumes exact ToolID matches. Only the leftover unmatched sets (old-only, new-only) feed into the Hungarian pass.
- scipy's `linear_sum_assignment` handles non-square matrices natively — no dummy row/column padding needed.
- If either unmatched set is empty after pass 1, skip the Hungarian pass entirely (early exit).
- Config hash similarity uses the full config hash from the `NormalizedNode` produced by Phase 3 — no re-hashing or stripping of connection data.

### Claude's Discretion
- Exact weights for position proximity vs config hash similarity within the per-type cost function.
- Specific normalization formula for canvas distance.
- Internal data structures (numpy array shape, index mapping, etc.) used to build and query the cost matrix.

</decisions>

<specifics>
## Specific Ideas

No specific references — open to standard approaches within the decided constraints.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-node-matcher*
*Context gathered: 2026-03-01*
