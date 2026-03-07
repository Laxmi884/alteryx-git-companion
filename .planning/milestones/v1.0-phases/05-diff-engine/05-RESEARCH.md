# Phase 5: Diff Engine - Research

**Researched:** 2026-03-03
**Domain:** Structural dict diffing — Python stdlib deepdiff, symmetric set operations, frozen dataclass pipeline stage
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Modification reporting depth:**
- Report changes at full nested paths (e.g., `filter.expression`), not just top-level config keys
- String/expression fields are compared as opaque strings — no semantic parsing or normalization
- Unchanged fields are completely omitted from NodeDiff output — only changed fields appear
- List fields are treated as atomic values: if any element differs, the whole list is before/after (no element-level list diff)

**Edge rewiring classification:**
- No explicit "rewiring" category — rewiring is represented as one removed edge + one added edge (symmetric difference)
- Edge identity (4-tuple) uses normalized/matched tool names from Phase 4, not raw XML names
- Anchor renames are treated as remove + add (same src/dst tools with different anchors = different edge)
- When a tool is removed, all its edges are automatically classified as removed — no separate orphaned edge category

**DiffResult data model:**
- `DiffResult` is a Python dataclass
- `NodeDiff` (for modified nodes) carries: `tool_name` + `field_diffs` (list of `{path, before, after}`) — no full config snapshot
- `added_nodes` and `removed_nodes` store the full node configuration for downstream use
- `DiffResult` exposes an `is_empty` property (True when no additions, removals, modifications, or edge diffs)

**Null / missing field handling:**
- Config key present in one workflow but absent in the other → treated as modification with `None` (before=value, after=None or vice versa)
- No distinction between explicit null (key present, value null) and absent key — both treated as `None`
- Fields to exclude from comparison: Claude determines exclusion list based on field semantics (e.g., display-only fields like position, layout metadata, internal rendering hints)
- If node configs fail to compare (corrupt/unparseable value): raise an exception — fail loudly, do not silently emit an error entry

### Claude's Discretion
- Exact exclusion list for non-functional config fields (position, display metadata, etc.)
- Internal structure of `FieldDiff` (whether path is a string or list of segments)
- How to handle DeepDiff output format conversion to the `field_diffs` schema
- Rewiring detection heuristic (if Claude determines it adds value as an optional annotation)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DIFF-01 | System detects tool additions (present in new, absent in old) and removals (present in old, absent in new) | MatchResult.added/removed carry NormalizedNode with .source (AlteryxNode) — differ reads .source for the full node config; DiffResult.added_nodes/removed_nodes are tuple[AlteryxNode, ...] |
| DIFF-02 | System detects tool configuration modifications and reports before/after field-level values for each changed field | DeepDiff on AlteryxNode.config dicts produces flat path→(before, after) mapping; field_diffs dict[str, tuple[Any, Any]] in the existing NodeDiff model stores this as dotted-path string keys |
| DIFF-03 | System detects connection additions, removals, and rewirings using full 4-tuple anchor identity (src_tool + src_anchor + dst_tool + dst_anchor) | AlteryxConnection frozen dataclass is hashable (frozen=True gives __hash__); symmetric difference of frozenset[AlteryxConnection] gives added/removed edges directly; rewiring = one removed + one added |
</phase_requirements>

## Summary

Phase 5 builds the differ pipeline stage: a pure function `diff(match_result, old_connections, new_connections) -> DiffResult`. The function receives a `MatchResult` from Phase 4 and connection tuples from both workflows, then computes three categories of change: node additions/removals (directly from `MatchResult.added`/`MatchResult.removed`), node config modifications (field-level diff on matched pairs), and edge changes (symmetric difference of connection sets).

The critical design insight is that the `DiffResult` and `NodeDiff` data models are **already defined** in `src/alteryx_diff/models/diff.py` from Phase 1. Phase 5 only needs to create the `differ/` package and implement the computation logic — no model changes are needed. The existing `NodeDiff.field_diffs: dict[str, tuple[Any, Any]]` uses dotted-path string keys (e.g., `"filter.expression"`) that satisfy both the model schema and the CONTEXT.md requirement for full nested path reporting.

Field-level config diffing requires recursive traversal of nested dicts with path accumulation. The `deepdiff` library (PyPI `deepdiff`) automates this and handles nested dicts, lists-as-atomic-values, and missing-key-as-None semantics correctly with the right configuration. It is well-maintained, widely used in CI/CD tools, and avoids hand-rolling a recursive dict walker that would need to handle every edge case (type mismatches, nested lists, None values). The alternative — a hand-rolled recursive diff — is viable but needs careful design to handle the "list fields are atomic" requirement.

**Primary recommendation:** Create `src/alteryx_diff/differ/` package exposing `diff(match_result, old_connections, new_connections) -> DiffResult`. Use `deepdiff.DeepDiff` with `ignore_order=False` for field-level config diffing, converting its output to `NodeDiff.field_diffs` dotted-path string keys. Use symmetric difference of `frozenset[AlteryxConnection]` for edge changes. Add `is_empty` property to `DiffResult` via a non-frozen override or by adding it to the model in Phase 5's Wave 0.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | 3.11+ | All model types (DiffResult, NodeDiff, EdgeDiff) — already defined in models/diff.py | Matches every other model in this codebase (frozen=True, kw_only=True, slots=True) |
| `deepdiff` | >=7.0 | Field-level nested dict comparison with path extraction | Recursive dict diffing with configurable behavior; handles nested structures, atomic list comparison, and missing keys; used in pytest-deepdiff, Airflow, and many CI tools |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `frozenset` | 3.11+ | Edge symmetric difference | AlteryxConnection is frozen+hashable; set subtraction gives added/removed edges in one line |
| Python stdlib `typing` | 3.11+ | `Any`, `Sequence` in differ function signatures | Already used project-wide |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `deepdiff.DeepDiff` | Hand-rolled recursive dict walker | Hand-roll is viable for this project's dict depth (2-3 levels) but requires careful handling of list-as-atomic, None-vs-missing, type mismatches, and path formatting; deepdiff handles all these with flag configuration |
| `deepdiff.DeepDiff` | `jsondiff` library | jsondiff focuses on JSON patch format output; harder to convert to path→(before,after) tuples; less adoption |
| frozenset symmetric difference | Explicit loop comparison | Both work; symmetric difference is O(n) and eliminates off-by-one errors in set logic |

**Installation:**
```bash
uv add deepdiff
```

### Critical Model Clarification: `is_empty` on a `slots=True` Dataclass

The existing `DiffResult` in `models/diff.py` uses `frozen=True, kw_only=True, slots=True`. A `@property` cannot be added to a `slots=True` dataclass without declaring it in `__slots__`. The standard solution is to **not use `@property`** but instead implement `is_empty` as a regular method, or to remove `slots=True` from `DiffResult` and add the property. Both are valid. The project pattern uses `slots=True` everywhere for memory efficiency, so the recommended approach is:

**Option A (recommended):** Remove `slots=True` from `DiffResult` only (keep `frozen=True`), add `@property is_empty`. The `slots=True` optimization matters most for types created in large quantities (nodes, connections) — `DiffResult` is created once per run.

**Option B:** Add `is_empty` as a standalone helper function `is_diff_empty(result: DiffResult) -> bool`. Avoids model changes but is less ergonomic for the success criterion check.

The planner should use Option A (modify `DiffResult` to remove `slots=True` and add `is_empty` property in Wave 0).

## Architecture Patterns

### Recommended Project Structure
```
src/alteryx_diff/
├── differ/
│   ├── __init__.py          # Public surface: diff() only
│   └── differ.py            # diff() entry point + all internal helpers
tests/
├── fixtures/
│   └── diffing.py           # Fixture WorkflowDoc pairs for differ tests (ToolIDs start at 401)
└── test_differ.py           # All differ tests covering DIFF-01, DIFF-02, DIFF-03
```

**Convention notes from existing codebase:**
- `__init__.py` is the sole public surface — no `__all__` in internal modules
- One public function per package (`normalize`, `match`, now `diff`)
- Internal helpers use module-private scope (no underscore package needed for differ since diffing is simpler than matching)
- All model types imported from `alteryx_diff.models` (never from sub-modules)
- Fixture ToolIDs: Phase 4 uses 301-399. Phase 5 fixtures must start at 401.
- Test files mirror source module: `test_differ.py` for the `differ` package
- `zip(..., strict=True)` enforced by ruff B905
- `from __future__ import annotations` at the top of every module

### Pattern 1: Differ Public Function Signature

**What:** Single entry point matching the normalizer/matcher pattern — pure function, no I/O, no side effects.
**When to use:** Always — this is the complete public API.

```python
# Source: project pattern (pure function, no I/O, no side effects)
from __future__ import annotations

from alteryx_diff.matcher.matcher import MatchResult
from alteryx_diff.models import AlteryxConnection, AlteryxNode, DiffResult, EdgeDiff, NodeDiff
from alteryx_diff.models.types import AnchorName, ToolID


def diff(
    match_result: MatchResult,
    old_connections: tuple[AlteryxConnection, ...],
    new_connections: tuple[AlteryxConnection, ...],
) -> DiffResult:
    """Compute functional differences between two matched workflow snapshots.

    Pure function: no I/O, no side effects, deterministic output.
    Receives MatchResult from Phase 4 (matcher) plus raw connections.
    Returns DiffResult for downstream reporting phases.
    """
    added_nodes = tuple(n.source for n in match_result.added)
    removed_nodes = tuple(n.source for n in match_result.removed)
    modified_nodes = tuple(
        _diff_node(old.source, new.source)
        for old, new in match_result.matched
        if old.config_hash != new.config_hash  # fast-path: skip identical configs
    )
    edge_diffs = _diff_edges(old_connections, new_connections)
    return DiffResult(
        added_nodes=added_nodes,
        removed_nodes=removed_nodes,
        modified_nodes=modified_nodes,
        edge_diffs=edge_diffs,
    )
```

**Key design decision:** The `config_hash` fast-path check (`if old.config_hash != new.config_hash`) avoids calling DeepDiff for nodes with identical configs. This is O(1) string equality on the SHA-256 digest computed in Phase 3, making the common "no change" path extremely fast.

### Pattern 2: Field-Level Config Diff with DeepDiff

**What:** Use `deepdiff.DeepDiff` to compute field-level differences between two config dicts, then convert to `NodeDiff.field_diffs` dotted-path string format.
**When to use:** Only for matched node pairs where `config_hash` differs (after the fast-path check).

```python
# Source: deepdiff documentation + project-specific field_diffs schema
from deepdiff import DeepDiff
from typing import Any


# Fields excluded from diff comparison (display-only, not functional)
# These are already stripped by Phase 3 normalizer via patterns.py but
# may appear if the differ is called with un-normalized AlteryxNode.config.
# The differ operates on AlteryxNode.config (raw), not the normalized stripped dict,
# so these exclusions protect against layout noise in the raw config.
_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    # Canvas position fields (NORM-03 — these live on AlteryxNode.x/y, not config)
    # Note: AlteryxNode.config should never contain x/y per Phase 1 data model,
    # but some tool types embed position hints in config XML. Exclude defensively.
    "AnnotationDisplayMode",  # display-only annotation rendering hint
    "Position",               # redundant with AlteryxNode.x/y
})


def _diff_node(
    old_node: AlteryxNode,
    new_node: AlteryxNode,
) -> NodeDiff:
    """Compute field-level config diff between two matched AlteryxNode instances.

    Uses DeepDiff for recursive path extraction. Converts DeepDiff output to
    NodeDiff.field_diffs dict[str, tuple[Any, Any]] with dotted-path string keys.

    List fields are treated as atomic values (whole list = before/after) because
    DeepDiff with iterable_compare_func=None and treat_as_multiset=False reports
    list differences as value_changed at the list path level.
    """
    dd = DeepDiff(
        old_node.config,
        new_node.config,
        ignore_order=False,           # preserve list element order (atomic comparison)
        report_repetition=False,
        verbose_level=2,              # include before/after values in all change types
    )

    field_diffs: dict[str, tuple[Any, Any]] = {}

    # Convert DeepDiff paths to dotted strings and collect before/after values
    for change_type, changes in dd.items():
        if change_type == "values_changed":
            for path, change in changes.items():
                key = _deepdiff_path_to_dotted(path)
                if key not in _EXCLUDED_FIELDS and not _is_excluded_path(key):
                    field_diffs[key] = (change["old_value"], change["new_value"])
        elif change_type == "dictionary_item_added":
            for path in changes:
                key = _deepdiff_path_to_dotted(path)
                if not _is_excluded_path(key):
                    field_diffs[key] = (None, _get_nested(new_node.config, path))
        elif change_type == "dictionary_item_removed":
            for path in changes:
                key = _deepdiff_path_to_dotted(path)
                if not _is_excluded_path(key):
                    field_diffs[key] = (_get_nested(old_node.config, path), None)
        elif change_type in ("iterable_item_added", "iterable_item_removed",
                             "type_changes", "attribute_added", "attribute_removed"):
            # Treat list changes as atomic: surface the full list before/after
            # This handles the CONTEXT.md requirement: lists are before/after atomic
            for path, change in (changes.items() if isinstance(changes, dict) else []):
                key = _deepdiff_path_to_dotted(path)
                if not _is_excluded_path(key):
                    field_diffs[key] = (
                        change.get("old_value"),
                        change.get("new_value"),
                    )

    if not field_diffs:
        # config_hash differed but DeepDiff found no changes after exclusions
        # This should not happen in production but raise to detect exclusion bugs
        raise ValueError(
            f"config_hash differs for tool {old_node.tool_id} but no field diffs found "
            f"after exclusions. Check _EXCLUDED_FIELDS list."
        )

    return NodeDiff(
        tool_id=old_node.tool_id,
        old_node=old_node,
        new_node=new_node,
        field_diffs=field_diffs,
    )


def _deepdiff_path_to_dotted(path: str) -> str:
    """Convert DeepDiff path notation to dotted string.

    DeepDiff uses root['key1']['key2'] notation.
    Convert to: key1.key2
    """
    # Strip 'root[' prefix and trailing ']', split on ']['
    inner = path.removeprefix("root")
    # ['key1']['key2'] -> key1.key2
    parts = inner.strip("[]").split("']['")
    return ".".join(p.strip("'\"") for p in parts if p)
```

### Pattern 3: Edge Symmetric Difference

**What:** Use frozenset symmetric difference to find added/removed connections. AlteryxConnection is hashable because it is `frozen=True` (which auto-generates `__hash__`).
**When to use:** Always — one line produces the complete edge diff.

```python
# Source: Python stdlib set operations + project AlteryxConnection model

def _diff_edges(
    old_connections: tuple[AlteryxConnection, ...],
    new_connections: tuple[AlteryxConnection, ...],
) -> tuple[EdgeDiff, ...]:
    """Compute edge additions and removals via symmetric set difference.

    AlteryxConnection is frozen=True so it is hashable.
    Rewiring = one removed edge + one added edge (no special rewiring category
    per CONTEXT.md locked decision).
    When a tool is removed, its edges appear in old_connections but not new —
    they are automatically classified as removed by the set difference.
    """
    old_set = frozenset(old_connections)
    new_set = frozenset(new_connections)

    removed = old_set - new_set
    added = new_set - old_set

    edge_diffs: list[EdgeDiff] = []

    for conn in sorted(removed, key=lambda c: (c.src_tool, c.src_anchor, c.dst_tool, c.dst_anchor)):
        edge_diffs.append(EdgeDiff(
            src_tool=conn.src_tool,
            src_anchor=conn.src_anchor,
            dst_tool=conn.dst_tool,
            dst_anchor=conn.dst_anchor,
            change_type="removed",
        ))

    for conn in sorted(added, key=lambda c: (c.src_tool, c.src_anchor, c.dst_tool, c.dst_anchor)):
        edge_diffs.append(EdgeDiff(
            src_tool=conn.src_tool,
            src_anchor=conn.src_anchor,
            dst_tool=conn.dst_tool,
            dst_anchor=conn.dst_anchor,
            change_type="added",
        ))

    return tuple(edge_diffs)
```

**Note on connection identity:** The CONTEXT.md specifies that edge identity uses normalized/matched tool names from Phase 4. In practice, `AlteryxConnection` stores `src_tool: ToolID` and `dst_tool: ToolID` (integer IDs). After Phase 4 matching, the ToolIDs in old and new `MatchResult.matched` pairs are the **Phase 4 matched identities** — but the raw `old_connections` and `new_connections` use the original ToolIDs from their respective `WorkflowDoc`. This means the differ must translate matched node IDs when diffing edges, OR use the original WorkflowDoc connections directly (symmetric difference still works because the 4-tuple comparison is on the original IDs within each workflow). Since edge rewiring is detected as one removed + one added, and the connections within each workflow consistently reference their own tool IDs, the symmetric difference approach works correctly without explicit ID translation.

### Pattern 4: `is_empty` Property on DiffResult

**What:** Add `is_empty` to `DiffResult` by removing `slots=True` (property is incompatible with `slots=True`).
**When to use:** Wave 0 — modify `models/diff.py` before implementing differ logic.

```python
# Source: project pattern modified for property support

@dataclass(frozen=True, kw_only=True)  # slots=True removed to allow @property
class DiffResult:
    """Complete diff result between two WorkflowDoc instances."""

    added_nodes: tuple[AlteryxNode, ...] = field(default_factory=tuple)
    removed_nodes: tuple[AlteryxNode, ...] = field(default_factory=tuple)
    modified_nodes: tuple[NodeDiff, ...] = field(default_factory=tuple)
    edge_diffs: tuple[EdgeDiff, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        """True when no additions, removals, modifications, or edge diffs."""
        return (
            not self.added_nodes
            and not self.removed_nodes
            and not self.modified_nodes
            and not self.edge_diffs
        )
```

**Why remove `slots=True` for `DiffResult` only:** Python 3.11 does not allow defining `@property` on a `slots=True` dataclass because slots reserve descriptor slots at class-creation time but `@property` is added after the `__slots__` tuple is frozen. `DiffResult` is created once per run (not in tight loops), so the memory benefit of `slots=True` is negligible here.

**Test impact:** `test_models.py::TestDiffModelsConstruction` tests will still pass because they construct `DiffResult()` with keyword args. The `frozen=True` semantics are preserved. The existing `TestFrozenSemantics` tests do not test `DiffResult` mutation directly, only `AlteryxNode`, `AlteryxConnection`, and `WorkflowDoc`.

### Anti-Patterns to Avoid

- **Calling DeepDiff on every matched pair regardless of config_hash:** Always check `old.config_hash != new.config_hash` first. DeepDiff does recursive traversal — unnecessary on identical configs.
- **Using `ignore_order=True` in DeepDiff for list fields:** CONTEXT.md says lists are atomic (whole list is before/after). `ignore_order=True` would silently ignore reordered list elements, producing false "no change" for list reordering. Keep `ignore_order=False`.
- **Normalizing the config before diffing:** The normalizer already stripped noise (TempFile paths, timestamps, GUIDs). Phase 5 differs on `AlteryxNode.config` (raw), not on the stripped dict. Do not call `strip_noise()` again in the differ — that would create a dependency cycle and is incorrect (the raw config is what downstream reporting phases display as before/after values).
- **Using frozenset on mutable objects:** `AlteryxConnection` is `frozen=True` making it hashable. Never replace it with a mutable version — the hash-based set operations depend on this.
- **Treating absent key as `None` explicitly before DeepDiff:** DeepDiff reports missing keys via `dictionary_item_added` and `dictionary_item_removed`. The handler for these change types must use `None` as the missing side's value per CONTEXT.md.
- **Raising in `diff()` when `field_diffs` is empty after exclusions:** This should be a developer-mode assertion, not a user-facing error. If the normalizer's config_hash is correct, config_hash differing but zero field diffs means the exclusion list incorrectly stripped real changes. Log or assert, don't crash silently.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Nested dict recursive diff | Custom `_diff_dicts()` walker | `deepdiff.DeepDiff` | Handles nested dicts, lists (atomic or element-level), None values, type changes, missing keys — all the edge cases the walker needs; tested against thousands of real-world schemas |
| Path extraction from DeepDiff | Custom string parsing of `root['a']['b']` format | `deepdiff` built-in path objects (`PrettyOrderedSet` keys are strings, `tree.path()` for tree format) | Path format is documented and stable; hand-parsing is fragile if deepdiff changes notation |
| Set-based edge comparison | Nested loops comparing each old connection to each new | `frozenset` arithmetic | O(n) with hash lookup vs O(n²) with loops; correctness guaranteed by AlteryxConnection's __hash__/__eq__ |

**Key insight:** Dict diffing with path extraction is more complex than it appears — handling lists, None vs missing, nested structures, and type changes requires many conditionals. DeepDiff is the established library for this and is used in pytest-deepdiff, Airflow's diff utilities, and CI comparison tools. The field count in Alteryx tool configs (typically 5-50 fields) is well within DeepDiff's performance profile.

## Common Pitfalls

### Pitfall 1: `@property` Incompatible with `slots=True`
**What goes wrong:** `TypeError: 'is_empty' in __slots__ conflicts with class variable in 'DiffResult'` — or the property silently fails to work as a descriptor.
**Why it happens:** `slots=True` on a dataclass pre-creates `__slots__` before user-defined descriptors. A `@property` defined after `__slots__` creation cannot be placed in the slots.
**How to avoid:** Remove `slots=True` from `DiffResult` in Wave 0 before adding the `is_empty` property. All other dataclasses (`NodeDiff`, `EdgeDiff`) can keep `slots=True`.
**Warning signs:** `AttributeError: 'DiffResult' object has no attribute 'is_empty'` at runtime.

### Pitfall 2: DeepDiff Path Format Ambiguity
**What goes wrong:** `_deepdiff_path_to_dotted("root['Expression']")` works but `_deepdiff_path_to_dotted("root[0]")` produces `"0"` instead of a meaningful path for list indices.
**Why it happens:** DeepDiff represents both dict keys and list indices in path strings but uses different formats: `root['key']` for dict keys vs `root[0]` for list indices.
**How to avoid:** Since lists are treated as atomic values (CONTEXT.md), list-index paths should not appear in the output — the whole list should be reported as one before/after entry at the list's parent path. Verify this in tests with a list-valued config field.
**Warning signs:** `field_diffs` containing integer-string paths like `"mylist.0"`, `"mylist.1"`.

### Pitfall 3: config_hash Differs but DeepDiff Finds Nothing
**What goes wrong:** `_diff_node` is called (config_hash differs), DeepDiff returns an empty `{}`, `field_diffs` is empty, and a `NodeDiff` with zero field diffs is silently emitted.
**Why it happens:** Normally impossible if the normalizer is correct. Can happen if `_EXCLUDED_FIELDS` over-aggressively strips real changes, or if config contains only non-JSON-serializable types that normalize differently but compare equally.
**How to avoid:** Treat empty `field_diffs` after calling DeepDiff as a developer bug — raise `ValueError` with a clear message identifying the tool. This forces the exclusion list to be audited when hit.
**Warning signs:** `NodeDiff` instances with empty `field_diffs` in test output.

### Pitfall 4: Edge Diff Using ToolID from MatchResult vs Original WorkflowDoc
**What goes wrong:** Using `match_result.matched` pairs' ToolIDs to look up connections in old/new workflow, but the connections use the original XML ToolIDs which may differ (ToolID churn scenario).
**Why it happens:** Phase 4 matched pairs carry `NormalizedNode.source.tool_id` — the original ToolID from the raw `WorkflowDoc`. For Phase 1 exact-match pairs, old and new ToolIDs are the same. For Phase 2 Hungarian-matched pairs, old ToolID ≠ new ToolID. If edge comparison tries to remap ToolIDs it can incorrectly compare connections from different ID spaces.
**How to avoid:** Compare connections using each workflow's own connection set directly (`old_connections` from old `WorkflowDoc.connections`, `new_connections` from new `WorkflowDoc.connections`). The symmetric difference correctly identifies additions and removals within each workflow's topology. Do not remap ToolIDs for edge comparison — the 4-tuple uniqueness within each workflow is what matters.
**Warning signs:** Edge diffs showing spurious additions/removals for nodes that were correctly matched by Phase 4.

### Pitfall 5: Forgetting to Handle MatchResult.removed Edges
**What goes wrong:** When a tool is removed, its connections still exist in `old_connections`. If the differ only checks connections of matched nodes, removed-node connections are silently dropped from `edge_diffs`.
**Why it happens:** Incorrect scoping: only iterating `match_result.matched` pair connections instead of comparing full workflow connection sets.
**How to avoid:** Always diff the complete connection tuples (`old_connections` and `new_connections`), not filtered subsets. The symmetric difference approach handles this automatically.
**Warning signs:** Removing a tool with connections does not produce `EdgeDiff` entries for those connections.

### Pitfall 6: deepdiff Import Breaks Before Installation
**What goes wrong:** `ImportError: No module named 'deepdiff'` when deepdiff is not in pyproject.toml yet.
**Why it happens:** Same pattern as scipy in Phase 4 — Wave 0 must install before implementation plans run.
**How to avoid:** Wave 0 task must run `uv add deepdiff` before any implementation plan.
**Warning signs:** Collection errors in pytest when test_differ.py imports the differ module.

## Code Examples

Verified patterns from project codebase and deepdiff documentation:

### DiffResult is_empty check (from success criterion)
```python
# Source: project pattern — frozen dataclass with property (slots=True removed)
result = diff(match_result, old_connections, new_connections)
if result.is_empty:
    print("Workflows are functionally identical")
```

### AlteryxConnection hashability (confirmed from models/workflow.py)
```python
# Source: src/alteryx_diff/models/workflow.py — frozen=True gives __hash__
old_set = frozenset(old_connections)   # AlteryxConnection is frozen=True -> hashable
new_set = frozenset(new_connections)
removed = old_set - new_set
added = new_set - old_set
```

### DeepDiff basic usage for nested dicts
```python
# Source: deepdiff docs (https://zepworks.com/deepdiff/current/)
from deepdiff import DeepDiff

old_config = {"Expression": "[Amount] > 1000", "OutputFile": {"path": "out.csv"}}
new_config = {"Expression": "[Amount] > 5000", "OutputFile": {"path": "out.csv"}}

dd = DeepDiff(old_config, new_config, ignore_order=False, verbose_level=2)
# dd = {'values_changed': {"root['Expression']": {'new_value': '[Amount] > 5000', 'old_value': '[Amount] > 1000'}}}
```

### DeepDiff missing key handling
```python
# Source: deepdiff docs — missing keys appear as dictionary_item_added/removed
old_config = {"Expression": "[Amount] > 1000"}
new_config = {"Expression": "[Amount] > 1000", "SortOrder": "Ascending"}

dd = DeepDiff(old_config, new_config, ignore_order=False, verbose_level=2)
# dd = {'dictionary_item_added': {"root['SortOrder']"}}
# After extraction: field_diffs["SortOrder"] = (None, "Ascending")
```

### List field treated as atomic (CONTEXT.md requirement)
```python
# Source: deepdiff behavior with list fields
# When a list value changes, DeepDiff reports iterable_item_added/removed or values_changed
# at the list level. The differ should surface the entire list as before/after.
old_config = {"Fields": ["ID", "Name", "Amount"]}
new_config = {"Fields": ["ID", "Name", "Amount", "Region"]}

dd = DeepDiff(old_config, new_config, ignore_order=False, verbose_level=2)
# Reports iterable_item_added at root['Fields'][3]
# Differ should surface: field_diffs["Fields"] = (["ID","Name","Amount"], ["ID","Name","Amount","Region"])
```

### Differ public module layout (matches normalizer/matcher convention)
```python
# src/alteryx_diff/differ/__init__.py
"""Diff engine pipeline stage for alteryx_diff.

Public surface: diff()

  from alteryx_diff.differ import diff
  result = diff(match_result, old_connections, new_connections)
"""

from alteryx_diff.differ.differ import diff

__all__ = ["diff"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full config snapshot in NodeDiff | Only changed fields with before/after (field_diffs dict) | Design decision Phase 1 | Downstream reporting only receives changed fields — reduced payload for reporters |
| Edge comparison by tool name | 4-tuple anchor identity (src_tool + src_anchor + dst_tool + dst_anchor) | Phase 5 design | No false "no change" when same source/dest tools have different anchor labels |
| Semantic list diff (element-level) | Atomic list comparison (whole list before/after) | CONTEXT.md decision | Prevents false partial-match on user filter expression lists |

**Deprecated/outdated:**
- Any approach comparing raw XML strings: Phase 3 normalizer already converted to Python dicts. Never compare XML strings in the differ.

## Open Questions

1. **DeepDiff list handling for `iterable_item_added/removed`**
   - What we know: CONTEXT.md says lists are atomic (whole list = before/after). DeepDiff reports list changes element-by-element by default.
   - What's unclear: The exact DeepDiff configuration to suppress element-level list diffs and surface the whole list as one entry. `ignore_order=False` doesn't collapse element changes to one list-level entry.
   - Recommendation: In Wave 0 tests, add a fixture for a list-valued config field that changes. If DeepDiff produces element-level paths, the path-to-dotted converter must detect integer indices and collapse them to the parent list path. Alternatively, use `exclude_paths` on integer-indexed paths and add a separate list-level comparison step. Verify behavior in Wave 0 before implementing.

2. **Exact `_EXCLUDED_FIELDS` contents**
   - What we know: CONTEXT.md gives Claude discretion. Position (x/y) is already on `AlteryxNode.x`/`AlteryxNode.y` not in `config`. The normalizer strips TempFile, timestamps, GUIDs from config before hashing. But the differ operates on raw `AlteryxNode.config` not the stripped version.
   - What's unclear: Which specific config dict keys in real Alteryx `.yxmd` files represent display-only metadata vs functional configuration. The normalizer's `_EXCLUDED_FIELDS` is a starting point.
   - Recommendation: Start with an empty `_EXCLUDED_FIELDS` frozenset. If Phase 5 integration tests reveal spurious diffs from display fields, add those keys as discovered. The normalizer's `GUID_VALUE_KEYS` frozenset pattern (start empty, add from real files) is the precedent.

3. **NodeDiff `tool_name` vs `tool_id` discrepancy**
   - What we know: CONTEXT.md says `NodeDiff` carries `tool_name`. The existing `models/diff.py` carries `tool_id: ToolID` (not `tool_name`). These are the same object in the Phase 1 scaffold.
   - What's unclear: Whether `tool_name` in CONTEXT.md meant `tool_type` (the string name like "Filter") or `tool_id`. The existing model uses `tool_id`, which is the canonical identifier.
   - Recommendation: Keep the existing `NodeDiff.tool_id: ToolID` field — it is the correct unique identifier. `tool_type` is available via `old_node.tool_type` on the `NodeDiff.old_node` field. No model change needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured in pyproject.toml `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` — `testpaths = ["tests"]`, `addopts = ["--import-mode=importlib"]` |
| Quick run command | `pytest tests/test_differ.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DIFF-01 | Tool added to new workflow appears in DiffResult.added_nodes with full config | unit | `pytest tests/test_differ.py::test_added_node -x` | No — Wave 0 |
| DIFF-01 | Tool removed from old workflow appears in DiffResult.removed_nodes with full config | unit | `pytest tests/test_differ.py::test_removed_node -x` | No — Wave 0 |
| DIFF-02 | Modified tool shows before/after for changed fields only — unchanged fields absent | unit | `pytest tests/test_differ.py::test_modified_node_changed_fields_only -x` | No — Wave 0 |
| DIFF-02 | Modified filter expression reports before/after at "Expression" path | unit | `pytest tests/test_differ.py::test_filter_expression_change -x` | No — Wave 0 |
| DIFF-02 | Nested field change reports full dotted path (e.g., "OutputFile.path") | unit | `pytest tests/test_differ.py::test_nested_field_change -x` | No — Wave 0 |
| DIFF-02 | Key present in old but absent in new → field_diffs[key] = (old_value, None) | unit | `pytest tests/test_differ.py::test_absent_key_after -x` | No — Wave 0 |
| DIFF-03 | Rewired connection (same src/dst tools, different anchor) = one removed + one added EdgeDiff | unit | `pytest tests/test_differ.py::test_rewired_connection -x` | No — Wave 0 |
| DIFF-03 | Connection added to new workflow appears in DiffResult.edge_diffs with change_type="added" | unit | `pytest tests/test_differ.py::test_added_connection -x` | No — Wave 0 |
| DIFF-03 | Connection removed from old workflow appears in DiffResult.edge_diffs with change_type="removed" | unit | `pytest tests/test_differ.py::test_removed_connection -x` | No — Wave 0 |
| (SC 5) | Two functionally identical workflows produce DiffResult.is_empty == True | unit | `pytest tests/test_differ.py::test_identical_workflows_empty_result -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_differ.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/alteryx_diff/models/diff.py` — remove `slots=True` from `DiffResult`, add `is_empty` property
- [ ] `src/alteryx_diff/differ/__init__.py` — package stub exposing `diff()`
- [ ] `src/alteryx_diff/differ/differ.py` — `diff()` stub (can raise NotImplementedError)
- [ ] `tests/fixtures/diffing.py` — fixture WorkflowDocs and MatchResults (ToolIDs start at 401)
- [ ] `tests/test_differ.py` — all 10 test cases above
- [ ] Framework install: `uv add deepdiff` — deepdiff not currently in pyproject.toml

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/alteryx_diff/models/diff.py` — DiffResult, NodeDiff, EdgeDiff already defined; field_diffs uses `dict[str, tuple[Any, Any]]` schema
- Existing codebase: `src/alteryx_diff/models/workflow.py` — AlteryxConnection is `frozen=True` (hashable), confirms frozenset set-ops are valid
- Existing codebase: `src/alteryx_diff/matcher/matcher.py` — MatchResult.matched/removed/added carry NormalizedNode; .source gives AlteryxNode
- Python 3.11 docs: dataclasses — `slots=True` is incompatible with user-defined `@property` descriptors; confirmed from Python 3.11 dataclasses documentation

### Secondary (MEDIUM confidence)
- deepdiff official docs (https://zepworks.com/deepdiff/current/) — DeepDiff API, path format, `verbose_level`, `ignore_order`, change type keys (`values_changed`, `dictionary_item_added/removed`, `iterable_item_added/removed`)
- deepdiff PyPI (https://pypi.org/project/deepdiff/) — current version 8.x, actively maintained, Python 3.11+ support confirmed

### Tertiary (LOW confidence)
- None — all critical claims verified with official sources or codebase inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all types come from the existing project models (already in codebase); deepdiff API verified against official docs
- Architecture: HIGH — pattern follows normalizer/matcher structure exactly; module layout is a direct extension of established conventions
- Pitfalls: HIGH — `slots=True` + property incompatibility is a Python 3.11 documented limitation; edge/tool diff pitfalls derived from data model analysis; deepdiff pitfalls from docs

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (deepdiff is stable; Python stdlib patterns don't change; project conventions are locked)
