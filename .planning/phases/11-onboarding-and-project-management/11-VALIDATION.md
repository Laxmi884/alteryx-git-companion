---
phase: 11
slug: onboarding-and-project-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-02-01 | 02 | 1 | ONBOARD-02 | unit | `pytest tests/test_projects.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | ONBOARD-02 | integration | `pytest tests/test_projects.py::test_git_init -x -q` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 1 | ONBOARD-03 | unit | `pytest tests/test_git_identity.py -x -q` | ❌ W0 | ⬜ pending |
| 11-04-01 | 04 | 2 | ONBOARD-04 | e2e | manual — verify project switching updates file list | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_projects.py` — stubs for ONBOARD-01 first-run detection, ONBOARD-02 folder add + git init, ONBOARD-04 project switching
- [ ] `tests/test_git_identity.py` — stubs for ONBOARD-03 git identity detection
- [ ] `tests/conftest.py` — shared fixtures (tmp dirs, mock config)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Welcome screen shown on first launch | ONBOARD-01 | Requires browser window to render; no headless test | Launch app fresh (no config), verify welcome screen appears before any other UI |
| Project list shows in left panel | ONBOARD-04 | UI layout verification | Add 2 projects, verify both appear in left panel and clicking switches active project |
| Native folder picker opens | ONBOARD-02 | OS dialog; cannot be automated headlessly | Click "Add folder" button, verify OS file picker opens |
| Folder with no git history: notification dialog appears after add | ONBOARD-02 | Requires OS folder picker + live backend | Add a non-git folder; verify notification dialog shown after add, not before |
| Folder with existing git history: added silently | ONBOARD-02 | Requires OS folder picker + live backend | Add a git repo folder; verify NO dialog appears at any point |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
