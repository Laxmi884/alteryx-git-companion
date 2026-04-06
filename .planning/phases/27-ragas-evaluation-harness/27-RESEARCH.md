# Phase 27: RAGAS Evaluation Harness - Research

**Researched:** 2026-04-06
**Domain:** RAGAS evaluation library, LangchainLLMWrapper, eval harness scripting
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Reference workflows are defined as in-memory XML bytes (same pattern as `tests/fixtures/pipeline.py`) — no `.yxmd` files committed to disk. 2-3 minimal but representative workflow bytes defined in the script or a `tests/eval/fixtures.py` module.

**D-02:** No `ground_truth` strings required. `faithfulness` and `answer_relevancy` both operate without ground truth — this avoids fixture maintenance overhead and matches the architecture (ContextBuilder is deterministic, not a fuzzy retriever).

**D-03:** `retrieved_contexts` = ContextBuilder output (the structured JSON dict serialized to strings), NOT raw XML. The eval mirrors production exactly: `.yxmd bytes → parser → WorkflowDoc → ContextBuilder → context dict → LLM`. Raw XML never crosses the LLM boundary in eval any more than it does in production.

**D-04:** Two env vars, same `provider:model_name` format as Phase 25:
- `ACD_LLM_MODEL` — the documentation-generation LLM (subject of evaluation)
- `RAGAS_CRITIC_MODEL` — the RAGAS critic LLM (faithfulness/relevancy judge); defaults to `ACD_LLM_MODEL` if not set

**D-05:** Script prints a clear error and exits non-zero if `ACD_LLM_MODEL` is not set, with an example. Includes a note that `RAGAS_CRITIC_MODEL` is optional but recommended for independent evaluation.

**D-06:** `faithfulness` + `answer_relevancy` only. `context_recall` and `context_precision` are dropped — they require ground truth and are designed for fuzzy RAG retrieval systems, not a deterministic context builder.

**D-07:** Passing threshold is `>=0.8` for faithfulness. Script prints per-sample scores and a summary. Does NOT fail the process on threshold miss — it reports the score and the threshold, leaving the developer to act.

**D-08:** Entry point: `python tests/eval/ragas_eval.py` — standalone script, not a pytest file. Can be run without `pytest` installed in the eval environment.

**D-09:** Script has a docstring (or inline README block) documenting: how to run, what `ACD_LLM_MODEL` to set, what the `>=0.8` threshold means, and how to add a new sample.

### Claude's Discretion

- RAGAS v0.4 Dataset/EvaluationDataset API specifics (exact class names and evaluate() call signature)
- Whether the RAGAS critic LLM is injected via `langchain_openai`/`langchain_ollama` wrappers or RAGAS's own LLM config
- Output format (table vs plain print vs JSON)
- Whether fixtures live in `ragas_eval.py` directly or split into `tests/eval/fixtures.py`
- Whether `require_llm_deps()` is called at script top or inside `if __name__ == "__main__"`

### Deferred Ideas (OUT OF SCOPE)

- `context_recall` / `context_precision` — requires ground_truth; wrong tool for deterministic ContextBuilder
- CI integration — running ragas_eval.py in GitHub Actions would require a live LLM
- Regression thresholds as test failures — making `pytest` fail if faithfulness drops below 0.8
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-02 | Developer can run RAGAS faithfulness evaluation (`tests/eval/ragas_eval.py`) to measure LLM output grounding quality against `ContextBuilder` output | RAGAS v0.4 `evaluate()` API verified; `EvaluationDataset.from_list()` and `LangchainLLMWrapper` patterns confirmed; full pipeline wiring from bytes → context → doc → eval traced |
</phase_requirements>

---

## Summary

Phase 27 delivers a single standalone script at `tests/eval/ragas_eval.py`. The script runs 2-3 reference workflows through the full production pipeline (bytes → parser → WorkflowDoc → ContextBuilder → generate_documentation) and feeds the output into RAGAS's `evaluate()` to score `faithfulness` and `answer_relevancy`. No new source files in `src/`. No new dependencies needed — `ragas~=0.4` is already in `pyproject.toml [llm]` extras.

The key integration challenge is wiring two separate LLMs: the documentation LLM under test (`ACD_LLM_MODEL`) and the RAGAS critic that judges faithfulness (`RAGAS_CRITIC_MODEL`, optional). RAGAS v0.4 uses `LangchainLLMWrapper` to accept any `BaseChatModel`, so the same `_resolve_llm` logic from `cli.py` can be extracted/replicated in the eval script. All LLM config comes from env vars — no interactive prompts.

`ContextBuilder.build_from_workflow()` returns a dict. RAGAS `retrieved_contexts` expects a `list[str]`. The bridge is to serialize each value of the context dict to a JSON string, turning the structured context into a list of retrievable string chunks — this mirrors what an LLM would receive in production as grounding context.

**Primary recommendation:** One implementation plan. Write `tests/eval/ragas_eval.py` containing: (1) inline fixture bytes, (2) a helper that replicates `_resolve_llm` for env-var-based LLM construction, (3) the eval loop building `EvaluationDataset` and calling `evaluate()`, (4) a score printer with threshold comparison. The script is self-contained — no imports from `tests/` or pytest machinery.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ragas | ~0.4 (0.4.3 current) | RAG evaluation metrics (faithfulness, answer_relevancy) | Already pinned in pyproject.toml [llm]; authoritative RAG eval framework |
| langchain-openai | ~0.3 | Build ChatOpenAI/OpenRouter LLM for critic | Already pinned in pyproject.toml [llm] |
| langchain-ollama | ~1.0 | Build ChatOllama LLM for local critic | Already pinned in pyproject.toml [llm] |

[VERIFIED: pip index versions ragas — latest stable is 0.4.3]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio | stdlib | Bridge async `generate_documentation()` to sync script | Always — same pattern as CLI |
| tempfile | stdlib | Write XML bytes to temp file for `parse_one()` | Required — `parse_one()` takes a Path, not bytes |
| json | stdlib | Serialize context dict values to strings for `retrieved_contexts` | Always |

**Installation:** No new dependencies. Everything needed is in:
```bash
pip install 'alteryx-diff[llm]'
```

---

## Architecture Patterns

### Recommended Project Structure
```
tests/
└── eval/
    ├── __init__.py        # empty, makes tests/eval a package (optional but clean)
    └── ragas_eval.py      # standalone eval script (the only required file)
```

Fixtures may be colocated in `ragas_eval.py` or split to `tests/eval/fixtures.py` — Claude's discretion.

### Pattern 1: Bytes → WorkflowDoc → Context (Production Pipeline Replication)

**What:** Write XML bytes to a named temp file, parse with `parse_one()`, build context with `ContextBuilder.build_from_workflow()`
**When to use:** For every eval sample — mirrors production path exactly

```python
# Source: inspection of src/alteryx_diff/parser.py + tests/fixtures/pipeline.py
import tempfile
import pathlib
from alteryx_diff.parser import parse_one
from alteryx_diff.llm.context_builder import ContextBuilder

def workflow_bytes_to_context(xml_bytes: bytes, stem: str) -> dict:
    with tempfile.NamedTemporaryFile(
        suffix=".yxmd",
        prefix=f"{stem}_",
        delete=False,
    ) as f:
        f.write(xml_bytes)
        tmp_path = pathlib.Path(f.name)
    doc = parse_one(tmp_path)
    tmp_path.unlink(missing_ok=True)
    return ContextBuilder.build_from_workflow(doc)
```

Note: `parse_one()` requires a real filesystem path because lxml uses `etree.parse(str(path), ...)` internally — `io.BytesIO` cannot substitute. Temp file is the correct approach. [VERIFIED: src/alteryx_diff/parser.py lines 131-132]

### Pattern 2: Context Dict → RAGAS `retrieved_contexts` Serialization

**What:** Convert the ContextBuilder dict to a `list[str]` for RAGAS `SingleTurnSample`
**When to use:** Always — RAGAS expects a list of string chunks, not a dict

```python
# Source: inspection of ragas dataset_schema.py via GitHub raw + search results
import json

def context_to_strings(context_dict: dict) -> list[str]:
    """Serialize ContextBuilder output values as string chunks for RAGAS."""
    return [json.dumps({k: v}, ensure_ascii=False) for k, v in context_dict.items()]
```

This produces a list like:
```
['{"workflow_name": "SalesFilter"}', '{"tool_count": 3}', '{"tools": [...]}', ...]
```

The LLM sees the same structured information it receives in production, chunked per key for RAGAS faithfulness claim extraction. [ASSUMED — specific serialization strategy; the important constraint from D-03 is that ContextBuilder output is the source, not raw XML]

### Pattern 3: RAGAS v0.4 Evaluation Call

**What:** Build `EvaluationDataset` from sample list, inject critic LLM via `LangchainLLMWrapper`, call `evaluate()`
**When to use:** Core eval loop

```python
# Source: ragas evaluation.py (GitHub), dataset_schema.py (GitHub), WebSearch verified
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness, AnswerRelevancy

samples = [
    {
        "user_input": "Document this Alteryx workflow.",
        "response": doc.model_dump_json(),          # WorkflowDocumentation output
        "retrieved_contexts": context_to_strings(context),  # ContextBuilder output
    },
    # ... more samples
]

dataset = EvaluationDataset.from_list(samples)
evaluator_llm = LangchainLLMWrapper(critic_llm)  # BaseChatModel wrapped for RAGAS

result = evaluate(
    dataset=dataset,
    metrics=[Faithfulness(), AnswerRelevancy()],
    llm=evaluator_llm,
)
```

[VERIFIED: evaluate() signature from raw.githubusercontent.com/explodinggradients/ragas]
[VERIFIED: EvaluationDataset.from_list() and SingleTurnSample fields from same source]
[CITED: https://github.com/explodinggradients/ragas/blob/main/src/ragas/evaluation.py]

### Pattern 4: LLM Construction from Env Vars

**What:** Replicate `_resolve_llm()` logic from `cli.py` for the eval script — no import from cli module (to avoid typer dependency)
**When to use:** At script startup; builds both `generator_llm` and `critic_llm`

```python
# Source: inspection of src/alteryx_diff/cli.py lines 244-283
import os, sys

def _build_llm_from_env(env_var: str, *, required: bool = True):
    model_str = os.environ.get(env_var)
    if not model_str:
        if required:
            print(
                f"Error: {env_var} is not set.\n"
                "Example: export ACD_LLM_MODEL=openrouter:mistralai/mistral-7b-instruct",
                file=sys.stderr,
            )
            sys.exit(1)
        return None
    provider, _, model_name = model_str.partition(":")
    if not model_name:
        print(f"Error: {env_var} must be 'provider:model_name', got {model_str!r}", file=sys.stderr)
        sys.exit(1)
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model_name, temperature=0)
    if provider in ("openai", "openrouter"):
        from langchain_openai import ChatOpenAI
        kwargs = {"model": model_name, "temperature": 0}
        if provider == "openrouter":
            kwargs["base_url"] = "https://openrouter.ai/api/v1"
            kwargs["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")
        else:
            kwargs["api_key"] = os.environ.get("OPENAI_API_KEY", "")
        return ChatOpenAI(**kwargs)
    print(f"Error: Unknown provider {provider!r}. Use: ollama, openai, openrouter", file=sys.stderr)
    sys.exit(1)
```

[VERIFIED: src/alteryx_diff/cli.py lines 244-283]

### Pattern 5: Score Printing with Threshold Reporting

**What:** Print per-sample scores and a summary line with threshold comparison
**When to use:** After `evaluate()` completes

```python
# Source: [ASSUMED] — ragas EvaluationResult returns a dict-like result;
# score access pattern inferred from ragas docs search results
result_df = result.to_pandas()  # EvaluationResult has to_pandas()
for i, row in result_df.iterrows():
    faithfulness = row.get("faithfulness", float("nan"))
    relevancy = row.get("answer_relevancy", float("nan"))
    print(f"  Sample {i+1}: faithfulness={faithfulness:.3f}  answer_relevancy={relevancy:.3f}")

mean_faithfulness = result_df["faithfulness"].mean()
threshold = 0.8
status = "PASS" if mean_faithfulness >= threshold else "BELOW THRESHOLD"
print(f"\nMean faithfulness: {mean_faithfulness:.3f}  (threshold: >={threshold})  [{status}]")
```

### Anti-Patterns to Avoid

- **Importing from `alteryx_diff.cli` in the eval script:** `cli.py` pulls in `typer`; importing it creates a hard typer dependency in the eval path. Copy the `_build_llm_from_env` logic inline or into a minimal helper.
- **Passing raw XML as `retrieved_contexts`:** Violates D-03; the eval must reflect the production LLM boundary where ContextBuilder output is the context, not raw XML.
- **Using `pytest.tmp_path` for temp files:** The script is not a pytest file (D-08). Use `tempfile.NamedTemporaryFile` or `tempfile.mkstemp` instead.
- **Calling `asyncio.run()` at module level:** Wrap it inside `if __name__ == "__main__"` to avoid issues if the file is imported.
- **Forgetting to delete temp files:** Each sample's temp `.yxmd` file should be cleaned up after `parse_one()` returns.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Faithfulness scoring | Custom LLM judge prompts | `ragas.metrics.Faithfulness` | RAGAS handles claim extraction, NLI scoring, aggregation — multi-step pipeline behind one class |
| Answer relevancy scoring | Cosine similarity of questions | `ragas.metrics.AnswerRelevancy` | RAGAS generates synthetic questions from answer and computes mean cosine similarity — non-trivial to replicate correctly |
| LLM critic injection | Custom wrapper | `ragas.llms.LangchainLLMWrapper` | RAGAS's official integration point; wraps any `BaseChatModel` |

**Key insight:** RAGAS faithfulness involves LLM-based claim extraction followed by NLI classification — not a single prompt. The library handles async execution, retries, and aggregation internally.

---

## Common Pitfalls

### Pitfall 1: `retrieved_contexts` Must Be a `list[str]`, Not a Dict

**What goes wrong:** Passing `ContextBuilder.build_from_workflow()` output directly as `retrieved_contexts` — it's a dict, not a list of strings.
**Why it happens:** RAGAS `SingleTurnSample.retrieved_contexts` is typed as `list[str]`.
**How to avoid:** Serialize the context dict values to strings via `json.dumps()` before putting them in `retrieved_contexts`.
**Warning signs:** Pydantic `ValidationError` from `SingleTurnSample` on dataset construction.

### Pitfall 2: `parse_one()` Requires a Filesystem Path

**What goes wrong:** Attempting to pass XML bytes directly or use `io.BytesIO` with `parse_one()`.
**Why it happens:** The parser calls `etree.parse(str(path), ...)` — an lxml restriction.
**How to avoid:** Write bytes to a `tempfile.NamedTemporaryFile`, call `parse_one()`, then delete the temp file.
**Warning signs:** `TypeError` or `AttributeError` on `parse_one()` call.

### Pitfall 3: Importing `cli._resolve_llm` Pulls in Typer

**What goes wrong:** Importing from `alteryx_diff.cli` in the eval script causes `typer` to be loaded; the eval environment may not have typer installed, or the import triggers CLI app initialization.
**Why it happens:** `cli.py` is an application entry point, not a library module.
**How to avoid:** Inline the provider-dispatch logic in `ragas_eval.py` or in a minimal `_llm.py` helper in `tests/eval/`.
**Warning signs:** `ImportError: No module named 'typer'` or unexpected click/typer side effects.

### Pitfall 4: `AnswerRelevancy` Requires `user_input` Field

**What goes wrong:** Building `SingleTurnSample` with only `response` and `retrieved_contexts` and then using `AnswerRelevancy`.
**Why it happens:** `AnswerRelevancy` generates synthetic questions from the response and compares them to `user_input` (cosine similarity). Missing `user_input` causes a runtime error or NaN scores.
**How to avoid:** Always include `user_input` in each sample dict. A fixed prompt like `"Document this Alteryx workflow."` is valid — it acts as the question the documentation answers.
**Warning signs:** NaN scores for `answer_relevancy` or KeyError during metric computation.

### Pitfall 5: `require_llm_deps()` Placement

**What goes wrong:** Calling `require_llm_deps()` at module top level in the eval script causes an `ImportError` when the script is imported by pytest collection without `[llm]` extras installed.
**Why it happens:** Module-level code runs at import time.
**How to avoid:** Call `require_llm_deps()` inside `if __name__ == "__main__"` (or in the `main()` function), not at module top level. The script should be importable without raising errors even without `[llm]` extras — the error should only trigger when the script is actually run.
**Warning signs:** Test collection failures for the entire `tests/` directory.

### Pitfall 6: RAGAS v0.3 vs v0.4 API Incompatibility

**What goes wrong:** Using the v0.3 `Dataset` HuggingFace-based API (e.g., `datasets.Dataset.from_dict(...)`) instead of v0.4's `EvaluationDataset.from_list(...)`.
**Why it happens:** Most web articles document the v0.1-0.3 API.
**How to avoid:** Use `from ragas.dataset_schema import EvaluationDataset` with `.from_list()`. The v0.4 API does not require the `datasets` (HuggingFace) library.
**Warning signs:** `ImportError: No module named 'datasets'` or deprecation warnings about `Dataset`.

---

## Code Examples

### Minimal Complete Eval Flow

```python
# Source: composite of verified patterns above
import asyncio, json, os, sys, tempfile, pathlib

def _build_llm(env_var: str, required: bool = True):
    # ... (Pattern 4 above)
    pass

def bytes_to_context(xml_bytes: bytes, stem: str) -> dict:
    # ... (Pattern 1 above)
    pass

def main():
    from alteryx_diff.llm import require_llm_deps
    require_llm_deps()

    from alteryx_diff.llm.doc_graph import generate_documentation
    from ragas import evaluate
    from ragas.dataset_schema import EvaluationDataset
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import AnswerRelevancy, Faithfulness

    generator_llm = _build_llm("ACD_LLM_MODEL", required=True)
    critic_base = _build_llm("RAGAS_CRITIC_MODEL", required=False) or generator_llm
    critic_llm = LangchainLLMWrapper(critic_base)

    samples = []
    for name, xml_bytes in FIXTURES:
        context = bytes_to_context(xml_bytes, name)
        doc = asyncio.run(generate_documentation(context, generator_llm))
        samples.append({
            "user_input": "Document this Alteryx workflow.",
            "response": doc.model_dump_json(),
            "retrieved_contexts": [json.dumps({k: v}) for k, v in context.items()],
        })

    dataset = EvaluationDataset.from_list(samples)
    result = evaluate(
        dataset=dataset,
        metrics=[Faithfulness(), AnswerRelevancy()],
        llm=critic_llm,
    )
    # ... print scores

if __name__ == "__main__":
    main()
```

[VERIFIED: evaluate() signature — github.com/explodinggradients/ragas]
[VERIFIED: EvaluationDataset.from_list(), SingleTurnSample fields — github.com/explodinggradients/ragas]
[VERIFIED: LangchainLLMWrapper import path — ragas.llms — confirmed via WebSearch]
[VERIFIED: generate_documentation() async signature — src/alteryx_diff/llm/doc_graph.py]
[VERIFIED: require_llm_deps() — src/alteryx_diff/llm/__init__.py]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datasets.Dataset.from_dict()` (HuggingFace dependency) | `EvaluationDataset.from_list()` (no HuggingFace required) | RAGAS v0.2 → v0.4 | No `datasets` package needed; cleaner API |
| Direct metric classes with `.score()` | `evaluate()` function with metric list | RAGAS v0.1 | Single call, async, supports batch |

**Deprecated/outdated:**
- `from datasets import Dataset` pattern for RAGAS: replaced by `EvaluationDataset.from_list()` in v0.4
- `ground_truth` field: still supported but not required for `faithfulness` or `answer_relevancy`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Serializing context dict as `[json.dumps({k:v}) for k,v in context.items()]` is the correct way to produce `retrieved_contexts` from ContextBuilder output | Architecture Patterns (Pattern 2) | Could affect what RAGAS faithfulness claims are grounded against; alternative: one flat JSON string for the whole dict. Either produces valid input — the question is granularity. |
| A2 | `result.to_pandas()` is the correct way to access per-sample scores from `EvaluationResult` in RAGAS v0.4 | Pattern 5 | If wrong, score access fails at print time; fallback: `result` dict-like access or `result.scores` |
| A3 | `AnswerRelevancy` does not require `retrieved_contexts` in v0.4 (only `user_input` and `response` are needed) | Common Pitfalls (Pitfall 4) | Low risk — if contexts are also included it is harmless; if required and missing it would show NaN |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|---------|
| Python | Script runtime | ✓ | 3.12.4 | — |
| pip | Dependency install | ✓ | 25.1.1 | — |
| ragas | Eval metrics | Not in current env | 0.4.3 available via pip | `pip install 'alteryx-diff[llm]'` |
| langchain-openai | OpenRouter/OpenAI critic | Not in current env | Available via [llm] extras | Same install |
| langchain-ollama | Ollama critic | Not in current env | Available via [llm] extras | Same install |

**Missing dependencies with no fallback:** None — all are installable via `pip install 'alteryx-diff[llm]'`

**Missing dependencies with fallback:** N/A

---

## Validation Architecture

> `workflow.nyquist_validation` is absent from config.json — treated as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/eval/ -x` (when eval tests exist) |
| Full suite command | `pytest tests/ -x` |

**Note:** Per D-08, `ragas_eval.py` is a standalone script, NOT a pytest file. However, a thin smoke-test `tests/eval/test_ragas_eval_smoke.py` that verifies the script is importable and `_build_llm_from_env` exits correctly on missing env var would be appropriate and fits within the pytest framework.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVAL-02 | `python tests/eval/ragas_eval.py` runs without errors and prints faithfulness score | smoke (manual run) | `python tests/eval/ragas_eval.py` (requires live LLM) | ❌ Wave 0 |
| EVAL-02 | Script exits non-zero with clear message when `ACD_LLM_MODEL` unset | unit | `pytest tests/eval/test_ragas_eval_smoke.py::test_missing_env_exits -x` | ❌ Wave 0 |
| EVAL-02 | `retrieved_contexts` is ContextBuilder output (not raw XML) | unit | `pytest tests/eval/test_ragas_eval_smoke.py::test_context_is_contextbuilder_output -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/eval/ -x` (unit tests only — no live LLM needed)
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`; live eval run with `ACD_LLM_MODEL` set (manual)

### Wave 0 Gaps
- [ ] `tests/eval/__init__.py` — makes eval a package; prevents pytest collection issues
- [ ] `tests/eval/test_ragas_eval_smoke.py` — smoke tests for env-var guard and import safety

---

## Security Domain

> `security_enforcement` is absent from config — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | XML bytes are parsed by lxml (existing parser); RAGAS inputs are internal data |
| V6 Cryptography | no | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leakage in error output | Information Disclosure | Never print env var values in error messages — only print that the var is unset |
| Temp file cleanup failure leaving XML on disk | Information Disclosure | Use try/finally or context manager to guarantee `tmp_path.unlink()` even on exception |

---

## Sources

### Primary (HIGH confidence)
- `src/alteryx_diff/llm/context_builder.py` — ContextBuilder.build_from_workflow() return shape and types
- `src/alteryx_diff/llm/doc_graph.py` — generate_documentation() async signature
- `src/alteryx_diff/llm/__init__.py` — require_llm_deps() behavior
- `src/alteryx_diff/cli.py` lines 244-283 — _resolve_llm() provider dispatch pattern
- `tests/fixtures/pipeline.py` — in-memory XML bytes fixture pattern
- `tests/llm/conftest.py` — sample_context fixture shape
- `pyproject.toml` — ragas~=0.4 confirmed in [llm] extras; no new deps needed
- [https://github.com/explodinggradients/ragas/blob/main/src/ragas/evaluation.py](https://github.com/explodinggradients/ragas/blob/main/src/ragas/evaluation.py) — evaluate() signature
- [https://github.com/explodinggradients/ragas/blob/main/src/ragas/dataset_schema.py](https://github.com/explodinggradients/ragas/blob/main/src/ragas/dataset_schema.py) — EvaluationDataset.from_list(), SingleTurnSample fields

### Secondary (MEDIUM confidence)
- WebSearch results confirming LangchainLLMWrapper usage pattern, AnswerRelevancy no-ground-truth behavior, EvaluationDataset.from_list() API
- pip index versions ragas — 0.4.3 confirmed as latest stable [VERIFIED: 2026-04-06]

### Tertiary (LOW confidence)
- `result.to_pandas()` score access — inferred from RAGAS v0.3 patterns and API shape; marked [ASSUMED] in log above

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already pinned in pyproject.toml; versions verified via pip registry
- Architecture patterns: HIGH — all key APIs traced to actual source files in this repo or ragas GitHub
- Pitfalls: HIGH — derived from direct source inspection (parse_one requires Path, dict not list[str], etc.)

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (ragas 0.4.x is stable; API unlikely to change within 30 days)
