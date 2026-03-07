---
phase: 09-cli-entry-point
plan: "01"
subsystem: cli
tags: [typer, rich, cli, pipeline, exit-codes, sha256, json-output]

requires:
  - phase: 08-visual-graph
    provides: GraphRenderer for graph_html generation in CLI HTML output path
  - phase: 07-html-report
    provides: HTMLRenderer for full HTML report generation
  - phase: 06-pipeline-orchestration-and-json-renderer
    provides: pipeline.run(), DiffRequest, DiffResponse, JSONRenderer

provides:
  - Typer CLI app with `acd diff` subcommand and 6 flags (--output, --include-positions, --canvas-layout, --quiet, --json)
  - Exit code protocol: 0=no changes, 1=changes found, 2=ParseError/MissingFile
  - DiffResponse extended with doc_a and doc_b WorkflowDoc fields for GraphRenderer
  - differ.diff() extended with include_positions keyword-only parameter
  - python -m alteryx_diff shim via __main__.py
  - CLI-schema JSON output ({added, removed, modified, metadata}) separate from JSONRenderer schema

affects: [09-02-html-governance, any downstream CI/CD tooling, integration tests]

tech-stack:
  added: [typer>=0.12, rich>=13.0 (typer dependency)]
  patterns:
    - Thin adapter pattern: CLI contains zero business logic; all computation in pipeline/stage modules
    - Stderr vs stdout separation: spinner+summary to stderr, JSON to stdout for pipe-friendliness
    - SHA-256 file digest computed pre-pipeline for audit governance metadata
    - CLI-specific JSON schema distinct from JSONRenderer schema (avoids breaking 5 passing tests)

key-files:
  created:
    - src/alteryx_diff/cli.py
    - src/alteryx_diff/__main__.py
  modified:
    - src/alteryx_diff/pipeline/pipeline.py
    - src/alteryx_diff/differ/differ.py
    - pyproject.toml
    - .pre-commit-config.yaml

key-decisions:
  - "typer.* and rich.* mypy overrides added to pyproject.toml (no stubs published) — follows deepdiff/networkx pattern"
  - "typer>=0.12 and rich>=13.0 added to pre-commit mypy additional_dependencies so hook env resolves imports"
  - "_cli_json_output() built in cli.py not JSONRenderer — preserves 5 passing JSONRenderer tests, different schema"
  - "Position-only NodeDiff built directly (field_diffs={'position': ...}) — bypasses _diff_node() which raises ValueError on no config diff"
  - "Spinner skipped when --json set (even without --quiet) — avoids edge cases with stderr/stdout stream confusion in JSON parsing tools"

requirements-completed: [CLI-01, CLI-02]

duration: 7min
completed: 2026-03-07
---

# Phase 09 Plan 01: CLI Entry Point Summary

**Typer `acd diff` command wiring all pipeline stages with exit-code protocol, spinner, SHA-256 audit metadata, and `--json` stdout output for CI/CD integration**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-07T06:41:45Z
- **Completed:** 2026-03-07T06:48:39Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Extended `DiffResponse` with `doc_a`/`doc_b` fields so GraphRenderer has parsed WorkflowDoc instances
- Extended `differ.diff()` with `include_positions: bool = False` for optional canvas-position change detection
- Created `src/alteryx_diff/cli.py` with Typer app: all 6 flags, exit codes 0/1/2, spinner, SHA-256 helpers, and `_cli_json_output()` producing CI-friendly JSON schema
- Created `src/alteryx_diff/__main__.py` so `python -m alteryx_diff` works as an alias
- All 93 existing tests pass with no regressions (1 expected xfail)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend pipeline.py and differ.py** - `290994a` (feat)
2. **Task 2: Create cli.py, __main__.py and update pyproject.toml** - `56c9cc9` (feat)

**Plan metadata:** (this summary commit)

## Files Created/Modified

- `src/alteryx_diff/cli.py` - Typer app with `diff` subcommand, exit code protocol, spinner, SHA-256 helpers, CLI JSON schema
- `src/alteryx_diff/__main__.py` - `python -m alteryx_diff` shim delegating to `cli:app`
- `src/alteryx_diff/pipeline/pipeline.py` - `DiffResponse` gains `doc_a`/`doc_b` fields; `run()` gains `include_positions` param
- `src/alteryx_diff/differ/differ.py` - `diff()` gains `include_positions: bool = False` keyword-only param; position-only NodeDiff path
- `pyproject.toml` - typer>=0.12 added to dependencies; entry point updated to `alteryx_diff.cli:app`; mypy overrides for typer.* and rich.*
- `.pre-commit-config.yaml` - typer>=0.12 and rich>=13.0 added to mypy hook additional_dependencies

## Decisions Made

- **typer.*/rich.* mypy overrides:** Neither package publishes stubs. Added `ignore_missing_imports = true` overrides in pyproject.toml, following the established deepdiff/networkx pattern. Also added both as pre-commit mypy `additional_dependencies` so the isolated hook env can resolve imports.
- **CLI JSON schema separate from JSONRenderer:** `_cli_json_output()` lives in `cli.py` and produces `{added, removed, modified, metadata}`. The existing `JSONRenderer` produces `{summary, tools, connections}`. Keeping them separate avoids breaking 5 passing JSONRenderer tests.
- **Position-only NodeDiff bypass:** When `include_positions=True` and only position differs (config unchanged), `_diff_node()` would raise `ValueError` (no DeepDiff changes). Instead, `NodeDiff` is constructed directly with `field_diffs={"position": (old, new)}`.
- **Spinner skipped for --json:** Even though spinner goes to stderr (separate stream from stdout), it is skipped when `--json` is active to avoid edge cases in environments that combine stdout+stderr.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added mypy overrides for typer/rich to unblock commit hook**
- **Found during:** Task 2 (commit attempt)
- **Issue:** Pre-commit mypy hook (--strict mode) failed with `Cannot find implementation or library stub for module named "typer"` and `rich.console`. Hook runs in isolated env without project venv.
- **Fix:** Added `[[tool.mypy.overrides]]` for `typer.*` and `rich.*` with `ignore_missing_imports = true` in `pyproject.toml`. Added `typer>=0.12` and `rich>=13.0` to `.pre-commit-config.yaml` mypy `additional_dependencies`.
- **Files modified:** `pyproject.toml`, `.pre-commit-config.yaml`
- **Verification:** `mypy src/alteryx_diff/cli.py` passes; pre-commit hook passes on retry commit.
- **Committed in:** `56c9cc9` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** Required for commit hook to pass. No scope creep — follows exact same pattern as deepdiff/networkx overrides established in earlier phases.

## Issues Encountered

- `uv` binary not in PATH for Bash shell session; typer installed via `pip install` into the active `venv/` environment and via the cached `uv` binary into `.venv/`. Pre-commit hook installs typer independently via `additional_dependencies`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `acd diff a.yxmd b.yxmd` is fully functional: runs pipeline, renders HTML report, respects all exit codes
- `--json` mode produces CI-friendly JSON to stdout; `--quiet` suppresses stderr output
- Plan 09-02 (HTML governance) can now embed audit metadata (sha256_a, sha256_b, generated_at) into the HTML report — metadata is computed in `_build_governance_metadata()` and ready to pass to HTMLRenderer

---
*Phase: 09-cli-entry-point*
*Completed: 2026-03-07*
