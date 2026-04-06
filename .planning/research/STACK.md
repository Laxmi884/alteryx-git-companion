# Stack Research

**Domain:** Python CLI tool — XML diff, graph analysis, interactive HTML report generation
**Researched:** 2026-02-28
**Confidence:** HIGH (all critical choices verified against PyPI current versions and official docs)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | NetworkX 3.6.1 requires >=3.11; aligns with modern type hint features used by Typer. Do not target 3.10 — it is excluded by current NetworkX. |
| lxml | 6.0.2 | XML parsing, normalization, canonicalization | C-based (libxml2), 5–20x faster than stdlib ElementTree for large files. Provides C14N 1.0/2.0 via `method="c14n2"` for stable attribute-ordered serialization — critical for hash-based normalization. Only library that supports both XPath and canonical serialization in a single dependency. |
| networkx | 3.6.1 | Directed graph model for workflow connections | Industry standard for Python graph analysis. DiGraph + topological_sort is the correct primitive for Alteryx DAG representation. Node/edge attributes carry tool metadata for diff annotation. |
| Typer | 0.24.1 | CLI interface | Built on Click underneath, but uses Python type hints for argument declaration — zero boilerplate for this project's 3–5 flags. Auto-generates help text and shell completion. Actively maintained (Feb 2026 release). |
| Jinja2 | 3.1.6 | HTML report templating | Standard Python HTML templating. Handles embedding large inline JS blobs cleanly via `{{ variable \| safe }}`. No framework lock-in. Works without a web server — renders to a static file. |
| pyvis | 0.3.2 | Interactive graph visualization in HTML | Wraps vis.js Network. Python-side node/edge construction, exports to HTML. Use `cdn_resources='in_line'` to produce single-file output with vis.js embedded (critical for offline use). Last released Feb 2023 — mature/stable but not actively developed. Sufficient for this use case. |
| pytest | 9.0.2 | Testing | Standard. Use parametrize + fixture pairs for golden-file XML diff testing. |
| uv | latest | Package management, virtual environments | 10–100x faster than pip. Manages pyproject.toml, lockfile (uv.lock), and Python version via `.python-version`. The 2025 standard for new Python CLI projects. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib | stdlib | SHA-256 hashing of normalized tool config blobs | Always — no additional dependency. Use `hashlib.sha256(canonical_xml_bytes).hexdigest()` to fingerprint each tool's config subtree for O(n) change detection. |
| deepdiff | 8.6.1 | Structured diff of Python dicts/objects | Use for the config-level diff layer: convert each tool's config XML subtree to a dict, then run DeepDiff to get field-level changes (added/removed/modified keys). Do NOT use as the primary XML diff engine — see Alternatives. |
| xml.etree.ElementTree | stdlib | Fallback validation only | Do not use for primary parsing. Use only as a zero-dependency validator in error-handling paths if lxml is unavailable (unlikely). |
| rich | latest | Terminal output formatting | For CLI progress/error messages with color. Optional — add only if UX polish is desired in Phase 1. |
| pytest-cov | latest | Code coverage | Dev dependency. Run with `uv run pytest --cov=alteryx_diff`. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Venv + dependency management | `uv init`, `uv add lxml networkx typer jinja2 pyvis deepdiff`, `uv add --dev pytest pytest-cov` |
| ruff | Linting + formatting | Fast, replaces flake8 + black + isort. Add to `[tool.ruff]` in pyproject.toml. |
| mypy | Static type checking | Enforce type hints. Works cleanly with Typer's type-hint-first design. |
| pyproject.toml | Project manifest | PEP 621 standard. Defines entry points, dependencies, tool config. Single source of truth. |

---

## Decision Rationale by Question

### XML Parsing: lxml wins decisively

**Use lxml 6.0.2, not xml.etree, not xmltodict.**

- `xml.etree`: Pure Python path is 5–20x slower; no C14N canonicalization; limited XPath. For 500-tool Alteryx workflows (~1–5 MB XML), this becomes the bottleneck.
- `xmltodict 1.0.4`: Converts XML to dicts. Explicitly documented to NOT preserve attribute order, multiple top-level comments, or mixed content. Its own docs say "for exact fidelity, use a full XML library such as lxml." Fatal for diff accuracy.
- `lxml 6.0.2`: C-based, XPath 1.0, C14N 2.0 (`etree.canonicalize()` or `method="c14n2"`). The canonicalize step sorts attributes lexicographically and normalizes whitespace — this solves the attribute-reordering false-positive problem in Alteryx XMLs without custom code.

**Confidence: HIGH** — Verified against lxml 6.0.2 PyPI page and lxml.de docs.

### Hashing/Normalization: lxml C14N + hashlib

**Use lxml's `etree.canonicalize()` to produce a stable byte representation, then `hashlib.sha256()` to fingerprint each tool config subtree.**

Do NOT implement custom attribute sorting or whitespace stripping — lxml C14N handles both per the W3C spec. The canonical form produces byte-identical output for semantically identical XML regardless of attribute order or whitespace formatting — exactly what is needed to eliminate Alteryx false positives.

Workflow:
1. Parse tool `<Node>` subtree with lxml
2. Strip position attributes (CenterPoint X/Y) before canonicalization unless `--include-positions` flag is set
3. `etree.canonicalize(from_node, strip_text=True)` — returns bytes
4. `hashlib.sha256(canonical_bytes).hexdigest()` — use as tool fingerprint
5. Compare fingerprints between old/new workflow to classify unchanged/modified tools

**Confidence: HIGH** — C14N attribute sorting behavior verified against lxml docs and W3C C14N spec.

### Diff Computation: Custom pipeline (not xmldiff, not difflib)

**Use a custom two-layer diff engine: hashlib fingerprints for tool-level detection, then DeepDiff for config-level detail.**

- `difflib`: Line-based text diff. Produces raw line hunks from XML text. Zero semantic understanding of tools or connections. Wrong abstraction level for this problem.
- `xmldiff 2.7.0`: XML-specific structured diff. Outputs edit operations (insert, delete, rename, move). Sound algorithm ("Change Detection in Hierarchically Structured Information" paper). But outputs raw XML patch operations, not "tool X's field Y changed from A to B" — requires significant post-processing to map to the Alteryx object model. Last active update: 2023. Python 3.11 support is listed as max — needs verification before using.
- `deepdiff 8.6.1`: Works on Python dicts/objects. After converting each tool's config XML to a dict (via `lxml`), DeepDiff produces human-readable field-level changes. Released Sep 2025 — actively maintained.
- **Custom pipeline** (recommended): Parse → normalize → fingerprint per tool → classify (added/removed/modified) → for modified tools, run DeepDiff on dict representation to get field-level detail. This gives exact control over what counts as a change and avoids fighting xmldiff's edit-operation abstraction.

**Confidence: HIGH** for architecture decision; MEDIUM for DeepDiff dict representation approach (well-established pattern, not verified against an Alteryx-specific reference).

### Graph Analysis: networkx 3.6.1

**Use networkx DiGraph.** It is the right choice in 2025.

- Nodes = Alteryx tools (ToolID, type, config hash)
- Edges = connections (FromToolID → ToToolID, with anchor metadata)
- `nx.topological_sort()` for ordered rendering
- Node/edge attributes carry diff status (added/removed/modified) — passes directly into pyvis node colors

**Constraint:** NetworkX 3.6.1 requires Python >=3.11. This drives the Python version floor.

**Confidence: HIGH** — Verified against networkx 3.6.1 PyPI page and official docs.

### Graph Visualization: pyvis 0.3.2 with `cdn_resources='in_line'`

**Use pyvis with `cdn_resources='in_line'`.**

- `pyvis` wraps vis.js Network — the most natural fit for workflow canvas visualization (node positions, directed edges, hover events)
- `cdn_resources='in_line'` embeds vis.js JavaScript directly in the HTML output, making the report a single self-contained file (no CDN dependency, works offline)
- DO NOT use `cdn_resources='local'` — there is a documented bug where it still loads from CDN despite the setting
- DO NOT use `cdn_resources='remote'` — requires internet connection at report view time

**D3.js alternative:** Would require 300–500 lines of JavaScript embedded in Jinja2 template. D3 has no built-in graph layout — you'd need d3-force or dagre-d3. High-effort, high-flexibility. Not justified for Phase 1 when pyvis delivers 80% of the result in 10% of the code. Phase 3+ (SaaS UI) can revisit D3.

**vis.js directly:** pyvis IS a vis.js wrapper. Using vis.js directly from Python would require generating raw JSON and JavaScript — essentially rebuilding pyvis. Not beneficial.

**pyvis maintenance concern:** Last PyPI release was Feb 2023. However, the underlying vis.js library (vis-network) remains maintained, and pyvis's feature set is complete for this use case. The risk is low for a Phase 1 CLI tool.

**Confidence: MEDIUM** — pyvis `in_line` behavior verified via GitHub issues; maintenance status and vis.js dependency verified.

### HTML Templating: Jinja2 3.1.6

**Use Jinja2.** No contest.

- Standard Python HTML templating — used by Flask, Django, Ansible, Pelican
- Handles embedding large pyvis HTML output blob, inline CSS, and per-tool diff sections without escaping issues
- `{{ graph_html | safe }}` pattern for embedding raw HTML from pyvis
- Filters for conditional CSS classes (`{{ 'modified' if tool.status == 'modified' else '' }}`)
- No server required — renders to a static `.html` file

**Confidence: HIGH** — Verified against Jinja2 3.1.6 PyPI page and official docs.

### CLI: Typer 0.24.1

**Use Typer, not Click, not argparse.**

- Typer is Click under the hood — all Click capabilities are available if needed
- Type hint-first: `def diff(file_a: Path, file_b: Path, include_positions: bool = False, output: Path = Path("diff.html"))` — the entire CLI is defined by the function signature
- Auto-generates `--help`, shell completion, and validation (file must exist, etc.) from type annotations
- Released Feb 2026 — actively maintained
- Click (38.7% ecosystem adoption) is the alternative if Typer's abstraction causes friction, but for this 3–5 argument CLI, Typer is strictly less code
- argparse: stdlib but verbose and manual. No type hint integration. No autocompletion. Not justified for a greenfield project.

**Confidence: HIGH** — Verified against Typer 0.24.1 PyPI page and Typer official docs.

### Testing: pytest 9.0.2 with golden-file fixtures

**Use pytest with parametrized golden-file tests.**

Pattern for XML diff tools:
1. `tests/fixtures/` — directory of `.yxmd` file pairs (`before.yxmd`, `after.yxmd`)
2. `tests/expected/` — expected diff output as JSON (the object model, not HTML)
3. `@pytest.mark.parametrize` over fixture pairs
4. Assert diff engine output matches expected JSON exactly
5. Separate test suite for HTML rendering (assert structure, not pixel equality)

Do NOT test HTML output byte-for-byte — pyvis output is non-deterministic (physics seed). Test the diff object model, not the rendered artifact.

**Confidence: HIGH** — pytest 9.0.2 PyPI verified. Pattern is standard for diff tools.

### Packaging: uv + pyproject.toml

**Use uv with pyproject.toml. No requirements.txt.**

```toml
[project]
name = "alteryx-diff"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "lxml>=6.0.2",
    "networkx>=3.6.1",
    "typer>=0.24.1",
    "jinja2>=3.1.6",
    "pyvis>=0.3.2",
    "deepdiff>=8.6.1",
]

[project.scripts]
acd = "alteryx_diff.cli:app"

[tool.uv]
dev-dependencies = [
    "pytest>=9.0.2",
    "pytest-cov",
    "ruff",
    "mypy",
]
```

**Confidence: HIGH** — uv workflow verified against astral.sh docs and Real Python guide.

---

## Installation

```bash
# Initialize project
uv init alteryx-diff
cd alteryx-diff

# Core runtime dependencies
uv add lxml networkx typer jinja2 pyvis deepdiff

# Dev dependencies
uv add --dev pytest pytest-cov ruff mypy

# Run CLI during development
uv run acd workflow_v1.yxmd workflow_v2.yxmd

# Run tests
uv run pytest --cov=alteryx_diff
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| XML parsing | lxml 6.0.2 | xml.etree (stdlib) | 5–20x slower; no C14N canonicalization; limited XPath |
| XML parsing | lxml 6.0.2 | xmltodict 1.0.4 | Explicitly does not preserve attribute order or XML nuances — self-disqualified for diff fidelity |
| Diff computation | Custom + DeepDiff | xmldiff 2.7.0 | Outputs raw edit operations (insert/delete/rename), not field-level changes; requires significant post-processing; Python 3.11 support uncertain |
| Diff computation | Custom + DeepDiff | difflib (stdlib) | Line-based text diff, no semantic understanding of XML structure |
| Graph viz | pyvis 0.3.2 (in_line) | D3.js embedded via Jinja2 | 300–500 lines of custom JavaScript; no built-in graph layout; high effort for equivalent output |
| Graph viz | pyvis 0.3.2 (in_line) | vis.js directly | pyvis IS the Python wrapper for vis.js; using vis.js directly means rebuilding pyvis |
| Graph viz | pyvis 0.3.2 (in_line) | Plotly/Bokeh | General-purpose charting libs, not graph network libraries; awkward fit for node+edge workflow canvas |
| CLI | Typer 0.24.1 | Click | Click is Typer's foundation; use Click directly only if Typer's type-hint abstraction causes friction |
| CLI | Typer 0.24.1 | argparse | Verbose, manual, no type hint integration, no autocompletion |
| Package mgmt | uv | Poetry | uv is 10–100x faster; simpler lockfile semantics; Poetry has slower resolver and more complex config |
| Package mgmt | uv | pip + venv | No lockfile, manual env management, no Python version pinning |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `xml.etree.ElementTree` as primary parser | Pure Python, no C14N, no XPath 1.0 — misses attribute normalization and is 5–20x slower | `lxml 6.0.2` |
| `xmltodict` | Self-documented as not preserving attribute order or XML nuances — will produce false positives in Alteryx XML | `lxml 6.0.2` |
| `xmldiff` as primary diff engine | Edit-operation abstraction (insert/delete/rename) does not map cleanly to "tool X field Y changed from A to B"; Python 3.11 support uncertain | Custom pipeline with DeepDiff |
| `difflib` for XML diff | Line-based text diff produces meaningless output for structured XML | Custom pipeline |
| `pyvis cdn_resources='local'` | Documented bug: still loads from CDN despite the setting name | `cdn_resources='in_line'` |
| `pyvis cdn_resources='remote'` | Requires internet at report-viewing time; breaks offline use | `cdn_resources='in_line'` |
| `requirements.txt` | No lockfile semantics, no Python version pinning, manual maintenance | `pyproject.toml` + `uv.lock` |
| Python < 3.11 | NetworkX 3.6.1 requires `>=3.11`; dropping to 3.10 means pinning to an older NetworkX | Python 3.11+ |

---

## Stack Patterns by Variant

**If Phase 3 API service layer is added:**
- Wrap the same `parse → normalize → diff → render` pipeline in a FastAPI endpoint
- Typer CLI and FastAPI route both call the same core library functions — no rearchitecting
- Add `fastapi>=0.115` and `uvicorn>=0.34` to dependencies at that point
- Because lxml, networkx, deepdiff, and Jinja2 have no web framework dependency, the transition is a thin adapter layer

**If Alteryx workflows exceed 500 tools (Phase 3+ scale):**
- Switch from full in-memory lxml tree to lxml's iterparse (SAX-style streaming) for parsing
- NetworkX DiGraph handles 10K+ nodes without issue
- pyvis may render slowly for 500+ nodes — consider switching to D3.js with WebWorker-based layout for large graphs
- deepdiff performance on large dicts is acceptable up to ~1000 keys; beyond that, profile before committing

**If self-contained HTML size becomes a concern:**
- pyvis in_line mode embeds the full vis.js bundle (~800KB minified)
- Alternative: write custom Jinja2 template that inlines only the vis-network UMD module and passes graph data as JSON
- This reduces the embedded JS to ~300KB and gives full control over the HTML structure

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| networkx 3.6.1 | Python >=3.11, !=3.14.1 | Hard floor — drives Python version requirement for the whole project |
| lxml 6.0.2 | Python 3.8–3.14 | More permissive than networkx; networkx sets the floor |
| typer 0.24.1 | click >=8.0 | Typer installs click as a transitive dependency; do not separately pin click |
| pyvis 0.3.2 | Python 3.x | No hard Python version constraint documented; works on 3.11 |
| deepdiff 8.6.1 | Python 3.8+ | No conflict with other deps |
| jinja2 3.1.6 | Python 3.7+ | No conflict with other deps |
| pytest 9.0.2 | Python 3.8+ | Dev only; no runtime conflict |

---

## Sources

- lxml 6.0.2 — https://pypi.org/project/lxml/ (verified current version Sep 2025)
- lxml C14N documentation — https://lxml.de/api.html (C14N 1.0 and 2.0 support, attribute sorting behavior)
- lxml performance benchmarks — https://lxml.de/performance.html (5–20x faster than stdlib ElementTree)
- networkx 3.6.1 — https://pypi.org/project/networkx/ (Python >=3.11 requirement verified)
- networkx topological sort — https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.topological_sort.html
- deepdiff 8.6.1 — https://pypi.org/project/deepdiff/ (Sep 2025 release verified)
- deepdiff docs — https://zepworks.com/deepdiff/current/diff.html
- typer 0.24.1 — https://pypi.org/project/typer/ (Feb 2026 release verified)
- jinja2 3.1.6 — https://pypi.org/project/Jinja2/ (current version verified)
- pyvis 0.3.2 — https://pypi.org/project/pyvis/ (last release Feb 2023)
- pyvis cdn_resources bug — https://github.com/WestHealth/pyvis/issues/228 (local CDN bug, in_line workaround)
- xmltodict 1.0.4 — https://pypi.org/project/xmltodict/ (explicitly discourages use for exact fidelity)
- xmldiff 2.7.0 — https://pypi.org/project/xmldiff/
- pytest 9.0.2 — https://pypi.org/project/pytest/ (Dec 2025 release verified)
- uv documentation — https://docs.astral.sh/uv/concepts/projects/config/
- typer vs click vs argparse comparison — https://codecut.ai/comparing-python-command-line-interface-tools-argparse-click-and-typer/

---

*Stack research for: Alteryx Canvas Diff (ACD) — Python CLI XML diff tool*
*Researched: 2026-02-28*
