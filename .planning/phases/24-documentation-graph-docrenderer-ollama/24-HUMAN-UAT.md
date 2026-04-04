---
status: partial
phase: 24-documentation-graph-docrenderer-ollama
source: [24-VERIFICATION.md]
started: 2026-04-04T23:55:00Z
updated: 2026-04-04T23:55:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Ollama Live End-to-End Run (EVAL-01)
expected: Pipeline completes and prints workflow name and intent. No cloud API key or network error. No `APIConnectionError` or `AuthenticationError`.
result: [pending]

**How to test:** Start a local Ollama instance with any model (e.g. `llama3` or `mistral`), then run:
```bash
uv run python -c "
import asyncio
from langchain_ollama import ChatOllama
from alteryx_diff.llm.doc_graph import generate_documentation

llm = ChatOllama(model='llama3')
ctx = {
    'workflow_name': 'TestWF',
    'tool_count': 1,
    'tools': [{'tool_id': 1, 'tool_type': 'DbFileInput', 'config': {}}],
    'connections': [],
    'topology': {'connections': [], 'source_tools': [1], 'sink_tools': [1], 'branch_points': []}
}
doc = asyncio.run(generate_documentation(ctx, llm))
print(doc.workflow_name)
print(doc.intent[:80])
"
```

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
