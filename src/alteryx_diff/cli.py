from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
from typing import Any

import typer
from rich.console import Console

from alteryx_diff.exceptions import MalformedXMLError, ParseError
from alteryx_diff.pipeline import DiffRequest, run
from alteryx_diff.renderers import GraphRenderer, HTMLRenderer

app = typer.Typer(no_args_is_help=True)
# Spinner + summary go to stderr so stdout stays clean for --json
_err_console = Console(stderr=True)


@app.command()
def diff(  # noqa: B008
    workflow_a: pathlib.Path = typer.Argument(  # noqa: B008
        ..., help="Baseline .yxmd or .yxwz file (quote paths that contain spaces)"
    ),
    workflow_b: pathlib.Path = typer.Argument(  # noqa: B008
        ..., help="Changed .yxmd or .yxwz file (quote paths that contain spaces)"
    ),
    output: pathlib.Path = typer.Option(  # noqa: B008
        pathlib.Path("diff_report.html"),
        "--output",
        "-o",
        help="Output path for the HTML report (ignored when --json is set)",
    ),
    include_positions: bool = typer.Option(  # noqa: B008
        False,
        "--include-positions",
        help=(
            "Include canvas X/Y position changes in diff detection"
            " (excluded by default to avoid layout noise)"
        ),
    ),
    canvas_layout: bool = typer.Option(  # noqa: B008
        False,
        "--canvas-layout",
        help=(
            "Use Alteryx canvas X/Y coordinates for graph node positions"
            " (default: hierarchical auto-layout following data flow)"
        ),
    ),
    filter_ui_tools: bool = typer.Option(  # noqa: B008
        True,
        "--no-filter-ui-tools",
        help=(
            "Include AlteryxGuiToolkit.* app interface nodes"
            " (Tab, TextBox, Action, etc.) filtered by default"
            " when comparing .yxwz apps against .yxmd workflows"
        ),
    ),
    quiet: bool = typer.Option(  # noqa: B008
        False,
        "--quiet",
        "-q",
        help="Suppress all terminal output; exit code only (for CI pipelines)",
    ),
    json_output: bool = typer.Option(  # noqa: B008
        False,
        "--json",
        help="Write JSON diff to stdout instead of HTML file (pipe-friendly)",
    ),
) -> None:
    """Compare two Alteryx .yxmd or .yxwz workflow/app files and report differences.

    Paths that contain spaces must be quoted in the shell, e.g.:

      alteryx-diff "My Workflow A.yxmd" "My Workflow B.yxmd"
    """
    # Compute governance metadata upfront — single timestamp for audit consistency
    # Guard here: missing file raises FileNotFoundError before pipeline even starts
    try:
        hash_a = _file_sha256(workflow_a)
        hash_b = _file_sha256(workflow_b)
    except OSError as e:
        typer.echo(f"Error: {e.strerror}: {e.filename}", err=True)
        raise typer.Exit(code=2) from None
    metadata = _build_governance_metadata(workflow_a, workflow_b, hash_a, hash_b)

    # Run pipeline (spinner goes to stderr; stdout stays clean for --json)
    try:
        if quiet or json_output:
            response = run(
                DiffRequest(
                    path_a=workflow_a,
                    path_b=workflow_b,
                    filter_ui_tools=filter_ui_tools,
                ),
                include_positions=include_positions,
            )
        else:
            with _err_console.status("Running diff...", spinner="dots"):
                response = run(
                    DiffRequest(
                        path_a=workflow_a,
                        path_b=workflow_b,
                        filter_ui_tools=filter_ui_tools,
                    ),
                    include_positions=include_positions,
                )
    except MalformedXMLError as e:
        typer.echo(f"Error: Invalid XML in {e.filepath}: {e.message}", err=True)
        raise typer.Exit(code=2) from None
    except ParseError as e:
        typer.echo(f"Error: {e.message}", err=True)
        raise typer.Exit(code=2) from None

    result = response.result

    if result.is_empty:
        if json_output:
            # Emit empty JSON for consistent downstream tool behaviour
            json_str = _cli_json_output(result, metadata)
            typer.echo(json_str)
        if not quiet:
            typer.echo("No differences found", err=True)
        raise typer.Exit(code=0)

    # Render output
    if json_output:
        json_str = _cli_json_output(result, metadata)
        typer.echo(json_str)  # stdout — pipe-friendly
    else:
        graph_renderer = GraphRenderer()
        graph_html = graph_renderer.render(
            result,
            all_connections=(response.doc_a.connections + response.doc_b.connections),
            nodes_old=response.doc_a.nodes,
            nodes_new=response.doc_b.nodes,
            canvas_layout=canvas_layout,
        )
        html = HTMLRenderer().render(
            result,
            file_a=str(workflow_a.resolve()),
            file_b=str(workflow_b.resolve()),
            graph_html=graph_html,
            metadata=metadata,  # CLI-04: governance footer in HTML report
        )
        output.write_text(html, encoding="utf-8")
        if not quiet:
            change_count = (
                len(result.added_nodes)
                + len(result.removed_nodes)
                + len(result.modified_nodes)
                + len(result.edge_diffs)
            )
            typer.echo(
                f"Report written to {output} ({change_count} changes detected)",
                err=True,
            )

    raise typer.Exit(code=1)


def _resolve_model_string(cli_model: str | None) -> str:
    """Resolve model preference via D-04 fallback chain.

    Order: (1) --model flag, (2) ACD_LLM_MODEL env var, (3) config_store['llm_model'],
    (4) raise typer.Exit(code=2) with clear install-hint error.

    Returns:
        A model string in 'provider:model_name' form.
    """
    import os
    if cli_model:
        return cli_model
    env_model = os.environ.get("ACD_LLM_MODEL")
    if env_model:
        return env_model
    try:
        from app.services.config_store import load_config
        cfg = load_config()
        stored = cfg.get("llm_model")
        if stored:
            return stored
    except Exception:
        pass  # config_store unavailable — fall through to error
    typer.echo(
        "Error: No LLM model configured. Use --model provider:model_name "
        "(e.g. --model ollama:llama3) or set ACD_LLM_MODEL environment variable.",
        err=True,
    )
    raise typer.Exit(code=2)


def _resolve_llm(model_str: str, base_url: str | None) -> "Any":  # noqa: F821
    """Build a BaseChatModel instance from a 'provider:model_name' string.

    D-01: provider is prefix before first ':'. D-02: API keys from env only.
    D-03: base_url overrides default endpoint for ollama/openai-compatible hosts.

    Raises:
        typer.Exit: On unknown provider with clear error message.
    """
    import os
    provider, _, model_name = model_str.partition(":")
    if not model_name:
        typer.echo(
            f"Error: --model must be 'provider:model_name', got {model_str!r}. "
            "Example: --model ollama:llama3",
            err=True,
        )
        raise typer.Exit(code=2)
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        kwargs: dict = {"model": model_name, "temperature": 0}
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOllama(**kwargs)
    if provider in ("openai", "openrouter"):
        from langchain_openai import ChatOpenAI
        kwargs = {"model": model_name, "temperature": 0}
        if provider == "openrouter":
            kwargs["base_url"] = base_url or "https://openrouter.ai/api/v1"
            kwargs["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")
        else:
            kwargs["api_key"] = os.environ.get("OPENAI_API_KEY", "")
            if base_url:
                kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)
    typer.echo(
        f"Error: Unknown provider {provider!r}. Use one of: ollama, openai, openrouter.",
        err=True,
    )
    raise typer.Exit(code=2)


@app.command()
def document(  # noqa: B008
    workflow: pathlib.Path = typer.Argument(  # noqa: B008
        ..., help="Path to an .yxmd or .yxwz workflow file"
    ),
    output: pathlib.Path | None = typer.Option(  # noqa: B008
        None, "--output", "-o",
        help="Output path for the generated Markdown doc. Defaults to {workflow_dir}/{stem}-doc.md next to the input file.",
    ),
    model: str | None = typer.Option(  # noqa: B008
        None, "--model",
        help="LLM provider and model, e.g. ollama:llama3 or openrouter:mistralai/mistral-7b-instruct. Falls back to ACD_LLM_MODEL env var, then config_store.",
    ),
    base_url: str | None = typer.Option(  # noqa: B008
        None, "--base-url",
        help="Override the default endpoint URL (useful for remote Ollama or OpenAI-compatible hosts).",
    ),
    filter_ui_tools: bool = typer.Option(  # noqa: B008
        True, "--no-filter-ui-tools",
        help="Include AlteryxGuiToolkit.* app-interface nodes (filtered by default).",
    ),
    quiet: bool = typer.Option(  # noqa: B008
        False, "--quiet", "-q",
        help="Suppress spinner and status messages.",
    ),
) -> None:
    """Generate a Markdown intent doc for a single Alteryx workflow using an LLM."""
    # D-10: require LLM extras FIRST. Any failure exits with install hint.
    try:
        from alteryx_diff.llm import require_llm_deps
        require_llm_deps()
    except ImportError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=2) from None

    # Resolve file
    if not workflow.exists():
        typer.echo(f"Error: Workflow file not found: {workflow}", err=True)
        raise typer.Exit(code=2)

    # Resolve model + build LLM (deferred imports inside _resolve_llm)
    model_str = _resolve_model_string(model)
    llm = _resolve_llm(model_str, base_url)

    # Deferred imports — must be inside function body (CORE-01)
    from alteryx_diff.parser import parse_one
    from alteryx_diff.llm.context_builder import ContextBuilder
    from alteryx_diff.llm.doc_graph import generate_documentation
    from alteryx_diff.renderers.doc_renderer import DocRenderer
    import asyncio

    # Parse workflow and build context
    doc = parse_one(workflow, filter_ui_tools=filter_ui_tools)
    context = ContextBuilder.build_from_workflow(doc)

    # Run LLM pipeline with spinner (D-11)
    if quiet:
        workflow_doc = asyncio.run(generate_documentation(context, llm))
    else:
        with _err_console.status("Generating documentation...", spinner="dots"):
            workflow_doc = asyncio.run(generate_documentation(context, llm))

    # Resolve output path (D-08 default, D-09 override)
    if output is None:
        output = workflow.parent / f"{workflow.stem}-doc.md"

    # Write Markdown
    written_path = DocRenderer().write_markdown(workflow_doc, output)
    if not quiet:
        typer.echo(f"Documentation written to {written_path}", err=True)


def _file_sha256(path: pathlib.Path) -> str:
    """Return 64-char SHA-256 hex digest. Uses hashlib.file_digest (Python 3.11+)."""
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256")
    return digest.hexdigest()


def _build_governance_metadata(
    path_a: pathlib.Path,
    path_b: pathlib.Path,
    hash_a: str,
    hash_b: str,
) -> dict[str, Any]:
    return {
        "file_a": str(path_a.resolve()),
        "file_b": str(path_b.resolve()),
        "sha256_a": hash_a,
        "sha256_b": hash_b,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }


def _cli_json_output(result: Any, metadata: dict[str, Any]) -> str:
    """Produce CLI --json schema: {added, removed, modified, metadata}.

    Distinct from JSONRenderer output ({summary, tools, connections}).
    Kept separate to avoid breaking existing JSONRenderer tests (5 passing).
    """
    from alteryx_diff.models import (  # local import: avoids circular at module level
        DiffResult,
    )

    r: DiffResult = result
    payload: dict[str, Any] = {
        "added": [
            {
                "tool_id": int(n.tool_id),
                "tool_type": n.tool_type,
                "config": dict(n.config),
            }
            for n in r.added_nodes
        ],
        "removed": [
            {
                "tool_id": int(n.tool_id),
                "tool_type": n.tool_type,
                "config": dict(n.config),
            }
            for n in r.removed_nodes
        ],
        "modified": [
            {
                "tool_id": int(nd.tool_id),
                "tool_type": nd.old_node.tool_type,
                "field_diffs": [
                    {"field": k, "before": v[0], "after": v[1]}
                    for k, v in nd.field_diffs.items()
                ],
            }
            for nd in r.modified_nodes
        ],
        "metadata": metadata,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
