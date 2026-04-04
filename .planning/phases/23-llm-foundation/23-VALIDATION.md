---
phase: 23
slug: llm-foundation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/llm/ -x -q` |
| **Full suite command** | `uv run pytest tests/ --ignore=tests/test_cli.py -x -q --deselect tests/test_remote.py::test_post_push_success --deselect tests/test_remote.py::test_push_repo_deleted` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/llm/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ --ignore=tests/test_cli.py -x -q --deselect tests/test_remote.py::test_post_push_success --deselect tests/test_remote.py::test_push_repo_deleted`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | CORE-01 | unit | `uv run pytest tests/llm/test_require_llm_deps.py -x -q` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 1 | CORE-01 | integration | `uv run pytest tests/ --ignore=tests/test_cli.py -x -q --deselect tests/test_remote.py::test_post_push_success --deselect tests/test_remote.py::test_push_repo_deleted` | ✅ | ⬜ pending |
| 23-01-03 | 01 | 2 | CORE-02 | unit | `uv run pytest tests/llm/test_context_builder.py -x -q` | ❌ W0 | ⬜ pending |
| 23-01-04 | 01 | 2 | CORE-02 | unit | `uv run pytest tests/llm/test_context_builder.py -x -q -k build_from_diff` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/llm/__init__.py` — empty file to make `tests/llm/` a package
- [ ] `tests/llm/test_require_llm_deps.py` — stubs for CORE-01 import guard tests
- [ ] `tests/llm/test_context_builder.py` — stubs for CORE-02 ContextBuilder tests

*Existing pytest infrastructure covers the core suite; only new test stubs needed for LLM tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fresh venv zero-import check | CORE-01 SC-1 | Requires isolated venv without llm extras | `python -m venv /tmp/test_venv && /tmp/test_venv/bin/pip install alteryx-diff && /tmp/test_venv/bin/python -c "import alteryx_diff; print('OK')"` |
| Full `[llm]` extras install | CORE-01 SC-2 | Requires pip install with extras | `pip install "alteryx-diff[llm]"` then verify langchain/langgraph importable |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (tests/llm/ stubs in Task 0)
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-04
