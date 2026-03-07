# Phase 2: XML Parser and Validation - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

lxml-based parser that reads two `.yxmd` files and returns two `WorkflowDoc` instances — all tool nodes, positions, configs, and connections populated — or raises a typed exception if either file is malformed, missing, or unreadable. Zero business logic beyond parsing and validation. No calls to `sys.exit`, `print`, or file I/O outside loading the input file.

</domain>

<decisions>
## Implementation Decisions

### Config dict extraction
- Nested dict mirroring XML hierarchy — not flat XPath-style keys, not raw XML string
- Preserves XML structure so Phase 5 (differ) can use DeepDiff for meaningful field-level paths (e.g. `root['Configuration']['Expression']`)
- XML attribute encoding (e.g. `@field`) and repeated element handling (e.g. `<Field/>` lists) are Claude's discretion — choose the convention that best serves Phase 3 normalizer and Phase 5 differ

### Exception hierarchy
- Subclass hierarchy rooted at a `ParseError` base class
- Subclasses: `MalformedXMLError`, `MissingFileError`, `UnreadableFileError`
- Each exception carries: `filepath: str` + `message: str` (plain English) + `__cause__` chaining to preserve the original lxml or OS exception for debuggability
- All exception classes live in `src/alteryx_diff/exceptions.py` — importable by any stage without circular dependencies

### Dual-file fail behavior
- Fail immediately on first error — parse `path_a` first; if it fails, raise without attempting `path_b`
- Explicit file existence check before opening: `if not path.exists(): raise MissingFileError(...)` — plain English error identifying the file path
- No partial state, no multi-error collection

### Test fixtures
- Fixture files live in `tests/fixtures/` directory
- Synthetic XML strings only for now — no real `.yxmd` files available yet; build minimal but structurally valid XML in-code for the happy path and all edge cases
- If real `.yxmd` files are added later they go in `tests/fixtures/` as golden fixtures

### Claude's Discretion
- Exact XML attribute encoding convention in the nested dict (e.g. `@attr_name` keys vs. dedicated sub-dict)
- Handling of repeated same-name XML child elements (e.g. `<Field/>` lists → list value in dict)
- Internal parser module structure (single `parser.py` vs. sub-package)
- Public function signature: `parse(path_a, path_b)` is locked; internal helpers are Claude's choice

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-xml-parser-and-validation*
*Context gathered: 2026-03-01*
