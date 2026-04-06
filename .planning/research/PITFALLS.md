# Pitfalls Research

**Domain:** XML diff / graph visualization / CLI developer tool (Alteryx Canvas Diff)
**Researched:** 2026-02-28
**Confidence:** MEDIUM-HIGH (XML/Python/pyvis: HIGH from official sources; Alteryx-specific XML: MEDIUM from community/GitHub inspection; Graph diffing: HIGH from academic literature)

---

## Critical Pitfalls

### Pitfall 1: ToolID-Only Node Matching Causes Phantom Add/Remove Pairs

**What goes wrong:**
Alteryx Designer regenerates ToolIDs on certain save operations (copy-paste, workflow merge, "save as"). If you match nodes across workflow versions purely by ToolID, a workflow where Tool 12 becomes Tool 47 after a save produces a false "Tool 12 removed + Tool 47 added" result — even though the tool, its configuration, and its position are unchanged. Users see the diff explode with phantom changes.

**Why it happens:**
ToolID is treated as the stable primary key during implementation because it appears in every `<Node ToolID="...">` element and looks like a reliable identifier. The regeneration behavior is not documented prominently and only discovered when real workflows are tested.

**How to avoid:**
Implement a two-pass matching strategy: first attempt exact ToolID match; when ToolID has no counterpart in the other version, fall back to secondary matching by (Plugin type + normalized X/Y position bucket). Only declare a tool "added" or "removed" after both passes fail. This is explicitly called out in PROJECT.md as a required design decision.

**Warning signs:**
- Integration tests show large numbers of additions/removals on workflows that were only repositioned
- A workflow saved as a copy reports completely different tool sets despite identical content
- Test fixtures that use synthetic ToolIDs (1, 2, 3...) always pass, but real workflow tests fail

**Phase to address:** Phase 1 — XML parsing and normalization layer, before any diff logic is built on top.

---

### Pitfall 2: Position Fields Leaking Into Diff Detection

**What goes wrong:**
`<Position x="486" y="246" />` in `<GuiSettings>` changes every time a developer nudges a tool on the canvas. If position data is not stripped from the diff detection path (only from the graph layout path), every routine canvas rearrangement generates a false "modified" result on every tool touched. The diff report fills with yellow-highlighted tools where nothing functionally changed.

**Why it happens:**
Position has a dual role in this project: it feeds graph layout rendering (always needed) AND exists in the XML being parsed for diff (must be excluded by default). Developers building the diff logic treat all parsed fields symmetrically and forget to apply the position exclusion filter before hashing or comparing tool state. The `--include-positions` flag is added as an afterthought and inverts the default incorrectly.

**How to avoid:**
Build the normalization step as an explicit, tested transformation that produces a `NormalizedTool` object with position separated into its own field (not included in the comparison hash by default). The graph layout renderer reads from `NormalizedTool.position`. The diff engine reads from `NormalizedTool.config_hash`. These are two distinct data paths — never unified.

**Warning signs:**
- Running diff on the same workflow saved twice with minor layout changes produces "modified" results
- Position values appear in the diff output body for tools the user didn't change
- The `--include-positions` test fixture is wrong: the flag should add position to detection, not remove it

**Phase to address:** Phase 1 — normalization layer design, established before diff engine is built.

---

### Pitfall 3: pyvis Fails to Produce a Truly Self-Contained HTML File

**What goes wrong:**
pyvis's `cdn_resources` option has three modes (`local`, `in_line`, `remote`). The `in_line` mode is the only one that reliably embeds vis.js into the HTML output. However, even with `cdn_resources="local"` or `cdn_resources="in_line"`, Bootstrap CSS is still fetched from an external CDN (`cdnjs.cloudflare.com`). The resulting HTML file requires internet access to render correctly — it is not truly self-contained.

**Why it happens:**
pyvis documentation implies that `cdn_resources="local"` creates a portable file. GitHub issue #228 on the pyvis repo documents that this is incorrect — CSS resources continue to be pulled externally regardless of the setting. Developers test the output while connected to the internet and don't notice the dependency.

**How to avoid:**
Use `cdn_resources="in_line"` which embeds the vis-network JS as an inline script, then post-process the generated HTML to either: (a) inline the Bootstrap CSS manually, or (b) remove the Bootstrap CDN link entirely and provide minimal inline CSS for the elements actually used. Test report rendering with network access disabled (e.g., offline mode in Chrome DevTools or a simple `python -m http.server` with hosts blocked).

Alternatively, evaluate whether D3.js with a custom Jinja2 template gives more control over the output — the D3 bundle is inlined cleanly as a single script block.

**Warning signs:**
- HTML report opens fine on developer machines but fails for analysts opening the file on air-gapped networks
- Chrome DevTools Network tab shows `cdnjs.cloudflare.com` requests when viewing the report
- Report displays without styling (unstyled HTML) in restricted environments

**Phase to address:** Phase 2 — graph visualization and HTML report generation, tested offline before shipping.

---

### Pitfall 4: Large Workflow Rendering Causes Browser to Hang (Physics Engine)

**What goes wrong:**
pyvis uses the vis.js physics engine for layout. For graphs with 150+ nodes (common in complex Alteryx workflows), the physics simulation runs for 30+ seconds in the browser before the graph stabilizes. At 500 nodes (the performance target), rendering with physics enabled can take minutes or cause the browser tab to crash.

**Why it happens:**
pyvis defaults to physics-enabled layout (Barnes-Hut algorithm). The physics engine is designed for exploratory graph visualization, not for rendering pre-positioned workflow graphs. Alteryx provides explicit X/Y canvas coordinates — there is no need to simulate physics; position is already known.

**How to avoid:**
Since Alteryx workflows have explicit X/Y positions for every tool, disable physics entirely (`physics=False`) and render nodes at their exact canvas coordinates. This renders immediately and is semantically correct — the "canvas" in the report matches the canvas in Alteryx Designer. Only enable physics as a fallback when position data is missing or corrupted.

**Warning signs:**
- Report opens with a spinning progress bar visible for more than 2 seconds
- Browser CPU spikes to 100% when opening the report
- 500-tool test fixture takes more than 5 seconds (violates the stated performance requirement)

**Phase to address:** Phase 2 — graph layout configuration, set from the start of visualization work.

---

### Pitfall 5: Over-Normalization Masks Real Configuration Changes

**What goes wrong:**
The normalization step strips too aggressively. Fields that appear to be "metadata" are actually semantically meaningful configuration. Examples: annotation text (a developer's comment explaining the tool's purpose), tool display name, or embedded SQL query whitespace. After normalization, two tools with different annotations or reformatted SQL hash identically — the diff engine reports "no change" when a meaningful change exists.

**Why it happens:**
The developer lists all "noise" fields to strip: positions, whitespace, attribute order. Then adds annotation text because it "looks like metadata." SQL whitespace is stripped because "whitespace doesn't matter in SQL." Both decisions lose real information. The project value prop is "zero false positives AND zero missed changes" — over-normalization violates the second half.

**How to avoid:**
Define a strict normalization contract: only strip fields that are demonstrably non-functional and auto-generated by Alteryx on save. This means: X/Y positions (by default), `<TempFile>` paths, attribute ordering within elements, and insignificant XML whitespace between tags. Do NOT strip: annotation text, display names, any configuration value, whitespace inside string values (SQL, expressions, formulas).

Create a normalization test suite that proves each stripped field cannot affect workflow output. If you can't write that proof, don't strip the field.

**Warning signs:**
- Two workflows with different filter expressions hash identically
- Annotation changes (developer comments) are invisible in the diff
- Users report "the diff says nothing changed but the workflow behaves differently"

**Phase to address:** Phase 1 — define the normalization contract as a formal spec with tests before implementation.

---

### Pitfall 6: XML Namespace Handling Breaks Parser Comparisons

**What goes wrong:**
lxml preserves namespace prefixes from the source document. ElementTree invents its own prefixes (`ns0`, `ns1`) during serialization. If the same Alteryx workflow is parsed by two different code paths (or the parser changes), identical elements produce different string representations. String-based comparison then reports changes where none exist.

**Why it happens:**
XML namespaces are identified by their URI, not their prefix. Two documents can use `ns0:tool` and `myns:tool` with the same URI — they are identical. But naive string comparison or hash-of-serialized-text treats these as different. ElementTree's namespace prefix rewriting is the most common trigger.

**How to avoid:**
Never compare XML by serializing to string and comparing strings. Always compare by navigating the parsed element tree and using Clark notation (`{namespace_uri}localname`) for tag comparisons. lxml's `tag` property returns Clark notation automatically. If you must serialize for hashing, use canonical XML (`lxml.etree.tostring(element, method="c14n")`) which normalizes namespace declarations deterministically.

**Warning signs:**
- Diff results change depending on whether a workflow was parsed with lxml vs. xml.etree
- Identical workflows loaded from different file paths produce "differences"
- Namespace prefix `ns0` appears in diff output

**Phase to address:** Phase 1 — XML parsing layer, verified with namespace-heavy test fixtures.

---

### Pitfall 7: CLI Logic Coupled to Presentation — Hard to Extract as API

**What goes wrong:**
The CLI entry point directly calls rendering functions, formats output to stdout, and handles error display inline. When Phase 3 requires a REST API layer, the diff pipeline cannot be called without triggering CLI-specific behavior (argument parsing, sys.exit, ANSI color codes, direct file writes). Extracting the API requires a rewrite of the core pipeline, not just adding a new entry point.

**Why it happens:**
The initial implementation treats the CLI as the product. Functions accept `argparse.Namespace` objects as parameters. Error handling calls `sys.exit(1)` directly. Report writing opens file handles inside the diff function. This is the natural way to write a script that is never intended to be called as a library.

**How to avoid:**
Build the pipeline as three independent, importable modules: `parser.py` (returns typed objects), `differ.py` (accepts typed objects, returns typed diff result), `renderer.py` (accepts diff result, returns HTML string). The CLI (`cli.py`) is a thin adapter: parse args, call pipeline, write output, handle exit codes. The future API layer (`api.py`) is another thin adapter calling the same pipeline. Neither adapter contains any business logic.

Concretely: no function in `parser.py`, `differ.py`, or `renderer.py` should call `sys.exit`, `print`, or open file handles.

**Warning signs:**
- Writing a unit test for the diff engine requires mocking `sys.argv`
- The differ function accepts `args.file1` instead of a `Path` or parsed `Workflow` object
- Adding a `--json` output flag requires modifying the diff engine, not just the renderer

**Phase to address:** Phase 1 — architecture decision before any code is written. Enforce with a test that imports and calls the differ without touching the CLI layer.

---

## Moderate Pitfalls

### Pitfall 8: CDATA Sections Silently Lose Content

**What goes wrong:**
Python's `xml.etree.ElementTree` converts CDATA sections (`<![CDATA[...]]>`) into plain text nodes, discarding the CDATA wrapper. If Alteryx embeds SQL or expression content in CDATA sections, comparing the raw text after round-trip through ElementTree is fine. However, if the code compares serialized XML (not parsed text), one representation has `<![CDATA[SELECT *]]>` and the other has `SELECT *`, producing a false diff.

**How to avoid:**
Always compare element `.text` content (the parsed string value), never the raw serialized XML byte string. Use lxml's element tree API throughout — avoid `lxml.etree.tostring()` comparisons except when using C14N canonicalization for hashing. Verify with a test fixture containing a CDATA-wrapped expression.

**Phase to address:** Phase 1 — XML parsing tests, include a CDATA fixture.

---

### Pitfall 9: TempFile Paths Embedded in Workflow XML Cause False Diffs

**What goes wrong:**
Alteryx embeds `<TempFile>` elements with system-generated paths like `Engine_23824_bbbeb6edfa4d41adbc1966eb1b8bff1a` inside workflow XML. These paths contain process IDs and random identifiers generated at runtime. A workflow saved on machine A has different TempFile paths than the same workflow opened on machine B. If TempFile elements are compared, every cross-machine or cross-session diff will show changes.

**Confirmed from:** Direct inspection of `RunUnitTests.yxmd` on GitHub (jdunkerley/AlteryxFormulaAddOns).

**How to avoid:**
Add `TempFile` elements to the normalization exclusion list explicitly. Strip all `<TempFile>` elements and their children from both workflow trees before comparison. Document this in the normalization spec so it is not accidentally re-added as "real" content.

**Phase to address:** Phase 1 — normalization layer, document as named exclusion rule.

---

### Pitfall 10: Graph Edit Distance Is Computationally Intractable for Large Graphs

**What goes wrong:**
NetworkX provides `graph_edit_distance()` for computing the minimum edit distance between two graphs. This is the theoretically correct way to match nodes across workflow versions. However, Graph Edit Distance is NP-hard — for a 500-node workflow, this function will not return within the 5-second performance requirement. It may not return within hours.

**How to avoid:**
Do not use `networkx.graph_edit_distance()` for node matching. Instead, use the deterministic two-pass matching strategy: ToolID match first, then (type + position bucket) for unmatched nodes. This runs in O(n log n) and handles the practical cases. GED is an academic tool, not a production tool for this scale.

**Phase to address:** Phase 1 — algorithm selection, documented explicitly so no one adds GED later as an "improvement."

---

### Pitfall 11: argparse Exit Code Inconsistency for Scripting Use

**What goes wrong:**
argparse calls `sys.exit(2)` on usage errors and `sys.exit(1)` on other errors. This inconsistency breaks shell scripts and CI pipelines that check `if [ $? -ne 0 ]` — they cannot distinguish "bad arguments" from "diff found changes" from "file not found." The tool becomes unreliable to script.

**How to avoid:**
Define explicit exit codes and document them: `0` = no differences found, `1` = differences found, `2` = error (file not found, invalid XML, etc.). Subclass `argparse.ArgumentParser` and override `.error()` to raise a custom exception that maps to exit code `2` instead of calling `sys.exit` directly. Map all internal errors through the exception hierarchy before the CLI layer converts to exit codes.

This also means the diff engine itself returns a typed result (DiffResult with `has_changes: bool`), not an exit code. The CLI layer converts the result to an exit code.

**Phase to address:** Phase 1 — CLI design, establish exit code contract in docstring/README from day one.

---

### Pitfall 12: Jinja2 Template Inlining Large Diff Data Causes Report Bloat

**What goes wrong:**
For a 500-tool workflow where most tools are modified, the HTML report embeds the full configuration XML diff for every tool as inline HTML. The report grows to 20-50 MB. Browsers struggle to render 20 MB HTML files. The report is "self-contained" as required but is functionally unusable.

**How to avoid:**
Keep per-tool diff content collapsed by default and use JavaScript-driven expand/collapse. Only render diff content into the DOM when a user clicks — not by hiding pre-rendered HTML with `display:none` (which still parses all the DOM). For very large diffs, embed the per-tool diff data as a JSON object in a `<script>` tag and render sections lazily via JavaScript when the user expands them. Test with a 500-tool fixture to measure actual report file size.

**Phase to address:** Phase 2 — HTML report generation, with a large-workflow performance test.

---

### Pitfall 13: Attribute Order Differences Between Python Versions Create Unstable Hashes

**What goes wrong:**
Before Python 3.8, ElementTree sorted attributes alphabetically during serialization. After Python 3.8, it preserves insertion order. If you hash serialized XML text to detect changes, a workflow serialized with Python 3.7 may hash differently than the same workflow serialized with Python 3.8+, even though the content is identical.

**How to avoid:**
Hash the parsed element tree content, not serialized bytes. When hashing is necessary (e.g., content-based matching), use canonical XML via `lxml.etree.tostring(element, method="c14n")` which sorts attributes deterministically per the C14N specification. Never hash `str(element)` or `tostring(element)` without canonicalization.

**Phase to address:** Phase 1 — hashing strategy, document the canonicalization requirement.

---

## Minor Pitfalls

### Pitfall 14: ANSI Color Codes Break Piped Output

**What goes wrong:**
If the CLI outputs colored text (for summary lines or error messages) using ANSI escape codes without checking whether stdout is a TTY, piping the output to a file or another tool produces garbage characters. `diff old.yxmd new.yxmd > report.txt` contains `\033[31m` instead of readable text.

**How to avoid:**
Use a library that auto-detects TTY (Click and Rich both do this automatically). If using argparse with manual coloring, check `sys.stdout.isatty()` before emitting ANSI codes.

**Phase to address:** Phase 1 — CLI output layer.

---

### Pitfall 15: Encoding Declaration Mismatch on Windows

**What goes wrong:**
Alteryx writes `.yxmd` files as UTF-8. On Windows, if the file is opened without explicitly specifying encoding (`open(path)` uses the system locale), non-ASCII characters in tool annotations, expressions, or file paths cause `UnicodeDecodeError`. This is most common on machines configured with Windows-1252 locale.

**How to avoid:**
Always open `.yxmd` files with explicit `encoding="utf-8"` or pass the file path directly to `lxml.etree.parse()` which reads the XML encoding declaration and handles it correctly. lxml is the safer choice here — it respects the `<?xml version="1.0" encoding="utf-8"?>` declaration.

**Phase to address:** Phase 1 — file I/O layer.

---

### Pitfall 16: Snapshot Tests That Don't Cover Round-Trip Stability

**What goes wrong:**
Unit tests verify that the diff engine produces the correct output for a given input. But they don't verify that parsing the same file twice produces the same internal representation. A flaky parser (one that produces different attribute ordering or whitespace handling on successive runs) causes intermittent test failures and unstable diffs.

**How to avoid:**
Add an explicit round-trip stability test: parse a workflow, serialize it to the internal model, parse again, and assert the two representations are identical. Use pytest-snapshot (or syrupy) for golden-file-based testing of HTML report output — update snapshots deliberately when the renderer changes, not accidentally.

**Phase to address:** Phase 1 — test suite scaffolding.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| String-compare serialized XML instead of parsing element trees | Fast to implement | False diffs from namespace prefix variation and attribute ordering; breaks silently on Python version changes | Never |
| ToolID-only node matching without fallback | Simple code path | Phantom add/remove pairs on ID-regenerated workflows; destroys core value prop | Never |
| Passing `argparse.Namespace` objects into diff functions | Fewer function parameters | Couples diff engine to CLI; impossible to call as API without `sys.argv` manipulation | Never for pipeline functions |
| Physics-enabled pyvis layout | Zero layout code needed | Browser hangs on 150+ node graphs; fails the 5-second performance requirement | Never (positions are known from XML) |
| Hardcoding the normalization list | Simpler initial code | New noise patterns in future Alteryx versions add false positives; normalization is invisible to maintainers | Acceptable if the list is documented and tested |
| Inline all diff data in HTML at render time | Single Jinja2 template, no JS | Report becomes 20-50 MB for large workflows; unusable in browser | Never for workflows >100 tools |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| lxml vs. xml.etree | Using xml.etree for development convenience, lxml for production — subtle behavioral differences (namespace prefixes, CDATA, encoding) cause test fixtures to pass but production to fail | Pick one parser and use it everywhere. Use lxml: it handles namespaces correctly and respects encoding declarations. |
| pyvis CDN resources | Trusting `cdn_resources="local"` produces a self-contained file | Use `cdn_resources="in_line"` and verify offline rendering; Bootstrap CSS still loads from CDN in some pyvis versions — post-process or remove the link manually. |
| NetworkX directed graphs | Using `Graph` (undirected) instead of `DiGraph` when loading Alteryx connections | Alteryx connections are directional (source anchor → destination anchor). Use `DiGraph`. Undirected graph loses connection directionality, breaks connection diff detection. |
| argparse exit codes | Allowing argparse's default `sys.exit(2)` on usage error | Override `ArgumentParser.error()` to raise a typed exception; catch at the CLI boundary and map to documented exit codes. |
| Jinja2 template escaping | Auto-escaping disabled by default in non-HTML Jinja2 environments | Use `Environment(autoescape=True)` when generating HTML; prevents XSS if tool annotations contain characters like `<`, `>`, `&`. |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Physics-enabled pyvis rendering | Browser hangs 30s-5min on open; 100% CPU | Set `physics=False`, use Alteryx X/Y coordinates directly | Any workflow with 150+ tools |
| Graph Edit Distance (networkx.graph_edit_distance) | Hangs indefinitely on large workflows; never returns | Use deterministic two-pass matching (ToolID then type+position) | Any workflow with 30+ tools |
| Inlining full diff HTML at report render time | Report file >10 MB; browser slow to parse DOM | Embed diff data as JSON in `<script>` block, render lazily on expand | Workflows with 100+ modified tools |
| String-serializing XML for comparison | Slow serialization; non-deterministic results | Compare element tree nodes directly; use C14N only for hashing | Any workflow; O(n) of XML text size |
| Loading vis.js from CDN at report open time | Report fails on slow/no internet; initial render delay | Use `in_line` mode or embed JS directly in template | Always (must be self-contained) |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Jinja2 autoescape disabled when rendering tool annotations | Tool annotation containing `<script>` tag executes in browser when report is opened — XSS in a local HTML file | Enable `autoescape=True` in Jinja2 Environment; or use `markupsafe.escape()` on all user-controlled content before rendering |
| Parsing untrusted .yxmd files with XML entity expansion enabled | XXE (XML External Entity) attack if tool is ever called on untrusted files (e.g., API mode) | Use lxml with `resolve_entities=False` and `no_network=True` in the XMLParser; xml.etree does not support external entities by default (safe) |
| Writing temp files to CWD with predictable names | Unlikely in CLI-only mode; becomes a risk in API mode | Avoid temp files; generate report in memory and write to the specified output path only |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Reporting "Tool 12 removed, Tool 47 added" for ToolID regeneration | Analyst reviews diff assuming a tool was deleted; misses the real change (if any) | Two-pass matching; only show add/remove when both ToolID AND type+position match fail |
| Reporting modified tools without showing what changed | "Tool 23 (Formula): modified" — analyst can't see what expression changed | Always show field-level diff for modified tools; highlight changed values specifically |
| Hiding position changes by default with no indicator | Developer can't tell if layout has changed at all | Show a lightweight summary line: "N tools repositioned (use --include-positions to see details)" |
| Opening a 20 MB HTML report in the browser | Browser hangs; analyst loses confidence in the tool | Lazy-load per-tool diff content; keep initial report render under 2 MB |
| Cryptic exit code in CI | `exit 1` with no message; developer doesn't know if diff was found or tool failed | Consistent exit codes + stderr message for errors; stdout summary for diff results |

---

## "Looks Done But Isn't" Checklist

- [ ] **ToolID matching:** Verify with a fixture where ToolIDs were regenerated — confirm no false add/remove pairs appear
- [ ] **Self-contained HTML:** Open the report with network access disabled — verify it renders correctly with no external requests
- [ ] **Performance:** Run against a 500-tool synthetic workflow — confirm total time under 5 seconds
- [ ] **Position normalization:** Run diff on the same workflow saved twice with tools moved — confirm zero "modified" results
- [ ] **TempFile exclusion:** Verify workflows containing `<TempFile>` elements produce no TempFile-related diffs
- [ ] **CDATA handling:** Verify a workflow with CDATA-wrapped expressions compares correctly
- [ ] **Exit codes:** Verify `echo $?` after: (a) no diff, (b) diff found, (c) bad file path — all produce distinct documented codes
- [ ] **Offline rendering:** Verify on a machine without internet access
- [ ] **Namespace stability:** Verify diff output is identical when input files are parsed with lxml vs. re-parsed after save
- [ ] **Large report size:** Check file size of report generated from 500-tool fixture — must be under 5 MB to render without browser lag

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| ToolID-only matching shipped to production | HIGH | Requires redesigning the matching algorithm and rebuilding test fixtures; user trust is damaged by phantom diffs |
| pyvis CDN dependency discovered post-ship | LOW | Add HTML post-processing step to inline or remove Bootstrap CDN link; ships as a patch |
| Physics rendering hangs shipped | LOW | Add `physics=False` configuration; ships as a patch |
| CLI coupled to pipeline (API extraction needed) | HIGH | Requires refactoring all pipeline functions to remove sys.exit/print calls; touches core diff, parser, and renderer |
| Over-normalization masking real changes | MEDIUM | Requires identifying stripped fields, adding them back, regenerating test fixtures, re-validating with real workflows |
| TempFile paths causing false diffs | LOW | Add TempFile to normalization exclusion list; ships as a patch with a new test fixture |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| ToolID-only matching | Phase 1: XML parsing + normalization | Integration test with ToolID-regenerated fixture |
| Position leaking into diff | Phase 1: Normalization contract | Test: same workflow saved twice = zero diffs |
| pyvis CDN dependency | Phase 2: Graph visualization | Offline rendering test |
| Large graph physics hang | Phase 2: Graph layout config | 500-node render time <2 seconds |
| Over-normalization masking changes | Phase 1: Normalization spec | Test: changed expression = diff detected |
| XML namespace comparison | Phase 1: XML parsing layer | Namespace-prefix test fixture |
| CLI-pipeline coupling | Phase 1: Architecture | Unit test calling differ without CLI |
| CDATA silently lost | Phase 1: XML parsing tests | CDATA expression fixture |
| TempFile false diffs | Phase 1: Normalization exclusion list | Cross-machine fixture test |
| Graph Edit Distance intractability | Phase 1: Algorithm selection | Documented in code; no GED import |
| argparse exit code inconsistency | Phase 1: CLI design | Shell script test: `diff; echo $?` |
| HTML report size bloat | Phase 2: Report generation | 500-tool report size check |
| Attribute order hashing instability | Phase 1: Hashing strategy | C14N canonicalization used; verified |
| ANSI codes in piped output | Phase 1: CLI output layer | `acd old.yxmd new.yxmd | cat` produces clean text |
| Windows encoding mismatch | Phase 1: File I/O | Test fixture with non-ASCII annotations |

---

## Sources

- pyvis GitHub issue #204 — Performance and Graph Sizes: https://github.com/WestHealth/pyvis/issues/204
- pyvis GitHub issue #228 — CDN resources not read from local drive: https://github.com/WestHealth/pyvis/issues/228
- pyvis GitHub issue #84 — Displaying very large networks: https://github.com/WestHealth/pyvis/issues/84
- Python bug tracker #34160 — ElementTree attribute order: https://bugs.python.org/issue34160
- Python bug tracker #20198 — ElementTree attribute sorting: https://bugs.python.org/issue20198
- lxml compatibility docs — namespace prefix behavior: https://lxml.de/compatibility.html
- lxml FAQ — namespace handling: https://lxml.de/FAQ.html
- NetworkX graph_edit_distance docs — NP-hard note: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.similarity.graph_edit_distance.html
- NetworkX VF2 isomorphism algorithm: https://networkx.org/documentation/stable/reference/algorithms/isomorphism.vf2.html
- Alteryx community — version control position drift: https://community.alteryx.com/t5/Alteryx-Designer-Desktop-Discussions/Alteryx-Workflow-Version-Control/td-p/175046
- Alteryx yxmd XML inspection (jdunkerley/AlteryxFormulaAddOns): https://github.com/jdunkerley/AlteryxFormulaAddOns/blob/master/RunUnitTests.yxmd
- Alteryx yxmd XML inspection (jdunkerley/Alteryx BBCFoodAggr): https://github.com/jdunkerley/Alteryx/blob/master/BBC%20Food%20Download/BBCFoodAggr.yxmd
- xmldiff library documentation: https://pypi.org/project/xmldiff/
- Using xmldiff in Python unit tests (ComplianceAsCode blog): https://complianceascode.github.io/template/2022/10/24/xmldiff-unit-tests.html
- Subgraph isomorphism NP-complete: https://en.wikipedia.org/wiki/Subgraph_isomorphism_problem
- pytest-snapshot: https://pypi.org/project/pytest-snapshot/
- syrupy snapshot testing: https://github.com/syrupy-project/syrupy
- XML normalization pitfalls (xml.com): https://www.xml.com/pub/a/2002/11/13/normalizing.html
- MoldStud — XML interoperability pitfalls 2024: https://moldstud.com/articles/p-interoperability-in-xml-how-to-avoid-common-pitfalls-in-2024
- Python lxml namespace handling (WebScraping.AI): https://webscraping.ai/faq/lxml/how-do-i-handle-namespaces-in-xml-parsing-with-lxml
- ElementTree CDATA support recipe: https://code.activestate.com/recipes/576536-elementtree-cdata-support/

---
*Pitfalls research for: XML diff / graph visualization / CLI developer tool (Alteryx Canvas Diff)*
*Researched: 2026-02-28*
