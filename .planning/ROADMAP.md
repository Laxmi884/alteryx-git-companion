# Roadmap: Alteryx Canvas Diff (ACD)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-9 (shipped 2026-03-07)
- 🚧 **v1.1 Alteryx Git Companion** — Phases 10-18 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-9) — SHIPPED 2026-03-07</summary>

- [x] Phase 1: Scaffold and Data Models (3/3 plans) — completed 2026-03-01
- [x] Phase 2: XML Parser and Validation (2/2 plans) — completed 2026-03-01
- [x] Phase 3: Normalization Layer (4/4 plans) — completed 2026-03-02
- [x] Phase 4: Node Matcher (3/3 plans) — completed 2026-03-02
- [x] Phase 5: Diff Engine (3/3 plans) — completed 2026-03-06
- [x] Phase 6: Pipeline Orchestration and JSON Renderer (3/3 plans) — completed 2026-03-06
- [x] Phase 7: HTML Report (2/2 plans) — completed 2026-03-06
- [x] Phase 8: Visual Graph (3/3 plans) — completed 2026-03-07
- [x] Phase 9: CLI Entry Point (3/3 plans) — completed 2026-03-07

Full phase details: [.planning/milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

### 🚧 v1.1 Alteryx Git Companion (In Progress)

**Milestone Goal:** Make Git-based version control accessible to non-technical Alteryx analysts via a desktop companion app (local web server, system tray, auto-start) and polished CI integration.

## Phase Details

### Phase 10: App Scaffold
**Goal**: A distributable Windows .exe launches a local web server and opens the app UI in a browser with reliable port handling
**Depends on**: Phase 9 (acd CLI bundled as dependency)
**Requirements**: APP-01, APP-03, APP-04
**Success Criteria** (what must be TRUE):
  1. User installs the app on a Windows machine without installing Python — the .exe runs standalone
  2. App starts a local web server on port 7433 and automatically tries 7434–7443 if that port is already in use
  3. Opening the app launches a browser tab at the correct localhost:PORT URL
  4. acd diff CLI is bundled inside the .exe and accessible to the FastAPI backend at runtime
**Plans**: 3 plans

Plans:
- [ ] 10-01-PLAN.md — FastAPI backend + port probe + entry point + unit tests
- [ ] 10-02-PLAN.md — React + Vite + shadcn/ui frontend scaffold + Makefile
- [ ] 10-03-PLAN.md — PyInstaller spec + version_info + icon + GitHub Actions release CI

### Phase 11: Onboarding and Project Management
**Goal**: New users are guided through first-run setup and can register and switch between multiple workflow project folders
**Depends on**: Phase 10
**Requirements**: ONBOARD-01, ONBOARD-02, ONBOARD-03, ONBOARD-04
**Success Criteria** (what must be TRUE):
  1. First-time user sees a welcome screen explaining what the app does before any setup step is required
  2. User can add a workflows folder — app auto-runs git init if the folder has no git history
  3. App detects missing git user.name / git user.email and prompts the user to enter their name and email before the first save
  4. User can register multiple project folders and switch between them from a left-panel project list
**Plans**: 5 plans

Plans:
- [ ] 11-01-PLAN.md — Install deps + backend/test scaffolding + frontend shadcn/zustand setup (Wave 1)
- [ ] 11-02-PLAN.md — Backend: config_store, git_ops, all 3 routers implemented + tests GREEN (Wave 2)
- [ ] 11-03-PLAN.md — Frontend: Zustand store, AppShell, Sidebar, WelcomeScreen, EmptyState (Wave 2, parallel)
- [ ] 11-04-PLAN.md — Wiring: register routers in server.py, GitIdentityCard, folder picker flow (Wave 3)
- [ ] 11-05-PLAN.md — Human verification checkpoint: full onboarding flow end-to-end (Wave 4)

### Phase 12: File Watcher
**Goal**: The app continuously monitors registered folders and surfaces detected changes with appropriate warnings
**Depends on**: Phase 11
**Requirements**: WATCH-01, WATCH-02, WATCH-03
**Success Criteria** (what must be TRUE):
  1. App detects when a .yxmd or .yxwz file in a registered folder is modified and shows a change badge in the UI
  2. App automatically uses polling (5-second interval) for network/SMB/UNC paths and native OS file events for local drives — no manual configuration required
  3. When a user is about to save their first version in a folder that already contains workflows, the app warns them how many files will be captured in the initial commit
**Plans**: TBD

### Phase 13: Save Version
**Goal**: Users can intentionally save a named version of changed workflows, undo the last save, and safely discard uncommitted changes
**Depends on**: Phase 12
**Requirements**: SAVE-01, SAVE-02, SAVE-03
**Success Criteria** (what must be TRUE):
  1. User can select which changed workflows to include, write a commit message with placeholder guidance, and save a version with one button
  2. User can undo the last saved version with one click — a confirmation dialog explains that file contents are preserved and only the version record is removed
  3. Discarding uncommitted changes moves the affected files to a .acd-backup folder rather than permanently deleting them
**Plans**: TBD

### Phase 14: History and Diff Viewer
**Goal**: Users can browse a flat timeline of saved versions and view the ACD diff report for any version inline
**Depends on**: Phase 13
**Requirements**: HIST-01, HIST-02
**Success Criteria** (what must be TRUE):
  1. User sees a flat timeline of saved versions per project showing date, commit message, and author — no branch DAG is shown
  2. Clicking any history entry embeds the ACD HTML diff report inline in the app (no separate browser tab or file download required)
**Plans**: TBD

### Phase 15: System Tray and Auto-start
**Goal**: The app runs silently in the background on Windows boot and communicates its status through a system tray icon
**Depends on**: Phase 14
**Requirements**: APP-02, APP-05
**Success Criteria** (what must be TRUE):
  1. App starts automatically when Windows boots and runs silently without opening a browser or blocking the user
  2. System tray icon reflects current app state — watching (active), changes detected (badge), idle — and opens the browser UI when clicked
**Plans**: TBD

### Phase 16: Remote Auth and Push
**Goal**: Users can authenticate with GitHub or GitLab and back up saved versions to a remote with a single button
**Depends on**: Phase 15
**Requirements**: REMOTE-01, REMOTE-02, REMOTE-03, REMOTE-04
**Success Criteria** (what must be TRUE):
  1. User can connect to GitHub using a browser-based OAuth flow — no PAT or command-line steps required
  2. User can connect to GitLab using a personal access token with in-app step-by-step instructions and a direct link to the GitLab token settings page
  3. Auth credentials survive app restarts — stored in Windows Credential Manager or macOS Keychain via the OS credential store, never in plaintext
  4. User can push saved versions to the connected remote with a single button click
**Plans**: TBD

### Phase 17: Branch Management
**Goal**: Users can create experiment copies of their project, switch between them, and always see which copy they are working on
**Depends on**: Phase 16
**Requirements**: BRANCH-01, BRANCH-02, BRANCH-03
**Success Criteria** (what must be TRUE):
  1. User can create an experiment copy with an auto-generated name in the format experiment/YYYY-MM-DD-description
  2. User can switch between experiment copies from within the app
  3. The current workspace (branch) is shown as a plain text label in the UI — no graph or DAG visualization is displayed
**Plans**: TBD

### Phase 18: CI Polish
**Goal**: CI template files live in the alteryx_diff repo under ci-templates/, are polished and production-ready, and ship with a setup README so users copy them into their own workflow repos
**Depends on**: Nothing (independent of desktop app — can execute in parallel with any phase)
**Requirements**: CI-01, CI-02, CI-03, CI-04
**Success Criteria** (what must be TRUE):
  1. GitHub Actions workflow updates the existing PR comment on each push instead of posting a new comment — one comment per PR regardless of push count
  2. GitHub Actions embeds the workflow graph diff as an inline PNG image in the PR comment body — no ZIP attachment or download link is required
  3. GitLab CI config no longer contains the placeholder test-job step
  4. ci-templates/README.md provides complete step-by-step setup instructions for both GitHub Actions and GitLab CI so a new user can configure it without reading source
**Plans**: TBD

## Progress

**Execution Order:** 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 (Phase 18 independent)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Scaffold and Data Models | v1.0 | 3/3 | Complete | 2026-03-01 |
| 2. XML Parser and Validation | v1.0 | 2/2 | Complete | 2026-03-01 |
| 3. Normalization Layer | v1.0 | 4/4 | Complete | 2026-03-02 |
| 4. Node Matcher | v1.0 | 3/3 | Complete | 2026-03-02 |
| 5. Diff Engine | v1.0 | 3/3 | Complete | 2026-03-06 |
| 6. Pipeline Orchestration and JSON Renderer | v1.0 | 3/3 | Complete | 2026-03-06 |
| 7. HTML Report | v1.0 | 2/2 | Complete | 2026-03-06 |
| 8. Visual Graph | v1.0 | 3/3 | Complete | 2026-03-07 |
| 9. CLI Entry Point | v1.0 | 3/3 | Complete | 2026-03-07 |
| 10. App Scaffold | v1.1 | 3/3 | Complete    | 2026-03-13 |
| 11. Onboarding and Project Management | v1.1 | 0/5 | Not started | - |
| 12. File Watcher | v1.1 | 0/TBD | Not started | - |
| 13. Save Version | v1.1 | 0/TBD | Not started | - |
| 14. History and Diff Viewer | v1.1 | 0/TBD | Not started | - |
| 15. System Tray and Auto-start | v1.1 | 0/TBD | Not started | - |
| 16. Remote Auth and Push | v1.1 | 0/TBD | Not started | - |
| 17. Branch Management | v1.1 | 0/TBD | Not started | - |
| 18. CI Polish | v1.1 | 0/TBD | Not started | - |
