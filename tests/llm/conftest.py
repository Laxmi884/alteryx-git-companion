"""Shared test fixtures for LLM tests (Plans 02 and 03 depend on these)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from alteryx_diff.llm.models import ToolNote, WorkflowDocumentation


def sample_workflow_documentation() -> WorkflowDocumentation:
    """Return a realistic WorkflowDocumentation instance for use in tests."""
    return WorkflowDocumentation(
        workflow_name="SalesFilter",
        intent=(
            "Filters high-value sales transactions from a CSV input file. "
            "Keeps only records where the Amount field exceeds $100 and writes them to an output CSV."
        ),
        data_flow=(
            "Raw sales data is read from data.csv by the Input tool (ID 1). "
            "The Filter tool (ID 2) retains rows where Amount > 100. "
            "Qualified records are written to output.csv by the Output tool (ID 3)."
        ),
        tool_notes=[
            ToolNote(
                tool_id=1,
                tool_type="AlteryxBasePluginsGui.DbFileInput.DbFileInput",
                role="Reads raw sales data from data.csv into the workflow",
            ),
            ToolNote(
                tool_id=2,
                tool_type="AlteryxBasePluginsGui.Filter.Filter",
                role="Keeps only rows where Amount > 100; discards the rest",
            ),
            ToolNote(
                tool_id=3,
                tool_type="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput",
                role="Writes filtered high-value sales records to output.csv",
            ),
        ],
        risks=[
            "Input CSV may contain null or non-numeric values in the Amount column",
            "Output file path must be writable; silent overwrite on re-run",
        ],
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    """Return a MagicMock that mimics a langchain LLM with structured output support."""
    llm = MagicMock()
    # Plain ainvoke returns content string (for topology notes etc.)
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="topology notes"))

    # with_structured_output returns a chain whose ainvoke returns WorkflowDocumentation
    structured_chain = MagicMock()
    structured_chain.ainvoke = AsyncMock(return_value=sample_workflow_documentation())
    llm.with_structured_output = MagicMock(return_value=structured_chain)

    return llm


@pytest.fixture
def sample_context() -> dict[str, Any]:
    """Return a context dict matching ContextBuilder.build_from_workflow output shape."""
    return {
        "workflow_name": "SalesFilter",
        "tool_count": 3,
        "tools": [
            {
                "tool_id": 1,
                "tool_type": "AlteryxBasePluginsGui.DbFileInput.DbFileInput",
                "config": {"file": "data.csv"},
            },
            {
                "tool_id": 2,
                "tool_type": "AlteryxBasePluginsGui.Filter.Filter",
                "config": {"expression": "Amount > 100"},
            },
            {
                "tool_id": 3,
                "tool_type": "AlteryxBasePluginsGui.DbFileOutput.DbFileOutput",
                "config": {"file": "output.csv"},
            },
        ],
        "connections": [
            {"src_tool": 1, "src_anchor": "Output", "dst_tool": 2, "dst_anchor": "Input"},
            {"src_tool": 2, "src_anchor": "True", "dst_tool": 3, "dst_anchor": "Input"},
        ],
        "topology": {
            "connections": [
                {"src_tool": 1, "src_anchor": "Output", "dst_tool": 2, "dst_anchor": "Input"},
                {"src_tool": 2, "src_anchor": "True", "dst_tool": 3, "dst_anchor": "Input"},
            ],
            "source_tools": [1],
            "sink_tools": [3],
            "branch_points": [],
        },
    }
