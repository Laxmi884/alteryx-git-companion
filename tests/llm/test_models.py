"""Tests for WorkflowDocumentation and ToolNote Pydantic models."""
import pytest

pytest.importorskip("langchain")

from pydantic import ValidationError  # noqa: E402

from alteryx_diff.llm.models import ToolNote, WorkflowDocumentation  # noqa: E402


def test_tool_note_validates() -> None:
    """ToolNote validates with all required fields."""
    note = ToolNote(tool_id=1, tool_type="AlteryxBasePluginsGui.Filter.Filter", role="Filters rows where Amount > 100")
    assert note.tool_id == 1
    assert note.tool_type == "AlteryxBasePluginsGui.Filter.Filter"
    assert note.role == "Filters rows where Amount > 100"


def test_workflow_documentation_validates() -> None:
    """WorkflowDocumentation validates with all required fields."""
    doc = WorkflowDocumentation(
        workflow_name="SalesFilter",
        intent="Filters sales transactions above $100 and writes them to the output file.",
        data_flow="Data flows from the Input tool through a Filter to the Output tool.",
        tool_notes=[
            ToolNote(tool_id=1, tool_type="DbFileInput", role="Reads raw sales data from CSV"),
            ToolNote(tool_id=2, tool_type="Filter", role="Filters rows where Amount > 100"),
            ToolNote(tool_id=3, tool_type="DbFileOutput", role="Writes filtered records to output CSV"),
        ],
        risks=["Input file may have missing Amount values", "Output path must be writable"],
    )
    assert doc.workflow_name == "SalesFilter"
    assert len(doc.tool_notes) == 3
    assert len(doc.risks) == 2


def test_workflow_documentation_rejects_missing_required_fields() -> None:
    """WorkflowDocumentation raises ValidationError when required fields are missing."""
    with pytest.raises(ValidationError):
        WorkflowDocumentation(
            workflow_name="TestWorkflow",
            # missing: intent, data_flow, tool_notes, risks
        )  # type: ignore[call-arg]


def test_workflow_documentation_no_assumptions_field() -> None:
    """WorkflowDocumentation does NOT have an 'assumptions' field."""
    doc = WorkflowDocumentation(
        workflow_name="TestWorkflow",
        intent="Test intent for workflow.",
        data_flow="Data flows from input to output.",
        tool_notes=[ToolNote(tool_id=1, tool_type="Input", role="Reads data")],
        risks=["No risks identified"],
    )
    assert not hasattr(doc, "assumptions"), "WorkflowDocumentation must not have an 'assumptions' field"


def test_workflow_documentation_json_round_trip() -> None:
    """WorkflowDocumentation.model_validate_json round-trips correctly."""
    original = WorkflowDocumentation(
        workflow_name="SalesFilter",
        intent="Filters high-value sales records from a CSV input.",
        data_flow="Input CSV -> Filter (Amount > 100) -> Output CSV.",
        tool_notes=[
            ToolNote(tool_id=1, tool_type="DbFileInput", role="Reads raw sales CSV"),
            ToolNote(tool_id=2, tool_type="Filter", role="Keeps rows where Amount exceeds threshold"),
        ],
        risks=["CSV may contain nulls in Amount column"],
    )
    json_str = original.model_dump_json()
    restored = WorkflowDocumentation.model_validate_json(json_str)
    assert restored.workflow_name == original.workflow_name
    assert restored.intent == original.intent
    assert len(restored.tool_notes) == len(original.tool_notes)
    assert restored.tool_notes[0].tool_id == original.tool_notes[0].tool_id


def test_conftest_sample_workflow_documentation() -> None:
    """conftest sample_workflow_documentation() returns a valid WorkflowDocumentation instance."""
    from tests.llm.conftest import sample_workflow_documentation

    sample = sample_workflow_documentation()
    assert isinstance(sample, WorkflowDocumentation)
    assert len(sample.tool_notes) >= 3
    assert len(sample.risks) >= 2
