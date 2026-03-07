# Phase 3: Normalization Layer - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the normalization pipeline stage: a pure Python function that takes `WorkflowDoc` instances from the parser and returns `NormalizedWorkflowDoc` instances with per-node `config_hash` values. Noise (GUIDs, timestamps, attribute ordering, canvas position) is stripped before hashing so Phase 5's differ only sees functional changes. The `--include-positions` flag is a Phase 5/9 concern — this phase stores positions separately and makes them available, but does not filter on them.

</domain>

<decisions>
## Implementation Decisions

### config_hash content
- Hash covers the `<Properties>` subtree only — ToolID and tool type are identity fields for the matcher, not config
- All children of `<Properties>` are included in the hash input after C14N + stripping — no tool-type-specific whitelist
- Hash equality is the authoritative equality signal: if two nodes have identical hashes, Phase 5 skips DeepDiff entirely
- Hash stored as SHA-256 hex digest string (64 chars)

### Stripping scope
- GUID stripping targets known XPath patterns for specific Alteryx-generated fields — no regex over all UUID-shaped values (risk of stripping user-supplied IDs in query configs)
- Timestamp stripping covers ISO 8601 formats only — US-format dates (MM/DD/YYYY) are more likely user-supplied filter expressions and must not be stripped
- TempFile paths replaced with `__TEMPFILE__` placeholder (not empty string, not element removal) — preserves structure for debugging
- All stripping patterns (XPath, timestamp regex, path patterns) live in a single `constants` or `patterns` module — adding new patterns requires one-file change, Phase 3 tests catch regressions

### Normalization API contract
- Normalizer produces `NormalizedNode` (frozen dataclass) wrapping source `AlteryxNode` plus `config_hash: str` and `position` (carried from source)
- Normalizer produces `NormalizedWorkflowDoc` (frozen dataclass) with `.nodes: List[NormalizedNode]` and `.connections` preserved from the source `WorkflowDoc`
- Entry point: `normalize(workflow_doc: WorkflowDoc) -> NormalizedWorkflowDoc` — pure function, no class, no state
- `NormalizedNode` and `NormalizedWorkflowDoc` defined in `models/` alongside Phase 1 dataclasses — all pipeline data contracts in one place

### Position handling
- `NormalizedNode.position` carries forward `AlteryxNode.position` (X/Y) unchanged — the normalizer does not transform positions
- Position is always excluded from `config_hash` — two nodes with identical configs but different canvas positions get identical hashes
- `normalize()` takes no `include_positions` parameter in Phase 3 — the flag is a Phase 5 (differ) and Phase 9 (CLI) concern; the normalizer is flag-agnostic

### Claude's Discretion
- Exact XPath expressions for known Alteryx GUID fields (to be derived from fixture inspection)
- C14N canonicalization call sequence (strip → canonicalize → hash, vs canonicalize → strip → hash)
- Internal helper structure within the normalizer module

</decisions>

<specifics>
## Specific Ideas

- The normalizer is a pure transformation: `WorkflowDoc → NormalizedWorkflowDoc`. No side effects, no I/O, no CLI knowledge.
- The `constants`/`patterns` module is the single place to add new Alteryx-generated metadata patterns as they're discovered in the field
- TempFile placeholder `__TEMPFILE__` is deterministic — both sides of a diff produce the same placeholder, so hashes match correctly

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-normalization-layer*
*Context gathered: 2026-03-01*
