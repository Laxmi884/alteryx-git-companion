---
phase: 17
slug: branch-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini or pyproject.toml |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | BRANCH-01 | unit | `pytest tests/test_git_ops.py::test_create_experiment_branch -x -q` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | BRANCH-01 | unit | `pytest tests/test_git_ops.py::test_branch_name_format -x -q` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 1 | BRANCH-02 | unit | `pytest tests/test_git_ops.py::test_list_branches -x -q` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 1 | BRANCH-02 | unit | `pytest tests/test_git_ops.py::test_switch_branch -x -q` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 2 | BRANCH-03 | unit | `pytest tests/test_routers.py::test_branch_status_endpoint -x -q` | ❌ W0 | ⬜ pending |
| 17-03-02 | 03 | 2 | BRANCH-03 | manual | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_git_ops.py` — stubs for BRANCH-01, BRANCH-02
- [ ] `tests/test_routers.py` — stubs for BRANCH-03 (branch status endpoint)

*Existing test infrastructure (pytest) covers the framework; only new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Branch label shown in UI header | BRANCH-03 | Frontend UI state — no automated DOM test | Open app, check header shows current branch name as plain text label |
| Switching branches updates UI label | BRANCH-02 | React state update — visual verification | Switch branch from popover, verify label updates without page reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
