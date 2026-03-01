# Alteryx Canvas Diff (ACD)

## What This Is

A CLI tool that compares two Alteryx workflow files (.yxmd) and generates a structured HTML diff report — showing exactly what changed at the tool, configuration, and connection level. Built for analytics developers and governance teams who need to understand what changed between workflow versions without reading XML.

Currently targeting an internal analytics team. Architecture is designed API-first so it can evolve into a SaaS service (Alteryx Server integration, Git PR comments) without rearchitecting.

## Core Value

Accurate detection of functional changes — zero false positives from layout noise, zero missed configuration changes.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Accept two .yxmd files as CLI input and validate XML structure
- [ ] Parse workflow into internal object model (ToolID, type, position, config, connections)
- [ ] Normalize XML to eliminate false positives (whitespace, attribute ordering, non-functional metadata, GUIDs/timestamps)
- [ ] Ignore position-only changes by default; expose `--include-positions` flag for opt-in
- [ ] Detect tool additions, removals, and modifications
- [ ] Detect configuration-level changes (expressions, filters, field selections, parameter values)
- [ ] Detect connection additions, removals, and rewirings
- [ ] Generate HTML report with color-coded summary and expandable per-tool detail sections
- [ ] Embed interactive visual graph (canvas-style nodes + directed edges) in HTML report
- [ ] Color-code graph: green=added, red=removed, yellow=modified, blue=connection changes
- [ ] Graph uses X/Y canvas coordinates for layout (not for diff detection)
- [ ] Support hover/click on graph nodes to display configuration diff inline
- [ ] Handle malformed or corrupted XML gracefully with descriptive error messages
- [ ] Perform under 5 seconds for workflows up to 500 tools

### Out of Scope

- Real-time overlay inside Alteryx Designer — Phase 2+
- Macro recursion parsing — Phase 2
- CI/CD automation platform — Phase 3
- Enterprise security framework — Phase 2+
- REST API service layer — Phase 3 (architecture supports it, but not built in Phase 1)
- Web upload UI — Phase 3

## Context

- Alteryx workflows are XML files (.yxmd). Developers version-control them in Git but have no visual diff capability — only raw XML diffs or manual canvas comparison.
- Key XML noise sources in Alteryx: position drift (tools nudged on canvas), attribute reordering, auto-generated GUIDs and timestamps injected on save. Normalization layer must handle all three.
- Positions (X/Y) have dual roles: input for visual graph layout (always used) but excluded from diff detection by default. This is a deliberate design decision to keep diffs signal-only.
- Current team pain: manual side-by-side comparison before workflow promotions — recurring and time-consuming.
- SaaS ambition: If internal pilot succeeds, evolve into an API service. Alteryx Server can call `POST /diff` on workflow promotion events; Git hooks can post diff reports as PR comments. CLI prototype maps directly to this — same pipeline, different entry point.
- Primary users: Analytics developers running local comparisons; governance teams reviewing diff reports for audit.

## Constraints

- **Tech Stack**: Python 3.10+, lxml or xml.etree, hashlib, difflib, networkx, pyvis or D3.js, Jinja2 — as defined in PRD
- **Performance**: Report generation under 5 seconds for workflows up to 500 tools
- **Deployment**: CLI-first for Phase 1; no server infrastructure required
- **Output**: Single self-contained HTML file + optional JSON summary; viewable in standard browser
- **Compatibility**: Must handle workflows with ToolID regeneration (secondary matching by type + position as fallback)

## Key Decisions

| Decision | Rationale | Outcome |
|---|---|---|
| Ignore position changes by default | Position drift is the #1 source of false positives; functional diff is the core value | — Pending |
| X/Y used for graph layout, not diffing | Positions serve layout rendering but not change detection — dual-role clarified explicitly | — Pending |
| API-first architecture target | Alteryx Server integration + Git hook layer both become thin wrappers over the same parse→diff→render pipeline | — Pending |
| CLI prototype first | Validates the diff engine and report quality before investing in API infrastructure | — Pending |
| Secondary matching (type + position) | ToolIDs can regenerate on Alteryx save; pure ID matching would cause false add/remove pairs | — Pending |

---
*Last updated: 2026-02-28 after initialization*
