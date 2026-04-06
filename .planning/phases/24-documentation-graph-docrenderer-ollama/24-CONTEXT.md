# Phase 24: DocumentationGraph + DocRenderer + Ollama - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the LangGraph 4-node documentation pipeline (`DocumentationGraph`), the `WorkflowDocumentation` Pydantic output model, a `DocRenderer` that renders it to Markdown and HTML fragment, and wire in provider-agnostic LLM support (Ollama, OpenRouter, and any `BaseChatModel`). No CLI subcommands, no app/FastAPI changes in this phase — those are Phases 25 and 26.

</domain>

<decisions>
## Implementation Decisions

### Output Model

- **D-01:** The documentation output model is named `WorkflowDocumentation` (Pydantic `BaseModel`) — NOT `WorkflowDoc`, which already exists as a frozen dataclass in `alteryx_diff.models.workflow` (the workflow *input* model). Using the same name would cause confusion at import sites.
- **D-02:** `WorkflowDocumentation` structure:
  ```python
  class ToolNote(BaseModel):
      tool_id: int
      tool_type: str
      role: str              # one sentence: what this tool does in context

  class WorkflowDocumentation(BaseModel):
      workflow_name: str
      intent: str            # 2-3 sentences: what the workflow accomplishes
      data_flow: str         # prose: how data moves source-to-sink
      tool_notes: list[ToolNote]
      risks: list[str]       # production concerns: data quality, config gotchas
  ```
- **D-03:** `assumptions` field is explicitly excluded — risk of hallucination on sparse context outweighs value. Can be added later as an additive field if RAGAS evaluation reveals a gap.
- **D-04:** `tool_notes` is a structured list (not prose) — enables clean Markdown table rendering, HTML iteration, and direct RAGAS evaluation per tool annotation.
- **D-05:** `data_flow` is prose (not structured) — connection topology is already machine-readable in `ContextBuilder` output; the LLM's value-add is semantic meaning, which is prose.
- **D-06:** `risks` is a flat `list[str]` — surfaced and scannable for governance use cases.

### Pipeline Topology

- **D-07:** Linear 4-node pipeline: `analyze_topology → annotate_tools → risk_scan → assemble_doc`. No fan-out. Each node is a single LLM call.
- **D-08:** The ARCHITECTURE.md research proposed per-tool fan-out via LangGraph's `Send` API — this is explicitly rejected for Phase 24. `tool_notes` entries are one-sentence roles, not paragraphs; single-call annotation is sufficient quality and matches the success criteria's "4-node pipeline" description.
- **D-09:** LangGraph state type: `TypedDict` only — Pydantic models are not supported in LangGraph v1.x `StateGraph`.
- **D-10:** Single automatic retry on `ValidationError` in the `generate_documentation()` convenience wrapper — wraps the full `ainvoke` call, appends the validation error to state context on retry. This matches the v1.2 key decision: single-pass retry, no critic loop.

### Config Field Strategy

- **D-11:** `ContextBuilder` passes `strip_noise(node.config)` (not raw `node.config`) for each tool's config in `build_from_workflow`. This reuses the existing `alteryx_diff.normalizer._strip.strip_noise` function — no new curation logic introduced in Phase 24.
- **D-12:** Rationale: `strip_noise` already removes timestamps, temp file paths, and GUIDs (variable-content noise). Structural noise (`Plugin` DLL names, `EngineSettings`, `Annotation` keys) is minimal and the LLM naturally ignores it. Full curation is deferred until Phase 27 RAGAS evaluation reveals actual token quality issues.
- **D-13:** This requires `ContextBuilder.build_from_workflow` to call `strip_noise` — a small update to Phase 23's implementation. The existing `build_from_diff` is unchanged (DiffResult already contains post-normalization data).

### LLM Injection Pattern

- **D-14:** Factory function pattern (not a class):
  ```python
  def build_doc_graph(llm: BaseChatModel) -> CompiledGraph: ...

  async def generate_documentation(
      context: dict,
      llm: BaseChatModel,
  ) -> WorkflowDocumentation: ...
  ```
  `generate_documentation()` is the primary public API for Phases 25 and 26 to consume.
- **D-15:** Ollama usage: caller passes `ChatOllama(model="llama3")` — no `use_ollama` flag or special adapter. Phase 24 success criteria SC-3 ("Passing `--ollama`") refers to Phase 25 CLI behavior, not Phase 24's internal API.
- **D-16:** OpenRouter usage: caller passes `ChatOpenAI(model="...", base_url="https://openrouter.ai/api/v1", api_key=...)` — OpenRouter exposes an OpenAI-compatible API; no special adapter needed.
- **D-17:** Add `langchain-openai~=0.3` to `[project.optional-dependencies] llm` in `pyproject.toml` — enables OpenRouter and any OpenAI-compatible endpoint without requiring a separate install.
- **D-18:** The factory function is provider-agnostic — any `BaseChatModel` instance works. No hardcoded provider checks.

### Claude's Discretion

- LangGraph `DocState` TypedDict field names and exact intermediate state structure
- Prompt wording for each of the 4 nodes
- Whether `build_doc_graph` is in `doc_graph.py` or split across files
- `DocRenderer` Markdown template format (section headers, table vs list for tool_notes)
- HTML fragment structure (a `<section>` element per ARCHITECTURE.md pattern)
- mypy/TYPE_CHECKING guards for optional `langchain` imports inside the llm subpackage
- Test fixture design for LangGraph tests (mock LLM vs `pytest.importorskip`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.2 Research (mandatory)
- `.planning/research/STACK.md` — Confirmed library versions (langchain 1.2.14, langgraph 1.1.4, langchain-ollama 1.0.1). Overrides any stale pins elsewhere.
- `.planning/research/ARCHITECTURE.md` — Component map, file paths, data flow, LangGraph async patterns. **Note:** fan-out approach in ARCHITECTURE.md is rejected for Phase 24 (see D-07/D-08). Use linear 4-node topology. Version pins in this file are stale — use STACK.md.

### Phase 23 Context (mandatory)
- `.planning/phases/23-llm-foundation/23-CONTEXT.md` — All D-01 through D-13 decisions are locked. ContextBuilder structure, `require_llm_deps()` pattern, test isolation strategy, CI two-job setup.

### Requirements
- `.planning/REQUIREMENTS.md` §CORE — CORE-03 (DocumentationGraph pipeline), CORE-04 (DocRenderer), EVAL-01 (Ollama support) acceptance criteria

### Existing Code (read before implementing)
- `src/alteryx_diff/llm/context_builder.py` — Phase 23 ContextBuilder (needs `strip_noise` update per D-13)
- `src/alteryx_diff/normalizer/_strip.py` — `strip_noise()` function to reuse in ContextBuilder
- `src/alteryx_diff/renderers/html_renderer.py` — Renderer pattern to follow for DocRenderer
- `src/alteryx_diff/models/workflow.py` — Existing `WorkflowDoc` dataclass (DO NOT reuse name — see D-01)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `strip_noise()` at `src/alteryx_diff/normalizer/_strip.py` — already tested, handles GUID/timestamp/path noise; reuse in `ContextBuilder.build_from_workflow`
- `src/alteryx_diff/renderers/` — all renderers are stateless classes with a render method; `DocRenderer` follows the same pattern
- `tests/llm/` — existing LLM test directory with `pytest.importorskip` pattern from Phase 23; new tests go here

### Integration Points
- `src/alteryx_diff/llm/doc_graph.py` — new file for `build_doc_graph()` and `generate_documentation()`
- `src/alteryx_diff/llm/models.py` — new file for `WorkflowDocumentation` and `ToolNote` Pydantic models
- `src/alteryx_diff/renderers/doc_renderer.py` — new file for `DocRenderer`
- `pyproject.toml` — add `langchain-openai~=0.3` to `[llm]` extras

</code_context>

<specifics>
## Specific Ideas

- User explicitly wants OpenRouter support — covered by provider-agnostic `BaseChatModel` injection + `langchain-openai` in extras. No special code path.
- "Reuse what we have" is the guiding principle: `strip_noise` for config filtering, existing renderer pattern for DocRenderer, existing `tests/llm/` structure for tests.
- `WorkflowDocumentation` is the canonical output model name — chosen specifically to avoid the `WorkflowDoc` collision that would make import sites ambiguous.

</specifics>

<deferred>
## Deferred Ideas

- **Per-tool config curation allowlist** — Filtering `AlteryxNode.config` to semantically meaningful fields. Deferred until Phase 27 RAGAS evaluation reveals whether config noise actually degrades output quality.
- **Fan-out `annotate_tools`** — Parallel per-tool LLM calls via LangGraph Send API. Deferred; may be revisited if single-call annotation quality is insufficient for large workflows (100+ tools).
- **`assumptions` field in `WorkflowDocumentation`** — Excluded due to hallucination risk on sparse context. Additive field — can be added later without schema migration.
- **LangSmith tracing** — Observability for LangGraph execution. Out of scope for v1.2; dev-only option via env var if needed.

</deferred>

---

*Phase: 24-documentation-graph-docrenderer-ollama*
*Context gathered: 2026-04-04*
