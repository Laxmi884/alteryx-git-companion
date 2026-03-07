# Phase 2: XML Parser and Validation - Research

**Researched:** 2026-03-01
**Domain:** Python XML parsing with lxml, Alteryx .yxmd file format, typed exception design
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Config dict extraction**
- Nested dict mirroring XML hierarchy — not flat XPath-style keys, not raw XML string
- Preserves XML structure so Phase 5 (differ) can use DeepDiff for meaningful field-level paths (e.g. `root['Configuration']['Expression']`)
- XML attribute encoding (e.g. `@field`) and repeated element handling (e.g. `<Field/>` lists) are Claude's discretion — choose the convention that best serves Phase 3 normalizer and Phase 5 differ

**Exception hierarchy**
- Subclass hierarchy rooted at a `ParseError` base class
- Subclasses: `MalformedXMLError`, `MissingFileError`, `UnreadableFileError`
- Each exception carries: `filepath: str` + `message: str` (plain English) + `__cause__` chaining to preserve the original lxml or OS exception for debuggability
- All exception classes live in `src/alteryx_diff/exceptions.py` — importable by any stage without circular dependencies

**Dual-file fail behavior**
- Fail immediately on first error — parse `path_a` first; if it fails, raise without attempting `path_b`
- Explicit file existence check before opening: `if not path.exists(): raise MissingFileError(...)` — plain English error identifying the file path
- No partial state, no multi-error collection

**Test fixtures**
- Fixture files live in `tests/fixtures/` directory
- Synthetic XML strings only for now — no real `.yxmd` files available yet; build minimal but structurally valid XML in-code for the happy path and all edge cases
- If real `.yxmd` files are added later they go in `tests/fixtures/` as golden fixtures

### Claude's Discretion

- Exact XML attribute encoding convention in the nested dict (e.g. `@attr_name` keys vs. dedicated sub-dict)
- Handling of repeated same-name XML child elements (e.g. `<Field/>` lists → list value in dict)
- Internal parser module structure (single `parser.py` vs. sub-package)
- Public function signature: `parse(path_a, path_b)` is locked; internal helpers are Claude's choice

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PARSE-01 | User can provide two `.yxmd` files as CLI arguments and the system loads both | `parse(path_a, path_b)` public function using `pathlib.Path` + `etree.parse()`; Phase 9 (CLI) will call this |
| PARSE-02 | System validates XML structure on load and rejects malformed files before any processing begins | `etree.XMLParser(recover=False)` raises `XMLSyntaxError` on any malformation; wrap in `MalformedXMLError` |
| PARSE-03 | System provides descriptive error messages for malformed, corrupted, or missing files | Exception hierarchy with `filepath` + `message` + `__cause__`; pre-check with `pathlib.Path.exists()` / `Path.is_file()` before lxml touches the file |
</phase_requirements>

---

## Summary

Phase 2 builds a pure parsing layer: given two file paths, return two `WorkflowDoc` instances populated with `AlteryxNode` and `AlteryxConnection` objects — or raise a typed exception. All Phase 1 data models are already built and tested. lxml 6.0.2 is already installed (locked in uv.lock). No new dependencies are needed.

The Alteryx `.yxmd` XML format is well-understood from real-file inspection. The root element is `<AlteryxDocument>`, tools live under `<Nodes><Node ToolID="N">`, positions in `<GuiSettings><Position x="N" y="N"/>`, configurations in `<Properties><Configuration>`, and connections in `<Connections><Connection>` with `<Origin>` / `<Destination>` child elements. All attributes are strings in the XML; ToolID must be cast to `int` for the `ToolID` NewType.

The exception design is fully specified in CONTEXT.md: three subclasses of `ParseError` in `exceptions.py`, each carrying `filepath`, `message`, and `__cause__`. The key implementation insight is that lxml raises `XMLSyntaxError` for all parse-time failures (malformed XML, empty file, binary content) and `OSError` for I/O failures (directory path, read error). A pre-flight `pathlib.Path` check intercepts the "file does not exist" case before lxml ever runs, producing a `MissingFileError` with a plain-English message.

**Primary recommendation:** Use `etree.parse(str(path))` with `XMLParser(recover=False)` as the parse engine. Pre-check file existence and readability with pathlib before calling lxml. Build a recursive `_element_to_dict` helper using `@attr` key convention for XML attributes, `#text` for element text content, and automatic list promotion for repeated same-tag children.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lxml | 6.0.2 (locked) | XML parsing, `etree.parse()`, `XMLSyntaxError` | Already in pyproject.toml; wraps libxml2 — fastest Python XML library, robust error reporting with line/column/filename in exception |
| pathlib (stdlib) | Python 3.11+ | File existence checks, path normalization | `Path.exists()`, `Path.is_file()`, `Path.stat()` give clean pre-flight checks without shell calls |
| dataclasses (stdlib) | Python 3.11+ | `AlteryxNode`, `AlteryxConnection`, `WorkflowDoc` | Already built in Phase 1 — immutable, typed, no ORM overhead |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing (stdlib) | Python 3.11+ | `Any` for `dict[str, Any]` config field, type annotations | Used in all typed code; mypy --strict enforced |
| pytest | >=8.0 (locked) | Test framework | All parser tests; in-memory XML strings as fixtures |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `lxml.etree` | `xml.etree.ElementTree` (stdlib) | stdlib ET doesn't raise typed exceptions with line/column/filename info; `lxml` error objects are richer and already installed |
| `lxml.etree` | `xml.etree.ElementTree` with `expat` | Same as above — no benefit over lxml, and lxml is already a project dependency |
| Nested dict for config | `lxml.objectify` | objectify auto-maps XML to Python objects but uses magic `__getattr__` that mypy can't type; nested dict is fully typed as `dict[str, Any]` |

**Installation:**
```bash
# Already installed — no action needed
# lxml = "6.0.2" in uv.lock; >=5.0 in pyproject.toml
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/alteryx_diff/
├── exceptions.py        # ParseError, MalformedXMLError, MissingFileError, UnreadableFileError
├── parser.py            # parse(path_a, path_b) -> tuple[WorkflowDoc, WorkflowDoc]
├── models/              # Phase 1 — already complete
│   ├── __init__.py
│   ├── workflow.py      # WorkflowDoc, AlteryxNode, AlteryxConnection
│   ├── types.py         # ToolID, ConfigHash, AnchorName
│   └── diff.py          # DiffResult, NodeDiff, EdgeDiff
└── __init__.py

tests/
├── fixtures/            # Synthetic .yxmd XML strings (in-code) and future golden files
├── test_import.py       # Phase 1 smoke test
├── test_models.py       # Phase 1 model tests
└── test_parser.py       # Phase 2 parser tests (new)
```

### Pattern 1: Pre-Flight + Parse + Convert

**What:** Three-stage function for each file: (1) pre-flight existence/readability check, (2) lxml parse with strict parser, (3) tree-to-model conversion.
**When to use:** Every call to the internal `_parse_one(path)` helper.

```python
# Source: verified against lxml 6.0.2 behavior (tested in this session)
import pathlib
from lxml import etree
from alteryx_diff.exceptions import MalformedXMLError, MissingFileError, UnreadableFileError

def _parse_one(path: pathlib.Path) -> WorkflowDoc:
    # Stage 1: pre-flight
    if not path.exists():
        raise MissingFileError(
            filepath=str(path),
            message=f"File not found: {path}",
        )
    if not path.is_file():
        raise UnreadableFileError(
            filepath=str(path),
            message=f"Path is not a regular file: {path}",
        )

    # Stage 2: parse
    parser = etree.XMLParser(recover=False)
    try:
        tree = etree.parse(str(path), parser)
    except etree.XMLSyntaxError as exc:
        raise MalformedXMLError(
            filepath=str(path),
            message=f"Malformed XML in {path.name}: {exc}",
        ) from exc
    except OSError as exc:
        raise UnreadableFileError(
            filepath=str(path),
            message=f"Cannot read {path}: {exc}",
        ) from exc

    # Stage 3: convert
    return _tree_to_workflow(tree, filepath=str(path))
```

### Pattern 2: Recursive Element-to-Dict

**What:** Converts any lxml `_Element` subtree into a `dict[str, Any]` with `@attr` convention for attributes, `#text` for text content, and automatic list promotion for repeated same-tag children.
**When to use:** For extracting `<Configuration>` content into `AlteryxNode.config`.

```python
# Source: verified by running against real .yxmd-shaped XML in this session
from typing import Any
from lxml.etree import _Element

def _element_to_dict(elem: _Element) -> dict[str, Any]:
    result: dict[str, Any] = {}
    # XML attributes become @key entries
    for k, v in elem.attrib.items():
        result[f"@{k}"] = v
    # Text content (non-whitespace only)
    if elem.text and elem.text.strip():
        result["#text"] = elem.text.strip()
    # Children — repeated same-tag siblings promoted to list
    children_by_tag: dict[str, Any] = {}
    for child in elem:
        child_dict = _element_to_dict(child)
        tag = child.tag
        if tag in children_by_tag:
            existing = children_by_tag[tag]
            if isinstance(existing, list):
                existing.append(child_dict)
            else:
                children_by_tag[tag] = [existing, child_dict]
        else:
            children_by_tag[tag] = child_dict
    result.update(children_by_tag)
    return result
```

**Example output** (from `<Configuration><Fields><Field name="id"/><Field name="val"/></Fields></Configuration>`):
```python
{
    "Fields": {
        "Field": [
            {"@name": "id"},
            {"@name": "val"},
        ]
    }
}
```

This convention:
- Gives Phase 3 normalizer predictable paths like `config["Fields"]["Field"]`
- Gives Phase 5 differ DeepDiff-compatible paths like `root['Configuration']['Fields']['Field'][0]['@name']`
- Avoids magic — fully typed as `dict[str, Any]`

### Pattern 3: Alteryx XML XPath Access

**What:** Direct element lookup paths for the three data regions of a `.yxmd` file.
**When to use:** Inside `_tree_to_workflow`.

```python
# Source: verified against real .yxmd file (kartik-chandna/Data-cleanup on GitHub) + lxml 6.0.2
root = tree.getroot()
# Nodes: root > Nodes > Node[ToolID="N"]
for node_elem in root.findall("Nodes/Node"):
    tool_id = ToolID(int(node_elem.get("ToolID")))
    gui = node_elem.find("GuiSettings")
    plugin = gui.get("Plugin") if gui is not None else ""
    pos = gui.find("Position") if gui is not None else None
    x = float(pos.get("x", "0")) if pos is not None else 0.0
    y = float(pos.get("y", "0")) if pos is not None else 0.0
    config_elem = node_elem.find("Properties/Configuration")
    config = _element_to_dict(config_elem) if config_elem is not None else {}
    # ...

# Connections: root > Connections > Connection > Origin + Destination
for conn_elem in root.findall("Connections/Connection"):
    origin = conn_elem.find("Origin")
    dest = conn_elem.find("Destination")
    src_tool = ToolID(int(origin.get("ToolID")))
    src_anchor = AnchorName(origin.get("Connection", "Output"))
    dst_tool = ToolID(int(dest.get("ToolID")))
    dst_anchor = AnchorName(dest.get("Connection", "Input"))
```

### Pattern 4: Exception Class Design

**What:** Minimal typed exceptions in `exceptions.py` — importable without circular deps.
**When to use:** All exception classes live here; parser, CLI, and tests all import from this single module.

```python
# Source: CONTEXT.md locked decision
class ParseError(Exception):
    """Base class for all parser errors."""
    filepath: str
    message: str

    def __init__(self, *, filepath: str, message: str) -> None:
        super().__init__(message)
        self.filepath = filepath
        self.message = message

class MalformedXMLError(ParseError):
    """Raised when lxml cannot parse the XML document."""

class MissingFileError(ParseError):
    """Raised when the file path does not exist."""

class UnreadableFileError(ParseError):
    """Raised when the file exists but cannot be read (permissions, binary, directory)."""
```

### Anti-Patterns to Avoid

- **`recover=True` on XMLParser:** lxml silently skips broken XML and returns a partial tree — parse-time errors become silent data loss. Always use `recover=False` (the default).
- **Calling `etree.parse()` without pre-flight:** A missing file raises `OSError` from lxml, not a `MissingFileError` with a plain-English message. Pre-flight with pathlib first.
- **Storing `lxml.etree._Element` objects in `AlteryxNode.config`:** Phase 1 explicitly defined `config: dict[str, Any]`. Raw elements are not picklable, not diffable, not mypy-typed. Convert fully to dict in the parser.
- **`sys.exit()` or `print()` in parser code:** CONTEXT.md explicitly forbids these. The parser must be importable as a library. All error signaling is via exceptions.
- **Single-file parsing with shared mutable state:** Each call to `_parse_one()` must be independent — no module-level parser instance that accumulates errors across calls.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML parsing | Custom regex or string splitting | `lxml.etree.parse()` | XML is not line-oriented; regex breaks on multiline values, namespaces, CDATA. lxml handles all edge cases. |
| Malformed-XML detection | `try: open(); check for '<'` | `etree.XMLParser(recover=False)` + catch `XMLSyntaxError` | The parser itself validates; hand-rolling XML validation misses encoding errors, BOM issues, unclosed tags, entity errors. |
| File permission detection | `os.access(path, os.R_OK)` | `try: etree.parse() except OSError` (after pathlib pre-flight) | `os.access()` has TOCTOU race conditions; catching the actual `OSError` is authoritative. |
| Element-to-dict | `lxml.objectify` | Hand-rolled `_element_to_dict` | objectify uses magic `__getattr__`; not typed, hard to test, mypy can't follow it. Our 20-line helper is fully typed and testable. |

**Key insight:** lxml already handles all the XML complexity. The parser module's job is to map lxml's tree output to the Phase 1 data models, and to translate lxml's native exceptions into the project's typed exception hierarchy.

---

## Common Pitfalls

### Pitfall 1: Missing `Connections` or `Nodes` element

**What goes wrong:** Some minimal `.yxmd` files (e.g., empty workflows) may have no `<Connections>` element at all. `root.findall("Connections/Connection")` returns an empty list safely, but `root.find("Connections")` returns `None`, and iterating `None` raises `TypeError`.
**Why it happens:** `findall()` on a missing parent returns `[]` silently, but `find()` returns `None`.
**How to avoid:** Use `root.findall("Connections/Connection")` directly (handles missing parent) or guard with `if conns := root.find("Connections")`.
**Warning signs:** `TypeError: 'NoneType' object is not iterable` in tests with minimal XML fixtures.

### Pitfall 2: ToolID and Position values are strings in XML

**What goes wrong:** `node_elem.get("ToolID")` returns `"1"` (string), not `1` (int). Passing a string to `ToolID(...)` satisfies the NewType at runtime (NewType is transparent at runtime) but fails `mypy --strict` type checking. Similarly, Position `x`/`y` attributes are strings and must be cast to `float`.
**Why it happens:** XML attributes are always strings. lxml makes no type coercions.
**How to avoid:** `ToolID(int(node_elem.get("ToolID")))` and `float(pos.get("x", "0"))`. Add mypy and tests to verify.
**Warning signs:** `mypy: error: Argument 1 to "ToolID" has incompatible type "str"; expected "int"`

### Pitfall 3: `None` from `.find()` on optional elements

**What goes wrong:** `.find("GuiSettings")` returns `None` if the element is absent. Chaining `.get("Plugin")` on `None` raises `AttributeError`.
**Why it happens:** `find()` returns `None` for missing elements — it does not raise.
**How to avoid:** Guard every `.find()` result: `if gui is not None`. For the parser, treat missing GuiSettings as a soft error (log and use defaults), or raise `MalformedXMLError` if it is required. Given phase scope, raise for missing `GuiSettings` — it is required for every tool node.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'get'` in tests.

### Pitfall 4: `etree.parse()` receives a `pathlib.Path`, not a `str`

**What goes wrong:** In lxml 6.x, `etree.parse(pathlib.Path(...))` may work, but the `filename` attribute on the caught `XMLSyntaxError` will be the `repr` of the Path object, not the plain string path.
**Why it happens:** lxml's C backend receives the path as an object; string conversion happens inside libxml2.
**How to avoid:** Always pass `str(path)` to `etree.parse()`. Verified: `etree.parse(str(path))` gives clean filename in exceptions.
**Warning signs:** Exception messages showing `PosixPath('...')` instead of the bare path string.

### Pitfall 5: Empty file raises XMLSyntaxError, not a special case

**What goes wrong:** An empty `.yxmd` file (0 bytes) raises `XMLSyntaxError: Document is empty`. This is correctly caught by the `MalformedXMLError` path — but test authors may be surprised it is not a separate exception class.
**Why it happens:** lxml treats an empty file as malformed XML, not a file I/O error.
**How to avoid:** No special-casing needed. The `MalformedXMLError` wrapper with the lxml message `"Document is empty"` is sufficiently descriptive.
**Warning signs:** Test expecting a different exception type for the empty-file case.

---

## Code Examples

Verified patterns from lxml 6.0.2 (tested in this session):

### Parsing a File with Strict Error Handling

```python
# Source: lxml 6.0.2 verified in session, https://lxml.de/parsing.html
import pathlib
from lxml import etree

path = pathlib.Path("workflow.yxmd")
parser = etree.XMLParser(recover=False)  # recover=False is default; explicit for clarity

# Pre-flight
if not path.exists():
    raise MissingFileError(filepath=str(path), message=f"File not found: {path}")
if not path.is_file():
    raise UnreadableFileError(filepath=str(path), message=f"Not a regular file: {path}")

# Parse
try:
    tree = etree.parse(str(path), parser)  # str() — NOT pathlib.Path directly
except etree.XMLSyntaxError as exc:
    raise MalformedXMLError(
        filepath=str(path),
        message=f"Malformed XML in {path.name}: {exc}",
    ) from exc
except OSError as exc:
    raise UnreadableFileError(
        filepath=str(path),
        message=f"Cannot read {path}: {exc}",
    ) from exc

root = tree.getroot()  # Returns the root _Element
```

### Accessing .yxmd Structure

```python
# Source: verified against real .yxmd file (GitHub: kartik-chandna/Data-cleanup)
# Structure: AlteryxDocument > Nodes > Node[ToolID] > GuiSettings > Position
#                            > Connections > Connection > Origin + Destination

root = tree.getroot()
assert root.tag == "AlteryxDocument", f"Unexpected root: {root.tag}"

nodes = []
for node_elem in root.findall("Nodes/Node"):
    tool_id = ToolID(int(node_elem.get("ToolID")))
    plugin = ""
    x, y = 0.0, 0.0
    gui = node_elem.find("GuiSettings")
    if gui is not None:
        plugin = gui.get("Plugin", "")
        pos = gui.find("Position")
        if pos is not None:
            x = float(pos.get("x", "0"))
            y = float(pos.get("y", "0"))
    config_elem = node_elem.find("Properties/Configuration")
    config = _element_to_dict(config_elem) if config_elem is not None else {}
    nodes.append(AlteryxNode(tool_id=tool_id, tool_type=plugin, x=x, y=y, config=config))

connections = []
for conn_elem in root.findall("Connections/Connection"):
    origin = conn_elem.find("Origin")
    dest = conn_elem.find("Destination")
    if origin is None or dest is None:
        continue  # skip malformed connection element
    connections.append(AlteryxConnection(
        src_tool=ToolID(int(origin.get("ToolID"))),
        src_anchor=AnchorName(origin.get("Connection", "Output")),
        dst_tool=ToolID(int(dest.get("ToolID"))),
        dst_anchor=AnchorName(dest.get("Connection", "Input")),
    ))
```

### Exception Class Structure

```python
# Source: CONTEXT.md locked decision + verified Python __cause__ chaining behavior
# File: src/alteryx_diff/exceptions.py

class ParseError(Exception):
    """Base for all parsing failures. Importable by any stage."""

    def __init__(self, *, filepath: str, message: str) -> None:
        super().__init__(message)
        self.filepath = filepath
        self.message = message

class MalformedXMLError(ParseError):
    """lxml raised XMLSyntaxError — XML is structurally invalid."""

class MissingFileError(ParseError):
    """Path does not exist on the filesystem."""

class UnreadableFileError(ParseError):
    """Path exists but cannot be read (permissions, directory, I/O error)."""
```

### Minimal Valid .yxmd Fixture for Tests

```python
# Source: structure verified against real .yxmd (kartik-chandna/Data-cleanup on GitHub)
MINIMAL_YXMD = b"""<?xml version="1.0"?>
<AlteryxDocument yxmdVer="11.0">
  <Nodes>
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput">
        <Position x="54" y="102" />
      </GuiSettings>
      <Properties>
        <Configuration>
          <File RecordLimit="0">data.csv</File>
        </Configuration>
      </Properties>
    </Node>
    <Node ToolID="2">
      <GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect">
        <Position x="162" y="102" />
      </GuiSettings>
      <Properties>
        <Configuration />
      </Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection>
      <Origin ToolID="1" Connection="Output" />
      <Destination ToolID="2" Connection="Input" />
    </Connection>
  </Connections>
</AlteryxDocument>"""
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `xml.etree.ElementTree` (stdlib) | `lxml.etree` | Project decision at roadmap time | lxml raises `XMLSyntaxError` with line/column/filename; stdlib ET raises generic `xml.etree.ElementTree.ParseError` with less context |
| Generic `except Exception` for parse errors | Typed exception hierarchy (`ParseError` subclasses) | This phase | Callers can distinguish `MissingFileError` vs `MalformedXMLError` vs `UnreadableFileError` for correct CLI exit codes in Phase 9 |

**Deprecated/outdated:**
- `lxml.objectify`: Auto-maps XML to Python objects with magic `__getattr__` — not typed, hard to test, incompatible with `mypy --strict`. Do not use.
- `recover=True` parsing: Silently skips broken XML nodes. Never appropriate for validation-first parsing.

---

## Open Questions

1. **Alteryx `Connection` attribute values beyond "Output"/"Input"**
   - What we know: Real `.yxmd` files show `Connection="Output"`, `Connection="Input"`, and likely `Connection="Left"`, `Connection="Right"`, `Connection="Join"` for tools like Join, Filter, etc.
   - What's unclear: The full enumeration of valid anchor names. Phase 1 defined `AnchorName` as `NewType("AnchorName", str)` — not an enum — so any string is valid at the model layer.
   - Recommendation: Accept any string value from `Connection` attribute. Phase 3 fixtures will flush out edge cases when real `.yxmd` files arrive.

2. **`Nodes` element presence in all valid .yxmd files**
   - What we know: All real `.yxmd` files examined have a `<Nodes>` element (even if empty workflows have no `<Node>` children).
   - What's unclear: Whether an Alteryx export ever omits `<Nodes>` entirely (e.g., a workflow with zero tools).
   - Recommendation: Treat an absent `<Nodes>` element as valid — return `WorkflowDoc` with empty `nodes` tuple. Use `root.findall("Nodes/Node")` which safely returns `[]` if `<Nodes>` is absent.

3. **`EngineSettings` and other non-config child elements of `<Node>`**
   - What we know: Each `<Node>` has `<GuiSettings>`, `<Properties>` (containing `<Configuration>`), and `<EngineSettings>`. `<EngineSettings>` carries DLL and entry-point metadata.
   - What's unclear: Whether Phase 3 normalizer will need `EngineSettings` data or if it is always discardable.
   - Recommendation: Parse only `GuiSettings` (for position and tool_type) and `Properties/Configuration` (for config dict). Ignore `EngineSettings` entirely. Phase 3 normalizer can add extraction if needed.

---

## Sources

### Primary (HIGH confidence)

- lxml 6.0.2 — verified by running `import lxml; print(lxml.__version__)` in the project venv; all exception behaviors tested in-session
- https://lxml.de/parsing.html — `etree.parse()`, `XMLParser`, `XMLSyntaxError`, `recover` parameter
- https://lxml.de/api/lxml.etree.XMLSyntaxError-class.html — exception attributes (`filename`, `lineno`, `position`, `error_log`)
- Real `.yxmd` file: https://github.com/kartik-chandna/Data-cleanup/blob/master/alteryx%20workflow.yxmd — confirmed XML structure (AlteryxDocument, Node, GuiSettings/Position, Properties/Configuration, Connections/Connection/Origin/Destination)
- Phase 1 source code — `WorkflowDoc`, `AlteryxNode`, `AlteryxConnection`, `ToolID`, `AnchorName` already built and tested

### Secondary (MEDIUM confidence)

- https://community.alteryx.com/t5/Alteryx-Designer-Desktop-Discussions/XML-to-Workflow-Understanding/td-p/1160582 — community-verified .yxmd structure description (aligns with real file inspection)
- WebSearch: "Alteryx yxmd XML AlteryxDocument Node ToolID GuiSettings Position_X Connection Origin Destination" — multiple community sources converge on same element names

### Tertiary (LOW confidence)

- Full enumeration of `Connection` attribute values (anchor names) — inferred from community posts, not from Alteryx official documentation. Mark for validation in Phase 3.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — lxml 6.0.2 already installed, version locked, exception behaviors verified by running code
- Architecture: HIGH — .yxmd XML structure confirmed against a real file on GitHub; XPath patterns tested in-session
- Pitfalls: HIGH — each pitfall was reproduced in-session (e.g., empty file → XMLSyntaxError, str() required for etree.parse, None from find())

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (lxml is a stable library; .yxmd format is stable across Alteryx versions)
