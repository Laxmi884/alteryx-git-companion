import pytest

pytest.importorskip("langchain")

from alteryx_diff.llm.context_builder import ContextBuilder  # noqa: E402
from alteryx_diff.models.diff import DiffResult, EdgeDiff, NodeDiff  # noqa: E402
from alteryx_diff.models.types import AnchorName, ToolID  # noqa: E402
from alteryx_diff.models.workflow import AlteryxConnection, AlteryxNode, WorkflowDoc  # noqa: E402


@pytest.fixture
def sample_doc() -> WorkflowDoc:
    """A WorkflowDoc with 3 nodes and 2 connections (1->2->3)."""
    nodes = (
        AlteryxNode(
            tool_id=ToolID(1),
            tool_type="AlteryxBasePluginsGui.DbFileInput.DbFileInput",
            x=0.0,
            y=0.0,
            config={"file": "data.csv"},
        ),
        AlteryxNode(
            tool_id=ToolID(2),
            tool_type="AlteryxBasePluginsGui.Filter.Filter",
            x=100.0,
            y=0.0,
            config={"expression": "Amount > 100"},
        ),
        AlteryxNode(
            tool_id=ToolID(3),
            tool_type="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput",
            x=200.0,
            y=0.0,
            config={"file": "output.csv"},
        ),
    )
    connections = (
        AlteryxConnection(
            src_tool=ToolID(1),
            src_anchor=AnchorName("Output"),
            dst_tool=ToolID(2),
            dst_anchor=AnchorName("Input"),
        ),
        AlteryxConnection(
            src_tool=ToolID(2),
            src_anchor=AnchorName("True"),
            dst_tool=ToolID(3),
            dst_anchor=AnchorName("Input"),
        ),
    )
    return WorkflowDoc(
        filepath="/workflows/MyWorkflow.yxmd",
        nodes=nodes,
        connections=connections,
    )


@pytest.fixture
def sample_diff() -> DiffResult:
    """A DiffResult with 1 added, 1 removed, 1 modified node, and 1 edge diff."""
    added_node = AlteryxNode(
        tool_id=ToolID(10),
        tool_type="AlteryxBasePluginsGui.Sample.Sample",
        x=50.0,
        y=50.0,
        config={"n": 100},
    )
    removed_node = AlteryxNode(
        tool_id=ToolID(5),
        tool_type="AlteryxBasePluginsGui.Formula.Formula",
        x=75.0,
        y=75.0,
        config={"formula": "old"},
    )
    old_node = AlteryxNode(
        tool_id=ToolID(2),
        tool_type="AlteryxBasePluginsGui.Filter.Filter",
        x=100.0,
        y=0.0,
        config={"expression": "Amount > 50"},
    )
    new_node = AlteryxNode(
        tool_id=ToolID(2),
        tool_type="AlteryxBasePluginsGui.Filter.Filter",
        x=100.0,
        y=0.0,
        config={"expression": "Amount > 100"},
    )
    modified_node = NodeDiff(
        tool_id=ToolID(2),
        old_node=old_node,
        new_node=new_node,
        field_diffs={"expression": ("Amount > 50", "Amount > 100")},
    )
    edge_diff = EdgeDiff(
        src_tool=ToolID(1),
        src_anchor=AnchorName("Output"),
        dst_tool=ToolID(5),
        dst_anchor=AnchorName("Input"),
        change_type="removed",
    )
    return DiffResult(
        added_nodes=(added_node,),
        removed_nodes=(removed_node,),
        modified_nodes=(modified_node,),
        edge_diffs=(edge_diff,),
    )


# --- build_from_workflow tests ---


def test_build_from_workflow_keys(sample_doc):
    result = ContextBuilder.build_from_workflow(sample_doc)
    assert set(result.keys()) == {"workflow_name", "tool_count", "tools", "connections", "topology"}


def test_build_from_workflow_name_from_filepath(sample_doc):
    result = ContextBuilder.build_from_workflow(sample_doc)
    assert result["workflow_name"] == "MyWorkflow"


def test_build_from_workflow_topology_keys(sample_doc):
    result = ContextBuilder.build_from_workflow(sample_doc)
    assert set(result["topology"].keys()) == {"connections", "source_tools", "sink_tools", "branch_points"}


def test_build_from_workflow_tool_serialization(sample_doc):
    result = ContextBuilder.build_from_workflow(sample_doc)
    for tool in result["tools"]:
        assert isinstance(tool["tool_id"], int)
        assert isinstance(tool["tool_type"], str)
        assert isinstance(tool["config"], dict)


# --- build_from_diff tests ---


def test_build_from_diff_keys(sample_diff):
    result = ContextBuilder.build_from_diff(sample_diff)
    assert set(result.keys()) == {"summary", "changes"}


def test_build_from_diff_summary_counts(sample_diff):
    result = ContextBuilder.build_from_diff(sample_diff)
    summary = result["summary"]
    assert set(summary.keys()) == {"added_count", "removed_count", "modified_count", "edge_change_count"}
    assert summary["added_count"] == 1
    assert summary["removed_count"] == 1
    assert summary["modified_count"] == 1
    assert summary["edge_change_count"] == 1


def test_build_from_diff_changes_categories(sample_diff):
    result = ContextBuilder.build_from_diff(sample_diff)
    changes = result["changes"]
    assert set(changes.keys()) == {"added", "removed", "modified", "edge_changes"}


def test_build_from_diff_field_diffs_are_lists(sample_diff):
    result = ContextBuilder.build_from_diff(sample_diff)
    for mod in result["changes"]["modified"]:
        for val in mod["field_diffs"].values():
            assert isinstance(val, list), f"Expected list, got {type(val)}"


# --- strip_noise integration ---


def test_build_from_workflow_strip_noise():
    """build_from_workflow applies strip_noise to each tool's config."""
    # ISO8601 timestamp in config — strip_noise replaces it with __TIMESTAMP__
    node = AlteryxNode(
        tool_id=ToolID(1),
        tool_type="AlteryxBasePluginsGui.DbFileInput.DbFileInput",
        x=0.0,
        y=0.0,
        config={"LastModified": "2024-03-15T14:30:00Z", "file": "data.csv"},
    )
    doc = WorkflowDoc(filepath="/workflows/MyWorkflow.yxmd", nodes=(node,), connections=())
    result = ContextBuilder.build_from_workflow(doc)
    tool_config = result["tools"][0]["config"]
    # ISO8601 timestamp should be replaced by __TIMESTAMP__ sentinel
    assert tool_config["LastModified"] == "__TIMESTAMP__", (
        f"Expected __TIMESTAMP__ sentinel but got: {tool_config['LastModified']!r}"
    )
    # Non-noise values should be preserved
    assert tool_config["file"] == "data.csv"
