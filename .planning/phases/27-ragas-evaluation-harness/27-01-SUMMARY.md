---
phase: 27-ragas-evaluation-harness
plan: "01"
subsystem: eval
tags: [ragas, llm-eval, faithfulness, answer-relevancy, smoke-tests]
dependency_graph:
  requires:
    - 23-llm-foundation (ContextBuilder, require_llm_deps)
    - 24-documentation-graph (generate_documentation, WorkflowDocumentation)
    - 25-cli-integration (ACD_LLM_MODEL env var pattern, provider dispatch)
  provides:
    - tests/eval/ragas_eval.py (RAGAS evaluation harness — EVAL-02)
    - tests/eval/test_ragas_eval_smoke.py (smoke tests for eval helpers)
  affects: []
tech_stack:
  added: [ragas~=0.4 (already in pyproject.toml llm extras)]
  patterns:
    - In-memory XML bytes fixtures (same pattern as tests/fixtures/pipeline.py)
    - LLM imports deferred to main() for module importability without extras
    - asyncio.run() bridge for async generate_documentation in standalone script
    - tempfile.NamedTemporaryFile + finally unlink (temp file safety)
key_files:
  created:
    - tests/eval/__init__.py
    - tests/eval/ragas_eval.py
    - tests/eval/test_ragas_eval_smoke.py
  modified: []
decisions:
  - "Fixtures defined as inline XML bytes (D-01) — no .yxmd files committed to disk"
  - "No ground_truth in samples (D-02) — faithfulness + answer_relevancy operate without it"
  - "retrieved_contexts = ContextBuilder output, not raw XML (D-03)"
  - "Two env vars: ACD_LLM_MODEL (required) + RAGAS_CRITIC_MODEL (optional critic, falls back to generator) (D-04)"
  - "Script reports scores, does not fail on threshold miss — developer decides action (D-07)"
  - "All LLM/RAGAS imports inside main() so module is importable without [llm] extras (Pitfall 5)"
metrics:
  duration: "~8 min"
  completed: "2026-04-06"
  tasks_completed: 2
  files_created: 3
---

# Phase 27 Plan 01: RAGAS Evaluation Harness Summary

RAGAS evaluation harness script plus smoke tests — runs full parse->ContextBuilder->generate_documentation pipeline on inline XML fixtures and scores LLM output faithfulness and answer_relevancy using RAGAS v0.4, with no ground truth required.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create tests/eval/ package with smoke tests | ef2c67f | tests/eval/__init__.py, tests/eval/test_ragas_eval_smoke.py |
| 2 | Create tests/eval/ragas_eval.py standalone script | 0e57b77 | tests/eval/ragas_eval.py |

## What Was Built

### tests/eval/ragas_eval.py (331 lines)

Standalone evaluation script (not pytest) with:

- **Module docstring** documenting usage, env vars, threshold (>=0.8), and how to add samples (D-09)
- **FAITHFULNESS_THRESHOLD = 0.8** constant
- **EVAL_WORKFLOW_FILTER** (ToolIDs 2701-2702): Input->Filter workflow with Revenue > 1000 expression
- **EVAL_WORKFLOW_JOIN** (ToolIDs 2703-2705): dual Input->Join workflow with JoinByPosition
- **FIXTURES** list: [("filter_workflow", ...), ("join_workflow", ...)]
- **_build_llm_from_env()**: reads env var, dispatches to ChatOllama/ChatOpenAI per provider prefix; exits(1) on missing required var or invalid format; never prints env var values (T-27-01)
- **_workflow_bytes_to_context()**: writes bytes to temp file, calls parse_one + ContextBuilder.build_from_workflow, deletes temp file in finally (T-27-02)
- **_context_to_strings()**: serializes context dict to list[str] of per-key JSON chunks for RAGAS retrieved_contexts (D-03)
- **main()**: all LLM/RAGAS imports inside; calls require_llm_deps(), builds generator + critic LLMs, runs FIXTURES through full pipeline, evaluates with EvaluationDataset.from_list + Faithfulness() + AnswerRelevancy(), prints per-sample and mean scores

### tests/eval/test_ragas_eval_smoke.py (6 tests)

| Test | Validates |
|------|-----------|
| test_missing_env_exits | exits(1) when ACD_LLM_MODEL unset (required=True) |
| test_optional_env_returns_none | returns None when RAGAS_CRITIC_MODEL unset (required=False) |
| test_invalid_format_exits | exits(1) when env var has no 'provider:model' colon |
| test_context_to_strings_returns_list_of_str | returns list[str] with one JSON chunk per key |
| test_context_to_strings_no_raw_xml | no XML angle brackets in output (D-03) |
| test_workflow_bytes_to_context_returns_expected_keys | MINIMAL_YXMD_A -> parse_one -> ContextBuilder returns 5 expected keys |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The eval script is fully wired. Live LLM execution requires ACD_LLM_MODEL env var and network access, which is expected for a developer-run evaluation tool.

## Threat Flags

No new network endpoints or auth paths introduced. The script reads env vars for API keys (ACD_LLM_MODEL, OPENAI_API_KEY, OPENROUTER_API_KEY) — these are standard patterns already in use in cli.py and are never printed in error messages (T-27-01). Temp file cleanup is guaranteed via try/finally (T-27-02).

## Verification Results

1. `pytest tests/eval/test_ragas_eval_smoke.py -x -q` — 6 passed
2. `python -c "import tests.eval.ragas_eval"` — Import OK (no [llm] extras needed)
3. Full suite (excluding pre-existing failures in test_ai.py and test_remote.py): 303 passed, 1 xfailed

Pre-existing failures confirmed by git stash check:
- `tests/test_ai.py::test_ai_summary_happy_path_emits_progress_then_result` — pre-existing, out of scope
- 5 tests in `tests/test_remote.py` — pre-existing, out of scope

## Self-Check: PASSED

- tests/eval/__init__.py: FOUND
- tests/eval/ragas_eval.py: FOUND (331 lines, >= 120)
- tests/eval/test_ragas_eval_smoke.py: FOUND
- Commit ef2c67f: FOUND
- Commit 0e57b77: FOUND
