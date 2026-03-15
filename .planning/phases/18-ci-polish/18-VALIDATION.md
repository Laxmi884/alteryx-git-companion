---
phase: 18
slug: ci-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual inspection + YAML linting |
| **Config file** | none — CI template files only |
| **Quick run command** | `cat ci-templates/github/workflow.yml | head -50` |
| **Full suite command** | `find ci-templates/ -type f | xargs ls -la` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Verify file exists and content matches intent
- **After every plan wave:** Run `find ci-templates/ -type f | xargs ls -la`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | CI-01 | manual | `grep "listComments\|updateComment" ci-templates/github/workflow.yml` | ✅ | ⬜ pending |
| 18-01-02 | 01 | 1 | CI-02 | manual | `grep "base64\|image/png\|inline" ci-templates/github/workflow.yml` | ✅ | ⬜ pending |
| 18-02-01 | 02 | 1 | CI-03 | manual | `grep -v "test-job" ci-templates/gitlab/.gitlab-ci.yml` | ✅ | ⬜ pending |
| 18-03-01 | 03 | 2 | CI-04 | manual | `wc -l ci-templates/README.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. This phase modifies CI template YAML/markdown files only — no test framework needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PR comment updates instead of creating new | CI-01 | Requires GitHub Actions runtime | Check workflow YAML uses find-or-update pattern with `<!-- acd-diff-report -->` marker |
| PNG embedded inline in PR comment | CI-02 | Requires GitHub Actions runtime | Check YAML encodes PNG as base64 and embeds in comment body |
| No test-job in GitLab CI | CI-03 | File inspection | `grep "test-job" ci-templates/gitlab/.gitlab-ci.yml` returns empty |
| README complete setup instructions | CI-04 | Content quality judgment | Read README — covers token setup, file copy, and trigger config for both GitHub and GitLab |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
