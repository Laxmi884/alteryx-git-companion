# Phase 25: CLI Integration - Research

**Researched:** 2026-04-05
**Domain:** Python CLI (Typer), async bridge (asyncio.run), LangChain/LangGraph LLM pipeline integration
**Confidence:** HIGH — all findings sourced from direct source-code inspection of the live codebase

## Summary

Phase 25 wires the Phase 23/24 LLM pipeline into two CLI entry points: a new `document` subcommand and a `--doc` flag on the existing `diff` command. The full LLM stack (LangGraph, ContextBuilder, DocRenderer) is already implemented and tested. Phase 25 is integration work — connecting CLI argument parsing to existing APIs — plus one new function (`generate_change_narrative`) and one kwarg addition (`HTMLRenderer.render(..., doc_fragment="")`).

The research confirms every integration point is well-defined. The existing `cli.py` patterns (typer options, `_err_console.status` spinner, `asyncio.run()` bridge in tests, `CliRunner` test harness) are consistent and provide clear templates for all new code. No new packages are required.

**Primary recommendation:** Follow the existing CLI patterns exactly. The codebase is consistent and the integration surface is narrow — deviation from established patterns is the only real risk.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `--model provider:model_name` flag for provider+model selection (e.g., `ollama:llama3`, `openrouter:mistralai/mistral-7b-instruct`, `openai:gpt-4o`). CLI parses the prefix to build the right `BaseChatModel`.
- **D-02:** API keys from env vars only (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`) — never from CLI flags.
- **D-03:** Optional `--base-url` flag for non-default Ollama host or OpenAI-compatible endpoint.
- **D-04:** Fallback resolution order when `--model` is not given: (1) `ACD_LLM_MODEL` env var, (2) `config_store`, (3) error with clear message.
- **D-05:** `config_store` stores model preference string. API keys stored in **keyring** — never in config files.
- **D-06:** Shared config contract with Phase 26 (Phase 26 settings panel writes; Phase 25 CLI reads same sources).
- **D-07:** `document` subcommand uses `ContextBuilder.build_from_workflow()` → `generate_documentation()` → `DocRenderer.write_markdown()`.
- **D-08:** Default output path: `{workflow_dir}/{stem}-doc.md` — co-located with input `.yxmd` file.
- **D-09:** `--output` flag overrides default path.
- **D-10:** Missing `[llm]` extras: `require_llm_deps()` called first — raises `ImportError` with install hint, exits non-zero.
- **D-11:** Progress: Rich spinner on stderr (`Generating documentation...`), suppressed by `--quiet`.
- **D-12:** `--doc` is opt-in on existing `diff` command — absent by default.
- **D-13:** `--doc` generates change narrative only via `ContextBuilder.build_from_diff()`.
- **D-14:** New `generate_change_narrative(context, llm)` async function in `doc_graph.py`.
- **D-15:** `HTMLRenderer.render()` gets new `doc_fragment: str = ""` kwarg; `DocRenderer.to_html_fragment()` output is passed as this kwarg.
- **D-16:** Progress: same Rich spinner as `document` subcommand.
- **D-17:** Async bridge via `asyncio.run()` — consistent with existing LLM tests.

### Claude's Discretion

- Exact `generate_change_narrative()` output model design (`ChangeNarrative` Pydantic model with `narrative: str` and optional `risks: list[str]`, or plain string)
- Prompt wording for change narrative nodes
- `--model` string parsing implementation (prefix split on first `:`)
- HTML template changes for narrative section (section heading, placement relative to graph)
- Test structure for new CLI commands (mock LLM, `pytest.importorskip`, `CliRunner`)

### Deferred Ideas (OUT OF SCOPE)

- Streaming token output to terminal during `document` generation
- Stage-by-stage progress printing (LangGraph streaming hooks)
- Both narrative + workflow doc in `--doc` (doubles LLM cost)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-01 | User can run `alteryx-diff document <workflow.yxmd>` to generate a Markdown intent doc for a single workflow | `document` subcommand on `app` typer object, consuming Phase 24 `generate_documentation()` → `DocRenderer.write_markdown()` pipeline; `require_llm_deps()` guard for missing-extras case |
| CLI-02 | User can pass `--doc` to `alteryx-diff diff` to embed an AI change narrative section in the HTML diff report output | `doc: bool` option on existing `diff()` command; new `generate_change_narrative()` in `doc_graph.py`; new `doc_fragment` kwarg on `HTMLRenderer.render()` |
</phase_requirements>

---

## Standard Stack

### Core (already in pyproject.toml — no new packages needed)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| typer | `>=0.12` | CLI argument parsing, `@app.command()` | Already wires `diff`; `document` is a new `@app.command()` |
| rich | transitive via typer | `Console(stderr=True).status(...)` spinner | `_err_console` already exists in `cli.py` |
| langchain | `~=1.2` | `BaseChatModel` injection, `with_structured_output` | Already in `[llm]` extra |
| langgraph | `~=1.1` | `generate_documentation()`, new `generate_change_narrative()` | Already in `[llm]` extra |
| langchain-openai | `~=0.3` | `ChatOpenAI` for OpenRouter and OpenAI providers | Already in `[llm]` extra (added Phase 24) |
| langchain-ollama | `~=1.0` | `ChatOllama` for local models | Already in `[llm]` extra |
| keyring | `>=24.0` | API key storage (OS credential store) | Already in core deps |
| platformdirs | `>=4.0` | `config_store` path resolution | Already in core deps |
| pydantic | transitive | `ChangeNarrative` output model | Available through langchain |

**Installation:** No new packages. All dependencies already declared.

---

## Architecture Patterns

### Existing `cli.py` Command Structure

The typer app is `app = typer.Typer(no_args_is_help=True)`. The existing `diff` function is decorated with `@app.command()`. The `document` subcommand is also `@app.command()` — no sub-app nesting needed.

**Important:** The existing `test_cli.py` invokes `runner.invoke(app, [str(path_a), str(path_b)])` without a "diff" prefix because typer's single-command mode makes `diff` the default. Once `document` is added, the app becomes multi-command and the test pattern changes: callers must pass the command name explicitly (`runner.invoke(app, ["diff", str(path_a), str(path_b)])`). This is a **regression risk** for all 13 existing `test_cli.py` tests if the typer app structure changes.

**Resolution:** `app = typer.Typer(no_args_is_help=True)` with multiple `@app.command()` functions — in multi-command mode, `diff` is no longer the implicit default. Existing `test_cli.py` tests must be updated to prepend `"diff"` to their arg lists.

### Pattern 1: `document` Subcommand

```python
# Source: cli.py — follows exact existing diff() pattern
@app.command()
def document(
    workflow: pathlib.Path = typer.Argument(..., help="..."),
    output: pathlib.Path | None = typer.Option(None, "--output", "-o", help="..."),
    model: str | None = typer.Option(None, "--model", help="provider:model_name"),
    base_url: str | None = typer.Option(None, "--base-url", help="..."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="..."),
) -> None:
    from alteryx_diff.llm import require_llm_deps
    require_llm_deps()
    # ...resolve model, build llm, run pipeline...
    import asyncio
    doc = asyncio.run(generate_documentation(context, llm))
```

### Pattern 2: `--doc` Flag on `diff`

Add one new parameter to the existing `diff()` signature:
```python
doc: bool = typer.Option(False, "--doc", help="Embed AI change narrative in HTML report"),
```

After `response` is obtained but before `HTMLRenderer().render(...)` is called, if `doc=True` and not `json_output`:
```python
if doc:
    # build narrative context, build llm, run asyncio.run(generate_change_narrative(...))
    doc_fragment = DocRenderer().to_html_fragment_from_narrative(narrative)

html = HTMLRenderer().render(result, ..., doc_fragment=doc_fragment)
```

### Pattern 3: `asyncio.run()` Bridge

All async LLM calls in CLI context bridge via `asyncio.run()`. The existing LLM test suite uses this same pattern (no `pytest-asyncio` dependency, no event loop fixture).

```python
# Source: tests/llm/test_doc_graph.py lines 61, 93, 140
import asyncio
doc = asyncio.run(generate_documentation(sample_context, mock_llm))
```

### Pattern 4: Spinner Pattern (from existing `diff` command)

```python
# Source: cli.py lines 100-108
with _err_console.status("Generating documentation...", spinner="dots"):
    doc = asyncio.run(generate_documentation(context, llm))
```
Wrapped in `if not quiet:` guard. When `quiet=True`, call without spinner.

### Pattern 5: Error Exit Pattern

```python
# Source: cli.py lines 83-85
typer.echo(f"Error: {message}", err=True)
raise typer.Exit(code=2) from None
```

### Pattern 6: `require_llm_deps()` Error Handling

```python
# Source: llm/__init__.py
# require_llm_deps() raises ImportError with message:
# "LLM features require optional dependencies. Install them with: pip install 'alteryx-diff[llm]'"
# CLI wraps this:
try:
    require_llm_deps()
except ImportError as e:
    typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(code=2) from None
```

### Pattern 7: `HTMLRenderer.render()` Optional Kwarg Pattern

Existing optional kwargs on `render()`:
- `graph_html: str = ""` — injected via `{{ graph_html | safe }}` in template
- `metadata: dict[str, Any] | None = None` — gated by `{% if metadata %}` in template

New kwarg follows the same convention:
- `doc_fragment: str = ""` — injected via `{{ doc_fragment | safe }}` in the HTML template

The `doc_fragment` HTML injection point in the template should appear **after** the `{{ graph_html | safe }}` line and **before** the `{% if metadata %}` governance block. This placement puts the AI narrative below the interactive graph and before governance metadata.

### Pattern 8: Model Resolution (`_resolve_llm`)

A private helper `_resolve_llm(model_str, base_url)` to build the correct `BaseChatModel` from the `provider:model_name` string:

```python
def _resolve_llm(model_str: str, base_url: str | None) -> "BaseChatModel":
    provider, _, model_name = model_str.partition(":")
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        kwargs = {"model": model_name, "temperature": 0}
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOllama(**kwargs)
    elif provider in ("openai", "openrouter"):
        from langchain_openai import ChatOpenAI
        kwargs = {"model": model_name, "temperature": 0}
        if provider == "openrouter":
            kwargs["base_url"] = base_url or "https://openrouter.ai/api/v1"
            kwargs["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")
        else:
            kwargs["api_key"] = os.environ.get("OPENAI_API_KEY", "")
        if base_url and provider == "openai":
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider!r}. Use ollama, openai, or openrouter.")
```

### Pattern 9: `config_store` — LLM Model Preference

The `config_store` in `app/services/config_store.py` uses `load_config()` / `save_config()` with a flat JSON dict at `platformdirs.user_data_dir("AlteryxGitCompanion") / "config.json"`. The model preference will be stored as `cfg["llm_model"]` (string). Read pattern:

```python
from app.services.config_store import load_config
cfg = load_config()
model_str = cfg.get("llm_model")
```

**Note for Phase 25:** The CLI only *reads* from `config_store`; Phase 26's settings panel writes it. Phase 25 must not fail if the key is absent — use `.get()` with `None` default.

### Pattern 10: Keyring — API Key Storage

Keyring pattern from `app/services/remote_auth.py`:

```python
import keyring
SERVICE = "AlteryxGitCompanion:llm"
USERNAME_KEY = "api_key"

# Store:
keyring.set_password(SERVICE, USERNAME_KEY, api_key)

# Retrieve:
api_key = keyring.get_password(SERVICE, USERNAME_KEY)  # returns None if absent
```

Phase 25 CLI reads API keys from env vars (D-02), not keyring directly. Keyring is Phase 26's write path; Phase 25 is only an occasional read fallback. **For Phase 25, env vars are sufficient — keyring read for API keys may be safely deferred to Phase 26 unless D-05 requires it for the CLI fallback path.** The CONTEXT.md D-05 says "API keys stored in keyring" but D-02 says "API keys come from env vars only" for CLI flags. These are consistent: Phase 26 writes to keyring; Phase 25 CLI reads from env vars (which may have been set from keyring by a wrapper script).

### Pattern 11: `generate_change_narrative()` New Function

Lives in `src/alteryx_diff/llm/doc_graph.py`. Signature (Claude's discretion for exact design):

```python
async def generate_change_narrative(
    context: dict,   # ContextBuilder.build_from_diff() output shape: {summary, changes}
    llm: "BaseChatModel",
) -> "ChangeNarrative":
    ...
```

`ChangeNarrative` is a new Pydantic model (in `llm/models.py`) with at minimum `narrative: str`. Simpler than `WorkflowDocumentation` — likely 1-2 LLM calls rather than a 4-node graph. The `context` shape differs from workflow context: it has `summary` and `changes` keys rather than `workflow_name`, `tools`, `topology`.

### Anti-Patterns to Avoid

- **Top-level LLM imports in `cli.py`:** All `langchain`/`langgraph` imports inside function bodies only. Same rule as the rest of the codebase (CORE-01 guarantee).
- **Importing `doc_graph.py` at module level from `cli.py`:** `doc_graph.py` has top-level LangChain imports (`from langchain_core.language_models import BaseChatModel`). It must only be imported inside the `document` and `diff` function bodies (deferred import).
- **Calling `asyncio.run()` inside an already-running event loop:** The CLI is synchronous (no FastAPI event loop at CLI invocation time), so `asyncio.run()` is safe. Do not add `pytest-asyncio` — the existing pattern uses `asyncio.run()` in test bodies directly.
- **Changing `app = typer.Typer()` configuration:** The `no_args_is_help=True` flag must be preserved.

---

## What Exists vs What Needs to Be Created

### What Exists (no changes)

| Item | Location | Status |
|------|----------|--------|
| `ContextBuilder.build_from_workflow()` | `src/alteryx_diff/llm/context_builder.py` | Complete — returns `{workflow_name, tool_count, tools, connections, topology}` |
| `ContextBuilder.build_from_diff()` | `src/alteryx_diff/llm/context_builder.py` | Complete — returns `{summary, changes}` |
| `generate_documentation(context, llm)` | `src/alteryx_diff/llm/doc_graph.py` | Complete — async, returns `WorkflowDocumentation` |
| `DocRenderer.write_markdown(doc, path)` | `src/alteryx_diff/renderers/doc_renderer.py` | Complete — writes Markdown, returns resolved path |
| `DocRenderer.to_html_fragment(doc)` | `src/alteryx_diff/renderers/doc_renderer.py` | Complete — returns `<section>...</section>` HTML string |
| `require_llm_deps()` | `src/alteryx_diff/llm/__init__.py` | Complete — raises with install hint |
| `HTMLRenderer.render(result, file_a, file_b, *, graph_html, metadata)` | `src/alteryx_diff/renderers/html_renderer.py` | Complete — needs `doc_fragment` kwarg added |
| Typer `app` with `diff` command | `src/alteryx_diff/cli.py` | Complete — `document` and `--doc` added here |
| `_err_console` Rich Console | `src/alteryx_diff/cli.py` | Complete — reuse for spinner |
| `load_config()` / `save_config()` | `app/services/config_store.py` | Complete — read `cfg.get("llm_model")` |
| keyring `get_password` / `set_password` | `app/services/remote_auth.py` | Complete — pattern to reuse for LLM API key |

### What Needs to Be Created / Modified

| Item | Location | Change Type |
|------|----------|-------------|
| `ChangeNarrative` Pydantic model | `src/alteryx_diff/llm/models.py` | **NEW** — add alongside `WorkflowDocumentation` |
| `generate_change_narrative(context, llm)` | `src/alteryx_diff/llm/doc_graph.py` | **NEW** async function |
| `DocRenderer.to_html_fragment_from_narrative(narrative)` OR reuse `to_html_fragment` with duck-typed input | `src/alteryx_diff/renderers/doc_renderer.py` | **NEW** method or adapt existing |
| `document` subcommand | `src/alteryx_diff/cli.py` | **NEW** `@app.command()` function |
| `doc: bool` option on `diff` | `src/alteryx_diff/cli.py` | **MODIFY** — add option, add LLM pipeline call |
| `HTMLRenderer.render(..., doc_fragment: str = "")` | `src/alteryx_diff/renderers/html_renderer.py` | **MODIFY** — add kwarg + template injection |
| `_TEMPLATE` in html_renderer.py | `src/alteryx_diff/renderers/html_renderer.py` | **MODIFY** — add `{{ doc_fragment | safe }}` injection point |
| `parse_one()` public function | `src/alteryx_diff/parser.py` | **NEW** — one-line public delegator to `_parse_one`; needed by `document` subcommand |
| Existing `test_cli.py` tests | `tests/test_cli.py` | **MODIFY** — prepend `"diff"` to all invoke() arg lists (multi-command regression) |
| New `tests/test_cli_llm.py` (or similar) | `tests/llm/test_cli_document.py` | **NEW** — `document` and `diff --doc` tests with mock LLM |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM provider abstraction | Custom provider factory | `BaseChatModel` + `ChatOllama` / `ChatOpenAI` | Provider-agnostic pattern already established in Phase 24 |
| Async-to-sync bridge | Custom event loop management | `asyncio.run()` | Simple, correct for synchronous CLI context |
| HTML escaping in narrative section | Manual escape logic | Jinja2 `autoescape=True` + `| e` filter | Already used in `DocRenderer._env_html` |
| OS credential storage | Custom file-based secrets | `keyring` (already in deps) | Cross-platform, secure, already used for PAT storage |
| Config persistence | Custom INI/TOML | `app/services/config_store.py` `load_config()`/`save_config()` | Already handles app config; adds `llm_model` key |
| Token counting | Custom approximation | `count_tokens_approximately` (langchain-core) | Already available transitively |

---

## Test Patterns

### Test Location

New LLM CLI tests go in `tests/llm/test_cli_document.py` (or `tests/llm/test_cli_llm.py`). This follows the `tests/llm/` convention for LLM-gated tests.

### Module-Level importorskip

```python
# Source: tests/llm/test_doc_graph.py line 15
pytest.importorskip("langchain")
```

Every test file in `tests/llm/` starts with this line. New CLI LLM tests must too.

### CliRunner Pattern with Multi-Command App

```python
from typer.testing import CliRunner
from alteryx_diff.cli import app

runner = CliRunner(mix_stderr=False)

# After adding `document` command, diff is no longer the default:
result = runner.invoke(app, ["diff", str(path_a), str(path_b)])
result = runner.invoke(app, ["document", str(workflow_path)])
```

### Mock LLM in CLI Tests

The CLI creates the LLM via `_resolve_llm()`. For tests, patch the resolver or mock at the `generate_documentation` / `generate_change_narrative` level:

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Option A: patch the generate function directly (simpler, preferred)
with patch("alteryx_diff.cli.generate_documentation", new=AsyncMock(return_value=sample_doc)):
    result = runner.invoke(app, ["document", str(wf_path)])

# Option B: patch _resolve_llm
with patch("alteryx_diff.cli._resolve_llm", return_value=mock_llm):
    result = runner.invoke(app, ["document", str(wf_path)])
```

### Testing Missing LLM Deps (CLI-01 success criteria)

```python
def test_document_without_llm_deps_exits_nonzero(tmp_path, monkeypatch):
    import builtins
    real_import = builtins.__import__
    def mock_import(name, *args, **kwargs):
        if name == "langchain" or name.startswith("langchain."):
            raise ImportError("mocked")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", mock_import)
    # ... invoke document command, assert exit_code != 0, assert install hint in stderr
```

Pattern sourced from `tests/llm/test_require_llm_deps.py` lines 9-27.

### Testing `--doc` absent (CLI-02 regression guard)

```python
def test_diff_without_doc_flag_has_no_narrative(tmp_path):
    """--doc absent: HTML report contains no narrative section."""
    # standard diff invocation without --doc
    result = runner.invoke(app, ["diff", str(path_a), str(path_b), "--output", str(output)])
    content = output.read_text(encoding="utf-8")
    assert "change-narrative" not in content  # whatever id/class the narrative section uses
```

---

## HTML Template — `doc_fragment` Injection

The `_TEMPLATE` string in `html_renderer.py` already uses `{{ graph_html | safe }}` for injecting the graph section (line 353). The `doc_fragment` injection follows the exact same convention.

**Current injection point (line 353):**
```html
{{ graph_html | safe }}
{% if metadata %}
<details id="governance">
  ...
```

**After change:**
```html
{{ graph_html | safe }}
{{ doc_fragment | safe }}
{% if metadata %}
<details id="governance">
  ...
```

The narrative section HTML (produced by the new renderer method) should use a distinct `id` attribute (e.g., `id="change-narrative"`) to allow the `--doc` absence test to verify the section is absent.

The `render()` method adds `doc_fragment=doc_fragment` to `template.render(...)` alongside `graph_html` and `metadata`.

---

## Config Store — LLM Model Preference

`app/services/config_store.py` uses `platformdirs.user_data_dir("AlteryxGitCompanion") / "config.json"`. Config is a flat JSON dict. The model preference will be stored at key `"llm_model"` (string value, e.g., `"ollama:llama3"`).

Reading pattern for Phase 25 CLI fallback (D-04 step 2):

```python
from app.services.config_store import load_config
cfg = load_config()
model_str = cfg.get("llm_model")  # None if Phase 26 has not run yet
```

**Import note:** `app.services.config_store` is a separate package from `alteryx_diff`. The CLI in `src/alteryx_diff/cli.py` imports from `app.` — this cross-package import already works because `pythonpath = ["."]` in `pyproject.toml`. Confirm this path remains valid before using it.

---

## Keyring — API Key Storage Pattern

From `app/services/remote_auth.py`:

```python
SERVICE_GITHUB = "AlteryxGitCompanion:github"
keyring.set_password(SERVICE_GITHUB, USERNAME_KEY, token)
token = keyring.get_password(SERVICE_GITHUB, USERNAME_KEY)  # None if absent
```

For LLM API keys, the analogous service name would be `"AlteryxGitCompanion:llm"` with username being the provider name (e.g., `"openai"`, `"openrouter"`).

**Phase 25 note:** D-02 states API keys come from env vars only for CLI. Phase 25 does not need to read from keyring for API keys — that is Phase 26's concern. The keyring pattern is documented here for completeness and for Phase 26 handoff.

---

## Common Pitfalls

### Pitfall 1: Multi-Command Typer App Breaks Existing CLI Tests

**What goes wrong:** Adding `@app.command() def document(...)` converts the single-command typer app to a multi-command app. In single-command mode, `runner.invoke(app, [path_a, path_b])` implicitly calls `diff`. In multi-command mode, the same invocation raises a "No such command" error.

**Why it happens:** Typer's implicit command dispatching only works when there is a single `@app.command()`. With two commands, the first positional argument is interpreted as the command name.

**How to avoid:** Update all 13 existing `test_cli.py` invocations from `runner.invoke(app, [args])` to `runner.invoke(app, ["diff", args])` **in the same plan task** as adding the `document` command. Do not split into separate tasks.

**Warning signs:** All `test_cli.py` tests fail with exit code `2` and a "No such command" error message.

### Pitfall 2: Top-Level Import of `doc_graph.py` from `cli.py`

**What goes wrong:** `doc_graph.py` has a top-level `from langchain_core.language_models import BaseChatModel` import. If `cli.py` imports from `doc_graph` at module level, the core test suite (252 tests for users without `[llm]`) fails with `ImportError`.

**Why it happens:** `langchain_core` is an `[llm]` extra — not in core deps.

**How to avoid:** In `cli.py`, all imports from `alteryx_diff.llm.*` must be inside function bodies (deferred import). Pattern: `from alteryx_diff.llm.doc_graph import generate_documentation` placed inside the `document()` and `diff()` function bodies, after `require_llm_deps()` is called.

**Warning signs:** `tests/test_import.py` or `tests/llm/test_require_llm_deps.py::test_core_import_no_llm_side_effects` fails.

### Pitfall 3: `asyncio.run()` Called Inside an Existing Event Loop

**What goes wrong:** If `document` or `diff --doc` is ever called from FastAPI context (Phase 26), `asyncio.run()` raises `RuntimeError: This event loop is already running`.

**Why it happens:** `asyncio.run()` creates a new event loop and is incompatible with an existing running loop.

**How to avoid:** Phase 25 scope is CLI only — no FastAPI context. For Phase 26 (app integration), the pattern changes to `await generate_documentation(...)` directly. This is explicitly deferred. For Phase 25, `asyncio.run()` is correct.

**Warning signs:** `RuntimeError: This event loop is already running` in FastAPI endpoint context (Phase 26 concern, not Phase 25).

### Pitfall 4: `--model` Flag Not Provided and No Fallback Available

**What goes wrong:** User runs `alteryx-diff document workflow.yxmd` without `--model`, without `ACD_LLM_MODEL` env var, and before Phase 26 writes to `config_store`. The CLI has no model to use.

**Why it happens:** D-04 defines a fallback chain but the third step is an error — this is the correct terminal behavior.

**How to avoid:** Implement the full fallback chain (D-04). Error message must be clear: `"No LLM model configured. Use --model provider:model_name or set ACD_LLM_MODEL environment variable."` Exit code 2.

**Warning signs:** Silent hang or cryptic error when no model is configured.

### Pitfall 5: `DiffResult.is_empty` Check Before `--doc` LLM Call

**What goes wrong:** In the `diff` command, if `result.is_empty`, the code currently exits at line 125 before reaching the HTML render path. Adding `--doc` must not call the LLM when there are no differences.

**Why it happens:** The early exit is correct behavior for the no-diff case. The LLM narrative call must be inserted **after** the `is_empty` check.

**How to avoid:** Only invoke `generate_change_narrative` in the HTML render branch (after `is_empty` check passes). The `--doc` flag on an identical diff should silently have no effect (or print a note that no changes were found).

### Pitfall 6: No Public Single-File Parser API

**What goes wrong:** The `document` subcommand needs to parse one `.yxmd` file, but the public `parse()` function requires two paths. Calling `parse(path, path)` with the same path twice parses the file twice (wasteful, but functional). Using `_parse_one` directly couples to a private API that could change without notice.

**Why it happens:** The parser was designed for the two-file diff use case. Single-file parsing was not a public requirement until Phase 25.

**How to avoid:** Add a public `parse_one(path, *, filter_ui_tools=True) -> WorkflowDoc` function to `parser.py` that delegates to `_parse_one`. This is a one-line addition with no behavioral change.

**Warning signs:** `ImportError: cannot import name 'parse_one'` or test failures caused by the file being parsed twice with divergent mutable state.

---

## Plan Decomposition Recommendation

Three plans are recommended for this phase.

**Plan 01 — Core Infrastructure (non-LLM changes):**
- Add `ChangeNarrative` Pydantic model to `llm/models.py`
- Add `doc_fragment: str = ""` kwarg to `HTMLRenderer.render()` + template injection
- Update existing `test_cli.py` tests to prepend `"diff"` for multi-command mode
- Tests for `HTMLRenderer` with `doc_fragment`

**Plan 02 — `document` Subcommand (CLI-01):**
- Add `generate_change_narrative()` async function to `doc_graph.py`
- Add `document` command to `cli.py` with full `_resolve_llm()` helper and model resolution fallback chain (D-04)
- Tests in `tests/llm/test_cli_document.py`: happy path, missing-deps exit, `--output` override, default output path

**Plan 03 — `diff --doc` Flag (CLI-02):**
- Add `doc: bool` option to `diff` command
- Wire `generate_change_narrative()` into diff HTML path with spinner
- Add `DocRenderer` HTML fragment for narrative (new method or adapt existing)
- Tests: `--doc` present embeds section, `--doc` absent section missing, `--doc` on identical diff (no LLM call)

**Rationale for split:** Plan 01 is pure non-LLM infrastructure that can be validated without LLM extras. Plans 02 and 03 each cover one acceptance criterion independently, making verification simpler. Plans 02 and 03 can run in parallel if desired.

---

## Risk Flags

| Risk | Severity | Mitigation |
|------|----------|------------|
| Multi-command Typer breaks all 13 existing `test_cli.py` tests | HIGH | Update test invocations in Plan 01 or Plan 02, whichever adds the `document` command |
| `doc_graph.py` top-level LangChain import breaks core import test | HIGH | All `alteryx_diff.llm.*` imports inside function bodies in `cli.py` |
| `asyncio.run()` nested loop if called from FastAPI (Phase 26) | MEDIUM | Explicit scope comment in Phase 25 code; Phase 26 must replace with `await` |
| `config_store` import path from `cli.py` (`app.services.config_store`) | MEDIUM | Verify cross-package import works in test context; consider moving config read logic to a shared utility |
| `is_empty` early exit in `diff` swallows `--doc` flag silently | LOW | Guard LLM call after `is_empty` check; emit message on stderr if `--doc` and no diff |
| No public single-file parser API (`_parse_one` is private) | MEDIUM | Add `parse_one()` public function to `parser.py` — one-line delegator; include in Plan 02 |
| `_resolve_llm` with unknown provider string | LOW | Explicit error with clear message; list valid providers in help text |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_cli.py tests/llm/ -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | `document` command generates Markdown file | smoke | `pytest tests/llm/test_cli_document.py -x` | No — Wave 0 |
| CLI-01 | Missing `[llm]` extras exits non-zero with install hint | unit | `pytest tests/llm/test_cli_document.py::test_document_without_llm_exits_nonzero -x` | No — Wave 0 |
| CLI-01 | `--output` override writes to specified path | smoke | `pytest tests/llm/test_cli_document.py::test_document_output_flag -x` | No — Wave 0 |
| CLI-02 | `--doc` embeds narrative section in HTML | smoke | `pytest tests/llm/test_cli_diff_doc.py::test_diff_doc_embeds_narrative -x` | No — Wave 0 |
| CLI-02 | `--doc` absent: narrative section not in HTML | regression | `pytest tests/test_cli.py::test_diff_writes_html_report_by_default -x` | Yes (modified) |

### Sampling Rate

- Per task commit: `python -m pytest tests/test_cli.py -q` (existing CLI tests — guard against multi-command regression)
- Per wave merge: `python -m pytest tests/ -q`
- Phase gate: Full suite green (282 passing, 2 pre-existing failures in `test_remote.py` are unrelated)

### Wave 0 Gaps

- [ ] `tests/llm/test_cli_document.py` — covers CLI-01 (document command)
- [ ] `tests/llm/test_cli_diff_doc.py` — covers CLI-02 (diff --doc flag)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Core | Yes | 3.12 (via conda) | — |
| pytest | Testing | Yes | 8.x | — |
| langchain / langgraph | LLM tests | Yes | 1.2.x / 1.1.x | `pytest.importorskip("langchain")` skip |
| Ollama (local) | End-to-end LLM test | Not checked | — | Mock LLM in unit tests |

**Missing dependencies with no fallback:** None (all tests use mock LLM; no real Ollama required for automated tests).

**Pre-existing test failures:** `tests/test_remote.py::test_post_push_success` and `tests/test_remote.py::test_push_repo_deleted` — 2 failures pre-dating Phase 25. Phase 25 must not make these worse but is not responsible for fixing them.

---

## Code Examples

### `HTMLRenderer.render()` — Adding `doc_fragment` Kwarg

```python
# Source: src/alteryx_diff/renderers/html_renderer.py — current signature
def render(
    self,
    result: DiffResult,
    file_a: str = "workflow_a.yxmd",
    file_b: str = "workflow_b.yxmd",
    *,
    graph_html: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:

# After Phase 25 change:
def render(
    self,
    result: DiffResult,
    file_a: str = "workflow_a.yxmd",
    file_b: str = "workflow_b.yxmd",
    *,
    graph_html: str = "",
    metadata: dict[str, Any] | None = None,
    doc_fragment: str = "",   # NEW — AI change narrative HTML fragment
) -> str:
```

### `generate_documentation()` — Existing Async Signature (consume as-is)

```python
# Source: src/alteryx_diff/llm/doc_graph.py lines 220-259
async def generate_documentation(
    context: dict,        # ContextBuilder.build_from_workflow() output
    llm: BaseChatModel,
) -> WorkflowDocumentation:
```

### `ContextBuilder` — Both Methods (consume as-is)

```python
# Source: src/alteryx_diff/llm/context_builder.py
# For document subcommand:
context = ContextBuilder.build_from_workflow(workflow_doc)  # WorkflowDoc input

# For diff --doc:
context = ContextBuilder.build_from_diff(diff_result)       # DiffResult input
```

### Keyring Service Pattern (reference for LLM API key storage)

```python
# Source: app/services/remote_auth.py
import keyring
SERVICE_GITHUB = "AlteryxGitCompanion:github"
keyring.set_password(SERVICE_GITHUB, "token", value)
result = keyring.get_password(SERVICE_GITHUB, "token")  # str | None
```

### Parser Entry Point (needed in `document` subcommand)

**VERIFIED:** `parser.py` has no public single-file parse function. The public `parse(path_a, path_b)` requires two paths. The `_parse_one(path)` helper is private (underscore prefix, not in `__all__`).

**Two implementation options for the planner to choose:**

Option A — Expose `_parse_one` as public `parse_one` (cleanest, recommended):
```python
# Add to src/alteryx_diff/parser.py:
def parse_one(path: pathlib.Path, *, filter_ui_tools: bool = True) -> WorkflowDoc:
    """Parse a single .yxmd file into a WorkflowDoc. Public surface for document command."""
    return _parse_one(path, filter_ui_tools=filter_ui_tools)

# Then in cli.py document():
from alteryx_diff.parser import parse_one
doc = parse_one(workflow_path)
```

Option B — Reuse `parse()` with duplicate path (no parser change, slight waste):
```python
from alteryx_diff.parser import parse
doc_a, _ = parse(workflow_path, workflow_path)
# doc_a and doc_b are identical since same path passed twice — safe, just wasteful
```

Option A is recommended: it adds a public contract, avoids parsing the file twice, and makes the intent clear.

---

## Sources

### Primary (HIGH confidence — direct source inspection)

- `src/alteryx_diff/cli.py` — exact existing patterns for typer, spinner, error handling
- `src/alteryx_diff/llm/doc_graph.py` — `generate_documentation()` signature and retry logic
- `src/alteryx_diff/llm/context_builder.py` — `build_from_workflow()` and `build_from_diff()` output shapes
- `src/alteryx_diff/renderers/html_renderer.py` — `render()` signature, `_TEMPLATE` injection points
- `src/alteryx_diff/renderers/doc_renderer.py` — `to_html_fragment()`, `write_markdown()` signatures
- `src/alteryx_diff/llm/__init__.py` — `require_llm_deps()` exact error message
- `src/alteryx_diff/llm/models.py` — `WorkflowDocumentation`, `ToolNote` Pydantic models
- `app/services/config_store.py` — `load_config()` / `save_config()` pattern
- `app/services/remote_auth.py` — keyring `set_password` / `get_password` pattern
- `tests/test_cli.py` — existing CliRunner patterns, 13 tests to update
- `tests/llm/test_doc_graph.py` — `asyncio.run()` test pattern, mock LLM construction
- `tests/llm/conftest.py` — `mock_llm` fixture, `sample_context` fixture
- `tests/llm/test_require_llm_deps.py` — missing-deps monkeypatch pattern
- `pyproject.toml` — confirmed `[llm]` extra already includes `langchain-openai~=0.3`
- `.planning/phases/25-cli-integration/25-CONTEXT.md` — all locked decisions
- `.planning/research/STACK.md` — confirmed library versions and API patterns

### Secondary (MEDIUM confidence)

- `.planning/phases/23-llm-foundation/23-CONTEXT.md` — test isolation strategy
- `.planning/phases/24-documentation-graph-docrenderer-ollama/24-CONTEXT.md` — pipeline design decisions

---

## Metadata

**Confidence breakdown:**
- Existing API surface: HIGH — read from live source files
- New `generate_change_narrative()` design: MEDIUM — shape specified but prompt wording is Claude's discretion
- Multi-command Typer regression: HIGH — documented Typer behavior
- `config_store` cross-package import: MEDIUM — pattern works but should be verified in test context

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable libraries; 30-day validity)
