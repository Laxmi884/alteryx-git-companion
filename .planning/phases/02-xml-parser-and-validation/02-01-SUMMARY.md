---
phase: 02-xml-parser-and-validation
plan: "01"
subsystem: parser
tags: [lxml, xml, exceptions, parsing, type-hierarchy]

# Dependency graph
requires:
  - phase: 01-scaffold-and-data-models
    provides: WorkflowDoc, AlteryxNode, AlteryxConnection, ToolID, AnchorName dataclasses

provides:
  - "Typed ParseError exception hierarchy (ParseError, MalformedXMLError, MissingFileError, UnreadableFileError)"
  - "Public parse(path_a, path_b) function returning tuple[WorkflowDoc, WorkflowDoc]"
  - "Internal helpers: _parse_one, _tree_to_workflow, _element_to_dict"

affects:
  - 03-normalizer
  - 09-cli

# Tech tracking
tech-stack:
  added: [lxml>=5.0 (runtime, already in deps), lxml-stubs>=0.5 (dev type stubs)]
  patterns:
    - "Pre-flight + Parse + Convert three-stage pattern for file parsing"
    - "Exception hierarchy with filepath + message attributes for structured error reporting"
    - "@attr / #text / list-promotion convention for XML-to-dict serialization"

key-files:
  created:
    - src/alteryx_diff/exceptions.py
    - src/alteryx_diff/parser.py
  modified:
    - pyproject.toml
    - .pre-commit-config.yaml

key-decisions:
  - "lxml-stubs added to dev deps and pre-commit mypy hook additional_dependencies — required for mypy --strict to resolve lxml private types"
  - "type: ignore[type-arg] on _ElementTree[_Element] annotations — lxml-stubs 0.5.1 does not declare _ElementTree as generic; ignore suppresses stubs-level error while preserving intent"
  - "_element_to_dict guards child.tag with isinstance(str) check — lxml-stubs types tag as str | bytes for processing instructions"
  - "attrib iteration decodes bytes keys with k.decode() — lxml-stubs types attrib keys as str | bytes in strict mode"

patterns-established:
  - "ParseError hierarchy: all parsing failures carry filepath + message; CLI catches ParseError base for exit code 2"
  - "Pre-flight order: path_a checked before path_b; first error terminates immediately, no multi-error collection"
  - "XML-to-dict: @key attributes, #text content, tag-keyed children with list promotion for repeated siblings"

requirements-completed: [PARSE-01, PARSE-02, PARSE-03]

# Metrics
duration: 7min
completed: 2026-03-01
---

# Phase 2 Plan 01: XML Parser and Exception Hierarchy Summary

**lxml-based parse(path_a, path_b) returning two WorkflowDoc instances via three-stage pre-flight/parse/convert pattern, with typed ParseError hierarchy for missing/unreadable/malformed file errors**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-01T14:51:42Z
- **Completed:** 2026-03-01T14:58:46Z
- **Tasks:** 2
- **Files modified:** 4 (2 new, 2 config updates)

## Accomplishments

- `exceptions.py`: ParseError base class with `filepath` + `message` attributes; MalformedXMLError, MissingFileError, UnreadableFileError subclasses; no project-internal imports; mypy --strict clean
- `parser.py`: `parse(path_a, path_b)` public function; `_parse_one` with three-stage pre-flight/parse/convert; `_tree_to_workflow` extracting nodes and connections; `_element_to_dict` with @attr / #text / list-promotion conventions
- All 22 existing model tests continue to pass; zero sys.exit or print calls in either file

## Task Commits

Each task was committed atomically:

1. **Task 1: Create exceptions.py with typed ParseError hierarchy** - `824663d` (feat)
2. **Task 2: Create parser.py with parse() and internal helpers** - `2942264` (feat)

**Plan metadata:** (see final commit)

## Files Created/Modified

- `src/alteryx_diff/exceptions.py` - Typed ParseError hierarchy with MalformedXMLError, MissingFileError, UnreadableFileError
- `src/alteryx_diff/parser.py` - Public parse() and internal _parse_one, _tree_to_workflow, _element_to_dict helpers
- `pyproject.toml` - Added lxml-stubs>=0.5 to dev dependency group
- `.pre-commit-config.yaml` - Added lxml-stubs==0.5.1 and lxml>=5.0 as additional_dependencies for mirrors-mypy hook

## Decisions Made

- Added `lxml-stubs` to dev deps and pre-commit hook: the pre-commit mypy env is isolated and needed stubs to correctly type-check lxml usage under `--strict`
- Used `type: ignore[type-arg]` on `etree._ElementTree[etree._Element]` annotations: lxml-stubs 0.5.1 does not declare `_ElementTree` as a generic class; the annotation documents intent while `type: ignore` suppresses the stubs-level error
- `_element_to_dict` guards `child.tag` with `isinstance(str)` check: lxml-stubs types `tag` as `str | bytes` for processing instructions; the guard also skips PI nodes cleanly at runtime
- Attribute iteration decodes bytes keys: lxml-stubs types attrib keys as `str | bytes`; `k.decode()` fallback handles that case safely

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added lxml-stubs dev dependency and pre-commit hook configuration**
- **Found during:** Task 2 (parser.py mypy --strict verification)
- **Issue:** `mypy --strict src/alteryx_diff/parser.py` failed with "Library stubs not installed for lxml [import-untyped]". The pre-commit mypy hook's isolated environment also lacked stubs, causing `type: ignore[type-arg]` comments to flip between "needed" and "unused" depending on environment.
- **Fix:** Installed `lxml-stubs==0.5.1` into venv; added `lxml-stubs>=0.5` to `[dependency-groups] dev` in pyproject.toml; added `additional_dependencies: [lxml-stubs==0.5.1, lxml>=5.0]` to the mirrors-mypy hook in `.pre-commit-config.yaml`; deleted stale pre-commit cache dir to force rebuild
- **Files modified:** pyproject.toml, .pre-commit-config.yaml
- **Verification:** `mypy --strict` exits 0 locally and pre-commit mypy hook passes
- **Committed in:** `2942264` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking dependency missing)
**Impact on plan:** Required for correctness — `mypy --strict` is an explicit success criterion. No scope creep.

## Issues Encountered

- lxml-stubs `_ElementTree` is non-generic in v0.5.1: using `_ElementTree[_Element]` produces a `type-arg` error with stubs but no error without stubs (falling back to Any). Resolved by keeping the generic annotation for documentation value and adding `# type: ignore[type-arg]` to suppress the stubs error while leaving intent clear.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `parse(path_a, path_b)` is fully implemented and tested — Phase 3 (normalizer) can import and consume `WorkflowDoc` instances immediately
- ParseError hierarchy established — Phase 9 (CLI) catches `ParseError` base for exit code 2
- All Phase 1 model tests still pass (22/22)
- No blockers for Phase 3

---
*Phase: 02-xml-parser-and-validation*
*Completed: 2026-03-01*

## Self-Check: PASSED

- FOUND: src/alteryx_diff/exceptions.py
- FOUND: src/alteryx_diff/parser.py
- FOUND: .planning/phases/02-xml-parser-and-validation/02-01-SUMMARY.md
- FOUND commit: 824663d (Task 1 - exceptions.py)
- FOUND commit: 2942264 (Task 2 - parser.py)
