# Phase 1: Scaffold and Data Models - Research

**Researched:** 2026-03-01
**Domain:** Python project scaffolding (uv, pyproject.toml, src-layout) + typed frozen dataclasses + dev tooling (ruff, mypy, pre-commit, pytest)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Package layout
- Package name: `alteryx_diff` (CLI entry point `acd` is a separate alias)
- Use src-layout: `src/alteryx_diff/` to prevent accidental root imports
- Tests in `tests/` at the project root (standard pytest convention)
- Models as a sub-package: `src/alteryx_diff/models/` with `__init__.py` exporting all dataclasses

#### ToolID representation
- ToolIDs are integers in Alteryx .yxmd XML (e.g., `ToolID="42"`)
- Use `NewType('ToolID', int)` — opaque type alias; mypy catches accidental int/ToolID mixing at zero runtime cost
- Additional domain NewTypes in `models/types.py`:
  - `ConfigHash = NewType('ConfigHash', str)` — SHA-256 hash strings
  - `AnchorName = NewType('AnchorName', str)` — connection anchor labels (used in EdgeDiff 4-tuples)
- All three NewTypes live in `models/types.py`, imported from there by all stages

#### Model field design
- `AlteryxNode.config`: Claude's discretion — choose whatever representation best serves downstream normalizer and differ stages
- `AlteryxNode` position: flat `x: float, y: float` fields directly on the node (not a nested dataclass or tuple)
- `NodeDiff` field changes: `field_diffs: dict[str, tuple[Any, Any]]` mapping field name → (old_value, new_value)
- Connections on `WorkflowDoc`, not on `AlteryxNode` — `WorkflowDoc.connections: list[AlteryxConnection]`; nodes are topology-free

#### Tooling
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PARSE-04 | System extracts ToolID, tool type, canvas X/Y position, configuration XML, and upstream/downstream connections for each tool into a typed internal object model | Frozen dataclasses with `NewType` provide the typed object model; `WorkflowDoc`, `AlteryxNode`, `AlteryxConnection`, `DiffResult`, `NodeDiff`, `EdgeDiff` are the six model types needed; `field()` with `default_factory` handles mutable defaults (lists/dicts) |
</phase_requirements>

---

## Summary

Phase 1 sets up the entire Python project from scratch: directory structure, packaging metadata (pyproject.toml), dev tooling (ruff, mypy, pre-commit), and the six frozen dataclasses that every downstream phase programs against. There is no business logic here — this phase creates typed boundaries only.

The stack is well-established and verified via official sources (uv docs, Python stdlib docs, ruff docs, pre-commit repos). The key technical insight is that `frozen=True, kw_only=True` dataclasses with `NewType` opaque aliases give you immutable, mypy-enforced contracts at zero runtime cost. Python 3.12.4 is already installed in the project venv, which exceeds the `>=3.11` requirement — `slots=True` is available and provides a memory/performance benefit at no cost.

The `AlteryxNode.config` discretionary field should be typed as `dict[str, Any]` — this representation is flat enough for the normalizer (Phase 3) to operate on as a key/value map, and flexible enough for the differ (Phase 5) to do field-level before/after comparison without XML dependency in the model layer.

**Primary recommendation:** Use `uv init --lib` to generate the src-layout scaffold with `uv_build` as the build backend, then define all six models as `@dataclass(frozen=True, kw_only=True, slots=True)` types in `models/`, exporting them from `models/__init__.py`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uv | latest (managed) | Project/package manager, lock file, venv | Single tool replaces pip, pip-tools, virtualenv; uv.lock provides reproducibility |
| Python stdlib `dataclasses` | 3.11+ | Frozen typed model definitions | Zero deps, mypy-compatible, `frozen=True` gives immutability + hashability |
| Python stdlib `typing` | 3.11+ | `NewType`, `Any`, `TYPE_CHECKING` | NewType creates opaque int/str subtypes mypy enforces at zero runtime cost |
| pytest | >=8.0 | Test runner for scaffold smoke tests | Standard Python test framework; pyproject.toml native configuration |
| ruff | >=0.15.4 | Lint + format (replaces flake8, isort, black) | 200x faster than flake8; single tool for all lint+format; pyproject.toml config |
| mypy | >=1.15 | Static type checking | Catches NewType misuse, frozen violations, dict[str, Any] typing; strict mode |
| pre-commit | >=3.0 | Git hook runner | Runs ruff + mypy before every commit; enforces quality gates |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pre-commit/pre-commit-hooks | v6.0.0 | check-yaml, check-toml, trailing-whitespace, end-of-file-fixer | Always — basic repo hygiene |
| astral-sh/ruff-pre-commit | v0.15.4 | ruff-check + ruff-format hooks | Always — enforces lint + format on commit |
| pre-commit/mirrors-mypy | latest tag | mypy type check hook | Always — enforces typed contracts on commit |
| uv_build | >=0.10.7 | Build backend for `uv build` | Default for src-layout pure-Python packages; auto-selected by `uv init --lib` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| uv_build | hatchling | hatchling has more flexibility (custom build hooks, VCS versions) but more config; uv_build is zero-config and 10-35x faster |
| frozen dataclasses | Pydantic BaseModel | Pydantic adds runtime validation (useful for user input, not internal models); adds a dep; overkill for internal typed boundaries |
| frozen dataclasses | attrs | attrs has more features but is an external dependency; stdlib dataclasses are sufficient here |
| `NewType` | custom wrapper class | Wrapper class has runtime overhead and requires `__eq__`/`__hash__`; NewType is zero-cost |

**Installation (dev dependencies via uv):**
```bash
uv add --dev pytest mypy ruff pre-commit
```

**Runtime dependencies (lower-bound ranges):**
```bash
uv add lxml>=5.0 networkx>=3.6
```

---

## Architecture Patterns

### Recommended Project Structure
```
alteryx_diff/
├── pyproject.toml              # Project metadata, all tool config, dep groups
├── uv.lock                     # Exact pinned versions (commit to git)
├── .pre-commit-config.yaml     # Hook definitions
├── .python-version             # Pin Python version for uv
├── src/
│   └── alteryx_diff/
│       ├── __init__.py         # Package init (version string)
│       ├── py.typed            # PEP 561 marker — typed package
│       └── models/
│           ├── __init__.py     # Re-exports all 6 model classes + NewTypes
│           ├── types.py        # ToolID, ConfigHash, AnchorName NewTypes
│           ├── workflow.py     # WorkflowDoc, AlteryxNode, AlteryxConnection
│           └── diff.py         # DiffResult, NodeDiff, EdgeDiff
└── tests/
    ├── __init__.py             # Empty — makes tests a package
    └── test_models.py          # Smoke: import + construct all model instances
```

### Pattern 1: Frozen Dataclass with NewType Fields

**What:** `@dataclass(frozen=True, kw_only=True, slots=True)` with `NewType`-typed fields and `field(default_factory=...)` for mutable defaults.

**When to use:** Every model class in `models/`. `frozen=True` prevents accidental mutation. `kw_only=True` forces explicit field names at construction. `slots=True` reduces memory footprint and speeds attribute access (Python 3.10+, available on Python 3.12).

**Example:**
```python
# Source: https://docs.python.org/3/library/dataclasses.html
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from alteryx_diff.models.types import ToolID, AnchorName

@dataclass(frozen=True, kw_only=True, slots=True)
class AlteryxNode:
    tool_id: ToolID
    tool_type: str
    x: float
    y: float
    config: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, kw_only=True, slots=True)
class AlteryxConnection:
    src_tool: ToolID
    src_anchor: AnchorName
    dst_tool: ToolID
    dst_anchor: AnchorName
```

**Note on `config: dict[str, Any]`:** `dict` is mutable, so `field(default_factory=dict)` is required (not `config: dict[str, Any] = {}`). Even though the dataclass is frozen (no field reassignment), the dict itself can be mutated post-construction. This is acceptable for internal models where config is set once at parse time. If full immutability is needed, use `MappingProxyType` — but this adds complexity the normalizer does not require.

### Pattern 2: NewType Opaque Aliases

**What:** `NewType('ToolID', int)` creates a type that mypy treats as distinct from `int`, but at runtime is identical to `int` (zero overhead).

**When to use:** ToolID, ConfigHash, AnchorName — domain identifiers that should never be accidentally mixed with plain strings/ints.

**Example:**
```python
# Source: https://docs.python.org/3/library/typing.html
from typing import NewType

ToolID = NewType('ToolID', int)
ConfigHash = NewType('ConfigHash', str)
AnchorName = NewType('AnchorName', str)

# mypy accepts this:
node_id = ToolID(42)

# mypy rejects this (plain int where ToolID expected):
def get_node(tool_id: ToolID) -> AlteryxNode: ...
get_node(42)  # mypy error: Argument 1 has incompatible type "int"; expected "ToolID"
```

### Pattern 3: Models `__init__.py` as Single Export Surface

**What:** `models/__init__.py` re-exports all public symbols so callers use `from alteryx_diff.models import WorkflowDoc` rather than knowing internal file structure.

**When to use:** Always — internal file organization can change without breaking imports.

**Example:**
```python
# src/alteryx_diff/models/__init__.py
from alteryx_diff.models.types import ToolID, ConfigHash, AnchorName
from alteryx_diff.models.workflow import WorkflowDoc, AlteryxNode, AlteryxConnection
from alteryx_diff.models.diff import DiffResult, NodeDiff, EdgeDiff

__all__ = [
    "ToolID", "ConfigHash", "AnchorName",
    "WorkflowDoc", "AlteryxNode", "AlteryxConnection",
    "DiffResult", "NodeDiff", "EdgeDiff",
]
```

### Pattern 4: pyproject.toml as Single Config File

**What:** All tool configuration (ruff, mypy, pytest) lives in `[tool.X]` sections of `pyproject.toml`. No separate `setup.cfg`, `.flake8`, `mypy.ini`, `pytest.ini`.

**When to use:** Always for new projects — reduces config file sprawl.

**Example:**
```toml
# Source: https://docs.astral.sh/uv/concepts/projects/init/
[project]
name = "alteryx-diff"
version = "0.1.0"
description = "CLI tool to diff Alteryx .yxmd workflow files"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "lxml>=5.0",
    "networkx>=3.6",
]

[build-system]
requires = ["uv_build>=0.10.7,<0.11.0"]
build-backend = "uv_build"

[project.scripts]
acd = "alteryx_diff.__main__:main"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "mypy>=1.15",
    "ruff>=0.15",
    "pre-commit>=3.0",
]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = []

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
strict = true
ignore_missing_imports = false
python_version = "3.11"

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--import-mode=importlib"]
```

### Anti-Patterns to Avoid

- **Mutable default fields:** `config: dict = {}` raises `ValueError` at class definition. Always use `field(default_factory=dict)` for mutable defaults.
- **Using `type X = int` (PEP 695 alias) instead of `NewType`:** PEP 695 type aliases are transparent aliases — mypy allows `int` where `X` is expected. `NewType` is opaque and enforces the distinction. Use `NewType` for domain IDs.
- **`from alteryx_diff.models.workflow import AlteryxNode` in non-models code:** Always import from `alteryx_diff.models` (the package), not from sub-modules. This insulates callers from internal reorganization.
- **Mixing `slots=True` with class inheritance across frozen/non-frozen:** `slots=True` creates a new class and does not combine cleanly with multiple inheritance. Keep models as standalone dataclasses with no inheritance chains.
- **Not committing `uv.lock`:** The lock file provides exact reproducible installs. Must be committed to git.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Project dependency management | Custom virtualenv scripts | `uv` | uv resolves, pins, syncs, and manages venvs in one tool; `uv sync` from a clean checkout is the required success criteria |
| Linting + formatting | Custom flake8/isort/black config | `ruff` | ruff replaces all three, is 200x faster, and reads from pyproject.toml; no multi-tool coordination |
| Type checking | Runtime isinstance guards | `mypy --strict` | mypy catches NewType misuse and frozen violations at zero runtime cost; isinstance guards are verbose and miss type-level errors |
| Git quality gates | Manual code review for style | `pre-commit` | pre-commit runs ruff + mypy before every commit; prevents bad code from entering git history |
| Module re-exports | Wildcard `from X import *` | Explicit `__all__` in `__init__.py` | Explicit `__all__` makes the public API clear to mypy, IDEs, and future developers |

**Key insight:** For a scaffold phase, every "custom solution" here is wheel re-invention. The entire value is in wiring up standard tools correctly the first time.

---

## Common Pitfalls

### Pitfall 1: `frozen=True` + `slots=True` + Mutable Field Default

**What goes wrong:** `@dataclass(frozen=True, slots=True)` with `config: dict[str, Any] = {}` raises `ValueError: mutable default <class 'dict'>` at class definition time.

**Why it happens:** Python detects the shared mutable default and raises immediately (unlike non-dataclass classes where it would silently share the instance across all instances).

**How to avoid:** Always use `field(default_factory=dict)` or `field(default_factory=list)` for mutable defaults.

**Warning signs:** `ValueError: mutable default <class 'dict'>` or `<class 'list'>` at import time.

### Pitfall 2: `frozen=True` + `slots=True` Incompatibility with `__post_init__`

**What goes wrong:** Trying to set a field inside `__post_init__` with direct assignment (`self.field = value`) raises `FrozenInstanceError` because `frozen=True` disallows `__setattr__`.

**Why it happens:** `frozen=True` replaces `__setattr__` with one that always raises `FrozenInstanceError`.

**How to avoid:** For `__post_init__` that needs to set a field, use `object.__setattr__(self, 'field', value)`. However, in this phase there is no `__post_init__` needed — all fields are provided at construction time.

**Warning signs:** `FrozenInstanceError: cannot assign to field 'X'` raised inside `__post_init__`.

### Pitfall 3: mypy `strict=true` Rejects `dict[str, Any]` Field Without Import

**What goes wrong:** `strict=true` requires `from typing import Any` — bare `Any` is not auto-imported and mypy will flag `Name "Any" is not defined`.

**Why it happens:** mypy strict mode treats implicit names as errors.

**How to avoid:** Always `from typing import Any` explicitly. Use `from __future__ import annotations` at the top of every model file (defers annotation evaluation, avoids circular import issues).

**Warning signs:** `Name "Any" is not defined` or `Need type annotation for 'config'`.

### Pitfall 4: pytest Cannot Import `src/` Package

**What goes wrong:** `pytest` with the default import mode cannot find `alteryx_diff` because `src/` is not on `sys.path`.

**Why it happens:** The default pytest import mode (`prepend`) doesn't handle src-layout correctly without an editable install.

**How to avoid:** Two options (use both for belt-and-suspenders):
1. Set `addopts = ["--import-mode=importlib"]` in `[tool.pytest.ini_options]` — recommended by pytest for new projects.
2. Run `uv pip install -e .` once after checkout (editable install adds `src/` to path).

With `uv sync`, the package is installed editably into the venv automatically — this is the primary solution.

**Warning signs:** `ModuleNotFoundError: No module named 'alteryx_diff'` when running pytest.

### Pitfall 5: mypy pre-commit Hook Missing Type Stubs

**What goes wrong:** mypy pre-commit hook (via mirrors-mypy) runs in an isolated virtualenv. It does not have access to your project's installed packages, so it cannot check imports for typed third-party packages.

**Why it happens:** pre-commit creates isolated environments. The mirrors-mypy hook needs `additional_dependencies` for any stubs or packages that mypy must see.

**How to avoid:** Add typed dependencies explicitly in `.pre-commit-config.yaml`:
```yaml
- id: mypy
  additional_dependencies: ["lxml-stubs"]
```
For Phase 1 (models only, no lxml imports), this is not yet needed. Add stubs when Phase 2 (parser) adds lxml imports.

**Warning signs:** `Cannot find implementation or library stub for module named 'lxml'` in pre-commit mypy run but not in local mypy run.

### Pitfall 6: `NewType` Called with Wrong Argument at Runtime

**What goes wrong:** Developer writes `ToolID("42")` (string) instead of `ToolID(42)` (int). At runtime, `NewType` is a callable that returns its argument unchanged — so `ToolID("42")` silently returns the string `"42"`. mypy catches this only if strict typing is enabled.

**Why it happens:** `NewType` is a zero-cost type alias at runtime. There is no runtime validation.

**How to avoid:** `mypy --strict` catches this. Pre-commit mypy hook enforces it at every commit. No extra code needed.

**Warning signs:** Type errors only show up in mypy output, not at runtime.

---

## Code Examples

Verified patterns from official sources:

### Complete `models/types.py`
```python
# Source: https://docs.python.org/3/library/typing.html
"""Domain NewType aliases shared across all pipeline stages."""
from typing import NewType

ToolID = NewType("ToolID", int)
"""Opaque integer identifier for an Alteryx tool. Distinct from plain int at mypy level."""

ConfigHash = NewType("ConfigHash", str)
"""SHA-256 hex digest of canonicalized tool configuration XML."""

AnchorName = NewType("AnchorName", str)
"""Alteryx connection anchor label, e.g. '1', 'True', 'False'."""
```

### Complete `models/workflow.py`
```python
# Source: https://docs.python.org/3/library/dataclasses.html
"""Workflow document and node models parsed from .yxmd XML."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from alteryx_diff.models.types import ToolID, AnchorName


@dataclass(frozen=True, kw_only=True, slots=True)
class AlteryxNode:
    """A single tool on the Alteryx canvas."""
    tool_id: ToolID
    tool_type: str
    x: float
    y: float
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True, slots=True)
class AlteryxConnection:
    """A directed edge connecting two tool anchors."""
    src_tool: ToolID
    src_anchor: AnchorName
    dst_tool: ToolID
    dst_anchor: AnchorName


@dataclass(frozen=True, kw_only=True, slots=True)
class WorkflowDoc:
    """Root document parsed from a .yxmd file."""
    filepath: str
    nodes: tuple[AlteryxNode, ...] = field(default_factory=tuple)
    connections: tuple[AlteryxConnection, ...] = field(default_factory=tuple)
```

**Note on `tuple` vs `list` for `nodes`/`connections`:** `tuple` is immutable and hashable, compatible with `frozen=True` semantics. Use `tuple[AlteryxNode, ...]` (homogeneous tuple of arbitrary length). Construction requires converting a list: `WorkflowDoc(filepath="x.yxmd", nodes=tuple(node_list), connections=tuple(conn_list))`. This is acceptable at parse boundaries.

### Complete `models/diff.py`
```python
# Source: https://docs.python.org/3/library/dataclasses.html
"""Diff result types returned by the differ stage."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from alteryx_diff.models.types import ToolID, AnchorName
from alteryx_diff.models.workflow import AlteryxNode, AlteryxConnection


@dataclass(frozen=True, kw_only=True, slots=True)
class NodeDiff:
    """A modification detected for a single tool."""
    tool_id: ToolID
    old_node: AlteryxNode
    new_node: AlteryxNode
    field_diffs: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    """Maps field name -> (old_value, new_value) for each changed field."""


@dataclass(frozen=True, kw_only=True, slots=True)
class EdgeDiff:
    """A connection change (addition or removal)."""
    src_tool: ToolID
    src_anchor: AnchorName
    dst_tool: ToolID
    dst_anchor: AnchorName
    change_type: str  # "added" | "removed"


@dataclass(frozen=True, kw_only=True, slots=True)
class DiffResult:
    """Complete diff between two WorkflowDoc instances."""
    added_nodes: tuple[AlteryxNode, ...] = field(default_factory=tuple)
    removed_nodes: tuple[AlteryxNode, ...] = field(default_factory=tuple)
    modified_nodes: tuple[NodeDiff, ...] = field(default_factory=tuple)
    edge_diffs: tuple[EdgeDiff, ...] = field(default_factory=tuple)
```

### Minimal Pytest Smoke Test
```python
# tests/test_models.py
"""Smoke test: all model classes can be imported and instantiated."""
from alteryx_diff.models import (
    ToolID, ConfigHash, AnchorName,
    WorkflowDoc, AlteryxNode, AlteryxConnection,
    DiffResult, NodeDiff, EdgeDiff,
)


def test_alteryx_node_construction() -> None:
    node = AlteryxNode(
        tool_id=ToolID(1),
        tool_type="AlteryxBasePluginsGui.DbFileInput.DbFileInput",
        x=100.0,
        y=200.0,
    )
    assert node.tool_id == ToolID(1)
    assert node.config == {}


def test_workflow_doc_construction() -> None:
    doc = WorkflowDoc(filepath="test.yxmd")
    assert doc.nodes == ()
    assert doc.connections == ()


def test_diff_result_construction() -> None:
    result = DiffResult()
    assert result.added_nodes == ()
    assert result.edge_diffs == ()
```

### `.pre-commit-config.yaml`
```yaml
# Source: https://github.com/astral-sh/ruff-pre-commit (v0.15.4)
# Source: https://github.com/pre-commit/pre-commit-hooks (v6.0.0)
# Source: https://github.com/pre-commit/mirrors-mypy
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.4
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: ''  # Pin to latest tag at setup time; run: pre-commit autoupdate
    hooks:
      - id: mypy
        args: [--strict]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| flake8 + isort + black | ruff (single tool) | 2022-present (stable 2024) | One config section, 200x faster, no multi-tool ordering issues |
| setup.py / setup.cfg | pyproject.toml ([project] table) | PEP 621, widely adopted 2023+ | All metadata and tool config in one file |
| pip + requirements.txt | uv + uv.lock + dependency-groups | 2024-present | Lock file with cross-platform reproducibility; dev groups separate from runtime deps |
| NamedTuple for domain models | frozen dataclasses | Python 3.7+ (standard by 2023) | kw_only, slots, field(), better mypy support than NamedTuple |
| hatchling (uv default) | uv_build (new stable default) | July 2025 | uv_build is 10-35x faster builds; will become default in future uv version |
| `python_requires` in setup.py | `requires-python` in pyproject.toml | PEP 621 | Standard field, respected by uv, pip, and all PEP 517 build tools |

**Deprecated/outdated:**
- `setup.py`: Replaced by pyproject.toml. Do not create.
- `setup.cfg`: Replaced by pyproject.toml `[project]` table. Do not create.
- `requirements.txt` for dev deps: Replaced by `[dependency-groups]` in pyproject.toml.
- `NamedTuple` for frozen domain models: dataclasses with `frozen=True, kw_only=True` are the modern equivalent with better tooling support.

---

## Open Questions

1. **`AlteryxNode.config` field type: `dict[str, Any]` vs `str` (raw XML)**
   - What we know: The user deferred this to Claude's discretion. Phase 3 (normalizer) needs to strip metadata and canonicalize. Phase 5 (differ) needs field-level before/after values.
   - What's unclear: Whether config is best stored as parsed key/value dict or as raw XML string until Phase 3 parses it.
   - Recommendation: Use `dict[str, Any]` — it forces Phase 2 (parser) to produce a structured intermediate rather than passing raw XML strings through the pipeline. This gives Phase 3 a clean map to operate on. If Phase 2 cannot fully parse config at XML parse time, it can use a single `"__raw_xml__"` key as a fallback without changing the type signature. Keeping `str` (raw XML) in the model would leak an XML dependency into the model layer and require Phase 5 to re-parse XML for comparison.

2. **`nodes` and `connections` as `tuple` vs `list` in `WorkflowDoc`/`DiffResult`**
   - What we know: `frozen=True` prevents field reassignment but not mutation of mutable fields (lists). `tuple` is immutable.
   - What's unclear: Whether downstream phases (especially Phase 4 NodeMatcher) need to mutate or sort the collections.
   - Recommendation: Use `tuple[T, ...]` for frozen doc fields (immutable by convention) — downstream phases that need sorted/filtered views create new tuples or local lists. `DiffResult` also uses tuples for the same reason. Phase 4 NodeMatcher works on `list[AlteryxNode]` locally during matching, then constructs a new `DiffResult` with tuples.

---

## Validation Architecture

*nyquist_validation not enabled in .planning/config.json — section skipped.*

---

## Sources

### Primary (HIGH confidence)
- https://docs.python.org/3/library/dataclasses.html — frozen, kw_only, slots parameters; field() default_factory; FrozenInstanceError behavior
- https://docs.python.org/3/library/typing.html — NewType semantics, runtime behavior, mypy enforcement
- https://docs.astral.sh/uv/concepts/projects/init/ — uv init --lib, src-layout generation, uv_build backend, pyproject.toml structure
- https://docs.astral.sh/uv/concepts/projects/dependencies/ — [dependency-groups], uv add --dev, uv.lock
- https://docs.astral.sh/ruff/configuration/ — [tool.ruff], [tool.ruff.lint], [tool.ruff.format] pyproject.toml sections
- https://github.com/astral-sh/ruff-pre-commit — v0.15.4 (released 2026-02-26), ruff-check + ruff-format hook IDs
- https://github.com/pre-commit/pre-commit-hooks — v6.0.0, check-yaml, check-toml, trailing-whitespace, end-of-file-fixer
- https://docs.pytest.org/en/stable/explanation/goodpractices.html — src layout + importlib mode + pythonpath config

### Secondary (MEDIUM confidence)
- https://mypy.readthedocs.io/en/stable/config_file.html — [tool.mypy] strict mode, overrides pattern (verified against official mypy docs)
- https://github.com/pre-commit/mirrors-mypy — mirrors-mypy hook, additional_dependencies pattern for stubs

### Tertiary (LOW confidence)
- Medium article on uv_build vs hatchling — corroborates official uv docs; 10-35x build speed claim is from unofficial source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools verified against official docs; versions confirmed from GitHub releases
- Architecture: HIGH — src-layout, frozen dataclasses, NewType patterns verified against official Python and uv docs
- Pitfalls: HIGH — mutable default / FrozenInstanceError from stdlib docs; pytest import mode from official pytest docs; mypy pre-commit isolation from mirrors-mypy README

**Research date:** 2026-03-01
**Valid until:** 2026-06-01 (stable tools — ruff, pytest, uv are actively developed but APIs are stable; only hook version pins need refreshing)
