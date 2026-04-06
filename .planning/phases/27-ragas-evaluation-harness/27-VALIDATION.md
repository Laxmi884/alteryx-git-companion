---
phase: 27
slug: ragas-evaluation-harness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/eval/ -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/eval/ -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | EVAL-02 | — | N/A | integration | `python tests/eval/ragas_eval.py` | ❌ W0 | ⬜ pending |
| 27-01-02 | 01 | 1 | EVAL-02 | — | N/A | unit | `pytest tests/eval/test_ragas_eval.py -x -q` | ❌ W0 | ⬜ pending |
| 27-01-03 | 01 | 1 | EVAL-02 | — | N/A | integration | `python tests/eval/ragas_eval.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/eval/ragas_eval.py` — main evaluation script
- [ ] `tests/eval/fixtures/` — sample workflow XML fixtures
- [ ] `tests/eval/test_ragas_eval.py` — unit tests for helper functions (bridge logic, LLM builder)

*Existing pytest infrastructure covers most requirements; only eval-specific files need creation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Faithfulness score ≥ 0.8 against real LLM | EVAL-02 | Requires live LLM API key and is non-deterministic | Run `python tests/eval/ragas_eval.py` with valid API key set, verify score printed per sample |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
