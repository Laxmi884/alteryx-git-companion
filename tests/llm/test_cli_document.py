"""CLI tests for the `document` subcommand (CLI-01 acceptance criteria).

Requires LLM extras (langchain/langgraph) — skipped automatically if not installed.
All tests use CliRunner(mix_stderr=False) for clean stdout/stderr separation.
"""
from __future__ import annotations

import builtins
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

langchain = pytest.importorskip("langchain")

from typer.testing import CliRunner  # noqa: E402

from alteryx_diff.cli import app  # noqa: E402
from tests.llm.conftest import sample_workflow_documentation  # noqa: E402
from tests.fixtures.cli import MINIMAL_YXMD_A  # noqa: E402

runner = CliRunner(mix_stderr=False)


@pytest.fixture
def workflow_file(tmp_path: pathlib.Path) -> pathlib.Path:
    """Write a minimal valid .yxmd to a temp file and return the path."""
    p = tmp_path / "test_workflow.yxmd"
    p.write_bytes(MINIMAL_YXMD_A)
    return p


def test_document_happy_path_writes_markdown(
    workflow_file: pathlib.Path,
) -> None:
    """document subcommand writes a Markdown doc to the default output path."""
    sample_doc = sample_workflow_documentation()
    # generate_documentation is imported inside the function body (CORE-01), so patch at source
    with (
        patch("alteryx_diff.llm.doc_graph.generate_documentation", new=AsyncMock(return_value=sample_doc)),
        patch("alteryx_diff.cli._resolve_llm", return_value=MagicMock()),
    ):
        result = runner.invoke(
            app,
            ["document", str(workflow_file), "--model", "ollama:llama3"],
        )

    expected_output = workflow_file.parent / f"{workflow_file.stem}-doc.md"
    assert result.exit_code == 0, f"stderr: {result.stderr}"
    assert expected_output.exists(), f"Expected {expected_output} to exist"


def test_document_output_flag_overrides_default_path(
    workflow_file: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    """--output flag writes to the specified path; default path must NOT exist."""
    sample_doc = sample_workflow_documentation()
    custom_output = tmp_path / "custom.md"
    default_output = workflow_file.parent / f"{workflow_file.stem}-doc.md"

    with (
        patch("alteryx_diff.llm.doc_graph.generate_documentation", new=AsyncMock(return_value=sample_doc)),
        patch("alteryx_diff.cli._resolve_llm", return_value=MagicMock()),
    ):
        result = runner.invoke(
            app,
            ["document", str(workflow_file), "--model", "ollama:llama3", "--output", str(custom_output)],
        )

    assert result.exit_code == 0, f"stderr: {result.stderr}"
    assert custom_output.exists(), f"Expected {custom_output} to exist"
    assert not default_output.exists(), f"Default path {default_output} should NOT exist"


def test_document_without_llm_deps_exits_nonzero_with_install_hint(
    workflow_file: pathlib.Path,
    monkeypatch,
) -> None:
    """When langchain is not importable, exit code != 0 and install hint is in stderr."""
    real_import = builtins.__import__

    def _import_blocker(mod_name, *args, **kwargs):
        if mod_name == "langchain" or mod_name.startswith("langchain."):
            raise ImportError(f"Mocked ImportError for {mod_name}")
        return real_import(mod_name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import_blocker)

    result = runner.invoke(
        app,
        ["document", str(workflow_file), "--model", "ollama:llama3"],
    )

    assert result.exit_code != 0
    assert "pip install" in result.stderr
    assert "alteryx-diff[llm]" in result.stderr


def test_document_no_model_configured_exits_nonzero(
    workflow_file: pathlib.Path,
    monkeypatch,
) -> None:
    """Without --model or env var or config, exit code 2 with clear error."""
    monkeypatch.delenv("ACD_LLM_MODEL", raising=False)

    with patch("alteryx_diff.cli._resolve_model_string", side_effect=lambda m: (_ for _ in ()).throw(
        __import__("typer").Exit(code=2)
    )):
        # Simplest approach: just patch the entire model resolution to trigger exit(2)
        pass

    # Direct test: invoke without --model and verify it errors
    with patch("app.services.config_store.load_config", return_value={}):
        result = runner.invoke(
            app,
            ["document", str(workflow_file)],
        )

    assert result.exit_code == 2
    assert "No LLM model configured" in result.stderr


def test_document_model_flag_parses_provider_and_name(
    workflow_file: pathlib.Path,
) -> None:
    """--model ollama:llama3 results in ChatOllama being called with model='llama3'."""
    import sys
    sample_doc = sample_workflow_documentation()
    mock_chat_ollama = MagicMock()

    # langchain_ollama may not be installed; inject a mock module so _resolve_llm's
    # `from langchain_ollama import ChatOllama` resolves without ImportError
    mock_ollama_module = MagicMock()
    mock_ollama_module.ChatOllama = mock_chat_ollama

    # generate_documentation is a deferred import inside document(), patch at source
    with (
        patch("alteryx_diff.llm.doc_graph.generate_documentation", new=AsyncMock(return_value=sample_doc)),
        patch.dict(sys.modules, {"langchain_ollama": mock_ollama_module}),
    ):
        result = runner.invoke(
            app,
            ["document", str(workflow_file), "--model", "ollama:llama3"],
        )

    assert result.exit_code == 0, f"stderr: {result.stderr}"
    mock_chat_ollama.assert_called_once()
    assert mock_chat_ollama.call_args.kwargs["model"] == "llama3"


def test_document_bad_model_string_exits_nonzero(
    workflow_file: pathlib.Path,
) -> None:
    """--model with no colon gives exit code 2 and mentions 'provider:model_name'."""
    result = runner.invoke(
        app,
        ["document", str(workflow_file), "--model", "justamodelname"],
    )

    assert result.exit_code == 2
    assert "provider:model_name" in result.stderr
