---
phase: 26
slug: companion-app-ai-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` or `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | APPAI-01 | — | Business context stored in .acd/context.json | unit | `uv run pytest tests/test_save.py -k business_context -x -q` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 1 | APPAI-02 | — | SSE endpoint module importable and router registered | unit | `uv run pytest tests/test_ai.py -x -q` | ❌ W0 | ⬜ pending |
| 26-02-01 | 02 | 2 | APPAI-01 | — | business_context field accepted and .acd/context.json written | unit | `uv run pytest tests/test_save.py -k business_context -x -q` | ❌ W0 | ⬜ pending |
| 26-02-02 | 02 | 2 | APPAI-02 | — | Graceful degradation when LLM not installed | unit | `uv run pytest tests/test_ai.py -k no_extras -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_save.py` — extended with RED stubs for APPAI-01 (business context save, 4 tests)
- [ ] `tests/test_ai.py` — new file with RED stubs for APPAI-02 (SSE streaming, LLM graceful degradation, 5 tests)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE streaming live progress in browser | APPAI-02 | EventSource requires browser rendering | Open companion app, navigate to a saved version, click AI summary — verify progress messages stream before final text appears |
| Business context field visible on first commit | APPAI-01 | Requires new project with no prior commit | Create new project, open companion app — verify textarea is present before first commit |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
