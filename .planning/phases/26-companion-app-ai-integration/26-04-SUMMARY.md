---
phase: 26-companion-app-ai-integration
plan: "04"
subsystem: frontend
tags: [react, hooks, sse, eventsource, ai-summary, diffviewer]
dependency_graph:
  requires: [26-03]
  provides: [APPAI-02-frontend]
  affects: [app/frontend/src/hooks/useAISummary.ts, app/frontend/src/components/DiffViewer.tsx]
tech_stack:
  added: []
  patterns: [request-scoped-eventsource, sse-hook, streaming-ui]
key_files:
  created:
    - app/frontend/src/hooks/useAISummary.ts
  modified:
    - app/frontend/src/components/DiffViewer.tsx
decisions:
  - "useAISummary opens EventSource inside trigger() only — never on mount; request-scoped per D-08"
  - "Reset useEffect on sha/file/folder deps prevents stale AI state when navigating between diffs"
  - "AI panel gated by !isFirstCommit (D-05) — first-commit diffs never show the panel"
  - "AISummaryStatus union uses separate unavailable_no_extras / unavailable_no_model variants for distinct copy per UI-SPEC"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-06T01:37:00Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 26 Plan 04: AI Summary Frontend Hook + DiffViewer Panel Summary

APPAI-02 frontend complete: request-scoped useAISummary hook with EventSource lifecycle management and a full 5-state AI panel wired into DiffViewer between the sticky header and the diff iframe.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create useAISummary hook (request-scoped EventSource) | d970e0d | app/frontend/src/hooks/useAISummary.ts (new, 113 lines) |
| 2 | Add AI summary panel to DiffViewer | c759115 | app/frontend/src/components/DiffViewer.tsx (+97 lines) |

## What Was Built

### Task 1 — useAISummary hook

New file `app/frontend/src/hooks/useAISummary.ts` — a request-scoped EventSource hook that:

- Exports `AISummaryStatus` union type: `idle | loading | result | unavailable_no_extras | unavailable_no_model | error`
- Exports `UseAISummaryReturn` interface with `status`, `steps`, `narrative`, `risks`, `errorDetail`, `trigger()`, `reset()`
- Opens an `EventSource` to `/api/ai/summary?folder=...&sha=...&file=...` only inside `trigger()` — never on mount
- Handles all backend SSE event types: `progress` (appends to `steps[]`), `result` (sets narrative + risks + closes), `unavailable` (sets status variant + closes), `error` (sets errorDetail + closes)
- Closes stream on `onerror` (sets error status)
- Cleanup `useEffect` closes any active stream on component unmount — prevents leaked connections
- `trigger()` closes any previous stream before opening a new one — supports Regenerate without leaks
- `reset()` closes stream and resets all state to idle — called when navigating between diffs

### Task 2 — DiffViewer AI panel

Modified `app/frontend/src/components/DiffViewer.tsx` to add:

- Three new imports: `useAISummary`, `Button`, `Card`/`CardContent`
- `const ai = useAISummary()` inside function body
- Reset `useEffect` on `[sha, file, folder]` — clears AI state on diff navigation
- AI panel JSX between sticky header and content area, gated by `!isFirstCommit` (D-05)
- Five rendered states:
  1. **Idle**: `Button` with "Generate AI summary" — calls `ai.trigger(folder, sha, file)`
  2. **Loading**: previous steps as muted `<p>` list, spinner + current step label
  3. **Result**: `Card` with narrative text + optional risks `<ul>`, "Regenerate" `Button`
  4. **Unavailable no_extras**: muted `<p>` "AI summary unavailable — install LLM extras"
  5. **Unavailable no_model**: muted `<p>` "No LLM model configured"
  6. **Error**: "Summary failed — {detail}. Retry?" with inline `<button>` to retry
- `role="status"` + `aria-live="polite"` on the panel container per UI-SPEC accessibility

All UI-SPEC copy strings present verbatim (em-dash U+2014 in unavailable message).

## Verification Results

- `tsc --noEmit`: zero errors
- `npm run build` (Vite): clean build — 1843 modules transformed, 14.35s, zero warnings on new code
- All acceptance criteria assertions pass (grep counts all 1+)
- Existing sticky header, compare toggle, error state, loading spinner, iframe render — unchanged

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — the AI panel connects to the live `/api/ai/summary` SSE endpoint implemented in Plan 03.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. The EventSource URL is constructed with `encodeURIComponent` on all three query parameters.

## Self-Check: PASSED

- `app/frontend/src/hooks/useAISummary.ts` — FOUND
- `app/frontend/src/components/DiffViewer.tsx` — FOUND (modified)
- Commit d970e0d — FOUND (feat: create useAISummary hook)
- Commit c759115 — FOUND (feat: add AI summary panel to DiffViewer)
