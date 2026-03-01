# Phase 1: Scaffold and Data Models - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up the Python project scaffold (pyproject.toml, uv, directory structure, pre-commit hooks) and define all shared frozen dataclasses that every subsequent phase communicates through. Zero business logic lives here — this phase creates the typed boundaries that parser, normalizer, differ, and renderer stages program against.

</domain>

<decisions>
## Implementation Decisions

### Package layout
- Package name: `alteryx_diff` (CLI entry point `acd` is a separate alias)
- Use src-layout: `src/alteryx_diff/` to prevent accidental root imports
- Tests in `tests/` at the project root (standard pytest convention)
- Models as a sub-package: `src/alteryx_diff/models/` with `__init__.py` exporting all dataclasses

### ToolID representation
- ToolIDs are integers in Alteryx .yxmd XML (e.g., `ToolID="42"`)
- Use `NewType('ToolID', int)` — opaque type alias; mypy catches accidental int/ToolID mixing at zero runtime cost
- Additional domain NewTypes in `models/types.py`:
  - `ConfigHash = NewType('ConfigHash', str)` — SHA-256 hash strings
  - `AnchorName = NewType('AnchorName', str)` — connection anchor labels (used in EdgeDiff 4-tuples)
- All three NewTypes live in `models/types.py`, imported from there by all stages

### Model field design
- `AlteryxNode.config`: Claude's discretion — choose whatever representation best serves downstream normalizer and differ stages
- `AlteryxNode` position: flat `x: float, y: float` fields directly on the node (not a nested dataclass or tuple)
- `NodeDiff` field changes: `field_diffs: dict[str, tuple[Any, Any]]` mapping field name → (old_value, new_value)
- Connections on `WorkflowDoc`, not on `AlteryxNode` — `WorkflowDoc.connections: list[AlteryxConnection]`; nodes are topology-free

### Tooling
- Linter/formatter: `ruff` only (replaces flake8, isort, black) — single tool, configured in pyproject.toml
- Type checker: `mypy` in pre-commit hooks (enforces typed dataclass contracts at commit time)
- Dependency pinning: lower-bound ranges in pyproject.toml (e.g., `lxml>=5.0`); uv.lock provides exact reproducibility
- Pre-commit hooks:
  - ruff (lint + format)
  - mypy (type check)
  - check-yaml, check-toml
  - trailing-whitespace, end-of-file-fixer
  - Claude's discretion for any remaining standard hooks

### Claude's Discretion
- `AlteryxNode.config` field type — choose the representation that best serves the normalizer (Phase 3) and differ (Phase 5)
- Any additional pre-commit hooks beyond those listed above
- Internal file organization within `models/` sub-package (how to split the six dataclasses across files)

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

*Phase: 01-scaffold-and-data-models*
*Context gathered: 2026-03-01*
