"""Workflow Documentation Evaluation Harness.

Two-layer evaluation replacing the previous RAGAS-based approach:

  Layer 1 — Structural checks (deterministic, free, instant):
    • tool_id_coverage    — every tool ID from the context appears in tool_notes
                            (no phantoms)
    • tool_type_coverage  — every tool type from the context appears in tool_notes
    • fields_populated    — intent, data_flow, and risks are non-empty

  Layer 2 — G-Eval LLM-as-judge (5 domain-specific criteria, scored 0-10 each):
    • tool_coverage       — tool_notes accurately describe each tool's specific role
    • data_flow_accuracy  — data_flow correctly traces the workflow source→sink
    • grounding           — no claims contradict the actual workflow configuration
    • completeness        — all sections contain workflow-specific, non-generic content
    • no_hallucination    — no invented tool IDs, types, field names, or config values

Pass threshold: mean G-Eval score >= 7.0 / 10
(mirrors the old faithfulness >= 0.8 bar).

Usage:
    # With .env file (recommended):
    #   Create tests/eval/.env with ACD_LLM_MODEL, RAGAS_CRITIC_MODEL,
    #   OPENROUTER_API_KEY
    python tests/eval/workflow_doc_eval.py

    # Evaluate a specific workflow file:
    python tests/eval/workflow_doc_eval.py --workflow /path/to/file.yxmd

    # Score an existing doc without regenerating:
    python tests/eval/workflow_doc_eval.py --workflow file.yxmd --doc file.md

Requires: pip install 'alteryx-diff[llm]'
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import re
import sys
import tempfile

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GEVAL_THRESHOLD = 7.0  # out of 10

# ---------------------------------------------------------------------------
# Fixture XML bytes — same workflows as ragas_eval.py for comparability.
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

FIXTURES: list[tuple[str, bytes]] = [
    ("filter_workflow", EVAL_WORKFLOW_FILTER),
    ("join_workflow", EVAL_WORKFLOW_JOIN),
]

# ---------------------------------------------------------------------------
# G-Eval criterion definitions
# Each value is the scoring rubric shown to the judge LLM.
# ---------------------------------------------------------------------------

_GEVAL_CRITERIA: dict[str, str] = {
    "tool_coverage": (
        "Evaluate the `tool_notes` section of the documentation.\n"
        "Score 0-10:\n"
        "  10 — Every tool has a note; each note accurately reflects the tool's actual"
        " configuration (e.g., Filter note mentions the exact expression).\n"
        "   7 — All tools covered but notes are generic (e.g., 'filters data' without"
        " the actual condition).\n"
        "   4 — Some tools missing from tool_notes, or tool types are wrong.\n"
        "   0 — Major tools absent or descriptions completely incorrect."
    ),
    "data_flow_accuracy": (
        "Evaluate the `data_flow` section of the documentation.\n"
        "Score 0-10:\n"
        "  10 — Data flow correctly names source tools, intermediate tools, and sink"
        " tools in the right order, matching the connections in the context.\n"
        "   7 — Correct direction but vague about intermediate steps or tool types.\n"
        "   4 — Partially correct; some connections described in wrong order or wrong"
        " direction.\n"
        "   0 — Flow described backwards, key tools omitted, or describes a different"
        " workflow entirely."
    ),
    "grounding": (
        "Check whether specific claims in the documentation are consistent with the"
        " workflow context.\n"
        "Score 0-10:\n"
        "  10 — All specific values (filter expressions, join modes, aliases) exactly"
        " match the context.\n"
        "   7 — Minor imprecision (paraphrased expression) but no outright"
        " contradictions.\n"
        "   4 — One or more specific values contradict the actual context.\n"
        "   0 — Multiple contradictions with the workflow configuration."
    ),
    "completeness": (
        "Evaluate whether every section (intent, data_flow, tool_notes, risks) contains"
        " content specific to this particular workflow — not generic filler.\n"
        "Score 0-10:\n"
        "  10 — All sections are specific to this workflow; nothing reads as a"
        " placeholder.\n"
        "   7 — Most sections specific; one section has generic content.\n"
        "   4 — Multiple sections are generic ('This workflow processes data.').\n"
        "   0 — Documentation is almost entirely generic or templated."
    ),
    "no_hallucination": (
        "Check whether the documentation invents facts not present in the workflow"
        " context (tool IDs, tool types, field names, expressions,"
        " connection aliases).\n"
        "Score 0-10:\n"
        "  10 — No invented specifics; only tool IDs, types, and config values from"
        " the context are used.\n"
        "   7 — Minor embellishments about what standard tool types do, but no invented"
        " specifics.\n"
        "   4 — Some invented specifics (wrong tool IDs, fabricated field names).\n"
        "   0 — Major hallucinations: invented tools, wrong workflow name, fabricated"
        " configurations."
    ),
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _build_llm_from_env(env_var: str, *, required: bool = True):  # type: ignore[return]
    """Build a BaseChatModel from an environment variable holding 'provider:model_name'.

    Security: never prints the VALUE of the env var — only the variable name.
    """
    model_str = os.environ.get(env_var)

    if not model_str:
        if not required:
            return None
        print(
            f"Error: {env_var} is not set.\n"
            "Example: export ACD_LLM_MODEL=openrouter:anthropic/claude-sonnet-4-5",
            file=sys.stderr,
        )
        sys.exit(1)

    provider, _, model_name = model_str.partition(":")
    if not model_name:
        print(
            f"Error: {env_var} must be in 'provider:model_name' format.\n"
            "Valid providers: ollama, openai, openrouter.",
            file=sys.stderr,
        )
        sys.exit(1)

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
        f"Error: Unknown provider in {env_var}."
        " Valid providers: ollama, openai, openrouter.",
        file=sys.stderr,
    )
    sys.exit(1)


def _workflow_bytes_to_context(xml_bytes: bytes, stem: str) -> dict:
    """Parse XML bytes → context dict via parse_one + ContextBuilder."""
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


def _format_doc_for_judge(doc) -> str:  # type: ignore[no-untyped-def]
    """Render a WorkflowDocumentation as readable prose for the LLM judge.

    Avoids passing raw JSON so the judge can reason about natural-language claims.
    """
    lines = [
        f"**Workflow:** {doc.workflow_name}",
        "",
        f"**Intent:** {doc.intent}",
        "",
        f"**Data Flow:** {doc.data_flow}",
        "",
        "**Tool Notes:**",
    ]
    for note in doc.tool_notes:
        lines.append(f"  - Tool {note.tool_id} ({note.tool_type}): {note.role}")
    lines += ["", "**Risks:**"]
    for risk in doc.risks:
        lines.append(f"  - {risk}")
    return "\n".join(lines)


def _parse_judge_response(raw: str) -> tuple[float, str]:
    """Extract (score, reasoning) from an LLM judge response.

    Accepts JSON embedded anywhere in the response, with or without markdown fences.
    Falls back to searching for a bare number if JSON parsing fails.
    """
    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    # Try JSON extraction
    json_match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
    if json_match:
        try:
            obj = json.loads(json_match.group())
            score = float(obj.get("score", float("nan")))
            reasoning = str(obj.get("reasoning", ""))
            return score, reasoning
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: find first number 0-10
    num_match = re.search(r"\b(\d+(?:\.\d+)?)\b", cleaned)
    if num_match:
        score = min(10.0, float(num_match.group(1)))
        return score, cleaned
    return float("nan"), raw


# ---------------------------------------------------------------------------
# Structural checks (deterministic — no LLM)
# ---------------------------------------------------------------------------


def _short_tool_type(raw: str) -> str:
    """Normalize a full plugin string to its short name for comparison.

    'AlteryxBasePluginsGui.DbFileInput.DbFileInput' → 'DbFileInput'
    'DbFileInput' → 'DbFileInput'
    '' → ''

    Alteryx stores plugin names in the form Namespace.ShortName[.ShortName].
    The LLM consistently uses only the final segment, so we compare on that.
    """
    parts = [p for p in raw.split(".") if p]
    return parts[-1] if parts else ""


def structural_checks(doc, context: dict) -> dict:  # type: ignore[no-untyped-def]
    """Run deterministic checks on a WorkflowDocumentation against its context.

    Skipped for pre-built plain-text docs (_PrebuiltDoc) since they have no
    parsed tool_notes — returns a sentinel result with structural_score=None.

    Returns a dict with per-check boolean results and an overall structural_score (0-1).
    """
    if isinstance(doc, _PrebuiltDoc):
        return {
            "structural_score": None,
            "skipped": True,
            "reason": "pre-built doc — no parsed tool_notes to check",
        }

    expected_ids = {t["tool_id"] for t in context.get("tools", [])}
    # Known-unknown tools (empty tool_type) cannot be covered — exclude them.
    known_types = {
        _short_tool_type(t["tool_type"])
        for t in context.get("tools", [])
        if t["tool_type"]
    }

    doc_ids = {note.tool_id for note in doc.tool_notes}
    doc_types = {
        _short_tool_type(note.tool_type) for note in doc.tool_notes if note.tool_type
    }

    missing_ids = sorted(expected_ids - doc_ids)
    phantom_ids = sorted(doc_ids - expected_ids)
    missing_types = sorted(known_types - doc_types)

    tool_id_ok = not missing_ids and not phantom_ids
    tool_type_ok = not missing_types
    fields_ok = (
        bool(doc.intent.strip()) and bool(doc.data_flow.strip()) and bool(doc.risks)
    )

    checks_passed = sum([tool_id_ok, tool_type_ok, fields_ok])
    structural_score = checks_passed / 3

    return {
        "structural_score": round(structural_score, 4),
        "skipped": False,
        "tool_id_coverage": tool_id_ok,
        "tool_type_coverage": tool_type_ok,
        "fields_populated": fields_ok,
        "missing_tool_ids": missing_ids,
        "phantom_tool_ids": phantom_ids,
        "missing_tool_types": missing_types,
    }


# ---------------------------------------------------------------------------
# G-Eval LLM-as-judge
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = (
    "You are an objective evaluator of Alteryx workflow documentation. "
    "You will be given a workflow context (ground truth) and generated documentation. "
    "Score strictly according to the rubric. "
    "Respond ONLY with a JSON object: "
    '{"score": <0-10>, "reasoning": "<one sentence>"}. '
    "No markdown fences, no extra text."
)


async def _evaluate_criterion(
    name: str,
    rubric: str,
    doc_text: str,
    context: dict,
    critic_llm,  # type: ignore[no-untyped-def]
) -> tuple[float, str]:
    """Score one G-Eval criterion. Returns (score 0-10, reasoning)."""
    from langchain_core.messages import HumanMessage, SystemMessage

    context_summary = json.dumps(
        {
            "workflow_name": context.get("workflow_name"),
            "tools": context.get("tools", []),
            "connections": context.get("connections", []),
            "topology": context.get("topology", {}),
        },
        indent=2,
    )

    human = HumanMessage(
        content=(
            f"=== Criterion: {name} ===\n\n"
            f"{rubric}\n\n"
            f"--- Workflow Context (ground truth) ---\n{context_summary}\n\n"
            f"--- Generated Documentation ---\n{doc_text}\n\n"
            "Score this documentation on the criterion above. "
            'Return JSON only: {"score": <0-10>, "reasoning": "<one sentence>"}'
        )
    )

    try:
        result = await critic_llm.ainvoke([SystemMessage(content=_JUDGE_SYSTEM), human])
        raw = result.content if hasattr(result, "content") else str(result)
        return _parse_judge_response(raw)
    except Exception as exc:
        return float("nan"), f"Judge call failed: {exc}"


async def _evaluate_sample(
    stem: str,
    doc,  # type: ignore[no-untyped-def]
    context: dict,
    critic_llm,  # type: ignore[no-untyped-def]
) -> dict:
    """Run structural checks + all G-Eval criteria for one sample."""
    checks = structural_checks(doc, context)
    doc_text = _format_doc_for_judge(doc)

    # Run all 5 criteria concurrently
    criterion_names = list(_GEVAL_CRITERIA.keys())
    tasks = [
        _evaluate_criterion(name, _GEVAL_CRITERIA[name], doc_text, context, critic_llm)
        for name in criterion_names
    ]
    results = await asyncio.gather(*tasks)

    geval_scores: dict[str, float] = {}
    geval_reasoning: dict[str, str] = {}
    for name, (score, reasoning) in zip(criterion_names, results, strict=False):
        geval_scores[name] = round(score, 2)
        geval_reasoning[name] = reasoning

    valid_scores = [s for s in geval_scores.values() if s == s]  # filter NaN
    geval_mean = (
        round(sum(valid_scores) / len(valid_scores), 4)
        if valid_scores
        else float("nan")
    )

    return {
        "stem": stem,
        "structural": checks,
        "geval": geval_scores,
        "geval_reasoning": geval_reasoning,
        "geval_mean": geval_mean,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(
    extra_fixtures: list[tuple[str, bytes]] | None = None,
    prebuilt_samples: list[tuple[str, bytes, str]] | None = None,
) -> None:
    """Run the workflow documentation evaluation harness."""
    try:
        from dotenv import load_dotenv

        _here = pathlib.Path(__file__).parent
        _root = _here.parent.parent
        for _env_file in (_here / ".env", _root / ".env"):
            if _env_file.exists():
                load_dotenv(_env_file)
                print(f"Loaded env from {_env_file}")
                break
    except ImportError:
        pass

    from alteryx_diff.llm import require_llm_deps

    require_llm_deps()

    from alteryx_diff.llm.doc_graph import generate_documentation

    all_fixtures = FIXTURES + (extra_fixtures or [])
    all_prebuilt = prebuilt_samples or []
    needs_generator = bool(all_fixtures)

    generator_llm = _build_llm_from_env("ACD_LLM_MODEL", required=needs_generator)
    critic_llm = (
        _build_llm_from_env("RAGAS_CRITIC_MODEL", required=False) or generator_llm
    )

    print("=== Workflow Documentation Evaluation Harness ===\n")
    if needs_generator:
        print(f"Generator LLM : {os.environ['ACD_LLM_MODEL']}")
    else:
        print("Generator LLM : (skipped — using pre-built docs)")
    critic_model = os.environ.get("RAGAS_CRITIC_MODEL", "(same as generator)")
    print(f"Critic LLM    : {critic_model}")
    print(f"Samples       : {len(all_fixtures) + len(all_prebuilt)}")
    print(f"Threshold     : G-Eval mean >= {GEVAL_THRESHOLD} / 10\n")

    # -----------------------------------------------------------------------
    # Build (doc, context) pairs
    # -----------------------------------------------------------------------
    sample_pairs: list[tuple[str, object, dict]] = []

    for stem, xml_bytes in all_fixtures:
        print(f"Generating doc : {stem}...")
        context = _workflow_bytes_to_context(xml_bytes, stem)
        doc = asyncio.run(generate_documentation(context, generator_llm))
        sample_pairs.append((stem, doc, context))

    for stem, xml_bytes, doc_text in all_prebuilt:
        print(f"Pre-built doc  : {stem}...")
        context = _workflow_bytes_to_context(xml_bytes, stem)
        # Wrap raw text as a minimal object for _format_doc_for_judge
        # (pre-built docs are plain text, not WorkflowDocumentation objects)
        sample_pairs.append((stem, _PrebuiltDoc(doc_text), context))

    # -----------------------------------------------------------------------
    # Evaluate each sample
    # -----------------------------------------------------------------------
    print(f"\nEvaluating {len(sample_pairs)} sample(s)...\n")
    sample_results: list[dict] = []

    for stem, doc, context in sample_pairs:
        print(f"  Scoring: {stem}")
        result = asyncio.run(_evaluate_sample(stem, doc, context, critic_llm))
        sample_results.append(result)

    # -----------------------------------------------------------------------
    # Print results
    # -----------------------------------------------------------------------
    print("\n--- Per-Sample Results ---")
    criterion_names = list(_GEVAL_CRITERIA.keys())
    for i, r in enumerate(sample_results):
        print(f"\n  Sample {i + 1}: {r['stem']}")
        s = r["structural"]
        if s.get("skipped"):
            print(f"    Structural : skipped ({s['reason']})")
        else:
            print(
                f"    Structural : tool_id_coverage={s['tool_id_coverage']}"
                f"  tool_type_coverage={s['tool_type_coverage']}"
                f"  fields_populated={s['fields_populated']}"
                f"  score={s['structural_score']:.2f}"
            )
            if s["missing_tool_ids"]:
                print(f"    ⚠ Missing tool IDs  : {s['missing_tool_ids']}")
            if s["phantom_tool_ids"]:
                print(f"    ⚠ Phantom tool IDs  : {s['phantom_tool_ids']}")
            if s["missing_tool_types"]:
                print(f"    ⚠ Missing tool types: {s['missing_tool_types']}")
        print(f"    G-Eval mean: {r['geval_mean']:.2f} / 10")
        for name in criterion_names:
            score = r["geval"][name]
            score_str = f"{score:.1f}" if score == score else "NaN"
            reasoning = r["geval_reasoning"][name]
            print(f"      {name:<22}: {score_str:>4}  — {reasoning}")

    all_geval_means = [
        r["geval_mean"] for r in sample_results if r["geval_mean"] == r["geval_mean"]
    ]
    overall_mean = (
        sum(all_geval_means) / len(all_geval_means) if all_geval_means else float("nan")
    )
    status = "PASS" if overall_mean >= GEVAL_THRESHOLD else "BELOW THRESHOLD"

    scored_structural = [
        r["structural"]["structural_score"]
        for r in sample_results
        if not r["structural"].get("skipped")
    ]
    structural_mean = (
        sum(scored_structural) / len(scored_structural)
        if scored_structural
        else float("nan")
    )

    print("\n--- Summary ---")
    print(
        f"Mean G-Eval score    : {overall_mean:.3f} / 10"
        f"  (threshold: >={GEVAL_THRESHOLD})  [{status}]"
    )
    structural_str = (
        f"{structural_mean:.3f}" if structural_mean == structural_mean else "n/a"
    )
    print(f"Mean structural score: {structural_str} / 1.0  (generated docs only)")
    by_criterion = {
        name: round(
            sum(
                r["geval"][name]
                for r in sample_results
                if r["geval"][name] == r["geval"][name]
            )
            / max(
                sum(1 for r in sample_results if r["geval"][name] == r["geval"][name]),
                1,
            ),
            4,
        )
        for name in criterion_names
    }
    print("By criterion:")
    for name, score in by_criterion.items():
        print(f"  {name:<22}: {score:.2f}")

    # -----------------------------------------------------------------------
    # Save results JSON
    # -----------------------------------------------------------------------
    import datetime

    results_dir = pathlib.Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    results_path = results_dir / f"{ts}.json"

    payload = {
        "timestamp": ts,
        "generator": os.environ.get("ACD_LLM_MODEL", "unknown"),
        "critic": os.environ.get("RAGAS_CRITIC_MODEL", "(same as generator)"),
        "threshold": GEVAL_THRESHOLD,
        "status": status,
        "summary": {
            "geval_mean": round(overall_mean, 4),
            "structural_mean": round(structural_mean, 4)
            if structural_mean == structural_mean
            else None,
            "by_criterion": by_criterion,
        },
        "samples": [
            {
                "sample": i + 1,
                "stem": r["stem"],
                "geval_mean": r["geval_mean"],
                "geval": r["geval"],
                "structural": r["structural"],
            }
            for i, r in enumerate(sample_results)
        ],
    }
    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nResults saved → {results_path}")


# ---------------------------------------------------------------------------
# Pre-built doc shim — wraps a plain text doc for _evaluate_sample
# ---------------------------------------------------------------------------


class _PrebuiltDoc:
    """Minimal stand-in for WorkflowDocumentation when scoring a pre-built text doc."""

    def __init__(self, text: str) -> None:
        self._text = text
        # Satisfy structural_checks by providing empty tool_notes / intent / etc.
        # Pre-built docs are plain text; structural checks are skipped for them.
        self.tool_notes = []
        self.intent = text[:100]  # non-empty so fields_populated passes intent
        self.data_flow = text
        self.risks = ["(pre-built doc — risks not parsed)"]


def _format_doc_for_judge(doc) -> str:  # type: ignore[no-untyped-def]  # noqa: F811
    """Render doc as readable prose.

    Handles both WorkflowDocumentation and _PrebuiltDoc.
    """
    if isinstance(doc, _PrebuiltDoc):
        return doc._text

    lines = [
        f"**Workflow:** {doc.workflow_name}",
        "",
        f"**Intent:** {doc.intent}",
        "",
        f"**Data Flow:** {doc.data_flow}",
        "",
        "**Tool Notes:**",
    ]
    for note in doc.tool_notes:
        lines.append(f"  - Tool {note.tool_id} ({note.tool_type}): {note.role}")
    lines += ["", "**Risks:**"]
    for risk in doc.risks:
        lines.append(f"  - {risk}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Workflow documentation evaluation harness"
    )
    parser.add_argument(
        "--workflow",
        metavar="PATH",
        action="append",
        default=[],
        help="Path to a .yxmd file — generates doc then scores it (repeatable)",
    )
    parser.add_argument(
        "--doc",
        metavar="PATH",
        action="append",
        default=[],
        help=(
            "Path to an existing doc (.md) paired with its --workflow "
            "(skips generation, scores existing doc). "
            "Must match the number of --workflow flags."
        ),
    )
    args = parser.parse_args()

    if args.doc and len(args.doc) != len(args.workflow):
        print(
            "Error: --doc requires exactly one --workflow per --doc.\n"
            f"Got {len(args.workflow)} --workflow and {len(args.doc)} --doc.",
            file=sys.stderr,
        )
        sys.exit(1)

    extra: list[tuple[str, bytes]] = []
    prebuilt: list[tuple[str, bytes, str]] = []

    if args.doc:
        for wf_path, doc_path in zip(args.workflow, args.doc, strict=False):
            wf = pathlib.Path(wf_path)
            doc = pathlib.Path(doc_path)
            for p, label in ((wf, "--workflow"), (doc, "--doc")):
                if not p.exists():
                    print(f"Error: {label} file not found: {p}", file=sys.stderr)
                    sys.exit(1)
            prebuilt.append((wf.stem, wf.read_bytes(), doc.read_text(encoding="utf-8")))
    else:
        for wf_path in args.workflow:
            p = pathlib.Path(wf_path)
            if not p.exists():
                print(f"Error: workflow file not found: {p}", file=sys.stderr)
                sys.exit(1)
            extra.append((p.stem, p.read_bytes()))

    main(extra_fixtures=extra, prebuilt_samples=prebuilt)
