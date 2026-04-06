---
phase: 24
slug: documentation-graph-docrenderer-ollama
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-04
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/llm/ -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~30 seconds (core), ~60 seconds (llm with real model) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/llm/ -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 1 | D-01/D-02 | unit | `uv run pytest tests/llm/test_models.py -x -q` | ❌ W0 | ⬜ pending |
| 24-01-02 | 01 | 1 | D-11/D-13 | unit | `uv run pytest tests/llm/test_context_builder.py -x -q` | ✅ | ⬜ pending |
| 24-02-01 | 02 | 2 | D-07/D-09 | unit | `uv run pytest tests/llm/test_doc_graph.py -x -q` | ✅ W0 | ⬜ pending |
| 24-02-02 | 02 | 2 | D-10 | unit | `uv run pytest tests/llm/test_doc_graph.py -x -q` | ✅ W0 | ⬜ pending |
| 24-03-01 | 03 | 2 | EVAL-01 | unit | `uv run pytest tests/llm/test_doc_graph.py::test_provider_agnostic -x -q` | ✅ W0 | ⬜ pending |
| 24-03-02 | 03 | 2 | D-17 | unit | `uv run pytest tests/llm/ -x -q` | ✅ | ⬜ pending |
| 24-04-01 | 03 | 2 | CORE-04 | unit | `uv run pytest tests/llm/test_doc_renderer.py -x -q` | ✅ W0 | ⬜ pending |
| 24-04-02 | 03 | 2 | CORE-04 | unit | `uv run pytest tests/llm/test_doc_renderer.py -x -q` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/llm/test_models.py` — stubs for WorkflowDocumentation and ToolNote
- [ ] `tests/llm/test_doc_graph.py` — stubs for build_doc_graph and generate_documentation
- [ ] `tests/llm/test_doc_renderer.py` — stubs for DocRenderer markdown and HTML output

*Existing infrastructure covers framework; only test file stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ollama round-trip (real model) | D-15 | Requires running Ollama server | `ollama serve && python -c "from langchain_ollama import ChatOllama; from alteryx_diff.llm.doc_graph import generate_documentation; ..."` |
| OpenRouter round-trip (real API) | D-16 | Requires API key | Set `OPENROUTER_API_KEY` and run integration test manually |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
