# Phase 26: Companion App AI Integration - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Add two AI features to the companion app:
1. **Business context field** — shown on the first commit in a new project; user input stored in `.acd/context.json` in the project folder; passed as grounding context to subsequent LLM doc generation
2. **AI change summary panel** — in the diff viewer, shows an on-demand AI-generated narrative of the diff, streamed live via SSE with step-by-step progress updates

No new LLM pipeline logic — consume the existing `generate_change_narrative()` from `doc_graph.py` and `ContextBuilder.build_from_diff()` from Phase 25. No CLI changes in this phase.

</domain>

<decisions>
## Implementation Decisions

### Business Context Field

- **D-01:** The field appears **once — on the first commit in a new project only**. `hasAnyCommits === false` is already tracked in `ChangesPanel`. Once the user saves their first commit (whether or not they filled in the field), the field never reappears for that project.

- **D-02:** The field is **optional**. The save button works regardless of whether the user fills it in. If left blank, `.acd/context.json` is not created (or is written as an empty string — implementer's discretion). No prompt, warning, or blocking behavior for skipping.

- **D-03:** Storage: `.acd/context.json` in the project folder (project-local, next to `.acd-backup/`). This is separate from `config_store` (which uses platformdirs for app-global config). The `.acd/` directory already exists in the codebase for backup files.

### AI Summary Trigger

- **D-04:** The AI summary is **on-demand** — triggered by a button in the diff viewer ("Generate AI summary" or similar). The panel is visible but empty until clicked. This avoids auto-firing LLM calls on every diff open, which has cost and latency implications especially when no model is configured.

- **D-05:** The button/panel is shown for all non-first-commit diffs. First-commit diffs already return `is_first_commit: true` from the history endpoint — those show the existing "first commit" state and have no meaningful diff to summarize.

### LLM Unavailable States

- **D-06:** Both unavailable cases show a **muted, single-line message** in the AI summary panel — no CTAs, no install hints, no links:
  - LLM extras not installed: "AI summary unavailable — install LLM extras"
  - Model not configured: "No LLM model configured"
  Backend differentiates the two cases in the API response; frontend renders the appropriate message.

### Progress Streaming (SSE)

- **D-07:** Backend sends **one SSE event per LangGraph node** as it completes, plus a final event with the complete `ChangeNarrative`. Frontend renders the step label as each event arrives:
  - `{"type": "progress", "step": "Analyzing topology..."}`
  - `{"type": "progress", "step": "Annotating tools..."}`
  - `{"type": "progress", "step": "Assessing risks..."}`
  - `{"type": "result", "narrative": "...", "risks": [...]}`
  This uses the same `EventSourceResponse` pattern from `watch.py`.

- **D-08:** The new SSE endpoint is **request-scoped** (one stream per user click, not a persistent connection like `/api/watch/events`). Frontend opens `EventSource` on button click, closes it when the `result` event arrives or on error.

### Claude's Discretion

- Exact button label and placement within `DiffViewer.tsx` (above/below the iframe)
- Whether `.acd/context.json` is written on empty input or left absent
- Whether the AI summary panel has a loading skeleton while waiting for the first SSE event
- New FastAPI router file name (e.g., `app/routers/ai.py` or `app/routers/doc.py`)
- Test structure for the new SSE endpoint and frontend React component

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing SSE pattern
- `app/routers/watch.py` — `EventSourceResponse` + `event_generator()` pattern to replicate for AI summary stream
- `app/frontend/src/hooks/useWatchEvents.ts` — frontend `EventSource` hook pattern to follow

### Existing commit/diff flow
- `app/frontend/src/components/ChangesPanel.tsx` — `hasAnyCommits` prop, commit handler — where business context field is added
- `app/frontend/src/components/DiffViewer.tsx` — iframe-based diff viewer — where AI summary panel is added
- `app/routers/save.py` — commit endpoint — may need updating to accept and persist business context

### LLM APIs (Phase 23/24/25)
- `src/alteryx_diff/llm/doc_graph.py` — `generate_change_narrative(context, llm)` — the function to call from the app backend
- `src/alteryx_diff/llm/context_builder.py` — `ContextBuilder.build_from_diff()` — builds context dict for the narrative
- `app/services/config_store.py` — model preference storage pattern; app backend reads model config from here

### Requirements
- `.planning/REQUIREMENTS.md` §APPAI — APPAI-01, APPAI-02 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/routers/watch.py`: `EventSourceResponse` + asyncio queue pattern — directly reusable for the AI summary SSE stream
- `app/frontend/src/hooks/useWatchEvents.ts`: `EventSource` + Zustand pattern — template for a new `useAISummary` hook
- `app/services/config_store.py`: `load_config()` / `save_config()` — can add model config key here if not already present from Phase 25
- `app/frontend/src/components/ui/`: shadcn/ui components available (Button, Card, Textarea) for the new UI elements

### Established Patterns
- SSE: `sse_starlette.EventSourceResponse` on backend, browser `EventSource` on frontend — proven in watch/badge flow
- Request-scoped vs. persistent SSE: watch uses persistent; AI summary needs request-scoped (open on click, close on `result` event)
- `hasAnyCommits`: already a prop in `ChangesPanel` — first-commit detection is already in place, no new state needed
- `.acd/` directory: already used for `.acd-backup/` (see `app/routers/save.py`); `context.json` fits the same convention

### Integration Points
- `ChangesPanel.tsx`: add the business context `<Textarea>` inside the `!hasAnyCommits` conditional block (line 117)
- `DiffViewer.tsx`: add AI summary panel below/above the diff iframe; triggered by a button
- `app/routers/save.py`: `commit_version` endpoint may need to accept optional `business_context` field and write `.acd/context.json`
- New router `app/routers/ai.py` (or similar): SSE endpoint `GET /api/ai/summary?folder=...&sha=...&file=...` that calls `generate_change_narrative` and streams progress events

</code_context>

<specifics>
## Specific Ideas

No specific UI references — open to standard shadcn/ui patterns consistent with the rest of the app.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 26-companion-app-ai-integration*
*Context gathered: 2026-04-05*
