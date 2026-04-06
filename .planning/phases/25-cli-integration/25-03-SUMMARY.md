---
phase: 25
plan: 03
subsystem: cli
tags: [llm, cli, diff, narrative, html-report]
dependency_graph:
  requires: [25-01, 25-02]
  provides: [diff-doc-flag, cli-02]
  affects: [src/alteryx_diff/cli.py, tests/test_cli.py, tests/llm/test_cli_diff_doc.py]
tech_stack:
  added: []
  patterns: [deferred-import, asyncio-run, typer-option]
key_files:
  created:
    - tests/llm/test_cli_diff_doc.py
  modified:
    - src/alteryx_diff/cli.py
    - tests/test_cli.py
decisions:
  - "--doc flag is opt-in; doc_fragment defaults to empty string on no-doc path (zero regression)"
  - "Narrative generation gated after result.is_empty early exit (D-12 Pitfall 5 compliance)"
  - "generate_change_narrative patched at source module alteryx_diff.llm.doc_graph due to deferred import inside diff() body"
metrics:
  duration: ~6 minutes
  completed: 2026-04-05
---

# Phase 25 Plan 03: `diff --doc` Flag — AI Change Narrative in HTML Report Summary

**One-liner:** Added opt-in `--doc` flag to the `diff` command that calls `generate_change_narrative()` and injects the AI narrative fragment into the HTML report via `doc_fragment` kwarg.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add doc/model/base_url options to diff() and wire narrative pipeline | 59334e6 | src/alteryx_diff/cli.py |
| 2 | Create tests/llm/test_cli_diff_doc.py with 5 CLI-02 acceptance tests | 4f51c2f | tests/llm/test_cli_diff_doc.py |
| 3 | Add regression guard to tests/test_cli.py | afca3fb | tests/test_cli.py |

## Verification Results

```
tests/test_cli.py: 13 passed
tests/llm/test_cli_diff_doc.py: 5 passed
tests/llm/test_cli_document.py: 6 passed
Full suite: 298 passed, 2 pre-existing remote failures, 1 xfailed
```

## Decisions Made

1. `doc_fragment` defaults to `""` ensuring zero regression on the no-doc code path — `HTMLRenderer.render()` already accepted this kwarg (Plan 01).
2. Narrative generation block is placed AFTER the `if result.is_empty:` early-exit block — prevents any LLM spend on identical workflow pairs (Pitfall 5 compliance, D-12).
3. Both `--doc` with `--json` is handled gracefully: emits a note to stderr and skips LLM call entirely.
4. `generate_change_narrative` patched at `alteryx_diff.llm.doc_graph` (source module) in tests, not at `alteryx_diff.cli`, because the function is imported inside the `diff()` body (CORE-01 deferred import pattern).

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- `src/alteryx_diff/cli.py` — modified, exists
- `tests/llm/test_cli_diff_doc.py` — created, exists
- `tests/test_cli.py` — modified, exists
- Commits: 59334e6, 4f51c2f, afca3fb — all verified in git log
