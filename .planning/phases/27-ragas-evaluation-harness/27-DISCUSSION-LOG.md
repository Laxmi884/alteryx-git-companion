# Phase 27: RAGAS Evaluation Harness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-06
**Phase:** 27-ragas-evaluation-harness
**Mode:** discuss
**Areas discussed:** Sample fixtures, LLM provider setup, Metrics scope

---

## Areas Discussed

### Sample fixtures
| Decision | Choice | Reason |
|----------|--------|--------|
| Fixture format | In-memory XML bytes | Matches existing test pattern (tests/fixtures/pipeline.py); no committed .yxmd files |
| Ground truth | Not required | faithfulness + answer_relevancy work without it; avoids maintenance burden |

### LLM provider setup
| Decision | Choice | Reason |
|----------|--------|--------|
| Provider config | Single ACD_LLM_MODEL env var | Consistent with Phase 25 CLI pattern; drives both documentation LLM and RAGAS critic |

### Metrics scope
| Decision | Choice | Reason |
|----------|--------|--------|
| Initial selection | Full RAGAS suite | User's first choice |
| Revised to | faithfulness + answer_relevancy | context_recall/precision require ground_truth AND are designed for fuzzy RAG retrieval — wrong tool for a deterministic ContextBuilder |

---

## Key Discussion: Metrics Revision

User raised two important architectural concerns:

1. **Context size**: Full suite with ground_truth would inflate LLM context per sample.

2. **Architecture mismatch**: In production the LLM never sees raw XML — it sees ContextBuilder output (structured JSON). The eval must mirror this. Raw XML must NOT be `retrieved_contexts`.

Resolution agreed: `faithfulness` + `answer_relevancy` only. `context_recall`/`context_precision` dropped — they fit fuzzy RAG retrieval systems, not a deterministic structured context builder. `retrieved_contexts` = ContextBuilder output (serialized to strings), not raw XML.

---

## Corrections Made

### Metrics scope
- **Original selection:** Full RAGAS suite (faithfulness + answer_relevancy + context_recall + context_precision)
- **User correction:** Drop context_recall/precision after discussion
- **Reason:** Wrong metric type for deterministic ContextBuilder; would require ground_truth authoring; architecture mismatch (context_recall/precision assume fuzzy retrieval)
