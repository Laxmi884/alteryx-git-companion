# Phase 23: LLM Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 23-llm-foundation
**Areas discussed:** Tools context granularity, Topology field structure, Diff changes structure, Test isolation strategy

---

## Tools Context Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Type + name only | Minimal token use, but too sparse for documentation generation | |
| Full config dict | Pass full AlteryxNode.config dict; Phase 24 decides what to include in prompt | ✓ |
| Curated key fields only | Filter to 'interesting' fields; requires curation logic in Phase 23 | |

**User's choice:** Full config dict
**Notes:** User raised that "type + name only" is insufficient if this feeds LLM documentation generation — the LLM needs config detail to say anything meaningful about what a tool does. Curation deferred to Phase 24's prompt engineering layer.

---

## Topology Field Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Connection list only | Raw [{src, dst, anchors}] list | |
| Connection list + graph metadata | Connections + source_tools, sink_tools, branch_points | ✓ |
| Summary stats only | Counts only — loses structural information | |

**User's choice:** Connection list + graph metadata
**Notes:** User asked whether a graph representation would be more LLM-friendly and about LightRAG. Clarified that LLMs consume text not graph objects — "graph representation" means a text encoding, which is Phase 24's prompt engineering concern. Graph metadata (sources/sinks/branches) is precomputed cheaply in Phase 23 using networkx (already a core dep). LightRAG identified as wrong fit for single-workflow context building (see Deferred Ideas).

---

## Diff Changes Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Per-tool summaries + field diffs | Categorized added/removed/modified with field_diffs per modified tool | ✓ |
| Counts only | Too sparse for narrative generation | |

**User's choice:** Per-tool summaries + field diffs
**Notes:** Counts alone give the LLM nothing to work with for a change narrative. Full field_diffs (what changed from what to what) are needed.

---

## Test Isolation Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| pytest.importorskip per test file | Skip llm tests when extras absent; two CI jobs | ✓ |
| Always install [llm] in CI | Single job; never verifies zero-import guarantee | |

**User's choice:** pytest.importorskip + two CI jobs (core / llm)
**Notes:** The "always install" approach would never verify CORE-01 (that core CLI works with zero LLM imports). Two-job CI matrix directly validates the success criteria.

---

## Claude's Discretion

- ContextBuilder class structure (static methods vs plain functions)
- mypy handling of optional imports
- Exact `summary` field content

## Deferred Ideas

- LightRAG / graph-based RAG — wrong fit for v1.2 single-workflow use case; possible v2+ if corpora grow
- Config field curation — deferred to Phase 24 prompt engineering
