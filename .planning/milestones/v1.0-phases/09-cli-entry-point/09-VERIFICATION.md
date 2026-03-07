---
phase: 09-cli-entry-point
verified: 2026-03-07T00:00:00Z
status: passed
score: 16/16 must-haves verified
re_verification: false
---

# Phase 9: CLI Entry Point Verification Report

**Phase Goal:** Create the CLI entry point that exposes all pipeline functionality through the `acd diff` command
**Verified:** 2026-03-07
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `acd diff a.yxmd b.yxmd` runs and produces `diff_report.html`; `--output` writes to a custom path | VERIFIED | `cli.py` writes `output.write_text(html)` at line 125; `test_diff_writes_html_report_by_default` and `test_diff_output_flag_writes_custom_path` both pass |
| 2 | Exit code is 0 (no changes), 1 (changes found), 2 (parse error / missing file) | VERIFIED | `cli.py`: `raise typer.Exit(code=0)` at line 103, `raise typer.Exit(code=1)` at line 138, `raise typer.Exit(code=2)` at lines 71, 89, 92; all three paths covered by passing tests |
| 3 | `--json` writes JSON to stdout and no HTML file is written | VERIFIED | `cli.py` calls `typer.echo(json_str)` (stdout) in `json_output` branch and skips the HTML write block; `test_diff_json_flag_writes_to_stdout` passes confirming JSON on stdout with `{added, removed, modified, metadata}` keys |
| 4 | `--quiet` suppresses spinner and summary; stdout JSON still emits when combined with `--json` | VERIFIED | `cli.py` skips spinner via `if quiet or json_output` branch and skips `typer.echo("Report written...", err=True)` when `quiet`; `test_diff_quiet_flag_suppresses_stderr` confirms "changes detected" not in stderr |
| 5 | CLI contains zero business logic; all computation stays in pipeline and stage modules | VERIFIED | `cli.py` imports and calls `pipeline.run(DiffRequest(...))`, delegates to `GraphRenderer` and `HTMLRenderer`; no diff computation in `cli.py` itself |
| 6 | `acd --help` documents all flags with clear descriptions | VERIFIED | `python -m alteryx_diff --help` shows all 5 flags: `--output`, `--include-positions`, `--canvas-layout`, `--quiet`, `--json` with clear help text |
| 7 | HTML report contains a collapsed governance footer with File A path, SHA-256 A, File B path, SHA-256 B, and generated timestamp | VERIFIED | `html_renderer.py` `_TEMPLATE` contains `<details id="governance">` block with all 5 ALCOA+ fields; `test_diff_html_report_contains_governance_metadata` verifies full 64-char SHA-256 present in HTML output |
| 8 | The footer is collapsed by default (HTML `<details>`/`<summary>`) — auditors expand manually | VERIFIED | `html_renderer.py` uses `<details id="governance" ...>` / `<summary>` elements (no JS required) |
| 9 | SHA-256 values are the full 64-char hex string (ALCOA+ requirement) | VERIFIED | `_file_sha256()` uses `hashlib.file_digest(...).hexdigest()` producing 64-char hex; `test_diff_json_flag_writes_to_stdout` asserts `len(data["metadata"]["sha256_a"]) == 64` |
| 10 | Governance metadata appears only in the report file, not in terminal output | VERIFIED | `_build_governance_metadata()` result is passed to `HTMLRenderer().render(metadata=metadata)` only; no terminal echo of SHA-256 values anywhere in `cli.py` |
| 11 | `HTMLRenderer.render()` accepts a `metadata` dict parameter and embeds it in the template | VERIFIED | `html_renderer.py` line 286: `metadata: dict[str, Any] | None = None` keyword arg; passed to `template.render(..., metadata=metadata)` at line 322 |
| 12 | `cli.py` passes `metadata=metadata` to `HTMLRenderer().render()` | VERIFIED | `cli.py` line 123: `metadata=metadata,  # CLI-04: governance footer in HTML report` |
| 13 | Exit code 0 when both inputs are identical | VERIFIED | `test_diff_identical_files_exit_code_0` passes |
| 14 | Exit code 2 when a file is missing | VERIFIED | OSError guard wraps `_file_sha256()` calls; `test_diff_missing_file_exit_code_2` passes with "Error" in stderr |
| 15 | Exit code 2 when XML is malformed | VERIFIED | `MalformedXMLError` caught and mapped to `typer.Exit(code=2)`; `test_diff_malformed_xml_exit_code_2` passes |
| 16 | `--include-positions` flag: position-only change produces exit code 1 | VERIFIED | `differ.diff()` accepts `include_positions: bool = False`; position-only `NodeDiff` constructed directly bypassing `_diff_node()`; `test_diff_include_positions_detects_position_change` verifies exit 0 without flag, exit 1 with flag |

**Score:** 16/16 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/alteryx_diff/cli.py` | Typer app with diff subcommand, all flags, exit code protocol, spinner, SHA-256 helpers | VERIFIED | 205 lines; `app = typer.Typer(no_args_is_help=True)`; all 5 flags declared; exit codes 0/1/2 implemented; `_file_sha256()` and `_build_governance_metadata()` present |
| `src/alteryx_diff/__main__.py` | `python -m alteryx_diff` shim | VERIFIED | 5 lines: `from alteryx_diff.cli import app; app()` — confirmed substantive, not a stub |
| `src/alteryx_diff/pipeline/pipeline.py` | Extended `DiffResponse` carrying `doc_a` + `doc_b` for GraphRenderer | VERIFIED | `DiffResponse` dataclass has `result: DiffResult`, `doc_a: WorkflowDoc`, `doc_b: WorkflowDoc`; `run()` accepts `include_positions: bool = False` |
| `src/alteryx_diff/differ/differ.py` | `diff()` accepts `include_positions: bool = False` | VERIFIED | Line 36: `include_positions: bool = False` keyword-only param; position-only `NodeDiff` path implemented at lines 69-77 |
| `pyproject.toml` | `typer>=0.12` dependency; entry point `acd = "alteryx_diff.cli:app"` | VERIFIED | `typer>=0.12` in dependencies list; `acd = "alteryx_diff.cli:app"` in `[project.scripts]` |
| `src/alteryx_diff/renderers/html_renderer.py` | Updated `_TEMPLATE` with `<details>` governance footer; `render()` accepts `metadata: dict | None` | VERIFIED | `_TEMPLATE` contains `{% if metadata %}<details id="governance">...{% endif %}` at lines 131-144; `metadata: dict[str, Any] | None = None` at line 286 |
| `tests/fixtures/cli.py` | Minimal `.yxmd` byte fixtures for CLI tests (ToolIDs 901+) | VERIFIED | 86 lines; 6 constants: `MINIMAL_YXMD_A`, `MINIMAL_YXMD_B`, `IDENTICAL_YXMD`, `POSITION_YXMD_A`, `POSITION_YXMD_B`, `MALFORMED_XML` |
| `tests/test_cli.py` | 12 CLI smoke tests using `CliRunner` | VERIFIED | 243 lines; 12 test functions covering all exit codes, flags, HTML governance, and JSON output; all 12 pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/alteryx_diff/cli.py` | `src/alteryx_diff/pipeline/pipeline.py` | `from alteryx_diff.pipeline import DiffRequest, run` | WIRED | Line 13 import; `run(DiffRequest(...), include_positions=include_positions)` called at lines 77-86 |
| `src/alteryx_diff/cli.py` | `src/alteryx_diff/exceptions.py` | `MalformedXMLError`/`ParseError` catch -> exit code 2 | WIRED | Lines 87-92: `except MalformedXMLError ... raise typer.Exit(code=2)`; `except ParseError ... raise typer.Exit(code=2)` |
| `src/alteryx_diff/pipeline/pipeline.py` | `doc_a`, `doc_b` | `DiffResponse` carries both `WorkflowDoc` instances | WIRED | `DiffResponse` fields `doc_a: WorkflowDoc`, `doc_b: WorkflowDoc`; `return DiffResponse(result=diff_result, doc_a=doc_a, doc_b=doc_b)` at line 56 |
| `src/alteryx_diff/cli.py` | `src/alteryx_diff/renderers/html_renderer.py` | `HTMLRenderer().render(..., metadata=metadata)` | WIRED | Line 118-124: `html = HTMLRenderer().render(result, ..., metadata=metadata,)` |
| `src/alteryx_diff/renderers/html_renderer.py` | `_TEMPLATE` governance section | Jinja2 `{{ metadata.sha256_a }}` inside `<details>` block | WIRED | Lines 131-144: `{% if metadata %}<details id="governance">...<div><strong>SHA-256 A:</strong> {{ metadata.sha256_a }}</div>...{% endif %}` |
| `tests/test_cli.py` | `src/alteryx_diff/cli.py` | `from alteryx_diff.cli import app; CliRunner().invoke(app, [...])` | WIRED | Line 22: import; `runner.invoke(app, [...])` in all 12 test functions |
| `tests/fixtures/cli.py` | `tests/test_cli.py` | `IDENTICAL_YXMD`, `MINIMAL_YXMD_A/B`, `POSITION_YXMD_A/B`, `MALFORMED_XML` byte constants | WIRED | Lines 23-30: all 6 constants imported and used across 10 of the 12 test functions |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLI-01 | 09-01, 09-03 | User can run `acd workflow_v1.yxmd workflow_v2.yxmd` and receive `diff_report.html`; `--output` for custom path | SATISFIED | `cli.py` wires pipeline to HTML output; `--output` flag at line 29; `test_diff_writes_html_report_by_default` and `test_diff_output_flag_writes_custom_path` both pass |
| CLI-02 | 09-01, 09-03 | System exits with codes 0 = no differences, 1 = differences detected, 2 = error | SATISFIED | Three `typer.Exit(code=N)` paths in `cli.py`; all verified by passing tests (`test_diff_identical_files_exit_code_0`, `test_diff_different_files_exit_code_1`, `test_diff_missing_file_exit_code_2`, `test_diff_malformed_xml_exit_code_2`) |
| CLI-04 | 09-02, 09-03 | Report includes governance metadata: source file paths, SHA-256 file hashes, generation timestamp (ALCOA+ audit compliance) | SATISFIED | `_build_governance_metadata()` in `cli.py`; `metadata` param wired to `HTMLRenderer.render()` and `_cli_json_output()`; governance footer in `_TEMPLATE`; `test_diff_html_report_contains_governance_metadata` and `test_diff_json_flag_writes_to_stdout` (sha256 length assertion) both pass |

**Orphaned requirement check:**
REQUIREMENTS.md Traceability table maps CLI-01 → Phase 9, CLI-02 → Phase 9, CLI-03 → Phase 6, CLI-04 → Phase 9. CLI-03 is Phase 6 scope (`JSONRenderer`) and was verified in Phase 6 verification. No Phase 9 plans claimed CLI-03. No orphaned requirements for Phase 9.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODOs, FIXMEs, placeholders, empty return values, or stub implementations found in any Phase 9 files. All handler functions perform real operations.

---

### Human Verification Required

#### 1. Spinner display in real terminal

**Test:** Run `acd diff a.yxmd b.yxmd` in a real terminal (not CliRunner) against two differing workflow files.
**Expected:** Animated dots spinner appears on stderr while pipeline runs; spinner clears automatically when done; "Report written to diff_report.html (N changes detected)" summary appears.
**Why human:** CliRunner does not emulate a real TTY; Rich's spinner behavior depends on TTY detection and cannot be reliably asserted in automated tests.

#### 2. `--canvas-layout` graph positioning

**Test:** Run `acd diff a.yxmd b.yxmd --canvas-layout --output report.html` and open the HTML in a browser.
**Expected:** Graph nodes are positioned using Alteryx canvas X/Y coordinates rather than hierarchical auto-layout.
**Why human:** Visual graph layout cannot be verified from HTML string alone; requires browser rendering.

#### 3. HTML report readability and UX

**Test:** Open a generated `diff_report.html` in a browser; click the "Governance Metadata (ALCOA+)" disclosure triangle; verify the footer expands showing file paths, full 64-char SHA-256 values, and timestamp.
**Expected:** Footer is collapsed by default, expands on click, all fields readable.
**Why human:** Visual/interactive behavior cannot be verified programmatically.

---

### Test Suite Summary

| Suite | Tests | Result |
|-------|-------|--------|
| `tests/test_cli.py` | 12 | 12 passed |
| Full suite (`tests/`) | 105 + 1 xfail | 105 passed, 1 xfailed (pre-existing), 0 failed |

Full regression check: **105 passed, 1 xfailed** — no regressions introduced to any prior phase tests.

---

### Summary

Phase 9 has fully achieved its goal. The `acd diff` CLI entry point is wired end-to-end:

- All five flags (`--output`, `--include-positions`, `--canvas-layout`, `--quiet`, `--json`) are implemented with correct behavior
- Three-tier exit code protocol (0/1/2) is implemented and guarded by OSError + ParseError handlers
- `DiffResponse` extended with `doc_a`/`doc_b` for GraphRenderer
- `differ.diff()` extended with `include_positions` for canvas position detection
- ALCOA+ governance footer embedded in HTML via Jinja2 `<details>` block
- `pyproject.toml` entry point updated to `alteryx_diff.cli:app` with `typer>=0.12` dependency
- `__main__.py` shim enables `python -m alteryx_diff`
- 12 CLI smoke tests cover all behavioral contracts; all pass

Three items flagged for human verification are non-blocking visual/UX behaviors (spinner, graph layout, footer UX). All automated must-haves pass.

---

_Verified: 2026-03-07_
_Verifier: Claude (gsd-verifier)_
