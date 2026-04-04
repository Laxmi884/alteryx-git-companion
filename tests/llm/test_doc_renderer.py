"""Tests for DocRenderer — renders WorkflowDocumentation to Markdown and HTML fragment."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Skip entire module if langchain/pydantic LLM extras are not installed
# (conftest.py imports WorkflowDocumentation which requires pydantic from llm extras)
pytest.importorskip("langchain")

from tests.llm.conftest import sample_workflow_documentation  # noqa: E402


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def doc():
    """Return a WorkflowDocumentation instance for testing."""
    return sample_workflow_documentation()


@pytest.fixture
def renderer():
    """Return a DocRenderer instance."""
    from alteryx_diff.renderers.doc_renderer import DocRenderer

    return DocRenderer()


# ---------------------------------------------------------------------------
# to_markdown tests
# ---------------------------------------------------------------------------


def test_to_markdown_contains_sections(renderer, doc):
    """to_markdown output contains all expected section headings."""
    md = renderer.to_markdown(doc)
    assert f"# {doc.workflow_name}" in md
    assert "## Intent" in md
    assert "## Data Flow" in md
    assert "## Tool Inventory" in md
    assert "## Production Risks" in md


def test_to_markdown_tool_table(renderer, doc):
    """to_markdown output contains a Markdown table with tool notes."""
    md = renderer.to_markdown(doc)
    assert "| Tool ID |" in md
    assert "| Type |" in md
    assert "| Role |" in md
    # Verify rows for each tool note
    for note in doc.tool_notes:
        assert str(note.tool_id) in md
        assert note.tool_type in md
        assert note.role in md


def test_to_markdown_risks_list(renderer, doc):
    """to_markdown output contains each risk as a bullet point."""
    md = renderer.to_markdown(doc)
    for risk in doc.risks:
        assert f"- {risk}" in md


# ---------------------------------------------------------------------------
# to_html_fragment tests
# ---------------------------------------------------------------------------


def test_to_html_fragment_section_tag(renderer, doc):
    """to_html_fragment output starts with <section> and ends with </section>."""
    html = renderer.to_html_fragment(doc)
    assert html.startswith('<section class="workflow-doc"')
    assert html.endswith("</section>")


def test_to_html_fragment_contains_content(renderer, doc):
    """to_html_fragment contains expected structural HTML elements."""
    html = renderer.to_html_fragment(doc)
    assert "<h2>" in html
    assert "<h3>Intent</h3>" in html
    assert "<table>" in html
    assert "<ul>" in html


def test_to_html_fragment_escapes_html(renderer, doc):
    """to_html_fragment escapes HTML entities in content fields (no raw injection)."""
    from alteryx_diff.llm.models import ToolNote, WorkflowDocumentation

    xss_doc = WorkflowDocumentation(
        workflow_name="XSS Test",
        intent="<script>alert('xss')</script>",
        data_flow="Normal data flow",
        tool_notes=[
            ToolNote(tool_id=1, tool_type="SomeTool", role="Normal role"),
        ],
        risks=["<b>bold risk</b>"],
    )
    html = renderer.to_html_fragment(xss_doc)
    # Raw script tag must NOT appear in the output
    assert "<script>" not in html
    # Escaped form should be present
    assert "&lt;script&gt;" in html


# ---------------------------------------------------------------------------
# write_markdown tests
# ---------------------------------------------------------------------------


def test_write_markdown_creates_file(renderer, doc, tmp_path):
    """write_markdown creates a file at the given path with Markdown content."""
    output_path = tmp_path / "output.md"
    result = renderer.write_markdown(doc, output_path)
    assert result == output_path
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert f"# {doc.workflow_name}" in content


# ---------------------------------------------------------------------------
# Import safety test
# ---------------------------------------------------------------------------


def test_no_llm_import_at_module_level():
    """Importing doc_renderer must not trigger top-level langchain imports.

    Strategy: verify the source file does not contain a bare
    'from alteryx_diff.llm' import outside a TYPE_CHECKING block.
    """
    import inspect

    import alteryx_diff.renderers.doc_renderer as mod

    source = inspect.getsource(mod)

    # Ensure TYPE_CHECKING guard is present
    assert "TYPE_CHECKING" in source

    # Verify there is no bare top-level import of alteryx_diff.llm
    # (outside the TYPE_CHECKING block). We check that any 'from alteryx_diff.llm'
    # line is only found inside an indented TYPE_CHECKING block.
    lines = source.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("from alteryx_diff.llm"):
            # Must be inside an if TYPE_CHECKING block (indented)
            assert line.startswith(" ") or line.startswith("\t"), (
                f"Found bare top-level LLM import on line {i + 1}: {line!r}"
            )
