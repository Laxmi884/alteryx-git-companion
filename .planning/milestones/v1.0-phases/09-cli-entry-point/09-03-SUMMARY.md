---
phase: 09-cli-entry-point
plan: "03"
subsystem: testing
tags: [typer, click, cli, smoke-tests, fixtures, exit-codes, sha256, governance]

# Dependency graph
requires:
  - phase: 09-01
    provides: cli.py with Typer app, exit code protocol, _file_sha256, _cli_json_output
  - phase: 09-02
    provides: HTMLRenderer with ALCOA+ governance footer via metadata kwarg

provides:
  - "tests/fixtures/cli.py with 6 byte constants (MINIMAL_YXMD_A/B, IDENTICAL_YXMD, POSITION_YXMD_A/B, MALFORMED_XML) using ToolIDs 901-902"
  - "tests/test_cli.py with 12 smoke tests covering all exit codes, flags, HTML governance, and JSON output"
  - "OSError guard in cli.py for missing-file path (exit code 2 instead of unhandled FileNotFoundError)"

affects: [ci-cd, integration-testing, phase-09-complete]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-command Typer app invocation: runner.invoke(app, [path_a, path_b]) — no subcommand prefix in args list"
    - "click 8.2+ CliRunner(): stdout/stderr always separate; mix_stderr constructor arg removed upstream"
    - "OSError guard before pipeline.run() for missing-file exit-code-2 path"

key-files:
  created:
    - tests/fixtures/cli.py
    - tests/test_cli.py
  modified:
    - src/alteryx_diff/cli.py

key-decisions:
  - "CliRunner() without mix_stderr — click 8.2+ always separates stdout/stderr; constructor arg removed"
  - "Invocation pattern uses no subcommand prefix — single-command Typer app exposes diff function directly"
  - "OSError guard wraps _file_sha256() calls in cli.py — missing file raises FileNotFoundError before pipeline, must map to exit code 2"
  - "12 tests instead of plan's 11 — test_diff_include_positions_detects_position_change tests both flag states in one function, counted as one test item by pytest"

patterns-established:
  - "CLI smoke test pattern: CliRunner() in-process, tmp_path fixtures, result.stdout/result.stderr inspection"
  - "Fixture ToolID allocation enforced: Phase 9 CLI = 901-902, no collision with Phases 1-8 (max 815)"

requirements-completed: [CLI-01, CLI-02, CLI-04]

# Metrics
duration: 5min
completed: 2026-03-07
---

# Phase 09 Plan 03: CLI Smoke Tests Summary

**12-test CLI smoke suite using typer.testing.CliRunner verifying all exit codes (0/1/2), --json/--quiet/--include-positions/--output flags, SHA-256 governance footer, and OSError guard for missing-file exit-code-2 path**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-07T06:15:41Z
- **Completed:** 2026-03-07T06:20:54Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `tests/fixtures/cli.py` with 6 byte constants: `MINIMAL_YXMD_A/B` (ToolID 901, differing Expression), `IDENTICAL_YXMD` (alias of A), `POSITION_YXMD_A/B` (ToolID 902, differing Position only), and `MALFORMED_XML`
- Created `tests/test_cli.py` with 12 smoke tests covering exit codes 0/1/2, --json output structure (with governance metadata sha256_a 64-char), --quiet suppresses "changes detected" summary, --include-positions flag behavioral difference, HTML governance footer present with full SHA-256
- Fixed missing-file exit code: added `OSError` guard around `_file_sha256()` calls in `cli.py` so `FileNotFoundError` maps to exit code 2 instead of propagating as exit code 1
- Full suite: 105 tests passed, 1 xfailed (93 pre-existing + 12 new CLI tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CLI fixture library** - `5205581` (feat)
2. **Task 2: Write CLI smoke test suite** - `cfce10c` (feat)

**Plan metadata:** (this summary commit)

## Files Created/Modified

- `tests/fixtures/cli.py` - 6 byte fixture constants for CLI tests, ToolIDs 901-902
- `tests/test_cli.py` - 12 CLI smoke tests using typer.testing.CliRunner in-process
- `src/alteryx_diff/cli.py` - OSError guard around `_file_sha256()` for missing-file exit-code-2

## Decisions Made

- **CliRunner() without mix_stderr:** click 8.2+ removed the `mix_stderr` constructor argument — stdout and stderr are always separated. The plan specified `CliRunner(mix_stderr=False)` which raised `TypeError`. Removed the argument; behavior is identical.
- **No "diff" subcommand prefix in args:** The Typer app has a single `@app.command()` registered as `diff`. When invoked via CliRunner, the app exposes the command directly — no subcommand prefix in args list. The plan's `["diff", str(path_a), str(path_b)]` was incorrect for this structure.
- **OSError guard in cli.py:** `_file_sha256()` is called before `pipeline.run()`. A missing file raises `FileNotFoundError` (subclass of `OSError`) before the existing `ParseError` try/except block. Added a separate `try/except OSError` around SHA256 computation to return exit code 2 with error message on stderr.
- **12 tests not 11:** `test_diff_include_positions_detects_position_change` tests both with and without the flag in a single function (2 invoke calls). Pytest counts it as 1 test item. All planned behaviors covered.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed mix_stderr=False from CliRunner constructor**
- **Found during:** Task 2 (test collection — TypeError on import)
- **Issue:** `CliRunner(mix_stderr=False)` raises `TypeError: CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'` in click 8.3.1 (mix_stderr removed in click 8.2)
- **Fix:** Changed to `CliRunner()` — click 8.2+ always keeps stdout/stderr separate; `result.stdout` and `result.stderr` both available on all Result objects
- **Files modified:** `tests/test_cli.py`
- **Verification:** Test collection succeeds; all 12 tests runnable
- **Committed in:** `cfce10c` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed CliRunner invocation pattern — removed "diff" prefix**
- **Found during:** Task 2 (first test run — exit code 2 "Got unexpected extra argument")
- **Issue:** Plan specified `runner.invoke(app, ["diff", str(path_a), str(path_b)])` but the Typer app is a single-command app where `diff` is the registered command name exposed directly. Passing "diff" as the first positional arg caused click to treat it as WORKFLOW_A
- **Fix:** Removed "diff" from all invoke args lists: `runner.invoke(app, [str(path_a), str(path_b)])`
- **Files modified:** `tests/test_cli.py`
- **Verification:** All 12 tests pass with correct exit codes
- **Committed in:** `cfce10c` (Task 2 commit)

**3. [Rule 2 - Missing Critical] Added OSError guard in cli.py for missing-file exit code 2**
- **Found during:** Task 2 (test_diff_missing_file_exit_code_2 failed — exit code 1 instead of 2)
- **Issue:** `_file_sha256()` raises `FileNotFoundError` (subclass of `OSError`) for missing files BEFORE the `try/except ParseError` block. The exception propagated to CliRunner as exit code 1 (unhandled exception via `sys.exit(1)`)
- **Fix:** Added `try/except OSError` wrapping the two `_file_sha256()` calls in `cli.py`, echoing `"Error: {strerror}: {filename}"` to stderr and raising `typer.Exit(code=2)`
- **Files modified:** `src/alteryx_diff/cli.py`
- **Verification:** `test_diff_missing_file_exit_code_2` passes (exit code 2, "Error" in stderr)
- **Committed in:** `cfce10c` (Task 2 commit)

**4. [Rule 1 - Bug] Shortened 3 docstring lines to fit ruff E501 88-char limit**
- **Found during:** Task 2 (pre-commit ruff check caught 3 E501 violations in docstrings)
- **Issue:** 3 docstring lines in `test_cli.py` exceeded 88-char limit; ruff cannot auto-fix docstrings
- **Fix:** Shortened each docstring to fit within 88 chars while preserving meaning
- **Files modified:** `tests/test_cli.py`
- **Verification:** `ruff check tests/test_cli.py` passes with "All checks passed!"
- **Committed in:** `cfce10c` (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (2 Rule 1 - bug, 1 Rule 2 - missing critical, 1 Rule 1 - lint)
**Impact on plan:** All necessary for correctness. OSError guard (Rule 2) closes a real exit-code contract violation. CliRunner fixes adapt to the actual installed library versions. No scope creep.

## Issues Encountered

- click 8.3.1 / typer 0.24.1 installed — plan was written for an older click API (`mix_stderr` constructor arg). The actual behavior (always-separate streams) is what the tests need, just the API changed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 9 (CLI Entry Point) is now complete — all 3 plans done
- 105 tests passing (93 pre-existing + 12 new CLI smoke tests), 1 xfail
- The `acd diff` CLI is production-ready: exit codes, flags, governance metadata, JSON output all verified end-to-end
- Project is feature-complete (all 9 phases done)

## Self-Check: PASSED

- FOUND: `tests/fixtures/cli.py`
- FOUND: `tests/test_cli.py`
- FOUND: `src/alteryx_diff/cli.py`
- FOUND: `.planning/phases/09-cli-entry-point/09-03-SUMMARY.md`
- FOUND: commit `5205581` (feat(09-03): add CLI fixture library with ToolIDs 901-902)
- FOUND: commit `cfce10c` (feat(09-03): add 12 CLI smoke tests with CliRunner and fix missing-file exit code)

---
*Phase: 09-cli-entry-point*
*Completed: 2026-03-07*
