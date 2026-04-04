# Phase 23: LLM Foundation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire `[llm]` optional extras into `pyproject.toml` and implement `ContextBuilder` that transforms `WorkflowDoc`/`DiffResult` dataclasses into token-efficient JSON dicts for LLM consumption. No LLM pipeline, no CLI commands, no app changes in this phase — purely the package extras gate and the data transformation layer.

</domain>

<decisions>
## Implementation Decisions

### Package Extras

- **D-01:** Add `[project.optional-dependencies] llm = [...]` to `pyproject.toml` with pins: `langchain~=1.2`, `langgraph~=1.1`, `langchain-ollama~=1.0`, `ragas~=0.4`, `tiktoken>=0.7`
- **D-02:** The `langchain~=0.3` pin in ARCHITECTURE.md is stale — use `~=1.2` as confirmed in STACK.md research (langchain 1.2.14 is current production-stable)

### Optional Import Guard

- **D-03:** `llm/__init__.py` exposes `require_llm_deps()` — raises `ImportError` with a clear install hint (`pip install alteryx-diff[llm]`) when extras absent, returns cleanly when present
- **D-04:** The existing codebase must have zero top-level imports from `alteryx_diff.llm.*` — this is the #1 risk (noted in STATE.md); any accidental top-level import will break the 252-test suite for users without extras

### ContextBuilder — build_from_workflow

- **D-05:** Output includes `workflow_name`, `tool_count`, `tools`, `connections`, `topology` keys (as per success criteria SC-4)
- **D-06:** Each entry in `tools[]` includes the full `AlteryxNode.config` dict (no field curation in Phase 23) — Phase 24 handles prompt engineering and decides what config fields to include in the LLM prompt
- **D-07:** `topology` contains both a connection list and precomputed graph metadata:
  ```
  topology: {
    connections: [{src_tool, src_anchor, dst_tool, dst_anchor}],
    source_tools: [tool_ids with no inputs],
    sink_tools: [tool_ids with no outputs],
    branch_points: [tool_ids with out-degree > 1]
  }
  ```
  Rationale: graph metadata is cheap to compute here (networkx already in deps) and saves Phase 24 from re-deriving it from the edge list every time

### ContextBuilder — build_from_diff

- **D-08:** Output includes `summary` and `changes` keys (as per success criteria SC-4)
- **D-09:** `changes` is structured by change category with per-tool field diffs:
  ```
  changes: {
    added: [{tool_id, tool_type}],
    removed: [{tool_id, tool_type}],
    modified: [{tool_id, tool_type, field_diffs: {field: [old_val, new_val]}}],
    edge_changes: [{change_type: 'added'|'removed', src_tool, dst_tool, anchors}]
  }
  ```
  Rationale: Phase 24 needs the substance of what changed (not just counts) to generate a meaningful change narrative
- **D-10:** `summary` contains high-level counts: `{added_count, removed_count, modified_count, edge_change_count}`

### Test Isolation Strategy

- **D-11:** `pytest.importorskip('langchain')` at the top of every `tests/llm/` test file — skips automatically when `[llm]` extras are not installed
- **D-12:** CI runs two jobs: `core` (bare `pip install alteryx-diff`, must pass 252 existing tests) and `llm` (`pip install "alteryx-diff[llm]"`, runs llm tests) — this directly verifies CORE-01 (zero-import guarantee)
- **D-13:** LLM tests live under `tests/llm/` (new subdirectory), not mixed with existing tests

### Claude's Discretion

- `llm/context_builder.py` module structure and class design
- Whether `ContextBuilder` is a class with static methods or plain functions — either works
- mypy handling of optional imports (TYPE_CHECKING guard pattern recommended)
- Exact `summary` field content beyond counts (e.g., workflow name inclusion)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.2 Research (mandatory)
- `.planning/research/STACK.md` — Confirmed library versions (langchain 1.2.14, langgraph 1.1.4, etc.) and version rationale. Overrides stale pins in ARCHITECTURE.md.
- `.planning/research/ARCHITECTURE.md` — Component map, file paths, data flow diagram, LangGraph async patterns. Note: version pins are stale — use STACK.md versions instead.
- `.planning/research/PITFALLS.md` — General project pitfalls (context for why the LLM boundary constraint exists)

### Requirements
- `.planning/REQUIREMENTS.md` §CORE — CORE-01 and CORE-02 acceptance criteria (the exact success criteria for this phase)

### No external specs — requirements fully captured in decisions above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/alteryx_diff/models/workflow.py` — `WorkflowDoc` (filepath, nodes tuple, connections tuple) and `AlteryxNode` (tool_id, tool_type, x, y, config dict) — these are the inputs to `build_from_workflow`
- `src/alteryx_diff/models/diff.py` — `DiffResult` (added_nodes, removed_nodes, modified_nodes, edge_diffs), `NodeDiff` (tool_id, field_diffs dict), `EdgeDiff` (change_type, src/dst) — inputs to `build_from_diff`
- `networkx` is already in core deps — can compute source/sink/branch_point metrics without adding dependencies

### Established Patterns
- Frozen dataclasses with `slots=True` throughout models — ContextBuilder output is plain dicts (not dataclasses), which is appropriate here
- `from __future__ import annotations` used throughout — use the same
- `src/alteryx_diff/` layout with subpackages — new `llm/` subpackage follows the same pattern

### Integration Points
- `llm/__init__.py` must NOT import langchain/langgraph at module level — use deferred import inside `require_llm_deps()` only
- No changes to existing `pipeline.py`, `cli.py`, or any renderer — Phase 23 adds new code only
- `pyproject.toml` gains `[project.optional-dependencies]` section (currently has none)

</code_context>

<specifics>
## Specific Ideas

- User confirmed LightRAG is out of scope for Phase 23 (graph-based RAG for large corpus retrieval — wrong fit for single-workflow context building). Worth noting for v2+ if workflow corpora become large enough for retrieval.
- Topology graph metadata (`source_tools`, `sink_tools`, `branch_points`) is precomputed in `ContextBuilder` using networkx DiGraph — cheap here, saves Phase 24 from recomputing

</specifics>

<deferred>
## Deferred Ideas

- **LightRAG / graph-based RAG** — User asked about this during discussion. Relevant if Phase 27+ expands to handle large workflow corpora where subgraph retrieval is needed. Not applicable for single-workflow context building in v1.2.
- **Curated config field filtering** — Filtering `AlteryxNode.config` to "interesting" fields for token efficiency. Deferred to Phase 24 (prompt engineering layer); Phase 23 passes full config dict.

</deferred>

---

*Phase: 23-llm-foundation*
*Context gathered: 2026-04-04*
