---
phase: 25-cli-integration
verified: 2026-04-05T08:30:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 25: CLI Integration Verification Report

**Phase Goal:** Add CLI commands for LLM-powered workflow documentation and change narrative — `alteryx-diff document` subcommand and `diff --doc` flag that embed AI-generated content in diff reports.
**Verified:** 2026-04-05T08:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `alteryx-diff document <workflow.yxmd>` subcommand exists and dispatches to `document()` in cli.py | VERIFIED | `diff` and `document` registered as Typer callbacks in `app`; `document()` fully wired at lines 287-355 of `cli.py` |
| 2 | `alteryx-diff diff --doc` flag exists and is wired to call `generate_change_narrative()` | VERIFIED | `doc`, `model`, `base_url` params in `diff()` signature (lines 71-85 of `cli.py`); narrative pipeline at lines 142-174 |
| 3 | HTML diff report with `--doc` embeds `id="change-narrative"` section | VERIFIED | `doc_fragment` passed to `HTMLRenderer.render()` (line 195); `{{ doc_fragment | safe }}` in template at line 354 of `html_renderer.py`; 5 acceptance tests pass |
| 4 | `--doc` is opt-in — without it, HTML has no narrative section | VERIFIED | `doc_fragment` defaults to `""` in both `diff()` (line 143) and `HTMLRenderer.render()` (line 535); regression guard `test_diff_without_doc_flag_produces_html_without_narrative_id` passes |
| 5 | `ChangeNarrative` Pydantic model exists with `narrative` and `risks` fields | VERIFIED | `src/alteryx_diff/llm/models.py` lines 21-25; `ChangeNarrative(narrative='x').model_dump()` returns `{'narrative': 'x', 'risks': []}` |
| 6 | `generate_change_narrative()` function exists and is in `__all__` | VERIFIED | `doc_graph.py` lines 262-299; `__all__` at line 23 includes `"generate_change_narrative"` |
| 7 | `DocRenderer.to_html_fragment_from_narrative()` produces correct HTML with `id="change-narrative"` | VERIFIED | `doc_renderer.py` lines 120-129; runtime check confirms `id="change-narrative"` present, paragraphs split, risks rendered |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/alteryx_diff/llm/models.py` | `ChangeNarrative` Pydantic model with `narrative` + `risks` | VERIFIED | Exists, substantive (lines 21-25), used by `doc_graph.py` and test files |
| `src/alteryx_diff/llm/doc_graph.py` | `generate_change_narrative()` async function | VERIFIED | Exists, substantive (single-shot `with_structured_output` call, lines 262-299), in `__all__`, imported by `cli.py` at runtime |
| `src/alteryx_diff/renderers/doc_renderer.py` | `to_html_fragment_from_narrative()` and `_NARRATIVE_HTML_TEMPLATE` | VERIFIED | Exists, substantive (lines 61-75 template, lines 120-129 method), rendered HTML confirmed correct at runtime |
| `src/alteryx_diff/renderers/html_renderer.py` | `doc_fragment` kwarg in `render()` and `{{ doc_fragment \| safe }}` in template | VERIFIED | Exists (lines 535, 554); template injection at line 354; `doc_fragment` passed through at line 576 |
| `src/alteryx_diff/parser.py` | `parse_one()` public function in `__all__` | VERIFIED | Exists (lines 49-60), in `__all__ = ['parse', 'parse_one']`, delegates to `_parse_one` |
| `src/alteryx_diff/cli.py` | `document` subcommand + `_resolve_model_string` + `_resolve_llm` + `--doc` in `diff` | VERIFIED | All four present (lines 22-210 for diff, 213-283 for helpers, 287-355 for document); no top-level LangChain imports (CORE-01 preserved) |
| `tests/llm/test_cli_document.py` | 6 CLI-01 acceptance tests | VERIFIED | Exists with 6 tests; all 6 pass |
| `tests/llm/test_cli_diff_doc.py` | 5 CLI-02 acceptance tests | VERIFIED | Exists with 5 tests; all 5 pass |
| `tests/test_cli.py` | Multi-command `"diff"` prefix on all invocations + 1 regression guard | VERIFIED | All `runner.invoke` calls use `["diff", ...]` prefix; `test_diff_without_doc_flag_produces_html_without_narrative_id` added at line 228 |
| `tests/llm/test_doc_renderer.py` | 2 new tests for `to_html_fragment_from_narrative` | VERIFIED | Tests pass in full suite run |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py diff()` | `generate_change_narrative()` | Deferred import inside function body + `asyncio.run()` | WIRED | Lines 158-169; `narrative_context = ContextBuilder.build_from_diff(result)` feeds into call |
| `cli.py diff()` | `HTMLRenderer.render()` | `doc_fragment=doc_fragment` kwarg | WIRED | Line 195; `doc_fragment` is either rendered narrative HTML or `""` |
| `cli.py document()` | `generate_documentation()` | Deferred import + `asyncio.run()` | WIRED | Lines 333, 343-346; result passed to `DocRenderer().write_markdown()` |
| `DocRenderer.to_html_fragment_from_narrative()` | `_NARRATIVE_HTML_TEMPLATE` | `self._env_html.from_string(...)` | WIRED | Line 128; `paragraphs` and `risks` passed as template vars |
| `HTMLRenderer._TEMPLATE` | `doc_fragment` | `{{ doc_fragment \| safe }}` | WIRED | Line 354 of html_renderer.py template; confirmed with grep |
| `_resolve_model_string()` | `_resolve_llm()` | Both called in sequence in `diff()` and `document()` | WIRED | Lines 154-155 (diff), 327-328 (document) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `diff()` HTML path | `doc_fragment` | `DocRenderer().to_html_fragment_from_narrative(narrative)` where `narrative` comes from `asyncio.run(generate_change_narrative(narrative_context, llm))` | Yes — LLM structured output, rendered via Jinja2; degrades gracefully to `""` when `--doc` not passed | FLOWING |
| `document()` | `workflow_doc` | `asyncio.run(generate_documentation(context, llm))` | Yes — LangGraph 4-node pipeline produces `WorkflowDocumentation`; written to Markdown via `DocRenderer().write_markdown()` | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `ChangeNarrative` model instantiates correctly | `python -c "from alteryx_diff.llm.models import ChangeNarrative; print(ChangeNarrative(narrative='x').model_dump())"` | `{'narrative': 'x', 'risks': []}` | PASS |
| `generate_change_narrative` importable | `python -c "from alteryx_diff.llm.doc_graph import generate_change_narrative; print(generate_change_narrative)"` | `<function generate_change_narrative at ...>` | PASS |
| `to_html_fragment_from_narrative` produces `id="change-narrative"` | Runtime Python check | `has id: True`, `has Para one: True`, `has risk-a: True` | PASS |
| Both CLI commands registered | Inspect `app.registered_commands` callbacks | `['diff', 'document']` | PASS |
| `diff()` has `doc`, `model`, `base_url` params | `inspect.signature(diff).parameters` | All three present | PASS |
| CORE-01: no LangChain at `cli.py` import time | Check modules loaded after `from alteryx_diff.cli import app` | `LangChain modules loaded at import: none` | PASS |
| Full Phase 25 test suite | `pytest tests/test_cli.py tests/llm/test_cli_document.py tests/llm/test_cli_diff_doc.py tests/test_html_renderer.py tests/llm/test_doc_renderer.py -q` | `43 passed in 4.65s` | PASS |
| Full test suite (regression) | `pytest tests/ -q --tb=no` | `298 passed, 2 failed (pre-existing remote), 1 xfailed` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CLI-01 | 25-02-PLAN.md | User can run `alteryx-diff document <workflow.yxmd>` to generate a Markdown intent doc | SATISFIED | `document()` command fully implemented; 6 acceptance tests pass in `test_cli_document.py`; `parse_one()` API wired |
| CLI-02 | 25-03-PLAN.md | User can pass `--doc` to `alteryx-diff diff` to embed AI change narrative in HTML diff report | SATISFIED | `--doc` flag fully implemented; 5 acceptance tests pass in `test_cli_diff_doc.py`; regression guard in `test_cli.py` confirms opt-in behavior |

No orphaned requirements — both CLI-01 and CLI-02 were claimed by plans and are now satisfied.

---

### Anti-Patterns Found

No blockers or substantive anti-patterns detected.

| File | Pattern Checked | Finding |
|------|----------------|---------|
| `src/alteryx_diff/cli.py` | Top-level LangChain imports | None — CORE-01 preserved; all LLM imports are deferred inside function bodies |
| `src/alteryx_diff/cli.py` | TODO/FIXME/placeholder comments | None found |
| `src/alteryx_diff/cli.py` | Empty handlers / stub returns | None — both `document()` and `diff()` doc path are fully wired |
| `src/alteryx_diff/llm/doc_graph.py` | Stub `generate_change_narrative` | None — full implementation: `SystemMessage` + `HumanMessage` + `with_structured_output` + `ainvoke` |
| `src/alteryx_diff/renderers/doc_renderer.py` | Stub `to_html_fragment_from_narrative` | None — full Jinja2 template render with paragraph splitting and conditional risks |

---

### Human Verification Required

The following items require a human with a real LLM endpoint to verify end-to-end behavior:

**1. End-to-End `document` Subcommand**
**Test:** `alteryx-diff document tests/fixtures/simple_workflow.yxmd --model ollama:llama3`
**Expected:** A `.md` file written next to the fixture with intent, data_flow, and tool inventory sections populated by the LLM; non-zero meaningful content (not placeholder).
**Why human:** Requires a running Ollama/OpenAI endpoint; quality of LLM output cannot be verified programmatically.

**2. End-to-End `diff --doc` Flag**
**Test:** `alteryx-diff diff tests/fixtures/workflow_a.yxmd tests/fixtures/workflow_b.yxmd --doc --model ollama:llama3 --output /tmp/diff_with_narrative.html`
**Expected:** HTML report opens in browser with an "AI Change Narrative" section visible, containing 2-4 paragraphs describing the diff and optionally a risks list. Section appears between the graph visualization and the governance footer.
**Why human:** Requires running LLM endpoint; narrative quality and HTML visual rendering require human inspection.

**3. `--model` Fallback Chain**
**Test:** Unset `ACD_LLM_MODEL`; configure `llm_model` in `config_store`; run `alteryx-diff document workflow.yxmd` without `--model`.
**Expected:** Command uses the config_store model without error.
**Why human:** `config_store` integration path cannot be tested in isolation without the full app running; the env-var and `--model` paths are covered by tests but config_store fallback is not.

---

### Gaps Summary

No gaps found. All automated checks pass.

- All 7 observable truths are VERIFIED against actual codebase.
- All 10 required artifacts exist, are substantive, and are wired.
- All 6 key links are WIRED with evidence.
- CLI-01 and CLI-02 requirements are SATISFIED.
- 43 Phase 25 tests pass; full suite 298 passed with only 2 pre-existing remote test failures (unrelated to this phase).
- CORE-01 constraint (no top-level LangChain imports in `cli.py`) is preserved.

---

_Verified: 2026-04-05T08:30:00Z_
_Verifier: Claude (gsd-verifier)_
