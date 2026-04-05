---
phase: 25-cli-integration
plan: "01"
subsystem: llm
tags: [pydantic, langchain, jinja2, html-renderer, doc-renderer]

requires:
  - phase: 24-documentation-graph-docrenderer-ollama
    provides: WorkflowDocumentation model, DocRenderer, doc_graph pipeline, LLM extras infrastructure

provides:
  - ChangeNarrative Pydantic model in alteryx_diff.llm.models
  - generate_change_narrative() async function in doc_graph.py (single structured LLM call)
  - DocRenderer.to_html_fragment_from_narrative() method with _NARRATIVE_HTML_TEMPLATE
  - HTMLRenderer.render() doc_fragment kwarg for embedding narrative sections in diff reports

affects: [25-cli-integration-02, 25-cli-integration-03, 26-app-ai-integration]

tech-stack:
  added: []
  patterns:
    - "Single structured LLM call pattern (no LangGraph) for compact diff context"
    - "doc_fragment kwarg opt-in pattern: default empty string = zero regression"
    - "TYPE_CHECKING guard for ChangeNarrative in doc_renderer.py preserves import safety"

key-files:
  created: []
  modified:
    - src/alteryx_diff/llm/models.py
    - src/alteryx_diff/llm/doc_graph.py
    - src/alteryx_diff/renderers/doc_renderer.py
    - src/alteryx_diff/renderers/html_renderer.py
    - tests/llm/test_doc_renderer.py
    - tests/test_html_renderer.py

key-decisions:
  - "Single structured LLM call (not LangGraph graph) for generate_change_narrative -- diff context is already compact"
  - "id=\"change-narrative\" is load-bearing -- Plan 03 tests assert its presence/absence"
  - "doc_fragment uses | safe Jinja filter -- caller (DocRenderer) is responsible for safe HTML"

patterns-established:
  - "Optional kwarg pattern: doc_fragment: str = '' -- callers without LLM don't need to change"
  - "ChangeNarrative imported under TYPE_CHECKING in doc_renderer.py -- matches WorkflowDocumentation pattern"

requirements-completed: []

duration: 4min
completed: 2026-04-05
---

# Phase 25 Plan 01: Change Narrative Generation + HTMLRenderer doc_fragment Kwarg Summary

**ChangeNarrative Pydantic model, single-shot generate_change_narrative() LLM call, DocRenderer HTML fragment renderer, and opt-in doc_fragment kwarg wired into HTMLRenderer.render()**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-05T07:38:47Z
- **Completed:** 2026-04-05T07:42:17Z
- **Tasks:** 4
- **Files modified:** 6

## Accomplishments

- Added `ChangeNarrative` Pydantic model with `narrative` and optional `risks` fields
- Added `generate_change_narrative()` async function using single structured LLM call (no LangGraph pipeline)
- Added `DocRenderer.to_html_fragment_from_narrative()` with Jinja2 autoescape, paragraph splitting, and conditional risks section
- Added `doc_fragment: str = ""` kwarg to `HTMLRenderer.render()` with template injection between graph and metadata sections

## Task Commits

1. **Task 1: Add ChangeNarrative Pydantic model** - `e64321c` (feat)
2. **Task 2: Add generate_change_narrative() to doc_graph.py** - `a16c28a` (feat)
3. **Task 3: Add to_html_fragment_from_narrative() to DocRenderer** - `c2a6f15` (feat)
4. **Task 4: Add doc_fragment kwarg to HTMLRenderer.render()** - `c00c3f0` (feat)

## Files Created/Modified

- `src/alteryx_diff/llm/models.py` - Added ChangeNarrative BaseModel
- `src/alteryx_diff/llm/doc_graph.py` - Added generate_change_narrative() and updated __all__
- `src/alteryx_diff/renderers/doc_renderer.py` - Added _NARRATIVE_HTML_TEMPLATE and to_html_fragment_from_narrative()
- `src/alteryx_diff/renderers/html_renderer.py` - Added doc_fragment kwarg, template injection, updated render() signature
- `tests/llm/test_doc_renderer.py` - Added 2 tests for to_html_fragment_from_narrative()
- `tests/test_html_renderer.py` - Added 2 tests for doc_fragment kwarg behavior

## Decisions Made

- `generate_change_narrative()` uses a single `with_structured_output` call (not LangGraph) because `build_from_diff()` output is already compact -- no multi-node pipeline needed
- `id="change-narrative"` is load-bearing: Plan 03 tests will assert its presence/absence; this id must not change
- `doc_fragment` kwarg uses `| safe` Jinja filter -- the fragment from `DocRenderer.to_html_fragment_from_narrative()` is already autoescaped by Jinja2 at construction time

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Plans 02 and 03 can now run: generate_change_narrative() is available for Plan 03 to call from `diff --doc` flag
- HTMLRenderer.render() doc_fragment kwarg is wired and tested; Plan 03 integration is straightforward
- All 41 tests across affected files pass (26 existing + 4 new narrative tests + 11 existing cli/doc_graph)

## Self-Check: PASSED

- `src/alteryx_diff/llm/models.py` - exists with ChangeNarrative
- `src/alteryx_diff/llm/doc_graph.py` - exists with generate_change_narrative
- `src/alteryx_diff/renderers/doc_renderer.py` - exists with to_html_fragment_from_narrative
- `src/alteryx_diff/renderers/html_renderer.py` - exists with doc_fragment kwarg
- Commits e64321c, a16c28a, c2a6f15, c00c3f0 all present in git log

---
*Phase: 25-cli-integration*
*Completed: 2026-04-05*
