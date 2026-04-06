# Phase 27: RAGAS Evaluation Harness - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

A standalone evaluation script at `tests/eval/ragas_eval.py` that:
1. Runs the full parse → normalize → ContextBuilder → `generate_documentation()` pipeline on reference workflows
2. Feeds ContextBuilder output as `retrieved_contexts` into RAGAS
3. Scores `faithfulness` and `answer_relevancy` for each sample and prints results

No new LLM pipeline logic. No CI integration. No new app features. Consumes Phase 23/24/25 APIs as-is.

</domain>

<decisions>
## Implementation Decisions

### Fixtures

- **D-01:** Reference workflows are defined as **in-memory XML bytes** (same pattern as `tests/fixtures/pipeline.py`) — no `.yxmd` files committed to disk. 2-3 minimal but representative workflow bytes defined in the script or a `tests/eval/fixtures.py` module.

- **D-02:** No `ground_truth` strings required. `faithfulness` and `answer_relevancy` both operate without ground truth — this avoids fixture maintenance overhead and matches the architecture (ContextBuilder is deterministic, not a fuzzy retriever).

### What Passes the LLM Boundary

- **D-03:** `retrieved_contexts` = **ContextBuilder output** (the structured JSON dict serialized to strings), NOT raw XML. The eval mirrors production exactly: `.yxmd bytes → parser → WorkflowDoc → ContextBuilder → context dict → LLM`. Raw XML never crosses the LLM boundary in eval any more than it does in production.

### LLM Provider

- **D-04:** Two env vars, same `provider:model_name` format as Phase 25:
  - `ACD_LLM_MODEL` — the documentation-generation LLM (subject of evaluation)
  - `RAGAS_CRITIC_MODEL` — the RAGAS critic LLM (faithfulness/relevancy judge); defaults to `ACD_LLM_MODEL` if not set

  Using a stronger, independent model as the critic avoids self-grading bias (a model judging its own output). OpenRouter makes this zero-friction — one `OPENROUTER_API_KEY`, just swap the model name:
  ```
  ACD_LLM_MODEL=openrouter:mistralai/mistral-7b-instruct
  RAGAS_CRITIC_MODEL=openrouter:openai/gpt-4o
  ```
  Falls back gracefully to single-model mode (e.g., fully offline Ollama) when `RAGAS_CRITIC_MODEL` is not set.

- **D-05:** Script prints a clear error and exits non-zero if `ACD_LLM_MODEL` is not set, with an example. Includes a note that `RAGAS_CRITIC_MODEL` is optional but recommended for independent evaluation.

### Metrics

- **D-06:** `faithfulness` + `answer_relevancy` only. `context_recall` and `context_precision` are dropped — they require ground truth and are designed for fuzzy RAG retrieval systems, not a deterministic context builder like ContextBuilder.

- **D-07:** Passing threshold is `>=0.8` for faithfulness (per EVAL-02 success criteria). Script prints per-sample scores and a summary. Does NOT fail the process on threshold miss — it reports the score and the threshold, leaving the developer to act.

### Script Ergonomics

- **D-08:** Entry point: `python tests/eval/ragas_eval.py` — standalone script, not a pytest file. Can be run without `pytest` installed in the eval environment.

- **D-09:** Script has a docstring (or inline README block) documenting: how to run, what `ACD_LLM_MODEL` to set, what the `>=0.8` threshold means, and how to add a new sample (add a fixture + sample dict entry).

### Claude's Discretion

- RAGAS v0.4 Dataset/EvaluationDataset API specifics (exact class names and evaluate() call signature)
- Whether the RAGAS critic LLM is injected via `langchain_openai`/`langchain_ollama` wrappers or RAGAS's own LLM config
- Output format (table vs plain print vs JSON)
- Whether fixtures live in `ragas_eval.py` directly or split into `tests/eval/fixtures.py`
- Whether `require_llm_deps()` is called at script top or inside `if __name__ == "__main__"`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### LLM pipeline APIs (consumed by eval)
- `src/alteryx_diff/llm/context_builder.py` — `ContextBuilder.build_from_workflow()` — produces the `retrieved_contexts` dict
- `src/alteryx_diff/llm/doc_graph.py` — `generate_documentation(context, llm)` — generates the documentation being evaluated
- `src/alteryx_diff/llm/__init__.py` — `require_llm_deps()` — call before importing LLM code

### Existing test patterns to follow
- `tests/fixtures/pipeline.py` — in-memory XML bytes fixture pattern (D-01)
- `tests/llm/conftest.py` — LLM test fixture patterns, `WorkflowDocumentation` sample
- `tests/llm/test_doc_graph.py` — how `generate_documentation()` is invoked in tests

### Requirements
- `.planning/REQUIREMENTS.md` §EVAL — EVAL-02 acceptance criteria (exact success criteria for this phase)

### Prior phase context
- `.planning/phases/23-llm-foundation/23-CONTEXT.md` — `require_llm_deps()`, ContextBuilder design
- `.planning/phases/24-documentation-graph-docrenderer-ollama/24-CONTEXT.md` — `generate_documentation()`, WorkflowDocumentation model
- `.planning/phases/25-cli-integration/25-CONTEXT.md` — `ACD_LLM_MODEL` env var pattern, provider resolution

### Dependency
- `pyproject.toml` `[project.optional-dependencies] llm` — `ragas~=0.4` already present; no new deps needed

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ContextBuilder.build_from_workflow(doc: WorkflowDoc) -> dict` — returns the structured context dict; serialize values to strings for RAGAS `contexts` field
- `generate_documentation(context, llm)` — async; bridge via `asyncio.run()` (same pattern as CLI)
- `require_llm_deps()` — import guard; call at script top to give a clear error if `[llm]` extras not installed
- `tests/fixtures/pipeline.py` — `MINIMAL_YXMD_A`/`B` bytes — reuse or extend for eval fixtures

### Established Patterns
- Async bridge: `asyncio.run()` — used throughout CLI and LLM tests
- Provider construction: Phase 25 `--model provider:name` prefix-split pattern → builds `BaseChatModel` instance
- In-memory workflow parsing: `tmp_path` + bytes write in tests; eval can use `io.BytesIO` or `tmp_path`-equivalent

### Integration Points
- `tests/eval/` — new directory; `ragas_eval.py` is the only file needed (plus optional `fixtures.py`)
- No changes to `src/` — pure consumer of existing APIs

</code_context>

<specifics>
## Specific Ideas

- RAGAS `retrieved_contexts` = ContextBuilder output serialized as strings (values of the context dict), not the raw XML — mirrors production architecture exactly
- `faithfulness` + `answer_relevancy` without ground truth — appropriate for a deterministic context builder; `context_recall`/`context_precision` are the wrong tool here
- `ACD_LLM_MODEL` env var drives both the documentation LLM and the RAGAS critic — zero extra config for the developer

</specifics>

<deferred>
## Deferred Ideas

- **`context_recall` / `context_precision`** — dropped from this phase; requires ground_truth and is designed for fuzzy retrieval, not deterministic ContextBuilder. Revisit if architecture evolves to include vector store retrieval.
- **CI integration** — running ragas_eval.py in GitHub Actions would require a live LLM. Dev-only for now; CI gate is a future phase concern.
- **Regression thresholds as test failures** — making `pytest` fail if faithfulness drops below 0.8. Deferred; script reports scores, human decides action.

</deferred>

---

*Phase: 27-ragas-evaluation-harness*
*Context gathered: 2026-04-06*
