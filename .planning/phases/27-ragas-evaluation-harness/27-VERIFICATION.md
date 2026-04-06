---
phase: 27-ragas-evaluation-harness
verified: 2026-04-06T20:00:00Z
status: human_needed
score: 3/4 must-haves verified
re_verification: false
human_verification:
  - test: "Run `python tests/eval/ragas_eval.py` with ACD_LLM_MODEL set to a live provider"
    expected: "Script completes, prints per-sample faithfulness + answer_relevancy scores for both fixtures, prints Summary line with mean score and PASS/BELOW THRESHOLD status"
    why_human: "Requires a live LLM provider (Ollama, OpenAI, or OpenRouter) and network access. Cannot validate full pipeline execution (ContextBuilder -> generate_documentation -> RAGAS evaluate) without a running model."
---

# Phase 27: RAGAS Evaluation Harness Verification Report

**Phase Goal:** Developers can measure the faithfulness of LLM-generated documentation against `ContextBuilder` output using a repeatable RAGAS evaluation script — providing an objective quality gate before deploying model or prompt changes.
**Verified:** 2026-04-06T20:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Running `python tests/eval/ragas_eval.py` with ACD_LLM_MODEL set executes the full pipeline and prints faithfulness + answer_relevancy scores | ? HUMAN NEEDED | Script structure verified (main() correct, full pipeline wired). Live LLM execution requires human with running model. |
| 2 | Running the script without ACD_LLM_MODEL prints a clear error message and exits non-zero | ✓ VERIFIED | `_build_llm_from_env("ACD_LLM_MODEL", required=True)` calls `sys.exit(1)` with clear message; confirmed by smoke test `test_missing_env_exits` passing and manual CLI test (exit code 1). |
| 3 | retrieved_contexts in RAGAS samples contain ContextBuilder output (structured JSON), not raw XML | ✓ VERIFIED | `_context_to_strings()` serializes context dict as per-key JSON chunks; `test_context_to_strings_no_raw_xml` confirms no XML angle brackets; `_workflow_bytes_to_context()` routes bytes through `parse_one` + `ContextBuilder.build_from_workflow`. |
| 4 | Script docstring documents how to run, env vars, threshold, and how to add samples | ✓ VERIFIED | Module docstring contains: "export ACD_LLM_MODEL=...", "faithfulness >= 0.8", "Adding samples:", "pip install 'alteryx-diff[llm]'" — all required sections present. |

**Score:** 3/4 truths verified (1 requires human with live LLM)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/eval/__init__.py` | Package init for tests/eval | ✓ VERIFIED | File exists (1 line, package marker as intended) |
| `tests/eval/ragas_eval.py` | RAGAS evaluation harness script (>=120 lines, contains "faithfulness") | ✓ VERIFIED | 331 lines; contains `FAITHFULNESS_THRESHOLD = 0.8`, `from ragas import evaluate` (inside main()), `EvaluationDataset.from_list`, `Faithfulness()`, `ContextBuilder.build_from_workflow` |
| `tests/eval/test_ragas_eval_smoke.py` | Smoke tests (>=30 lines, contains "test_missing_env") | ✓ VERIFIED | 104 lines; contains all 6 required test functions |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/eval/ragas_eval.py` | `src/alteryx_diff/llm/context_builder.py` | `ContextBuilder.build_from_workflow()` | ✓ WIRED | `ContextBuilder.build_from_workflow` found at line 233; import deferred inside `_workflow_bytes_to_context()` |
| `tests/eval/ragas_eval.py` | `src/alteryx_diff/llm/doc_graph.py` | `generate_documentation(context, llm)` | ✓ WIRED | `generate_documentation` imported at line 269 inside `main()`; called at line 292 with `asyncio.run()` bridge |
| `tests/eval/ragas_eval.py` | `ragas` | `evaluate()` with `EvaluationDataset` | ✓ WIRED | `from ragas import evaluate` at line 270; `EvaluationDataset.from_list` at line 304; `Faithfulness()` + `AnswerRelevancy()` at line 307 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `ragas_eval.py` (FIXTURES) | `context` | `_workflow_bytes_to_context(xml_bytes, stem)` -> `parse_one` + `ContextBuilder.build_from_workflow` | Yes — live parse of real XML bytes | ✓ FLOWING |
| `ragas_eval.py` (samples) | `retrieved_contexts` | `_context_to_strings(context)` — serializes real ContextBuilder dict | Yes — JSON-serialized structured data, no raw XML | ✓ FLOWING |
| `ragas_eval.py` (result) | `mean_faith`, `mean_rel` | `evaluate(dataset, metrics, llm)` -> `result.to_pandas()` | Requires live LLM — cannot verify statically | ? HUMAN NEEDED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Module importable without [llm] extras | `python -c "import tests.eval.ragas_eval; print('Import OK')"` | `Import OK` | ✓ PASS |
| Env-var guard (missing ACD_LLM_MODEL exits 1) | `_build_llm_from_env("ACD_LLM_MODEL", required=True)` with env unset | exit code 1 | ✓ PASS |
| Smoke test suite | `pytest tests/eval/test_ragas_eval_smoke.py -v -q` | 6 passed in 0.13s | ✓ PASS |
| Full test suite (excluding pre-existing failures) | `pytest tests/ -q --ignore=tests/test_ai.py --ignore=tests/test_remote.py` | 267 passed, 1 xfailed | ✓ PASS |
| Live RAGAS evaluation end-to-end | `python tests/eval/ragas_eval.py` with live LLM | Not runnable in CI | ? SKIP (needs live LLM) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| EVAL-02 | 27-01-PLAN.md | RAGAS faithfulness evaluation harness | ✓ SATISFIED | `ragas_eval.py` implements full RAGAS v0.4 evaluation with `Faithfulness()` + `AnswerRelevancy()` metrics; ContextBuilder output as `retrieved_contexts`; threshold documented at 0.8 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No stubs, placeholders, or TODO/FIXME comments found in the eval harness files. The script is fully implemented — live LLM execution is gated by env var (by design, not a stub).

### Human Verification Required

#### 1. Live RAGAS Evaluation Run

**Test:** Set `ACD_LLM_MODEL=<provider>:<model>` (e.g., `ollama:mistral` or `openrouter:mistralai/mistral-7b-instruct`) and run `python tests/eval/ragas_eval.py`

**Expected:**
- Script prints header: "=== RAGAS Evaluation Harness ===" with generator/critic model names and sample count
- Processes both fixtures: "Processing: filter_workflow..." and "Processing: join_workflow..."
- Prints "--- Per-Sample Results ---" with `faithfulness=X.XXX  answer_relevancy=X.XXX` for both samples
- Prints "--- Summary ---" with mean faithfulness and `[PASS]` or `[BELOW THRESHOLD]` status
- Script exits 0 (does not fail on threshold miss by design)

**Why human:** Requires a running LLM model. Cannot mock the RAGAS `evaluate()` call in a meaningful way that validates real faithfulness scoring. The entire value of the harness is its live evaluation of LLM output.

### Gaps Summary

No code-level gaps found. All three artifacts exist and are substantive, wired, and data-flows are correct for the parts that can be verified statically. The single pending item is the live end-to-end evaluation which is gated by live LLM availability — this is expected behavior for an evaluation harness, not a deficiency.

**Pre-existing test failures (out of scope):**
- `tests/test_ai.py::test_ai_summary_happy_path_emits_progress_then_result` — pre-existing failure from Phase 26; not introduced by Phase 27
- 5 tests in `tests/test_remote.py` — pre-existing failures; not introduced by Phase 27

---

_Verified: 2026-04-06T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
