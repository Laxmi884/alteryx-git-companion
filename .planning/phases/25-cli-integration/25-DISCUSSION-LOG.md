# Phase 25: CLI Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 25-cli-integration
**Areas discussed:** LLM provider flags, `--doc` flag scope, `document` output path, progress UX

---

## LLM Provider Flags

| Option | Description | Selected |
|--------|-------------|----------|
| `--model provider:model_name` | Single flag parses prefix to build BaseChatModel | ✓ |
| Separate `--ollama` flag | Explicit flag for Ollama, `--model` for name | |
| Env vars only | No CLI flags, shell env only | |

**User's choice:** `--model provider:model_name` with `--base-url` override + API keys from env vars + `config_store` fallback for persistent config

**Notes:** User raised Phase 26 companion app use case — app users won't set shell env vars. Resolved by reading from `config_store` (written by Phase 26 settings panel) and keyring (for API keys), matching the existing Phase 16 PAT storage pattern. Env file explicitly rejected in favour of `config_store` + keyring.

---

## `--doc` Flag Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Change narrative only | `build_from_diff` context, AI summary of what changed | ✓ |
| Head workflow doc only | `build_from_workflow` on workflow_b | |
| Both narrative + doc | Two LLM calls | |

**User's choice:** Change narrative only

**Notes:** Uses `ContextBuilder.build_from_diff()` context shape — requires a new `generate_change_narrative()` function separate from the existing `generate_documentation()` which is designed for workflow context.

---

## `document` Output Path

| Option | Description | Selected |
|--------|-------------|----------|
| `{stem}-doc.md` in CWD | Writes to current working directory | |
| `{stem}-doc.md` next to input | Writes alongside the .yxmd file | ✓ |
| Stdout | Prints Markdown to stdout | |

**User's choice:** `{stem}-doc.md` next to the input `.yxmd` file

**Notes:** User clarified they want the doc saved in the workflow's own directory (the project directory the user has selected), not wherever the CLI is invoked from. Consistent with the companion app's project-directory model.

---

## Progress UX

| Option | Description | Selected |
|--------|-------------|----------|
| Spinner | Rich spinner on stderr, matches existing diff command | ✓ |
| Stage-by-stage progress | Print each LangGraph node completion | |
| Silent | No terminal output | |

**User's choice:** Spinner — `Generating documentation...` on stderr, suppressed by `--quiet`

---

## Claude's Discretion

- `generate_change_narrative()` output model design
- Prompt wording for change narrative nodes
- `--model` string parsing implementation
- HTML template changes for narrative section placement
- Test structure for new CLI commands

## Deferred Ideas

- Streaming token output to terminal
- Stage-by-stage LangGraph node progress
- Both narrative + workflow doc in `--doc`
