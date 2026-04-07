"""RAGAS Evaluation Harness for Alteryx Diff LLM Documentation.

Measures faithfulness and answer relevancy of LLM-generated workflow
documentation against ContextBuilder output using RAGAS v0.4.

Usage:
    # Option A — .env file (recommended, no exporting needed):
    #   Create tests/eval/.env with:
    #     ACD_LLM_MODEL=openrouter:anthropic/claude-sonnet-4-5
    #     RAGAS_CRITIC_MODEL=openrouter:openai/gpt-4o
    #     OPENROUTER_API_KEY=your-key
    #   Then just: python tests/eval/ragas_eval.py

    # Option B — environment variables:
    export ACD_LLM_MODEL=openrouter:anthropic/claude-sonnet-4-5
    export RAGAS_CRITIC_MODEL=openrouter:openai/gpt-4o
    export OPENROUTER_API_KEY=your-key
    python tests/eval/ragas_eval.py

Threshold: faithfulness >= 0.8 is considered passing.
Scores are reported per-sample and as a mean. The script does NOT
fail on threshold miss — it reports and the developer decides.

Adding samples:
    1. Define a new XML bytes constant in the FIXTURES list below
    2. Give it a descriptive stem name
    3. Re-run the script

Requires: pip install 'alteryx-diff[llm]'
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys
import tempfile

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAITHFULNESS_THRESHOLD = 0.8

# ---------------------------------------------------------------------------
# Fixture XML bytes (inline — no .yxmd files committed to disk, per D-01)
# ToolIDs 2701-2705 allocated for Phase 27 eval. No collision with other fixtures.
# ---------------------------------------------------------------------------

EVAL_WORKFLOW_FILTER: bytes = b"""<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2020.1">
  <Nodes>
    <Node ToolID="2701">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput">
        <Position x="60" y="100"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <Alias>Revenue Input</Alias>
        </Configuration>
      </Properties>
    </Node>
    <Node ToolID="2702">
      <GuiSettings Plugin="AlteryxBasePluginsGui.Filter">
        <Position x="160" y="100"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <Expression>Revenue > 1000</Expression>
        </Configuration>
      </Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection>
      <Origin ToolID="2701" Connection="Output"/>
      <Destination ToolID="2702" Connection="Input"/>
    </Connection>
  </Connections>
</AlteryxDocument>"""

EVAL_WORKFLOW_JOIN: bytes = b"""<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2020.1">
  <Nodes>
    <Node ToolID="2703">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput">
        <Position x="60" y="80"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <Alias>Left Input</Alias>
        </Configuration>
      </Properties>
    </Node>
    <Node ToolID="2704">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput">
        <Position x="60" y="160"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <Alias>Right Input</Alias>
        </Configuration>
      </Properties>
    </Node>
    <Node ToolID="2705">
      <GuiSettings Plugin="AlteryxBasePluginsGui.Join">
        <Position x="200" y="120"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <JoinByMode>JoinByPosition</JoinByMode>
        </Configuration>
      </Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection>
      <Origin ToolID="2703" Connection="Output"/>
      <Destination ToolID="2705" Connection="Left"/>
    </Connection>
    <Connection>
      <Origin ToolID="2704" Connection="Output"/>
      <Destination ToolID="2705" Connection="Right"/>
    </Connection>
  </Connections>
</AlteryxDocument>"""

# List of (stem_name, xml_bytes) tuples — add new entries here to expand eval set
FIXTURES: list[tuple[str, bytes]] = [
    ("filter_workflow", EVAL_WORKFLOW_FILTER),
    ("join_workflow", EVAL_WORKFLOW_JOIN),
]

# ---------------------------------------------------------------------------
# Helper functions (exported for smoke testing)
# ---------------------------------------------------------------------------


def _build_llm_from_env(env_var: str, *, required: bool = True):  # type: ignore[return]
    """Build a BaseChatModel from an environment variable holding 'provider:model_name'.

    Args:
        env_var: Name of the environment variable to read (e.g. "ACD_LLM_MODEL").
        required: If True, exit(1) when the variable is unset. If False, return None.

    Returns:
        A BaseChatModel instance, or None if not required and unset.

    Security:
        Never prints the VALUE of the env var — only the variable name and examples
        (per T-27-01).
    """
    model_str = os.environ.get(env_var)

    if not model_str:
        if not required:
            return None
        print(
            f"Error: {env_var} is not set.\n"
            "Example: export ACD_LLM_MODEL=openrouter:mistralai/mistral-7b-instruct\n\n"
            "RAGAS_CRITIC_MODEL is optional but recommended for independent evaluation.",
            file=sys.stderr,
        )
        sys.exit(1)

    provider, _, model_name = model_str.partition(":")
    if not model_name:
        print(
            f"Error: {env_var} must be in 'provider:model_name' format.\n"
            f"Got an invalid format. Valid providers: ollama, openai, openrouter.\n"
            "Example: export ACD_LLM_MODEL=openrouter:mistralai/mistral-7b-instruct",
            file=sys.stderr,
        )
        sys.exit(1)

    # Provider dispatch — replicate cli.py _resolve_llm WITHOUT importing from cli (Pitfall 3)
    if provider == "ollama":
        from langchain_ollama import ChatOllama  # type: ignore[import-not-found]

        return ChatOllama(model=model_name, temperature=0)

    if provider == "openai":
        from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

        return ChatOpenAI(
            model=model_name,
            temperature=0,
            api_key=os.environ.get("OPENAI_API_KEY", ""),
        )

    if provider == "openrouter":
        from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

        return ChatOpenAI(
            model=model_name,
            temperature=0,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )

    print(
        f"Error: Unknown provider in {env_var}. "
        "Valid providers: ollama, openai, openrouter.",
        file=sys.stderr,
    )
    sys.exit(1)


def _workflow_bytes_to_context(xml_bytes: bytes, stem: str) -> dict:
    """Parse XML bytes through parse_one + ContextBuilder without LLM.

    Writes bytes to a named temp file (deleted in finally block), calls parse_one,
    then ContextBuilder.build_from_workflow.

    Args:
        xml_bytes: Raw .yxmd XML content.
        stem: Short descriptive name used as temp file prefix.

    Returns:
        Context dict with keys: workflow_name, tool_count, tools, connections, topology.

    Security:
        Temp file is always deleted, even on exception (per T-27-02).
    """
    from alteryx_diff.llm.context_builder import ContextBuilder
    from alteryx_diff.parser import parse_one

    tmp_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".yxmd", prefix=f"{stem}_", delete=False
        ) as f:
            f.write(xml_bytes)
            tmp_path = pathlib.Path(f.name)

        doc = parse_one(tmp_path)
        return ContextBuilder.build_from_workflow(doc)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def _context_to_strings(context_dict: dict) -> list[str]:
    """Convert a context dict to a list of JSON string chunks (one per key).

    Each element is a JSON-serialized {key: value} dict. This produces
    fine-grained retrieved_contexts for RAGAS evaluation (per D-03).

    Args:
        context_dict: The context dict from ContextBuilder.build_from_workflow.

    Returns:
        List of JSON strings, one per key-value pair.
    """
    return [json.dumps({k: v}, ensure_ascii=False) for k, v in context_dict.items()]


# ---------------------------------------------------------------------------
# Main evaluation entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the RAGAS evaluation harness.

    All LLM and RAGAS imports happen inside this function so the module is
    importable without [llm] extras installed (per Pitfall 5).

    Loads tests/eval/.env automatically if python-dotenv is installed, so you
    don't need to export variables manually before each run.
    """
    try:
        from dotenv import load_dotenv

        # Search order: tests/eval/.env → project root .env
        _here = pathlib.Path(__file__).parent
        _root = _here.parent.parent
        for _env_file in (_here / ".env", _root / ".env"):
            if _env_file.exists():
                load_dotenv(_env_file)
                print(f"Loaded env from {_env_file}")
                break
    except ImportError:
        pass  # python-dotenv not installed — fall back to shell env vars

    from alteryx_diff.llm import require_llm_deps

    require_llm_deps()

    from alteryx_diff.llm.doc_graph import generate_documentation
    from ragas import evaluate  # type: ignore[import-not-found]
    from ragas.dataset_schema import EvaluationDataset  # type: ignore[import-not-found]
    from ragas.llms import LangchainLLMWrapper  # type: ignore[import-not-found]
    from ragas.metrics import AnswerRelevancy, Faithfulness  # type: ignore[import-not-found]

    # Build LLMs (per D-04: separate generator and critic roles)
    generator_llm = _build_llm_from_env("ACD_LLM_MODEL", required=True)
    critic_base = _build_llm_from_env("RAGAS_CRITIC_MODEL", required=False) or generator_llm
    critic_llm = LangchainLLMWrapper(critic_base)

    print("=== RAGAS Evaluation Harness ===\n")
    print(f"Generator LLM: {os.environ['ACD_LLM_MODEL']}")
    critic_model = os.environ.get("RAGAS_CRITIC_MODEL", "(same as generator)")
    print(f"Critic LLM:    {critic_model}")
    print(f"Samples:       {len(FIXTURES)}")
    print(f"Threshold:     faithfulness >= {FAITHFULNESS_THRESHOLD}\n")

    # Build samples — run each fixture through the full pipeline
    samples = []
    for stem, xml_bytes in FIXTURES:
        print(f"Processing: {stem}...")
        context = _workflow_bytes_to_context(xml_bytes, stem)
        doc = asyncio.run(generate_documentation(context, generator_llm))
        samples.append(
            {
                "user_input": "Document this Alteryx workflow.",
                "response": doc.model_dump_json(),
                "retrieved_contexts": _context_to_strings(context),
            }
        )

    print(f"\nRunning RAGAS evaluation ({len(samples)} samples)...\n")

    # Evaluate faithfulness + answer_relevancy (per D-06)
    dataset = EvaluationDataset.from_list(samples)
    result = evaluate(
        dataset=dataset,
        metrics=[Faithfulness(), AnswerRelevancy()],
        llm=critic_llm,
    )

    # Print per-sample and summary results (per D-07)
    result_df = result.to_pandas()
    print("--- Per-Sample Results ---")
    for i, row in result_df.iterrows():
        faithfulness = row.get("faithfulness", float("nan"))
        relevancy = row.get("answer_relevancy", float("nan"))
        print(f"  Sample {i+1}: faithfulness={faithfulness:.3f}  answer_relevancy={relevancy:.3f}")

    mean_faith = result_df["faithfulness"].mean()
    mean_rel = result_df["answer_relevancy"].mean()
    status = "PASS" if mean_faith >= FAITHFULNESS_THRESHOLD else "BELOW THRESHOLD"
    print(f"\n--- Summary ---")
    print(
        f"Mean faithfulness:      {mean_faith:.3f}  "
        f"(threshold: >={FAITHFULNESS_THRESHOLD})  [{status}]"
    )
    print(f"Mean answer_relevancy:  {mean_rel:.3f}")

    # Save results to tests/eval/results/<timestamp>.json
    import datetime

    results_dir = pathlib.Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    results_path = results_dir / f"{ts}.json"
    results_payload = {
        "timestamp": ts,
        "generator": os.environ.get("ACD_LLM_MODEL", "unknown"),
        "critic": os.environ.get("RAGAS_CRITIC_MODEL", "(same as generator)"),
        "threshold": FAITHFULNESS_THRESHOLD,
        "status": status,
        "summary": {"faithfulness": round(mean_faith, 4), "answer_relevancy": round(mean_rel, 4)},
        "samples": [
            {
                "sample": i + 1,
                "faithfulness": round(row.get("faithfulness", float("nan")), 4),
                "answer_relevancy": round(row.get("answer_relevancy", float("nan")), 4),
            }
            for i, row in result_df.iterrows()
        ],
    }
    results_path.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    print(f"\nResults saved → {results_path}")


if __name__ == "__main__":
    main()
