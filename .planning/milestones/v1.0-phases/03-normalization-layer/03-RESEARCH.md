# Phase 3: Normalization Layer - Research

**Researched:** 2026-03-01
**Domain:** Python dict/XML canonicalization, SHA-256 hashing, regex stripping, frozen dataclass extension
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**config_hash content**
- Hash covers the `<Properties>` subtree only — ToolID and tool type are identity fields for the matcher, not config
- All children of `<Properties>` are included in the hash input after C14N + stripping — no tool-type-specific whitelist
- Hash equality is the authoritative equality signal: if two nodes have identical hashes, Phase 5 skips DeepDiff entirely
- Hash stored as SHA-256 hex digest string (64 chars)

**Stripping scope**
- GUID stripping targets known XPath patterns for specific Alteryx-generated fields — no regex over all UUID-shaped values (risk of stripping user-supplied IDs in query configs)
- Timestamp stripping covers ISO 8601 formats only — US-format dates (MM/DD/YYYY) are more likely user-supplied filter expressions and must not be stripped
- TempFile paths replaced with `__TEMPFILE__` placeholder (not empty string, not element removal) — preserves structure for debugging
- All stripping patterns (XPath, timestamp regex, path patterns) live in a single `constants` or `patterns` module — adding new patterns requires one-file change, Phase 3 tests catch regressions

**Normalization API contract**
- Normalizer produces `NormalizedNode` (frozen dataclass) wrapping source `AlteryxNode` plus `config_hash: str` and `position` (carried from source)
- Normalizer produces `NormalizedWorkflowDoc` (frozen dataclass) with `.nodes: List[NormalizedNode]` and `.connections` preserved from the source `WorkflowDoc`
- Entry point: `normalize(workflow_doc: WorkflowDoc) -> NormalizedWorkflowDoc` — pure function, no class, no state
- `NormalizedNode` and `NormalizedWorkflowDoc` defined in `models/` alongside Phase 1 dataclasses — all pipeline data contracts in one place

**Position handling**
- `NormalizedNode.position` carries forward `AlteryxNode.position` (X/Y) unchanged — the normalizer does not transform positions
- Position is always excluded from `config_hash` — two nodes with identical configs but different canvas positions get identical hashes
- `normalize()` takes no `include_positions` parameter in Phase 3 — the flag is a Phase 5 (differ) and Phase 9 (CLI) concern; the normalizer is flag-agnostic

### Claude's Discretion
- Exact XPath expressions for known Alteryx GUID fields (to be derived from fixture inspection)
- C14N canonicalization call sequence (strip → canonicalize → hash, vs canonicalize → strip → hash)
- Internal helper structure within the normalizer module

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NORM-01 | System strips whitespace differences and normalizes XML attribute ordering using C14N canonicalization to eliminate false positives | Canonical dict serialization via `json.dumps(sort_keys=True, separators=(',', ':'))` achieves attribute-order independence on the stored config dict; see Architecture Patterns §Canonical Serialization |
| NORM-02 | System removes non-functional Alteryx-generated metadata (GUIDs, timestamps, TempFile paths) before comparison | XPath/key-based targeted stripping of known fields (TempFile, Engine paths), ISO 8601 timestamp regex, path pattern regex; see Architecture Patterns §Stripping Pipeline |
| NORM-03 | Canvas position (X/Y) is excluded from diff detection by default — stored separately for graph layout use only | `NormalizedNode.position` carries (x, y) from `AlteryxNode`; `config_hash` never includes x/y; see Architecture Patterns §Position Separation |
| NORM-04 | User can opt in to position-based change detection via `--include-positions` flag with clear `--help` documentation | `normalize()` is flag-agnostic; Phase 5 differ receives `NormalizedNode.position` as a separate field and uses it only when `--include-positions` is set; `--help` doc is Phase 9 CLI concern |
</phase_requirements>

## Summary

Phase 3 builds a pure transformation function `normalize(WorkflowDoc) -> NormalizedWorkflowDoc`. The core technical challenge is producing a deterministic, noise-free byte sequence from each tool's `<Properties>` configuration so that SHA-256 produces identical hashes for functionally equivalent tools. Because the Phase 2 parser already converted the `<Properties/Configuration>` XML subtree into a Python dict (using the `@key`/`#text` convention), the normalizer works on that dict — not on raw XML bytes. This means "C14N canonicalization" in the ROADMAP translates concretely to canonical dict serialization: `json.dumps` with `sort_keys=True` and compact separators. This achieves the same attribute-ordering independence that XML C14N achieves, but operates on the existing data model without requiring the parser to be changed.

The stripping pass must run BEFORE canonicalization + hashing. Stripping mutates the dict copy (the source `AlteryxNode` is frozen and must not be modified) by removing or replacing known noise keys: TempFile engine paths (regex on string values matching `Engine_{PID}_{hex}` patterns), ISO 8601 timestamps in known positions, and any dict keys that map to known GUID-generating fields. All patterns live in `src/alteryx_diff/normalizer/patterns.py` as a single-source registry so that adding a new noise field is a one-line change with no normalizer.py edit required.

The key risk flagged in STATE.md — "Alteryx XML format assumptions (TempFile element structure, GUID field names, position XPath) need validation against real .yxmd files" — is real. From inspecting real GitHub-hosted `.yxmd` files, TempFile paths are confirmed at `Node > Properties > Configuration > TempFile` with values like `C:\Users\...\AppData\Local\Temp\Engine_{PID}_{hexhash}\Engine_{PID}_{hexhash}.yxdb`. GUID fields in `<Properties>` are not universally present in simple workflows; fixture tests with injected GUIDs are how this phase validates its stripping logic.

**Primary recommendation:** Work on the existing `AlteryxNode.config` dict directly. Strip noise by walking the dict recursively and replacing known value patterns with sentinels. Canonicalize the stripped dict copy via `json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=False)`. Hash the resulting UTF-8 bytes with `hashlib.sha256().hexdigest()`. No parser changes needed, no XML reconstruction.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `hashlib` | stdlib (Python 3.11+) | SHA-256 hex digest production | stdlib, zero dep, FIPS-safe |
| `json` | stdlib (Python 3.11+) | Canonical dict serialization with `sort_keys=True` | stdlib, deterministic, human-readable for debugging |
| `re` | stdlib (Python 3.11+) | ISO 8601 timestamp pattern matching, TempFile path detection | stdlib, compiled patterns cached at module load |
| `dataclasses` | stdlib (Python 3.11+) | `NormalizedNode`, `NormalizedWorkflowDoc` frozen dataclasses with `slots=True` | Matches Phase 1 conventions; `replace()` unavailable on frozen+slots, use `__init__` |
| `lxml` | >=5.0 (already in pyproject.toml) | Already installed — available if XML re-serialization is ever needed | Already a project dependency |
| `copy` | stdlib | Deep-copy config dict before mutation (source `AlteryxNode` is frozen) | stdlib |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` (NewType, Literal) | stdlib 3.11+ | `Position` tuple type alias, `ConfigHash` already defined | For type annotations on new models |
| `lxml.etree` | >=5.0 | C14N on XML bytes if design pivots to storing raw XML | Only if parser is later changed to carry raw `<Properties>` bytes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `json.dumps(sort_keys=True)` | `lxml.etree.tostring(elem, method='c14n')` | lxml C14N requires XML element objects, but parser stored dicts. Would require dict→XML reconstruction, adding complexity and fragility. json.dumps is simpler and achieves same ordering guarantee. |
| Recursive key walk + sentinel replacement | XPath targeting on raw XML element | XPath would be more precise for targeting nested elements by path, but is only available on XML objects not dicts. Dict walk with path-tracking achieves the same targeted stripping. |
| `json` module | `orjson` or `msgpack` | orjson/msgpack are faster but not stdlib; output format differences require explanation. json stdlib is sufficient for config dicts sized in kilobytes. |

**Installation:**
```bash
# No new dependencies — all stdlib except lxml which is already installed
uv sync  # no changes to pyproject.toml required
```

## Architecture Patterns

### Recommended Project Structure
```
src/alteryx_diff/
├── models/
│   ├── __init__.py          # Add NormalizedNode, NormalizedWorkflowDoc exports
│   ├── workflow.py          # Existing: AlteryxNode, WorkflowDoc, AlteryxConnection
│   ├── types.py             # Existing: ConfigHash, ToolID, AnchorName (Position alias added here)
│   ├── diff.py              # Existing: DiffResult, NodeDiff, EdgeDiff
│   └── normalized.py        # NEW: NormalizedNode, NormalizedWorkflowDoc
├── normalizer/
│   ├── __init__.py          # Exports: normalize()
│   ├── normalizer.py        # Entry point: normalize(workflow_doc) -> NormalizedWorkflowDoc
│   ├── patterns.py          # Single-source registry of all stripping patterns
│   └── _strip.py            # Internal: strip_noise(config_dict) -> dict
tests/
├── fixtures/
│   ├── __init__.py          # Existing XML fixtures; add normalization fixtures
│   └── normalization.py     # NEW: fixture pairs for normalizer contract tests
└── test_normalizer.py       # NEW: normalization contract tests
```

### Pattern 1: Frozen Dataclass for NormalizedNode
**What:** Extend the Phase 1 pattern (frozen=True, kw_only=True, slots=True) to `NormalizedNode` and `NormalizedWorkflowDoc`. These wrap existing model instances rather than inheriting from them (inheritance with slots=True is tricky across module boundaries).
**When to use:** Always — all pipeline data contracts are frozen.

```python
# Source: Phase 1 pattern, verified against Python 3.11 dataclasses docs
# src/alteryx_diff/models/normalized.py

from __future__ import annotations
from dataclasses import dataclass
from alteryx_diff.models.types import ConfigHash, ToolID
from alteryx_diff.models.workflow import AlteryxNode, AlteryxConnection, WorkflowDoc


@dataclass(frozen=True, kw_only=True, slots=True)
class NormalizedNode:
    """An AlteryxNode with its config_hash computed and position separated."""
    source: AlteryxNode          # carry the original for downstream stages
    config_hash: ConfigHash      # SHA-256 hex digest of stripped+canonical config
    position: tuple[float, float]  # (x, y) from source — separate data path


@dataclass(frozen=True, kw_only=True, slots=True)
class NormalizedWorkflowDoc:
    """A WorkflowDoc with all nodes replaced by NormalizedNode instances."""
    source: WorkflowDoc
    nodes: tuple[NormalizedNode, ...]
    connections: tuple[AlteryxConnection, ...]  # preserved unchanged from source
```

**IMPORTANT:** `slots=True` and `frozen=True` together mean you cannot use `dataclasses.replace()` — construct with the full `__init__`. This is the established Phase 1 pattern.

### Pattern 2: Canonical Dict Serialization for Hashing
**What:** Produce a deterministic byte sequence from the config dict. `json.dumps` with `sort_keys=True` recursively sorts dict keys at every nesting level. Compact separators (`(',', ':')`) eliminate optional whitespace.
**When to use:** For computing `config_hash` on the stripped config dict.

```python
# Source: Python stdlib docs, json.dumps sort_keys behavior
# src/alteryx_diff/normalizer/normalizer.py

import hashlib
import json
from typing import Any

def _dict_to_canonical_bytes(config: dict[str, Any]) -> bytes:
    """Convert a config dict to a deterministic canonical byte sequence.

    sort_keys=True ensures attribute-order independence at every nesting level.
    separators=(',', ':') eliminates whitespace differences.
    ensure_ascii=False preserves Unicode as-is (no percent-encoding noise).
    """
    return json.dumps(
        config,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
    ).encode('utf-8')


def _compute_config_hash(stripped_config: dict[str, Any]) -> str:
    """SHA-256 hex digest of canonical config bytes. Returns 64-char lowercase hex."""
    canonical_bytes = _dict_to_canonical_bytes(stripped_config)
    return hashlib.sha256(canonical_bytes).hexdigest()
```

### Pattern 3: Stripping Pipeline with Single-Source Patterns Registry
**What:** Strip noise from a deep-copy of the config dict before canonicalization. All patterns (regex, key names, path patterns) live in `patterns.py`. The strip function walks the dict recursively.
**When to use:** Before hashing. Order: strip → canonicalize → hash.

```python
# src/alteryx_diff/normalizer/patterns.py
"""Single-source registry of all Alteryx noise-stripping patterns.

Adding a new Alteryx-generated metadata pattern requires only editing this file.
All patterns are compiled at import time for performance.
"""
import re

# TempFile path pattern: matches Engine_{PID}_{hexhash} path segments
# Replaces entire string value with __TEMPFILE__ sentinel
# Confirmed from real .yxmd files: C:\...\Engine_3640_96bb13fd...\Engine_1952_94164fc3....yxdb
TEMPFILE_PATH_PATTERN: re.Pattern[str] = re.compile(
    r'(?:C:|/)[^\'"]*Engine_\d+_[0-9a-fA-F]+[^\'"]*',
    re.IGNORECASE,
)
TEMPFILE_SENTINEL: str = "__TEMPFILE__"

# ISO 8601 timestamp pattern: YYYY-MM-DDTHH:MM:SS variants
# Intentionally NOT matching MM/DD/YYYY (user-supplied filter dates)
ISO8601_PATTERN: re.Pattern[str] = re.compile(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?',
)
ISO8601_SENTINEL: str = "__TIMESTAMP__"

# Dict keys whose string values contain Alteryx-generated GUIDs
# These are TARGETED by key name, not by UUID shape, to avoid stripping user values
# Populated from fixture inspection in Phase 3 tests; add here as discovered
GUID_VALUE_KEYS: frozenset[str] = frozenset({
    # Keys known to hold engine-generated GUIDs (XPath leaf names as dict keys)
    # Examples added as discovered from real .yxmd fixture inspection:
    # "@GUID", "CUID", "RuntimeDataGUID"
    # Phase 3 tests with injected GUIDs will validate these
})
GUID_SENTINEL: str = "__GUID__"
```

```python
# src/alteryx_diff/normalizer/_strip.py
"""Internal noise-stripping logic for the normalizer."""
import copy
from typing import Any
from alteryx_diff.normalizer.patterns import (
    TEMPFILE_PATH_PATTERN, TEMPFILE_SENTINEL,
    ISO8601_PATTERN, ISO8601_SENTINEL,
    GUID_VALUE_KEYS, GUID_SENTINEL,
)


def strip_noise(config: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copy of config with all Alteryx noise stripped.

    Does NOT mutate the input (source AlteryxNode is frozen).
    Recursively processes nested dicts and lists.
    """
    return _strip_value(copy.deepcopy(config))  # type: ignore[return-value]


def _strip_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_dict_entry(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_value(item) for item in value]
    if isinstance(value, str):
        return _strip_string(value)
    return value


def _strip_dict_entry(key: str, value: Any) -> Any:
    """Apply key-targeted stripping before general value stripping."""
    if key in GUID_VALUE_KEYS and isinstance(value, str):
        return GUID_SENTINEL
    return _strip_value(value)


def _strip_string(value: str) -> str:
    """Apply TempFile and ISO 8601 replacements to a string value."""
    value = TEMPFILE_PATH_PATTERN.sub(TEMPFILE_SENTINEL, value)
    value = ISO8601_PATTERN.sub(ISO8601_SENTINEL, value)
    return value
```

### Pattern 4: normalize() Entry Point
**What:** Pure function that iterates nodes and applies the strip → canonicalize → hash pipeline per node.
**When to use:** Called by pipeline orchestrator (Phase 6) after parse().

```python
# src/alteryx_diff/normalizer/normalizer.py
from alteryx_diff.models import WorkflowDoc
from alteryx_diff.models.normalized import NormalizedNode, NormalizedWorkflowDoc
from alteryx_diff.models.types import ConfigHash
from alteryx_diff.normalizer._strip import strip_noise


def normalize(workflow_doc: WorkflowDoc) -> NormalizedWorkflowDoc:
    """Pure transformation: WorkflowDoc -> NormalizedWorkflowDoc.

    No I/O, no side effects, no CLI knowledge, no mutable state.
    """
    normalized_nodes = tuple(
        _normalize_node(node) for node in workflow_doc.nodes
    )
    return NormalizedWorkflowDoc(
        source=workflow_doc,
        nodes=normalized_nodes,
        connections=workflow_doc.connections,
    )


def _normalize_node(node: AlteryxNode) -> NormalizedNode:
    stripped = strip_noise(node.config)
    config_hash = ConfigHash(_compute_config_hash(stripped))
    return NormalizedNode(
        source=node,
        config_hash=config_hash,
        position=(node.x, node.y),
    )
```

### Pattern 5: Stripping Call Sequence (Claude's Discretion Decision)
**Recommended sequence:** strip → canonicalize → hash

**Why strip BEFORE canonicalize:**
- Stripping replaces values with sentinels (e.g., `__TEMPFILE__`). These sentinels are plain strings — canonical JSON serialization handles them identically regardless of order.
- If you canonicalize first (dict → canonical JSON bytes), you still need to apply regex replacements on the bytes/string, which introduces encoding assumptions.
- Stripping on the dict is cleaner: key-targeted logic works on Python structure, not string patterns applied to JSON output.
- The sequence `strip(config) → json.dumps(sort_keys=True) → sha256()` is simpler, more testable in isolation, and matches how Phase 3 plans are specified.

### Anti-Patterns to Avoid
- **Mutating `AlteryxNode.config` directly:** It's a dict on a frozen dataclass; mutation at the dict level IS possible (frozen prevents attribute reassignment, not dict content mutation). Always use `copy.deepcopy()` before stripping.
- **UUID regex over all string values:** Risk of stripping user-supplied IDs in formula expressions or query strings. Only strip by known key names or confirmed path patterns.
- **Stripping `MM/DD/YYYY` dates:** These are US-format filter expressions, not Alteryx-generated timestamps. The ISO 8601 pattern (`YYYY-MM-DDTHH:MM:SS`) is the correct scope.
- **Removing TempFile elements instead of replacing with sentinel:** Removal changes the dict structure, so two versions of the same workflow with different TempFile presence would hash differently. The `__TEMPFILE__` sentinel preserves structure.
- **Importing `NormalizedNode` from `models.workflow`:** Add it to `models/normalized.py` and export from `models/__init__.py`. Do NOT define it outside `models/`.
- **Putting strip patterns inline in normalizer.py:** A single `patterns.py` is the one-file-change requirement. Inline patterns scatter the registry and make regression testing harder.
- **Using `dataclasses.replace()` on frozen+slots instances:** Not available when `slots=True`. Construct new instances with the full `NormalizedNode(source=..., config_hash=..., position=...)` call.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deterministic dict serialization | Custom recursive key-sorter | `json.dumps(sort_keys=True, separators=(',', ':'))` | sort_keys recursively sorts nested dicts; stdlib handles all JSON-compatible types correctly |
| SHA-256 hex digest | Custom byte hashing | `hashlib.sha256(bytes).hexdigest()` | FIPS-safe, constant-time comparison, 64-char hex output matches `ConfigHash` type doc |
| Deep copy before mutation | Custom dict cloner | `copy.deepcopy(config)` | Handles nested dicts, lists, and any JSON-compatible types recursively |
| ISO 8601 regex | Hand-crafted date parser | Compiled `re.Pattern` with verified RFC 3339 pattern | Regex is sufficient for text replacement; full datetime parsing is over-engineering |
| TempFile path detection | Filesystem path analysis | Regex pattern matching `Engine_{PID}_{hex}` path segment | The path structure is fixed: Engine_\d+_[0-9a-fA-F]+ is the distinctive marker |

**Key insight:** The complexity in this domain is in getting the stripping patterns right (requires real fixture testing), not in the code structure. The code is simple; the validation fixtures are where the effort goes.

## Common Pitfalls

### Pitfall 1: Mutating Frozen Dataclass dict Content
**What goes wrong:** `AlteryxNode` is frozen (`frozen=True`), which prevents field reassignment. But `config: dict[str, Any]` is a mutable dict — you CAN call `node.config['key'] = 'value'` without a FrozenInstanceError. Tests pass, but you've silently corrupted the source data model.
**Why it happens:** Python's frozen dataclass only prevents `node.config = new_dict`, not `node.config['key'] = value`.
**How to avoid:** Always `copy.deepcopy(node.config)` before any mutation in `strip_noise()`. Add a test that asserts `node.config` is unchanged after `normalize()`.
**Warning signs:** Tests that verify post-normalize state of `node.config` values pass when they should (the original is clean), but only because they're checking after deepcopy is applied.

### Pitfall 2: Incorrect Stripping Scope — Over-Stripping User Values
**What goes wrong:** Applying UUID/GUID regex over all string values strips user-supplied GUIDs in SQL queries, formula fields referencing connection IDs, or metadata that happens to look like a UUID.
**Why it happens:** UUID is a common data pattern in enterprise data, not just Alteryx metadata.
**How to avoid:** GUID stripping must be KEY-TARGETED. Only strip values at known dict key names (`@GUID`, `CUID`, etc.). Build these keys into `GUID_VALUE_KEYS` from fixture inspection, not from regex heuristics.
**Warning signs:** A test fixture with a user-supplied GUID value (e.g., a filter expression `[ID] = '{550e8400-e29b-41d4-a716-446655440000}'`) produces a different hash after stripping than it should.

### Pitfall 3: json.dumps Non-Determinism on Non-Standard Types
**What goes wrong:** `json.dumps` raises `TypeError` if the config dict contains types it cannot serialize (e.g., `None` is fine, but custom objects, `bytes`, or numpy types would fail). The parser's `_element_to_dict` only produces `str`, `dict`, `list`, and no other types — but if that ever changes, the normalizer breaks silently with an exception.
**Why it happens:** `json.dumps` has no fallback for non-JSON-native types.
**How to avoid:** The normalizer should pass `default=str` as a safety net, OR add a type assertion in the test that confirms `_dict_to_canonical_bytes` never raises on all fixture configs.
**Warning signs:** `TypeError: Object of type X is not JSON serializable` in the normalizer, especially after parser changes.

### Pitfall 4: Position Included in Hash Path
**What goes wrong:** `NormalizedNode.position` and `NormalizedNode.config_hash` are supposed to be separate data paths. If the position (x, y) is accidentally included in the dict passed to `_compute_config_hash`, canvas nudging causes false positives.
**Why it happens:** `AlteryxNode.x` and `AlteryxNode.y` are on the node, not in `node.config` — but if someone adds position to the config dict before hashing, the separation breaks.
**How to avoid:** The hash input must be `node.config` (stripped), never `{'x': node.x, 'y': node.y, **node.config}`. Add a fixture test that computes hashes for two nodes differing only in position and asserts they are equal.
**Warning signs:** Position-drift tests fail — the same workflow saved twice with a nudged tool shows a config diff.

### Pitfall 5: TempFile Sentinel Does Not Survive Round-Trip
**What goes wrong:** The TempFile regex replaces the path with `__TEMPFILE__`, but the replacement is applied to the outer path string, not just the engine segment. If the path has no `Engine_` marker (e.g., a clean workflow with no cached BrowseV2), the regex produces no replacement — correct behavior. But if the same workflow is compared against a version where TempFile is absent (element not present at all), the config dicts have different structures and produce different hashes.
**Why it happens:** TempFile presence depends on whether the workflow has been run. An unrun workflow has no TempFile key; a run workflow does.
**How to avoid:** The stripping pass should normalize TempFile to `__TEMPFILE__` when present. Two nodes — one with TempFile, one without — still differ. This is correct: one has been run, one hasn't. The sentinel replacement only equalizes runs with different temporary paths, not runs vs. no-runs.
**Warning signs:** Fixtures need both "unrun" and "run" variants to verify the correct behavior.

### Pitfall 6: lxml C14N Method Applied to Dict (API Confusion)
**What goes wrong:** The ROADMAP mention of `lxml.etree.canonicalize()` leads to an implementation that calls `etree.fromstring(json.dumps(config))` (invalid XML) or reconstructs XML from the dict before applying C14N, creating a lossy round-trip.
**Why it happens:** "C14N" is used in the ROADMAP conceptually to mean "attribute-order-independent canonical form." But the parser already converted XML attributes to `@key` dict keys. True lxml C14N operates on XML element objects, not dicts.
**How to avoid:** Use `json.dumps(sort_keys=True)` for canonical dict form. Only use `lxml.etree.canonicalize()` if the normalizer is given raw XML bytes (which would require a parser change).
**Warning signs:** Attempts to call `etree.canonicalize()` on a Python dict result in `TypeError` or require serialization to a JSON-as-XML hybrid that is never parseable again.

## Code Examples

### Computing config_hash for a Node
```python
# Verified pattern: stdlib only, no new dependencies
import hashlib
import json
import copy
from typing import Any

def compute_node_config_hash(config: dict[str, Any]) -> str:
    """Strip noise, canonicalize, and SHA-256 hash a node's config dict.

    Returns a 64-character lowercase hexadecimal string (SHA-256 hex digest).
    """
    stripped = strip_noise(copy.deepcopy(config))  # never mutate original
    canonical = json.dumps(
        stripped,
        sort_keys=True,      # attribute-order independence at every nesting level
        separators=(',', ':'),  # no whitespace
        ensure_ascii=False,  # no encoding noise from Unicode escapes
    ).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()
```

### TempFile Path Regex Pattern (Confirmed from Real .yxmd Files)
```python
# Confirmed from CSV Reader.yxmd and other GitHub-hosted workflows:
# C:\Users\Alteryx\AppData\Local\Temp\2\Engine_3640_96bb13fd499947b58eac9db8a9db378a\
#   Engine_1952_94164fc329fc43f9b6f37832878b4181.yxdb
# Pattern: Engine_{integer_pid}_{hex32+}
import re

TEMPFILE_PATH_PATTERN = re.compile(
    r'(?:[A-Za-z]:\\|/).*?Engine_\d+_[0-9a-fA-F]+[^\'"]*',
    re.IGNORECASE,
)
# Note: This regex is conservative — targets Engine_ path segments only,
# not all Windows paths. Confirmed safe against user-supplied file paths
# that don't contain the Engine_ marker.
```

### ISO 8601 Timestamp Regex (NOT MM/DD/YYYY)
```python
# Covers: 2024-03-15T14:30:00, 2024-03-15T14:30:00Z, 2024-03-15T14:30:00+05:30
# Does NOT match: 03/15/2024 (user filter dates)
import re

ISO8601_PATTERN = re.compile(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?',
)
```

### Fixture Pair Structure for Normalizer Tests
```python
# tests/fixtures/normalization.py — Verified fixture pattern from Phase 2
# Each pair: (config_a, config_b) where normalize(config_a) == normalize(config_b)

# Pair 1: attribute reordering (tests NORM-01)
CONFIG_ATTR_ORDER_A = {"File": {"@type": "csv", "@RecordLimit": "0", "#text": "data.csv"}}
CONFIG_ATTR_ORDER_B = {"File": {"@RecordLimit": "0", "#text": "data.csv", "@type": "csv"}}
# Both should produce identical config_hash

# Pair 2: TempFile presence (tests NORM-02)
CONFIG_WITH_TEMPFILE = {
    "TempFile": "C:\\Users\\user\\AppData\\Local\\Temp\\Engine_1234_abc123def456.yxdb"
}
CONFIG_WITHOUT_NOISE = {
    "TempFile": "__TEMPFILE__"  # pre-stripped sentinel — same hash expected
}

# Pair 3: position drift (tests NORM-03)
# Construct two AlteryxNode instances with identical config but different x/y
# Their NormalizedNode.config_hash must be equal; NormalizedNode.position differs
```

### lxml C14N API (Available but NOT Used on Dicts)
```python
# Source: lxml docs, verified: etree.tostring(elem, method='c14n') returns bytes
# method='c14n'  → W3C Canonical XML 1.0 (exclusive=False by default)
# method='c14n2' → W3C Canonical XML 2.0 (strip_text=True removes insignificant whitespace)
# Only available when you have an lxml _Element object, NOT a Python dict

from lxml import etree

# For reference IF the parser ever stores raw XML elements:
def xml_element_to_c14n_bytes(elem: etree._Element) -> bytes:
    return etree.tostring(elem, method='c14n', with_comments=False)
    # Returns bytes, UTF-8 encoded, attributes alphabetically sorted
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw string XML diff (`diff workflow_a.yxmd workflow_b.yxmd`) | Structured hash comparison with noise stripping | This project | Eliminates GUID/timestamp/position false positives |
| XML C14N on element objects | Canonical dict serialization (`json.dumps(sort_keys=True)`) | Design constraint from Phase 2 dict storage | Same ordering guarantee, no parser change required |
| lxml C14N 1.0 (`method='c14n'`) | lxml C14N 2.0 (`method='c14n2'`, `strip_text=True`) available since lxml 4.6 | lxml 4.6 (2020) | C14N 2.0 adds `strip_text` parameter; relevant only if XML element hashing path is chosen |

**Deprecated/outdated:**
- **PyXML c14n.py**: Ancient pre-lxml Python XML library. Not used — lxml >=5.0 is already the project's XML library.
- **ElementTree's xml.etree**: Standard library ElementTree has no C14N support. lxml is already the parser choice (and C14N is moot anyway since we work on dicts).

## Open Questions

1. **Which Alteryx tool types generate GUID fields in their `<Properties>` subtree?**
   - What we know: TempFile paths are confirmed in BrowseV2. The CONTEXT.md mentions GUIDs as a stripping target. Real .yxmd files from GitHub did not show explicit `@GUID` attributes in simple workflows.
   - What's unclear: Whether more complex tools (e.g., Join, Spatial, Reporting) embed GUIDs in their `<Properties/Configuration>` elements.
   - Recommendation: Phase 3 Plan 02 (GUID/timestamp stripping) should create fixtures with MANUALLY INJECTED GUIDs at likely key positions (`@GUID`, `CUID`, `RuntimeData`) and test stripping. Start with `GUID_VALUE_KEYS = frozenset()` (empty), add keys as found via fixture inspection. The test validates that identical workflows with/without GUIDs produce the same hash — if no GUIDs found in real files, this is still architecturally correct.

2. **Does `json.dumps(sort_keys=True)` handle list-of-dicts ordering correctly?**
   - What we know: `sort_keys=True` sorts dict keys recursively, including dicts inside lists. But list ORDER is preserved — if the parser produces `[{"@name": "b"}, {"@name": "a"}]` for one run and `[{"@name": "a"}, {"@name": "b"}]` for another, the hashes differ.
   - What's unclear: Whether Alteryx XML attribute lists (e.g., `<Field>` elements under `<Fields>`) appear in consistent order.
   - Recommendation: The parser produces list order from XML document order (lxml preserves document order). If Alteryx preserves element order in repeated saves, this is not a problem. Fixture tests should validate: take a workflow, parse it twice, verify identical hashes. If element order varies, a list-sorting step by a canonical key (e.g., `@name`) would be needed — but this is NOT in scope unless tests reveal the problem.

3. **Should `NormalizedNode.position` be a `tuple[float, float]` or a named tuple/dataclass?**
   - What we know: Phase 5 (differ) needs to compare positions when `--include-positions` is active. `tuple[float, float]` is the simplest representation and compatible with frozen+slots dataclasses.
   - What's unclear: Whether named fields (`Position.x`, `Position.y`) would improve Phase 5 code clarity.
   - Recommendation: Use `tuple[float, float]` for Phase 3 (matches simplicity principle). If Phase 5 needs named fields, define a `Position` NamedTuple at that point. NamedTuples are not frozen dataclasses and mixing the two requires care.

## Sources

### Primary (HIGH confidence)
- Python stdlib docs (docs.python.org) — `hashlib.sha256()`, `json.dumps(sort_keys=True)`, `copy.deepcopy()`, `re.compile()`, `dataclasses` (`frozen=True`, `kw_only=True`, `slots=True`)
- lxml.de/api.html — `etree.canonicalize()`, `etree.tostring(method='c14n'/'c14n2')`, `C14NWriterTarget` with `strip_text` parameter
- Phase 1 and Phase 2 source code (`models/workflow.py`, `parser.py`, `models/types.py`) — direct inspection of existing data model and parser conventions
- Real `.yxmd` files inspected: `jdunkerley/AlteryxRecordID/Example Workflow.yxmd`, `jdunkerley/Alteryx/CSV Reader.yxmd`, `Hiblet/Alteryx_CRS_Demo/CRS_Validate.yxmd`

### Secondary (MEDIUM confidence)
- Alteryx help docs (help.alteryx.com) — Tools that generate temporary files: BrowseV2, Sort, Join, Summarize, and others
- lxml test suite (`github.com/lxml/lxml/blob/master/src/lxml/tests/test_etree.py`) — Confirmed `etree.tostring(elem, method='c14n', exclusive=True, inclusive_ns_prefixes=['y'])` pattern
- death.andgravity.com/stable-hashing — Canonical dict hashing via `json.dumps(sort_keys=True)`

### Tertiary (LOW confidence)
- Alteryx community forum discussions about TempFile paths and version control — confirmed path structure but not official docs
- STATE.md blocker note: "Alteryx XML format assumptions (TempFile element structure, GUID field names, position XPath) need validation against real .yxmd files in Phase 3 fixture tests" — this LOW confidence signal is the correct risk characterization; Phase 3 fixture tests are the validation mechanism

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib except lxml which is already a project dependency; API verified
- Architecture (canonical dict serialization): HIGH — json.dumps sort_keys behavior is well-documented stdlib; directly applicable to existing dict-based data model
- Architecture (stripping patterns): MEDIUM — TempFile path structure confirmed from real files; GUID key names require fixture validation in Phase 3 tests
- Pitfalls: HIGH — derived from direct code inspection of frozen dataclass constraints, json.dumps behavior, and parser storage format

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stdlib patterns are stable; lxml >=5.0 already pinned; only Alteryx-specific patterns may need updates as new tool types are discovered)
