"""CLI tests for the `diff --doc` flag (CLI-02 acceptance criteria).

Requires LLM extras (langchain/langgraph) — skipped automatically if not installed.
All tests use CliRunner(mix_stderr=False) for clean stdout/stderr separation.
"""
from __future__ import annotations

import builtins
import json
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

langchain = pytest.importorskip("langchain")

from typer.testing import CliRunner  # noqa: E402

from alteryx_diff.cli import app  # noqa: E402
from alteryx_diff.llm.models import ChangeNarrative  # noqa: E402
from tests.fixtures.cli import MINIMAL_YXMD_A, MINIMAL_YXMD_B  # noqa: E402

runner = CliRunner(mix_stderr=False)

_SAMPLE_NARRATIVE = ChangeNarrative(
    narrative="Narrative body text here.",
    risks=["risk-alpha"],
)


@pytest.fixture
def workflow_a(tmp_path: pathlib.Path) -> pathlib.Path:
    """Write MINIMAL_YXMD_A to a temp file and return the path."""
    p = tmp_path / "workflow_a.yxmd"
    p.write_bytes(MINIMAL_YXMD_A)
    return p


@pytest.fixture
def workflow_b(tmp_path: pathlib.Path) -> pathlib.Path:
    """Write MINIMAL_YXMD_B to a temp file and return the path."""
    p = tmp_path / "workflow_b.yxmd"
    p.write_bytes(MINIMAL_YXMD_B)
    return p


def test_diff_with_doc_flag_embeds_narrative_section(
    workflow_a: pathlib.Path,
    workflow_b: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    """--doc flag calls LLM and embeds the narrative section in the HTML report."""
    out = tmp_path / "out.html"

    with (
        patch(
            "alteryx_diff.llm.doc_graph.generate_change_narrative",
            new=AsyncMock(return_value=_SAMPLE_NARRATIVE),
        ),
        patch("alteryx_diff.cli._resolve_llm", return_value=MagicMock()),
    ):
        result = runner.invoke(
            app,
            ["diff", str(workflow_a), str(workflow_b), "--doc", "--model", "ollama:llama3", "--output", str(out)],
        )

    # Non-empty diff → exit code 1 (existing convention)
    assert result.exit_code == 1, f"stderr: {result.stderr}"
    content = out.read_text(encoding="utf-8")
    assert 'id="change-narrative"' in content, "Narrative section id missing from HTML"
    assert "Narrative body text here." in content, "Narrative body text missing from HTML"
    assert "risk-alpha" in content, "Risk item missing from HTML"


def test_diff_without_doc_flag_has_no_narrative_section(
    workflow_a: pathlib.Path,
    workflow_b: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    """Without --doc, no LLM call is made and no narrative section appears in HTML."""
    out = tmp_path / "out.html"
    mock_narrative = AsyncMock(return_value=_SAMPLE_NARRATIVE)

    with patch("alteryx_diff.llm.doc_graph.generate_change_narrative", new=mock_narrative):
        result = runner.invoke(
            app,
            ["diff", str(workflow_a), str(workflow_b), "--output", str(out)],
        )

    assert result.exit_code == 1, f"stderr: {result.stderr}"
    assert mock_narrative.called is False, "generate_change_narrative should NOT be called without --doc"
    content = out.read_text(encoding="utf-8")
    assert 'id="change-narrative"' not in content, "Narrative section should not appear without --doc"


def test_diff_doc_on_identical_workflows_skips_llm(
    workflow_a: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    """--doc on identical workflows: is_empty early exit fires, LLM is never called."""
    mock_narrative = AsyncMock(return_value=_SAMPLE_NARRATIVE)

    with patch("alteryx_diff.llm.doc_graph.generate_change_narrative", new=mock_narrative):
        result = runner.invoke(
            app,
            ["diff", str(workflow_a), str(workflow_a), "--doc", "--model", "ollama:llama3"],
        )

    assert result.exit_code == 0, f"Expected exit code 0 for identical diff; got {result.exit_code}"
    assert mock_narrative.called is False, "LLM should NOT be called when diff is empty"


def test_diff_doc_with_json_skips_narrative_with_note(
    workflow_a: pathlib.Path,
    workflow_b: pathlib.Path,
) -> None:
    """--doc with --json: LLM is skipped, stderr note is emitted, stdout is valid JSON."""
    mock_narrative = AsyncMock(return_value=_SAMPLE_NARRATIVE)

    with patch("alteryx_diff.llm.doc_graph.generate_change_narrative", new=mock_narrative):
        result = runner.invoke(
            app,
            ["diff", str(workflow_a), str(workflow_b), "--doc", "--json", "--model", "ollama:llama3"],
        )

    assert mock_narrative.called is False, "LLM should NOT be called when --json is set"
    assert "--doc has no effect with --json" in result.stderr, "Expected note about --doc/--json conflict"
    # stdout must be valid JSON
    data = json.loads(result.stdout)
    assert "added" in data
    assert "removed" in data
    assert "modified" in data


def test_diff_doc_without_llm_deps_exits_nonzero(
    workflow_a: pathlib.Path,
    workflow_b: pathlib.Path,
    monkeypatch,
) -> None:
    """When langchain is not importable, --doc exits non-zero with install hint."""
    real_import = builtins.__import__

    def _import_blocker(mod_name, *args, **kwargs):
        if mod_name == "langchain" or mod_name.startswith("langchain."):
            raise ImportError(f"Mocked ImportError for {mod_name}")
        return real_import(mod_name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import_blocker)

    result = runner.invoke(
        app,
        ["diff", str(workflow_a), str(workflow_b), "--doc", "--model", "ollama:llama3"],
    )

    assert result.exit_code != 0, "Expected non-zero exit code when LLM deps are missing"
    assert "pip install" in result.stderr
    assert "alteryx-diff[llm]" in result.stderr
