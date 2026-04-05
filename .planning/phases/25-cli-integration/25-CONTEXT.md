# Phase 25: CLI Integration - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Add two new CLI entry points to `alteryx-diff`:
1. `document` subcommand — parses a single workflow, builds context, calls the LLM pipeline, and writes a Markdown intent doc next to the workflow file
2. `--doc` flag on the existing `diff` command — calls the LLM pipeline with the diff context and embeds an AI change narrative section in the HTML diff report

No FastAPI/app changes in this phase — that is Phase 26. No new LLM pipeline logic — consume the Phase 24 APIs.

</domain>

<decisions>
## Implementation Decisions

### LLM Provider Flags

- **D-01:** Single `--model provider:model_name` flag for provider+model selection:
  ```
  --model ollama:llama3
  --model openrouter:mistralai/mistral-7b-instruct
  --model openai:gpt-4o
  ```
  CLI parses the prefix to build the right `BaseChatModel` instance. Scales to any future provider without new flags.

- **D-02:** API keys come from env vars only (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`) — never from CLI flags. Keys in shell history are a security smell.

- **D-03:** Optional `--base-url` flag for non-default Ollama host or other OpenAI-compatible endpoints:
  ```
  --model ollama:llama3 --base-url http://gpu-server:11434
  ```

- **D-04:** Fallback resolution order when `--model` is not given:
  1. `ACD_LLM_MODEL` env var (useful for CI pipelines)
  2. `config_store` (persisted model preference — Phase 26 settings panel writes this)
  3. Error with a clear message: "No LLM model configured. Use --model or set ACD_LLM_MODEL."

- **D-05:** `config_store` stores the model preference string (e.g., `ollama:llama3`). API keys are stored in **keyring** (same pattern as GitHub/GitLab PATs from Phase 16) — never in config files to avoid accidental git commit.

- **D-06:** This design serves both CLI users (`--model` flag or env var) and the companion app (Phase 26 settings panel writes to `config_store`/keyring; app backend reads from the same source). Env file is NOT used — `config_store` + keyring is the right persistence layer given existing patterns.

### `document` Subcommand

- **D-07:** Uses `ContextBuilder.build_from_workflow()` → `generate_documentation()` → `DocRenderer.write_markdown()` pipeline (all Phase 23/24 APIs).

- **D-08:** Default output: `{workflow_dir}/{stem}-doc.md` — next to the `.yxmd` input file, regardless of CWD. Rationale: doc stays co-located with the workflow it describes; consistent with the companion app's project-directory model.

- **D-09:** `--output` flag overrides the default path.

- **D-10:** Missing `[llm]` extras: `require_llm_deps()` is called first — raises `ImportError` with install hint (`pip install alteryx-diff[llm]`), exits non-zero. This satisfies CLI-01 success criteria directly.

- **D-11:** Progress: Rich spinner on stderr (`Generating documentation...`), matching the existing `diff` command pattern. Suppressed by `--quiet`.

### `diff --doc` Flag

- **D-12:** `--doc` is opt-in on the existing `diff` command — absent by default, so zero regression risk for existing callers.

- **D-13:** Generates a **change narrative only** (not a workflow intent doc). Uses `ContextBuilder.build_from_diff()` for context — this returns `{summary, changes}`, a different shape from `build_from_workflow`.

- **D-14:** Requires a **new generation function** (e.g., `generate_change_narrative(context, llm)`) in `doc_graph.py` — the existing `generate_documentation()` is designed for workflow context shape and `WorkflowDocumentation` output model. The change narrative needs its own prompt and likely a simpler output model (prose narrative string rather than structured fields).

- **D-15:** `HTMLRenderer.render()` needs a new optional `doc_fragment: str = ""` kwarg (same pattern as existing `graph_html` and `metadata` kwargs). The `DocRenderer.to_html_fragment()` output is passed as this kwarg. When empty (no `--doc`), HTML report is unchanged.

- **D-16:** Progress: same Rich spinner pattern as `document` subcommand. `--quiet` suppresses it.

### asyncio Bridge

- **D-17:** `generate_documentation()` and `generate_change_narrative()` are both async. CLI bridges via `asyncio.run()` — consistent with `asyncio.run()` usage in existing LLM tests (from STATE.md notes).

### Claude's Discretion

- Exact `generate_change_narrative()` output model design (simple `ChangeNarrative` with `narrative: str` and optional `risks: list[str]`, or just a plain string)
- Prompt wording for the change narrative nodes
- `--model` string parsing implementation detail (prefix split on first `:`)
- HTML template changes for the narrative section (section heading, placement relative to graph)
- Test structure for the new CLI commands (mock LLM, `pytest.importorskip`, `CliRunner`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 23 & 24 Context (mandatory — these APIs are consumed in Phase 25)
- `.planning/phases/23-llm-foundation/23-CONTEXT.md` — `require_llm_deps()`, ContextBuilder, test isolation strategy, CI two-job setup
- `.planning/phases/24-documentation-graph-docrenderer-ollama/24-CONTEXT.md` — `generate_documentation()`, `WorkflowDocumentation`, `DocRenderer`, provider-agnostic `BaseChatModel` injection

### Requirements
- `.planning/REQUIREMENTS.md` §CLI — CLI-01 and CLI-02 acceptance criteria (exact success criteria for this phase)

### Existing Code (read before implementing)
- `src/alteryx_diff/cli.py` — existing `diff` command; `document` subcommand and `--doc` flag add to this file
- `src/alteryx_diff/llm/doc_graph.py` — `generate_documentation()` and `build_doc_graph()` — new `generate_change_narrative()` goes here
- `src/alteryx_diff/llm/context_builder.py` — `build_from_workflow()` and `build_from_diff()` — both consumed in Phase 25
- `src/alteryx_diff/renderers/html_renderer.py` — `HTMLRenderer.render()` — needs `doc_fragment` kwarg added
- `src/alteryx_diff/renderers/doc_renderer.py` — `DocRenderer.to_html_fragment()` and `write_markdown()` — consumed in Phase 25

### v1.2 Research
- `.planning/research/STACK.md` — confirmed library versions; relevant for any new langchain-related code

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `typer` app already set up in `cli.py` with `app = typer.Typer(no_args_is_help=True)` — `document` is a new `@app.command()`
- `_err_console = Console(stderr=True)` already in `cli.py` — reuse for spinner in `document` and `--doc`
- `require_llm_deps()` in `llm/__init__.py` — call at top of both new CLI paths
- `DocRenderer.write_markdown()` already writes to a `Path` — direct use in `document` subcommand
- `DocRenderer.to_html_fragment()` returns an HTML string — pass as `doc_fragment` to `HTMLRenderer.render()`
- keyring already a dependency (Phase 16 PAT storage) — reuse for API key storage

### Established Patterns
- Async bridge: `asyncio.run()` — consistent with LLM test pattern in `tests/llm/`
- Error handling: `typer.echo(f"Error: ...", err=True)` + `raise typer.Exit(code=2)` — match existing `diff` error pattern
- Spinner: `with _err_console.status("...", spinner="dots"):` — exact pattern from `diff` command
- Optional kwargs with `""` default: `graph_html=""`, `metadata=None` in `HTMLRenderer.render()` — follow same pattern for `doc_fragment=""`

### Integration Points
- `cli.py`: new `@app.command() def document(...)` + new `doc: bool` option on `diff()`
- `doc_graph.py`: new `generate_change_narrative(context, llm)` async function
- `html_renderer.py`: add `doc_fragment: str = ""` kwarg, inject fragment into HTML template when non-empty
- `pyproject.toml` `[project.optional-dependencies] llm`: no new packages needed for Phase 25 (all provider libs already added in Phase 23/24)

</code_context>

<specifics>
## Specific Ideas

- `--model provider:model_name` flag is the single UX for provider selection — designed with OpenRouter in mind (`openrouter:mistralai/mistral-7b-instruct` handles the slash-in-model-name case cleanly)
- Phase 26 settings panel will write the model preference to `config_store` and API key to keyring — Phase 25 CLI reads from the same sources as fallback, making the two phases share one config contract
- `config_store` + keyring (not a `.env` file) is the persistence choice — avoids accidental key commits, consistent with existing Phase 16 PAT storage pattern

</specifics>

<deferred>
## Deferred Ideas

- **Streaming token output** — Streaming LLM tokens to terminal during `document` generation. Deferred; spinner is sufficient for v1.2. Revisit if users report the wait feels too long.
- **Stage-by-stage progress** — Printing each LangGraph node completion (`✓ Analysing topology`, etc.). More feedback on slow models but requires LangGraph streaming hooks. Deferred to post-RAGAS if warranted.
- **Both narrative + workflow doc in `--doc`** — Generating a full workflow intent doc alongside the change narrative in the HTML report. Doubles LLM cost; deferred until user demand confirmed.

</deferred>

---

*Phase: 25-cli-integration*
*Context gathered: 2026-04-05*
