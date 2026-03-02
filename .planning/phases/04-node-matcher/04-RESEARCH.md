# Phase 4: Node Matcher - Research

**Researched:** 2026-03-01
**Domain:** Bipartite graph matching — two-pass node pairing via exact ToolID lookup + Hungarian algorithm (scipy.optimize.linear_sum_assignment)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Cost function weighting:**
- Tool type is a hard block: a cost matrix is built per-type — only same-type tools are compared against each other. Cross-type pairs never appear in the matrix.
- Within same-type: type match is guaranteed (enforced at construction), so cost is computed from position proximity + config hash similarity only.
- Exact sub-weights between position and config hash: Claude's discretion.
- Position proximity uses normalized canvas distance — normalize (x, y) by workflow canvas bounds so absolute pixel scale doesn't skew results for large vs small workflows.

**Threshold + rejection behavior:**
- Threshold is hardcoded at 0.8 (no configurable parameter).
- After Hungarian assigns pairs, any pair with cost > 0.8 is rejected: the old node goes to removals, the new node goes to additions.
- Threshold applies at the pair level (per assigned pair, not per-tool independently).
- No low-confidence annotation — rejected pairs are simply unmatched. Callers do not see ambiguous matches.

**Matcher output contract:**
- Function signature: accepts `list[NormalizedNode]` (old) and `list[NormalizedNode]` (new) — Phase 3 output is the direct input. Matcher never touches raw XML.
- Returns a named tuple or dataclass: `MatchResult(matched: list[tuple[NormalizedNode, NormalizedNode]], removed: list[NormalizedNode], added: list[NormalizedNode])`.
- Each matched pair contains the full `(old_node, new_node)` NormalizedNode objects — no ID-only tuples.
- No `match_source` annotation. Which pass produced a match is an internal implementation detail, not surfaced to callers.

**Partial regeneration handling:**
- Pass 1 consumes exact ToolID matches. Only the leftover unmatched sets (old-only, new-only) feed into the Hungarian pass.
- scipy's `linear_sum_assignment` handles non-square matrices natively — no dummy row/column padding needed.
- If either unmatched set is empty after pass 1, skip the Hungarian pass entirely (early exit).
- Config hash similarity uses the full config hash from the `NormalizedNode` produced by Phase 3 — no re-hashing or stripping of connection data.

### Claude's Discretion
- Exact weights for position proximity vs config hash similarity within the per-type cost function.
- Specific normalization formula for canvas distance.
- Internal data structures (numpy array shape, index mapping, etc.) used to build and query the cost matrix.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DIFF-04 | System uses two-pass node matching — exact ToolID lookup first, then Hungarian algorithm similarity fallback — to prevent phantom add/remove pairs when Alteryx regenerates ToolIDs | scipy.optimize.linear_sum_assignment provides the Hungarian algorithm; MatchResult dataclass provides the output contract; per-type cost matrix construction ensures type safety |
</phase_requirements>

## Summary

Phase 4 implements a two-pass node matcher that accepts two `list[NormalizedNode]` (old/new) and returns a `MatchResult` dataclass. Pass 1 is an O(n) exact ToolID dict lookup that consumes all exact-match pairs. Pass 2 applies the Hungarian algorithm via `scipy.optimize.linear_sum_assignment` to the remaining unmatched leftovers, using a per-type cost matrix built from normalized position distance and config hash similarity. Any assigned pair with cost > 0.8 is rejected to unmatched sets.

The primary new dependency is `scipy>=1.13` (for `linear_sum_assignment`, Python 3.11 support, and non-square matrix handling). numpy is a transitive dependency of scipy and does not need to be listed separately unless numpy-specific APIs are called directly. The existing project codebase pattern — pure functions, frozen dataclasses, no mutable state — applies identically here. The matcher module follows the same package structure as the normalizer (a `matcher/` package with `__init__.py` exposing a single public function).

The critical design insight is that the cost matrix is built **per tool type**, not across all tools at once. This means one `linear_sum_assignment` call per distinct tool type present in the unmatched sets. Within each type-group, costs come from (a) normalized Euclidean canvas distance and (b) config hash similarity (0 if hashes match, 1 otherwise, or a fractional similarity if preferred). Threshold rejection at cost > 0.8 is the final gate before pairs enter `MatchResult.matched`.

**Primary recommendation:** Implement `src/alteryx_diff/matcher/matcher.py` exposing `match(old_nodes, new_nodes) -> MatchResult`. Add `scipy>=1.13` as a runtime dependency in `pyproject.toml`. Use `numpy.ndarray` internally for the cost matrix. Do not expose numpy or scipy from the public API.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scipy | >=1.13 | `linear_sum_assignment` — Hungarian algorithm for rectangular cost matrices | The only well-maintained Python implementation of the Jonker-Volgenant algorithm; handles non-square matrices natively; used in production (DETR, MOT trackers, etc.) |
| numpy | >=1.26.4 (transitive via scipy) | Cost matrix array construction; index mapping after assignment | Required by scipy; provides `ndarray` for O(1) indexed access after assignment |

**Note:** scipy 1.17.1 (released 2026-02-22) is the latest stable release. It requires Python >=3.11 (matching project constraint) and numpy >=1.26.4. scipy 1.13+ has long supported Python 3.11 and non-square matrices. Use `scipy>=1.13` as the lower bound in pyproject.toml to avoid pinning too tightly.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python standard `dataclasses` | stdlib (3.11+) | `MatchResult` return type; `frozen=True, kw_only=True, slots=True` | Same pattern as all other model types in this codebase |
| Python standard `math` | stdlib | `sqrt`, `hypot` for Euclidean distance; `isinf` guard | Canvas distance computation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `scipy.optimize.linear_sum_assignment` | `lapjv` (Jonker-Volgenant pure Python) | lapjv is faster at very large matrices but not in PyPI standard; scipy is already the "one dependency" add for this feature |
| `scipy.optimize.linear_sum_assignment` | networkx `min_weight_matching` | networkx is already in the project, but it targets general graph matching, not bipartite assignment; scipy is strictly faster and cleaner for this use case |
| `dataclass` for `MatchResult` | `typing.NamedTuple` | Both are valid; the CONTEXT.md says "named tuple or dataclass" — use frozen dataclass to stay consistent with every other model in the project |

**Installation:**
```bash
uv add scipy
```
(numpy is pulled in as a transitive dependency of scipy — no separate `uv add numpy` needed)

## Architecture Patterns

### Recommended Project Structure
```
src/alteryx_diff/
├── matcher/
│   ├── __init__.py          # Public surface: match() only
│   ├── matcher.py           # match() entry point; pass 1 exact, pass 2 Hungarian dispatch
│   └── _cost.py             # Cost matrix construction helpers (_build_cost_matrix, _position_cost, _hash_cost)
tests/
├── fixtures/
│   └── matching.py          # Fixture nodes for matcher tests (ToolIDs start at 301 to avoid collision)
└── test_matcher.py          # All matcher tests; covers all DIFF-04 scenarios
```

**Convention notes from existing codebase:**
- `__init__.py` is the sole public surface; no `__all__` inside internal modules
- Internal helpers use underscore prefix (`_cost.py`, `_strip.py` pattern already established)
- All model types imported from `alteryx_diff.models` (never from sub-modules)
- Fixture ToolIDs: Phase 1 uses 1-100, Phase 2 uses 1-2, Phase 3 uses 101-201. Phase 4 fixtures should start at 301.
- Test files mirror source module name: `test_matcher.py` for the `matcher` package
- `zip(..., strict=True)` is enforced by ruff B905 — always use `strict=True`

### Pattern 1: Two-Pass Match Function

**What:** Pass 1 does exact ToolID lookup in O(n); Pass 2 dispatches Hungarian per-type on leftovers.
**When to use:** Always — this is the top-level entry point.

```python
# Source: project pattern (pure function, no I/O, no side effects)
from __future__ import annotations

from dataclasses import dataclass, field
from alteryx_diff.models import NormalizedNode


@dataclass(frozen=True, kw_only=True, slots=True)
class MatchResult:
    matched: tuple[tuple[NormalizedNode, NormalizedNode], ...]
    removed: tuple[NormalizedNode, ...]   # present in old, absent in new
    added: tuple[NormalizedNode, ...]     # present in new, absent in old


COST_THRESHOLD = 0.8


def match(
    old_nodes: list[NormalizedNode],
    new_nodes: list[NormalizedNode],
) -> MatchResult:
    """Two-pass node matcher. Pass 1: exact ToolID. Pass 2: Hungarian per-type."""
    matched: list[tuple[NormalizedNode, NormalizedNode]] = []

    # Pass 1: exact ToolID lookup — O(n)
    new_by_id = {n.source.tool_id: n for n in new_nodes}
    unmatched_old: list[NormalizedNode] = []
    matched_new_ids: set[int] = set()

    for old in old_nodes:
        if old.source.tool_id in new_by_id:
            matched.append((old, new_by_id[old.source.tool_id]))
            matched_new_ids.add(old.source.tool_id)
        else:
            unmatched_old.append(old)

    unmatched_new = [n for n in new_nodes if n.source.tool_id not in matched_new_ids]

    # Pass 2: Hungarian fallback — skip entirely if nothing left to match
    if unmatched_old and unmatched_new:
        extra_matched, remaining_old, remaining_new = _hungarian_match(
            unmatched_old, unmatched_new
        )
        matched.extend(extra_matched)
        unmatched_old = remaining_old
        unmatched_new = remaining_new

    return MatchResult(
        matched=tuple(matched),
        removed=tuple(unmatched_old),
        added=tuple(unmatched_new),
    )
```

### Pattern 2: Per-Type Hungarian Dispatch

**What:** Group unmatched old/new nodes by tool_type, then call `linear_sum_assignment` once per type group.
**When to use:** In Pass 2, after exact-match pass.

```python
# Source: project pattern + scipy docs (https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html)
from collections import defaultdict
import numpy as np
from scipy.optimize import linear_sum_assignment


def _hungarian_match(
    unmatched_old: list[NormalizedNode],
    unmatched_new: list[NormalizedNode],
) -> tuple[
    list[tuple[NormalizedNode, NormalizedNode]],
    list[NormalizedNode],
    list[NormalizedNode],
]:
    """Run Hungarian algorithm per tool_type group. Returns (matched, leftover_old, leftover_new)."""
    # Group by tool_type — cross-type pairs are never compared
    old_by_type: dict[str, list[NormalizedNode]] = defaultdict(list)
    new_by_type: dict[str, list[NormalizedNode]] = defaultdict(list)
    for node in unmatched_old:
        old_by_type[node.source.tool_type].append(node)
    for node in unmatched_new:
        new_by_type[node.source.tool_type].append(node)

    all_types = set(old_by_type) | set(new_by_type)
    matched: list[tuple[NormalizedNode, NormalizedNode]] = []
    leftover_old: list[NormalizedNode] = []
    leftover_new: list[NormalizedNode] = []

    for tool_type in all_types:
        old_group = old_by_type.get(tool_type, [])
        new_group = new_by_type.get(tool_type, [])

        if not old_group:
            leftover_new.extend(new_group)
            continue
        if not new_group:
            leftover_old.extend(old_group)
            continue

        # Build cost matrix: shape (len(old_group), len(new_group))
        cost = _build_cost_matrix(old_group, new_group)

        # Assign — scipy handles non-square natively
        row_ind, col_ind = linear_sum_assignment(cost)

        matched_old_idx: set[int] = set()
        matched_new_idx: set[int] = set()

        for r, c in zip(row_ind, col_ind, strict=True):
            if cost[r, c] <= COST_THRESHOLD:
                matched.append((old_group[r], new_group[c]))
                matched_old_idx.add(r)
                matched_new_idx.add(c)
            # else: rejected — both go to leftovers below

        leftover_old.extend(n for i, n in enumerate(old_group) if i not in matched_old_idx)
        leftover_new.extend(n for i, n in enumerate(new_group) if i not in matched_new_idx)

    return matched, leftover_old, leftover_new
```

### Pattern 3: Cost Matrix Construction

**What:** Build a 2D numpy float array where `cost[i, j]` is the pairwise cost between `old_group[i]` and `new_group[j]`.
**When to use:** Called once per type group in Pass 2.

```python
# Source: project pattern — canvas bounds normalization as decided in CONTEXT.md

def _build_cost_matrix(
    old_group: list[NormalizedNode],
    new_group: list[NormalizedNode],
) -> np.ndarray:
    """
    Build cost matrix of shape (len(old_group), len(new_group)).

    Cost is in [0.0, 1.0]: 0.0 = perfect match, 1.0 = maximally different.
    cost[i, j] = 0.5 * position_cost(i, j) + 0.5 * hash_cost(i, j)
    """
    # Canvas bounds from the union of both groups for normalization
    all_positions = [n.position for n in old_group + new_group]
    xs = [p[0] for p in all_positions]
    ys = [p[1] for p in all_positions]
    x_range = max(xs) - min(xs) if len(xs) > 1 else 1.0
    y_range = max(ys) - min(ys) if len(ys) > 1 else 1.0

    rows = len(old_group)
    cols = len(new_group)
    cost = np.empty((rows, cols), dtype=np.float64)

    for i, old in enumerate(old_group):
        for j, new in enumerate(new_group):
            pos_cost = _position_cost(old.position, new.position, x_range, y_range)
            hash_cost = 0.0 if old.config_hash == new.config_hash else 1.0
            cost[i, j] = 0.5 * pos_cost + 0.5 * hash_cost

    return cost


def _position_cost(
    pos_a: tuple[float, float],
    pos_b: tuple[float, float],
    x_range: float,
    y_range: float,
) -> float:
    """Normalized Euclidean distance in [0.0, 1.0].

    Normalize each axis independently by workflow canvas bounds so large vs
    small workflows produce comparable costs. Clamp to 1.0 (max cost).
    """
    import math
    dx = (pos_a[0] - pos_b[0]) / x_range
    dy = (pos_a[1] - pos_b[1]) / y_range
    dist = math.hypot(dx, dy)
    # Maximum possible normalized distance is sqrt(2) for the unit square
    return min(dist / math.sqrt(2), 1.0)
```

### Anti-Patterns to Avoid

- **Building one giant cost matrix across all tool types:** Never put different tool types in the same matrix. A Filter tool would be incorrectly matched to a Join tool if positions happened to align. Per-type grouping is a hard block per CONTEXT.md.
- **Padding non-square matrices with dummy rows/columns:** `linear_sum_assignment` natively handles rectangular matrices. Padding wastes memory and requires tracking which pairs are dummy.
- **Storing `match_source` ("exact" vs "hungarian") on pairs:** This is an internal implementation detail. The output contract does not expose it. Callers receive only matched/removed/added.
- **Running Hungarian on all nodes when unmatched sets are empty:** The early exit guard prevents calling scipy unnecessarily when all tools matched exactly.
- **Mutable MatchResult:** Use `frozen=True` to match all other model types. `tuple[tuple[...], ...]` for all sequence fields (not `list`).
- **Calling `object.__setattr__` in tests to bypass frozen:** This bypasses slots enforcement. Use `pytest.raises(dataclasses.FrozenInstanceError)` with direct assignment.
- **Using `zip()` without `strict=True`:** ruff B905 enforces this project-wide. All `zip()` calls need `strict=True`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Optimal bipartite assignment | Custom Kuhn-Munkres implementation | `scipy.optimize.linear_sum_assignment` | Jonker-Volgenant O(n^3) implementation; handles rectangular matrices; edge cases with identical costs handled correctly |
| Non-square matrix zero-padding | Manual dummy row/column injection | Native rectangular support in scipy | `linear_sum_assignment` already produces partial assignments for non-square inputs |

**Key insight:** The Hungarian algorithm has a deceptively complex implementation — augmenting path tracking, potentials, degenerate cost matrices. scipy's implementation uses a modified Jonker-Volgenant algorithm with no initialization and is battle-tested in scientific computing and computer vision (used by DETR, MOT trackers). Hand-rolling this is high-risk with zero benefit.

## Common Pitfalls

### Pitfall 1: x_range or y_range is zero
**What goes wrong:** Division by zero in `_position_cost` when all tools in a type group share the same canvas coordinate (common in small workflows with just 1 tool of a given type in each unmatched set).
**Why it happens:** A type group with 1 old tool and 1 new tool has `max - min = 0` for a single dimension.
**How to avoid:** Default `x_range` and `y_range` to `1.0` when the range is zero (any nonzero sentinel preserves ratio correctness since numerator also collapses). Already shown in code example above.
**Warning signs:** `ZeroDivisionError` or `nan` in cost matrix.

### Pitfall 2: Threshold applied before assignment, not after
**What goes wrong:** Pre-filtering the cost matrix to infinity/nan before calling `linear_sum_assignment` to "force" threshold rejection. This corrupts the assignment: scipy may produce invalid assignments if the matrix contains inf/nan.
**Why it happens:** Intuition says "block impossible pairs first." But scipy needs a clean cost matrix to find the optimal assignment.
**How to avoid:** Always call `linear_sum_assignment` on the raw cost matrix. Apply threshold check to each returned `(r, c)` pair post-assignment.
**Warning signs:** Tests pass for square matrices but fail for non-square.

### Pitfall 3: Config hash comparison using string prefix, not equality
**What goes wrong:** Using startswith() or truncated comparison for `config_hash`. Two different configurations could share a hash prefix.
**Why it happens:** Attempting to do fuzzy hash similarity (e.g., counting matching characters). The CONTEXT.md is explicit: `hash_cost = 0 if hashes match, 1 otherwise`. Binary. No partial credit.
**How to avoid:** `hash_cost = 0.0 if old.config_hash == new.config_hash else 1.0`
**Warning signs:** Two different configurations being matched at zero hash cost.

### Pitfall 4: MatchResult using list instead of tuple
**What goes wrong:** Type check failure with mypy --strict; inconsistency with every other frozen model in the codebase.
**Why it happens:** `list` is the natural Python container for "append then return."
**How to avoid:** Accumulate into `list` during computation, then `tuple(...)` in the final `MatchResult` constructor call.
**Warning signs:** `FrozenInstanceError` if you try to append to a MatchResult field; mypy errors if you annotate as `list`.

### Pitfall 5: scipy import at module level creates hard dependency before installation
**What goes wrong:** `ImportError` during any import of `alteryx_diff` if `scipy` is not yet installed (e.g., during the Wave 0 setup task).
**Why it happens:** `from scipy.optimize import linear_sum_assignment` at the top of `matcher.py` fails at import time.
**How to avoid:** Add `scipy>=1.13` to `[project] dependencies` in `pyproject.toml` before any code that imports it. The Wave 0 plan task must install scipy (`uv add scipy`) before any implementation plan runs.
**Warning signs:** `ModuleNotFoundError: No module named 'scipy'` in tests.

### Pitfall 6: Per-type dispatch misses tool types present only in old or only in new
**What goes wrong:** Tools that exist only in old (no same-type counterpart in new) are silently dropped rather than placed in `removed`.
**Why it happens:** Iterating only over `set(old_by_type) & set(new_by_type)` instead of `set(old_by_type) | set(new_by_type)`.
**How to avoid:** Union of all type keys: `all_types = set(old_by_type) | set(new_by_type)`. Handle empty group case explicitly (extend leftovers, continue).
**Warning signs:** `len(result.removed) + len(result.added) + len(result.matched) * 2 != len(old) + len(new)` — this invariant is always true and is a good test assertion.

## Code Examples

Verified patterns from official sources:

### scipy.optimize.linear_sum_assignment — Basic Usage
```python
# Source: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html
import numpy as np
from scipy.optimize import linear_sum_assignment

# Rectangular cost matrix: 3 old nodes, 2 new nodes (non-square — no padding needed)
cost = np.array([
    [0.1, 0.9],   # old[0] vs new[0], new[1]
    [0.8, 0.2],   # old[1] vs new[0], new[1]
    [0.5, 0.6],   # old[2] vs new[0], new[1]
])
row_ind, col_ind = linear_sum_assignment(cost)
# row_ind: [0, 1]  — old[0] -> new[0], old[1] -> new[1]
# col_ind: [0, 1]
# old[2] is unmatched (more rows than cols — scipy leaves it out)
# cost[row_ind, col_ind].sum() = 0.1 + 0.2 = 0.3
```

### MatchResult Invariant Check (use in tests)
```python
# Source: project pattern
def _check_match_result_invariant(
    result: MatchResult,
    old_nodes: list[NormalizedNode],
    new_nodes: list[NormalizedNode],
) -> None:
    """Every node must appear exactly once across matched/removed/added."""
    total_old_accounted = len(result.matched) + len(result.removed)
    total_new_accounted = len(result.matched) + len(result.added)
    assert total_old_accounted == len(old_nodes), (
        f"Old node count mismatch: {total_old_accounted} accounted, {len(old_nodes)} total"
    )
    assert total_new_accounted == len(new_nodes), (
        f"New node count mismatch: {total_new_accounted} accounted, {len(new_nodes)} total"
    )
```

### Frozen Dataclass for MatchResult (matches project pattern)
```python
# Source: project pattern from models/normalized.py, models/diff.py
from __future__ import annotations
from dataclasses import dataclass
from alteryx_diff.models import NormalizedNode


@dataclass(frozen=True, kw_only=True, slots=True)
class MatchResult:
    """Output of the two-pass node matcher.

    matched: pairs of (old_node, new_node) that were successfully paired
    removed: nodes present in old workflow, absent in new (genuine removals)
    added:   nodes present in new workflow, absent in old (genuine additions)
    """
    matched: tuple[tuple[NormalizedNode, NormalizedNode], ...]
    removed: tuple[NormalizedNode, ...]
    added: tuple[NormalizedNode, ...]
```

### Weight Recommendation for Cost Function
```python
# Source: Claude's discretion (CONTEXT.md gives freedom here)
# Recommended: equal weighting 0.5 / 0.5
# Rationale:
#   - Config hash is binary (match=0, mismatch=1) — high discriminating power for identical clones
#   - Position is continuous [0,1] — gradient useful when multiple tools of same type exist
#   - Equal weighting avoids over-relying on position in large workflows where
#     position proximity is less informative (tools can be far apart)
POSITION_WEIGHT = 0.5
HASH_WEIGHT = 0.5
# cost[i,j] = POSITION_WEIGHT * pos_cost + HASH_WEIGHT * hash_cost
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Naive ToolID equality only | Two-pass: exact ID + Hungarian fallback | Driven by Alteryx ToolID regeneration behavior | Prevents all phantom add/remove pairs when IDs are regenerated |
| scipy uses classical Hungarian O(n^3) | Modified Jonker-Volgenant with no initialization (still O(n^3) but faster constants) | scipy ~0.17+ | Lower constant factor; better for medium-sized matrices (10-200 tools) |
| Cost matrix with dummy padding for non-square | Native rectangular support in scipy | scipy has always supported this | No implementation burden; no index remapping needed |

**Deprecated/outdated:**
- Manual dummy-row/column padding for non-square matrices: unnecessary — scipy handles rectangular natively since at least v0.17.

## Open Questions

1. **Exact config hash similarity weight vs position weight**
   - What we know: CONTEXT.md marks this as Claude's discretion. Binary hash (0 or 1). Normalized position [0, 1].
   - What's unclear: Whether 0.5/0.5 equal weighting is optimal for Alteryx workflows that may have many tools of the same type clustered near each other.
   - Recommendation: Start with 0.5/0.5. The threshold test (> 0.8 rejection) provides a safety net. Tests will validate behavior against the known scenarios (exact match, ToolID regeneration, genuine add/remove).

2. **Canvas bounds normalization edge case: single-tool type groups**
   - What we know: A type group with exactly 1 old and 1 new tool has range = 0 for any shared dimension.
   - What's unclear: Should position be considered at all when there is only one candidate pair per type?
   - Recommendation: When range is 0, default x_range/y_range to 1.0. With a single pair per type, position cost is 0.0 (same x in the group means normalized dx = 0). The hash component alone determines match quality — appropriate behavior.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_matcher.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DIFF-04 | Exact ToolID match — all tools paired, zero phantom add/remove | unit | `pytest tests/test_matcher.py::test_exact_id_match -x` | No — Wave 0 |
| DIFF-04 | Full ToolID regeneration — zero phantom add/remove via Hungarian | unit | `pytest tests/test_matcher.py::test_full_toolid_regeneration -x` | No — Wave 0 |
| DIFF-04 | Partial ToolID regeneration — some exact, some Hungarian | unit | `pytest tests/test_matcher.py::test_partial_toolid_regeneration -x` | No — Wave 0 |
| DIFF-04 | Genuine addition identified, not rematch | unit | `pytest tests/test_matcher.py::test_genuine_addition -x` | No — Wave 0 |
| DIFF-04 | Genuine removal identified, not matched to unrelated tool | unit | `pytest tests/test_matcher.py::test_genuine_removal -x` | No — Wave 0 |
| DIFF-04 | Threshold > 0.8 rejects low-confidence pair → add + remove | unit | `pytest tests/test_matcher.py::test_threshold_rejection -x` | No — Wave 0 |
| DIFF-04 | MatchResult node count invariant holds for all cases | unit | `pytest tests/test_matcher.py -x` (assertion in helper) | No — Wave 0 |
| DIFF-04 | Empty old or new list — early exit, no Hungarian called | unit | `pytest tests/test_matcher.py::test_empty_inputs -x` | No — Wave 0 |
| DIFF-04 | Cross-type tools never matched (e.g., Filter vs Join) | unit | `pytest tests/test_matcher.py::test_cross_type_isolation -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_matcher.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/fixtures/matching.py` — fixture nodes for matcher tests (ToolIDs 301+)
- [ ] `tests/test_matcher.py` — all 9 test cases above
- [ ] `src/alteryx_diff/matcher/__init__.py` — package stub
- [ ] `src/alteryx_diff/matcher/matcher.py` — match() stub (can raise NotImplementedError)
- [ ] `src/alteryx_diff/matcher/_cost.py` — cost helpers stub
- [ ] Framework install: `uv add scipy` — scipy not currently in pyproject.toml

## Sources

### Primary (HIGH confidence)
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html — API signature, parameters, return values, non-square matrix behavior (scipy v1.17.0)
- https://docs.python.org/3/library/dataclasses.html — frozen=True, kw_only=True, slots=True dataclass pattern
- Existing codebase (`src/alteryx_diff/models/`, `src/alteryx_diff/normalizer/`) — conventions for package structure, module naming, frozen dataclasses, pure functions

### Secondary (MEDIUM confidence)
- https://scipy.org/news/ and https://pypi.org/project/SciPy/ — scipy 1.17.1 is latest stable (2026-02-22), requires Python >=3.11
- WebSearch confirmed scipy 1.13+ supports Python 3.11; rectangular matrices supported since scipy ~0.17+
- WebSearch confirmed numpy 2.4.2 is latest stable (2026-02-01), pulled transitively by scipy

### Tertiary (LOW confidence)
- None — all critical claims verified with official sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — scipy API verified against official docs; version requirements confirmed from PyPI and toolchain docs
- Architecture: HIGH — patterns derived directly from existing codebase conventions + CONTEXT.md locked decisions
- Pitfalls: HIGH — derived from algorithmic properties of `linear_sum_assignment` and project codebase conventions (ruff B905, frozen dataclasses, mypy strict)

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (scipy is stable; pyproject.toml version pinning insulates from patch releases)
