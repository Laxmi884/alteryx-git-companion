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

---
---

# Pitfalls Research — LLM Documentation Feature (April 2026)

**Feature:** Optional `pip install alteryx-diff[llm]` — LangGraph-based documentation generation
**Researched:** 2026-04-02
**Overall confidence:** MEDIUM — GitHub issues and official docs consulted; rate limit numbers
and token estimates should be re-verified at provider dashboards before finalizing architecture.

---

## Critical Pitfalls (will block shipping if not addressed)

### C1 — Import guard missing: LLM code bleeds into non-LLM code path

**Problem:** Any top-level import of `langchain`, `langgraph`, or `openai` in a module that
is imported unconditionally will crash the 252-test suite (and the packaged .exe) when
`[llm]` extras are not installed.

**Symptom:** `ModuleNotFoundError: No module named 'langchain_core'` on pytest collection,
not at feature invocation — the whole test run fails before any test runs.

**Prevention:** Gate every LLM import behind a `TYPE_CHECKING` block or inside a function
body. Use a single `_llm_available(): bool` guard at the feature entry point. Never import
LLM deps at module level.

```python
# BAD — crashes entire test suite when langchain is absent
from langchain_core.language_models import BaseChatModel

# GOOD
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

def get_llm() -> "BaseChatModel":
    from langchain_core.language_models import BaseChatModel  # lazy
    ...
```

**Phase to address:** Phase 1 (skeleton / optional extras wiring)

---

### C2 — asyncio.run() inside a FastAPI async endpoint raises RuntimeError

**Problem:** FastAPI endpoints run inside uvicorn's already-running event loop. Calling
`asyncio.run(graph.ainvoke(...))` inside `async def` raises
`RuntimeError: asyncio.run() cannot be called from a running event loop`.

**Symptom:** 500 error on first LLM generation request; traceback points at `asyncio.run`.
Works fine in a standalone script but fails inside the server.

**Prevention:** Use `await graph.ainvoke(...)` directly. Never wrap async LangGraph calls in
`asyncio.run()` inside FastAPI endpoints. If a sync wrapper is unavoidable, use
`asyncio.to_thread()` to offload it to a thread pool.

**Note on nest_asyncio:** `nest_asyncio.apply()` patches asyncio to allow nested event loops
and is a known workaround for this error. It is not a production pattern — it has performance
implications and masks real design problems. Do not ship it.

**Phase to address:** Phase 1 (FastAPI endpoint scaffolding)

Sources: [langchain#8494](https://github.com/langchain-ai/langchain/issues/8494),
[nest-asyncio PyPI](https://pypi.org/project/nest-asyncio/)

---

### C3 — PyInstaller .exe cannot load post-install LLM deps

**Problem:** Because [llm] deps are NOT bundled in the .exe, users who install them
post-deployment via `pip install alteryx-diff[llm]` cannot use them from the GUI. The .exe
only knows about modules frozen at build time; it cannot load from the system Python.

**Symptom:** `ModuleNotFoundError` at runtime inside the frozen .exe even though the package
is installed in the system Python. No workaround — this is a fundamental PyInstaller
constraint.

**Prevention:** LLM features must either (a) run out-of-process (subprocess calling a system
Python with `sys.executable -m alteryx_diff.llm_runner`) or (b) be documented as CLI-only,
not available from the GUI .exe. Architecture decision required before any LLM UI is built.

**Phase to address:** Phase 1 (architecture decision — subprocess vs. in-process)

---

### C4 — Context window overflow raises unhandled HTTP 400 from provider API

**Problem:** LangChain does NOT silently truncate when context length is exceeded. It
propagates the provider's error: OpenAI raises `openai.BadRequestError` (code
`context_length_exceeded`), Ollama raises a `ValueError` from llama.cpp. Without a
pre-flight guard, the user sees a raw traceback.

**Symptom:** Unhandled exception; generation fails with no user-friendly message.

**Prevention:** Estimate tokens before calling the model. If over ~75% of the context window,
truncate or refuse with a clear error. Hard-limit the input: refuse to proceed and surface a
friendly message rather than letting the API call fail.

**Phase to address:** Phase 2 (prompt construction)

Sources: [langchain#12264](https://github.com/langchain-ai/langchain/issues/12264),
[langchain#15333](https://github.com/langchain-ai/langchain/issues/15333)

---

## PyInstaller Integration Pitfalls

### PI1 — `lark` is a hidden import required by LangChain

LangChain uses `lark` for query parsers. PyInstaller misses it because it is loaded
dynamically via `importlib`. If LangChain is ever bundled inside the .exe, add `'lark'` to
`hiddenimports` in `app.spec`. This is one of the most frequently reported LangChain +
PyInstaller failures.

Source: [langchain#9264](https://github.com/langchain-ai/langchain/issues/9264),
[lark#1319](https://github.com/lark-parser/lark/issues/1319)

### PI2 — LangChain data files (prompt templates, grammars) not bundled

LangChain loads prompt templates and grammar files from its package data at runtime via
`importlib.resources`. PyInstaller does not pick these up automatically. If bundling any
LangChain code, add to `app.spec`:

```python
import langchain, langchain_core
datas=[
    ...
    (langchain.__path__[0], 'langchain'),
    (langchain_core.__path__[0], 'langchain_core'),
]
```

Source: [langchain#15386](https://github.com/langchain-ai/langchain/issues/15386)

### PI3 — Pydantic v2 required; no v1 shim available

LangChain >=0.3 requires Pydantic v2 and removed the `langchain_core.pydantic_v1`
compatibility shim. The existing codebase uses Pydantic v2 (via FastAPI) — this is
compatible. Verify no transitive dependency pulls in a Pydantic v1 constraint when adding
`[llm]` extras. Pin `pydantic>=2.0` explicitly in the `[llm]` optional group.

Source: [langchain#27687](https://github.com/langchain-ai/langchain/issues/27687)

### PI4 — httpx version conflict between openai SDK and existing dependency

The core project already pins `httpx>=0.27`. The `openai` SDK and `langchain-openai` also
pin `httpx` requirements. Verify there is no upper-bound conflict. Run `uv tree --extra llm`
to inspect the resolved dependency tree before merging.

### PI5 — Recommended strategy: do NOT bundle LLM deps in the .exe

LangChain + OpenAI + LangGraph add approximately 200-400 MB to the bundle. This is
impractical for a desktop .exe. Ship the .exe without them. Document that LLM features
require a system Python with `pip install alteryx-diff[llm]` and are invoked via CLI
(`acd generate-docs workflow.yxmd`). The GUI can invoke `subprocess.run([sys.executable,
"-m", "alteryx_diff.llm_runner", ...])` to delegate LLM work to the unbundled interpreter.

**Known hidden imports if LLM code is ever bundled (reference only):**
```
lark
langchain_core
langchain_community
langchain_openai
langchain_ollama
langgraph
openai
anthropic
tiktoken
tiktoken_ext
tiktoken_ext.openai_public
```

Use `collect_submodules('langchain_core')` in the spec file to catch dynamically loaded
components. Expect the resulting .exe to be 400-600 MB larger.

---

## Async / Event Loop Pitfalls

### AE1 — asyncio.run() in async context is always wrong

Pattern to AVOID:
```python
@app.post("/generate-docs")
async def generate_docs(req: Request):
    result = asyncio.run(graph.ainvoke(state))  # WRONG — RuntimeError
```

Correct pattern:
```python
@app.post("/generate-docs")
async def generate_docs(req: Request):
    result = await graph.ainvoke(state)  # CORRECT
```

Sources: [langchain#8494](https://github.com/langchain-ai/langchain/issues/8494),
[Medium — event loop fix](https://medium.com/@vyshali.enukonda/how-to-get-around-runtimeerror-this-event-loop-is-already-running-3f26f67e762e)

### AE2 — LangGraph sync .invoke() blocks the uvicorn event loop

Calling synchronous `.invoke()` (not `.ainvoke()`) inside an async FastAPI endpoint blocks
the entire event loop for the duration of the LLM call (30-120 seconds for local models).
All other requests queue behind it. Prevention: always use `.ainvoke()` from async context,
or offload to `asyncio.to_thread(graph.invoke, state)`.

### AE3 — SSE streaming + LangGraph: use astream_events()

The existing project already uses `sse-starlette` for streaming. For streaming LLM output
to the frontend, use LangGraph's `.astream_events()` method and yield SSE chunks. Do not
buffer the entire response — for long workflows this kills UX (no feedback for 30+ seconds).

### AE4 — Ollama HTTP calls must use the async client

`langchain-ollama` uses `httpx` for HTTP transport (same library as the existing project).
Ensure the async `httpx.AsyncClient` is used (the `.ainvoke()` code path), not the sync
client, to avoid blocking the event loop during model inference.

---

## Ollama Pitfalls

### OL1 — Cold start: 13-60 seconds on first request

Model loading time by size and hardware class:
- `llama3.2:3b` (~2 GB): approximately 13-20 seconds
- `qwen2.5-coder:7b` (~4.7 GB): approximately 20-35 seconds
- `qwen2.5-coder:14b` (~9 GB): approximately 29-45 seconds

**UX pattern used by other tools:** Pre-warm by sending a minimal prompt ("hi") when the
user first enables LLM features, before the actual generation request. Show a
"Loading local model..." progress indicator. Ollama's `keep_alive` parameter (default:
5 minutes) keeps the model in VRAM between calls — set it to 10m for the session.

**Implementation:** Send `POST http://localhost:11434/api/generate` with
`{"model": model_name, "prompt": "", "keep_alive": "10m"}` on feature activation.

Sources: [Ollama FAQ](https://docs.ollama.com/faq),
[Medium — preloading LLMs into RAM](https://medium.com/@rafal.kedziorski/speed-up-ollama-how-i-preload-local-llms-into-ram-for-lightning-fast-ai-experiments-291a832edd48)

### OL2 — with_structured_output compatibility is model-dependent

Ollama supports JSON schema enforcement (added late 2024), but enforcement quality varies:
- **Well-supported:** `llama3.2`, `qwen2.5-coder`, `mistral`, `phi-3`
- **Problematic:** `gpt-oss` variants, some heavily quantized builds
- **Failure mode:** Model returns extra prose, unclosed JSON, or schema violations — the
  Pydantic validator raises `ValidationError` or `OutputParserException`

**Prevention:** Always wrap `.with_structured_output()` calls in try/except catching
`ValidationError` and `OutputParserException`. On failure, retry once with an explicit JSON
repair prompt. Use `method="json_schema"` (not `"function_calling"`) for Ollama — it is
more reliable for local models.

Sources: [Ollama structured outputs docs](https://docs.ollama.com/capabilities/structured-outputs),
[langchain#25343](https://github.com/langchain-ai/langchain/issues/25343),
[Ollama#8063](https://github.com/ollama/ollama/issues/8063)

### OL3 — Ollama not running: connection refused

If Ollama is not started, `langchain-ollama` raises `httpx.ConnectError: Connection refused`.
**Prevention:** Before any Ollama call, ping `GET http://localhost:11434/api/tags`. If it
fails, return a clear user error: "Ollama is not running. Start it with `ollama serve`." Do
not propagate the raw httpx exception.

### OL4 — Default Ollama context window may be too small

Some Ollama model builds default to `num_ctx=2048` or `num_ctx=4096` regardless of the
model's theoretical maximum. A 50-tool workflow prompt (~12,000 tokens) will silently
overflow a 4K context window, producing garbage output without raising an exception.

**Prevention:** Always explicitly set `num_ctx` when constructing the Ollama client:
`ChatOllama(model="qwen2.5-coder:7b", num_ctx=32768)`. Verify the model's actual context
window with `ollama show <model>` before hardcoding.

### OL5 — Air-gapped / offline use case

This is a core requirement (Ollama local model must work without internet). Ensure LLM
config surfaces a clear "offline mode" that shows only Ollama as the available provider.
OpenAI and Anthropic calls should fail fast with a user-readable message in offline mode,
not hang on connection timeout.

---

## Context Window Pitfalls

### CW1 — Provider raises HTTP 400, not a Python exception

OpenAI raises `openai.BadRequestError` (code: `context_length_exceeded`) at 128K tokens.
Anthropic raises `anthropic.BadRequestError`. Ollama raises a `ValueError` from llama.cpp.
None silently truncate. LangChain propagates these as the underlying provider exception or
as `langchain_core.exceptions.OutputParserException`.

Sources: [langchain#12264](https://github.com/langchain-ai/langchain/issues/12264),
[langchain#15333](https://github.com/langchain-ai/langchain/issues/15333)

### CW2 — Token estimation for a 50-tool Alteryx workflow

A 50-tool workflow, when serialized with annotations (node names, types, connections, config
snippets), is approximately:
- Raw XML: 40,000-80,000 characters
- After normalization to a prompt-friendly dict: ~8,000-15,000 tokens (input)
- Expected LLM annotations per tool: ~50-100 tokens each = 2,500-5,000 tokens (output)
- **Total per generation:** ~10,500-20,000 tokens

This fits within GPT-4o-mini (128K) and Claude Haiku (200K) context windows with room to
spare. Ollama models with 4K-8K context windows (default for some quantized builds) will
overflow. Verify and set `num_ctx` explicitly for Ollama (see OL4).

### CW3 — LangGraph checkpointer + conversation history overflow

If LangGraph is configured with a persistent checkpointer and conversation history grows
across multiple invocations, the accumulated messages can eventually overflow the context
window. For a stateless "generate docs" use case (no multi-turn), use a fresh graph state
per request — do not persist conversation history between generation runs.

Source: [langgraph#3717](https://github.com/langchain-ai/langgraph/issues/3717)

### CW4 — Guard pattern (recommended implementation)

```python
import tiktoken

def estimate_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

MAX_INPUT_FRACTION = 0.75  # leave 25% headroom for output

def guard_context(prompt: str, model_context_window: int) -> None:
    tokens = estimate_tokens(prompt)
    max_tokens = int(model_context_window * MAX_INPUT_FRACTION)
    if tokens > max_tokens:
        raise ValueError(
            f"Workflow too large for context window: {tokens} tokens "
            f"(max {max_tokens}). Try a smaller workflow subset."
        )
```

For Ollama models, read `num_ctx` from the model config and pass it into this guard.

---

## Security Pitfalls

### SEC1 — API keys in environment variables: acceptable, but use keyring

Storing `ALTERYX_DIFF_LLM_API_KEY` as an environment variable is standard practice and is
what OpenAI, Anthropic, and LangChain all recommend. The key is NOT embedded in the .exe
binary.

The project already uses `keyring` for secure credential storage (Windows Credential
Manager / macOS Keychain). Extend this pattern to LLM API keys rather than relying solely on
plain environment variables. Reading from keyring first, falling back to the env var, is the
recommended pattern for desktop tools.

**Prompt injection risk:** LLM agents can be socially engineered to reveal environment
variables. For this project (no agent loop, no user-controlled input in the prompt, workflow
XML is a trusted local file), this risk is LOW.

### SEC2 — Supply chain risk: litellm PyPI packages compromised (March 2026)

A supply-chain attack compromised `litellm` PyPI packages in March 2026 (TeamPCP campaign).
The malicious package delivers a credential stealer. If the project uses `litellm` as a
routing layer, pin exact versions and use hash verification in `uv.lock`. Prefer direct
`langchain-openai` and `langchain-anthropic` over `litellm` as the dependency.

Sources: [Sonatype — compromised litellm](https://www.sonatype.com/blog/compromised-litellm-pypi-package-delivers-multi-stage-credential-stealer),
[Help Net Security](https://www.helpnetsecurity.com/2026/03/25/teampcp-supply-chain-attacks/)

### SEC3 — PyInstaller .exe does not expose API keys in binary

PyInstaller does not embed runtime environment variables from the build machine into the .exe.
Keys set at runtime (via env var or keyring) are safe from binary inspection. Do not hardcode
API keys in source or pass them as build arguments (they would appear in CI logs).

### SEC4 — Governance label must be enforced in the renderer, not the LLM output

The "AI-Assisted — Review Before Use" watermark must be applied by the Jinja2 renderer, not
generated by the LLM (which could omit or alter it). This makes the label mandatory and
tamper-resistant. For enterprise users, AI-generated documentation without this label may be
treated as human-reviewed content, creating a compliance risk.

---

## Testing Pitfalls

### TP1 — Real API calls in tests break CI and cost money

Any test that instantiates a real `ChatOpenAI` or `ChatAnthropic` will fail in CI (no API
key) and incur real costs locally. Use `FakeListChatModel` for unit tests.

```python
from langchain_community.chat_models.fake import FakeListChatModel

fake_llm = FakeListChatModel(responses=['{"summary": "Test annotation", "tool_type": "Filter"}'])
node = AnnotateToolNode(llm=fake_llm)
result = node.run(state)
assert result["annotations"]["tool_1"]["summary"] == "Test annotation"
```

Source: [LangChain fake model API](https://api.python.langchain.com/en/latest/community/chat_models/langchain_community.chat_models.fake.FakeListChatModel.html),
[How to mock LangChain in unit tests](https://medium.com/@matgmc/how-to-properly-mock-langchain-llm-execution-in-unit-tests-python-76efe1b8707e)

### TP2 — FakeListChatModel may not support with_structured_output cleanly

If `with_structured_output` is used and the fake model returns a plain string, the Pydantic
validator will raise. Pre-serialize fake responses as JSON matching the schema, or mock the
structured output wrapper directly:

```python
from unittest.mock import patch, MagicMock

with patch("alteryx_diff.llm.nodes.get_llm") as mock_get_llm:
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = ToolAnnotation(
        summary="test", tool_type="Filter"
    )
    mock_get_llm.return_value = mock_llm
    result = annotate_tool(state)
```

### TP3 — Tests must pass when [llm] extras are NOT installed

The 252 existing tests must continue to pass in the base environment. Add a pytest marker
and skip condition for all LLM-dependent tests:

```python
import pytest

try:
    import langchain_core
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

llm_only = pytest.mark.skipif(not HAS_LLM, reason="[llm] extras not installed")

@llm_only
def test_annotation_node(): ...
```

Run the test suite in two separate CI environments: (1) base deps only, (2) base + llm
extras. Both must pass with exit code 0.

### TP4 — LangGraph node tests do not need the graph runtime

Test individual node functions directly — pass a state dict, assert the returned dict. Do
not invoke the full graph for unit tests; the graph runner adds complexity without exercising
node logic. Reserve full-graph integration tests for a separate CI job with LLM mocked.

Source: [Unit Testing LangGraph — Medium](https://medium.com/@anirudhsharmakr76/unit-testing-langgraph-testing-nodes-and-flow-paths-the-right-way-34c81b445cd6)

### TP5 — RAGAS faithfulness is not usable without a retrieval system

RAGAS `faithfulness` metric requires a retrieved context list, a question, and an answer. It
is designed for RAG pipelines with a retrieval step. For this project (no vector store, no
retrieval — just workflow XML as context), RAGAS is the wrong tool.

**Alternative:** Use DeepEval's `HallucinationMetric` or a simple LLM-as-judge pattern
where a second LLM call checks whether each annotation claim is supported by the workflow
XML. This is cheaper, simpler, and does not require a retrieval infrastructure.

Source: [RAGAS faithfulness docs](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)

---

## uv / Optional Deps Pitfalls

### UV1 — uv sync resolves all optional deps even when not requested

There is an active bug (reported through early 2026) where `uv sync` resolves optional
dependency groups even when `--extra` is not specified. This can cause unnecessary build
failures for C-extension packages (e.g., `tiktoken`) on machines without the Rust toolchain.

**Prevention:** Pin exact wheels for `tiktoken` in `uv.lock`. If tiktoken fails to build
from source on a target platform, use `--only-binary tiktoken` or provide pre-built wheels.

Sources: [uv#6729](https://github.com/astral-sh/uv/issues/6729),
[uv#17903](https://github.com/astral-sh/uv/issues/17903)

### UV2 — tiktoken requires Rust (Cargo) at build time from source

`tiktoken` has a Rust extension. If installed from source (not from a wheel), it requires
the Rust toolchain. Windows CI runners may not have Rust installed by default. Ensure the
`uv.lock` pins a pre-built wheel for `win-amd64`, or add a Rust install step to the CI
workflow before `uv sync --extra llm`.

### UV3 — Circular optional dependency resolution crash

`uv sync` can crash with a `ResolutionError` on circular optional dependencies when packages
are installed from GitHub sources. Ensure all `[llm]` deps are pinned to PyPI releases, not
git sources.

Source: [uv#14193](https://github.com/astral-sh/uv/issues/14193)

---

## Cost and Rate Limit Estimates

### Token Cost Table

| Workflow Size | Model | Est. Input Tokens | Est. Output Tokens | Est. Cost (USD) |
|--------------|-------|-------------------|-------------------|----------------|
| 10 tools | GPT-4o-mini | ~2,500 | ~600 | ~$0.0004 |
| 10 tools | Claude Haiku 4.5 | ~2,500 | ~600 | ~$0.006 |
| 50 tools | GPT-4o-mini | ~12,000 | ~3,000 | ~$0.0020 |
| 50 tools | Claude Haiku 4.5 | ~12,000 | ~3,000 | ~$0.027 |
| 100 tools | GPT-4o-mini | ~22,000 | ~5,500 | ~$0.0036 |
| 100 tools | Claude Haiku 4.5 | ~22,000 | ~5,500 | ~$0.050 |
| 50 tools (Ollama local) | qwen2.5-coder:7b | ~12,000 | ~3,000 | $0.00 |

**Pricing basis (April 2026):**
- GPT-4o-mini: $0.15/1M input, $0.60/1M output
- Claude Haiku 4.5: $1.00/1M input, $5.00/1M output

**Key finding:** GPT-4o-mini is 5-8x cheaper than Claude Haiku for this output-heavy use
case. Ollama is free but adds 13-60 second cold-start latency and GPU/RAM requirements.

Sources: [AI API pricing comparison 2026](https://intuitionlabs.ai/articles/ai-api-pricing-comparison-grok-gemini-openai-claude),
[Claude API pricing](https://platform.claude.com/docs/en/about-claude/pricing)

---

## Rate Limits

### RL1 — OpenAI GPT-4o-mini (Tier 1 baseline)

- RPM: 500 requests/minute
- TPM: 200,000 tokens/minute
- TPD: 2,000,000 tokens/day

At 50 tools with ~15,000 tokens per generation, a single run consumes negligible TPD quota.
Rate limits are not a concern for single-user desktop use. For parallel per-tool annotation
(50 calls at ~300 tokens each), 50 RPM is well within the 500 RPM limit.

**Recommendation:** Add a semaphore cap of ~20 concurrent calls as a precaution. Implement
exponential backoff with jitter on 429 responses.

Source: [OpenAI rate limits 2026](https://inference.net/content/openai-rate-limits-guide/)

### RL2 — Anthropic Claude Haiku 4.5 (Tier 1 — binding constraint)

- RPM: 50 requests/minute (Tier 1, after first $5 spend)
- ITPM: 50,000 input tokens/minute
- Free tier: 5 RPM (too slow for any parallel annotation)

**Critical:** At Tier 1, 50 parallel calls to Anthropic would saturate the 50 RPM limit in
a single burst. This is the binding constraint for Claude-based annotation.

**Prevention:** Cap concurrent Anthropic calls at ≤5 via a semaphore. Implement exponential
backoff on 429. Surface a UX note: "Claude annotation may be slower due to API rate limits."

Source: [Anthropic rate limits](https://platform.claude.com/docs/en/api/rate-limits),
[Claude API quota tiers 2026](https://www.aifreeapi.com/en/posts/claude-api-quota-tiers-limits)

### RL3 — Recommended concurrency pattern

```python
import asyncio
from typing import Any

# Safe for Anthropic Tier 1; increase for OpenAI or Ollama
MAX_CONCURRENT_LLM_CALLS = 5

async def annotate_all_tools(
    tools: list[dict[str, Any]], llm: Any
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)

    async def annotate_one(tool: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await annotate_tool_node(tool, llm)

    return await asyncio.gather(*[annotate_one(t) for t in tools])
```

---

## Phase-Specific Warnings Summary

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Optional extras wiring | LLM import bleeds into base (C1) | Lazy imports, TYPE_CHECKING guard |
| FastAPI endpoint scaffolding | asyncio.run() in async context (C2, AE1) | Always await ainvoke() |
| PyInstaller .exe build | LLM deps not bundleable (C3, PI5) | Subprocess / CLI-only LLM path |
| Prompt construction | Context overflow (C4, CW2) | tiktoken guard before API call |
| Ollama integration | Cold start UX, structured output (OL1, OL2) | Pre-warm + retry on ValidationError |
| Ollama context window | Default num_ctx too small (OL4) | Explicitly set num_ctx=32768+ |
| Test suite | Tests fail without [llm] extras (TP3) | skipif marker + dual CI environment |
| Cost and concurrency | Anthropic Tier 1 RPM limit (RL2) | Semaphore cap at 5 concurrent calls |
| uv extras | tiktoken Rust build failure (UV2) | Pin wheel, --only-binary tiktoken |
| Supply chain | litellm compromise (SEC2) | Avoid litellm; use direct provider SDKs |

---

## LLM Integration Sources

- [langchain#9264 — lark hidden import](https://github.com/langchain-ai/langchain/issues/9264)
- [langchain#15386 — langchain not PyInstaller friendly](https://github.com/langchain-ai/langchain/issues/15386)
- [langchain#8494 — asyncio.run() in event loop](https://github.com/langchain-ai/langchain/issues/8494)
- [langchain#12264 — token limit exception](https://github.com/langchain-ai/langchain/issues/12264)
- [langchain#15333 — context length exceeded error](https://github.com/langchain-ai/langchain/issues/15333)
- [langchain#27687 — Pydantic v2 shim removal](https://github.com/langchain-ai/langchain/issues/27687)
- [langchain#25343 — structured output nested schemas](https://github.com/langchain-ai/langchain/issues/25343)
- [langgraph#3717 — context overflow from checkpointer](https://github.com/langchain-ai/langgraph/issues/3717)
- [Ollama structured outputs docs](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama#8063 — structured output not respected](https://github.com/ollama/ollama/issues/8063)
- [Ollama FAQ — keep_alive](https://docs.ollama.com/faq)
- [uv#6729 — sync resolves all extras](https://github.com/astral-sh/uv/issues/6729)
- [uv#17903 — builds extra packages when not requested](https://github.com/astral-sh/uv/issues/17903)
- [uv#14193 — circular optional deps crash](https://github.com/astral-sh/uv/issues/14193)
- [RAGAS faithfulness metric](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)
- [FakeListChatModel API](https://api.python.langchain.com/en/latest/community/chat_models/langchain_community.chat_models.fake.FakeListChatModel.html)
- [Unit testing LangGraph nodes — Medium](https://medium.com/@anirudhsharmakr76/unit-testing-langgraph-testing-nodes-and-flow-paths-the-right-way-34c81b445cd6)
- [How to mock LangChain in unit tests — Medium](https://medium.com/@matgmc/how-to-properly-mock-langchain-llm-execution-in-unit-tests-python-76efe1b8707e)
- [Anthropic rate limits](https://platform.claude.com/docs/en/api/rate-limits)
- [Claude API quota tiers 2026](https://www.aifreeapi.com/en/posts/claude-api-quota-tiers-limits)
- [OpenAI rate limits 2026](https://inference.net/content/openai-rate-limits-guide/)
- [AI API pricing comparison 2026](https://intuitionlabs.ai/articles/ai-api-pricing-comparison-grok-gemini-openai-claude)
- [Sonatype — litellm supply chain attack March 2026](https://www.sonatype.com/blog/compromised-litellm-pypi-package-delivers-multi-stage-credential-stealer)
- [nest-asyncio PyPI](https://pypi.org/project/nest-asyncio/)
- [PyInstaller when things go wrong](https://pyinstaller.org/en/stable/when-things-go-wrong.html)
- [Medium — preloading Ollama LLMs into RAM](https://medium.com/@rafal.kedziorski/speed-up-ollama-how-i-preload-local-llms-into-ram-for-lightning-fast-ai-experiments-291a832edd48)

---
*LLM documentation feature pitfalls research for: Alteryx Canvas Diff v1.2*
*Researched: 2026-04-02*
