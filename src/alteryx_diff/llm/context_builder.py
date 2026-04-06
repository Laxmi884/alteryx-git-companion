"""ContextBuilder: transforms WorkflowDoc/DiffResult into token-efficient dicts for LLM consumption.

No LLM imports here — only alteryx_diff.models and networkx.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx

from alteryx_diff.models.diff import DiffResult
from alteryx_diff.models.workflow import WorkflowDoc
from alteryx_diff.normalizer._strip import strip_noise


def _compute_topology(doc: WorkflowDoc) -> dict[str, Any]:
    """Build a NetworkX DiGraph from the workflow and compute topology metadata."""
    G: nx.DiGraph[int] = nx.DiGraph()
    for node in doc.nodes:
        G.add_node(int(node.tool_id))
    for conn in doc.connections:
        src = int(conn.src_tool)
        dst = int(conn.dst_tool)
        G.add_edge(src, dst)

    serialized_connections = [
        {
            "src_tool": int(c.src_tool),
            "src_anchor": str(c.src_anchor),
            "dst_tool": int(c.dst_tool),
            "dst_anchor": str(c.dst_anchor),
        }
        for c in doc.connections
    ]

    return {
        "connections": serialized_connections,
        "source_tools": [n for n in G.nodes if G.in_degree(n) == 0],
        "sink_tools": [n for n in G.nodes if G.out_degree(n) == 0],
        "branch_points": [n for n in G.nodes if G.out_degree(n) > 1],
    }


class ContextBuilder:
    """Transforms WorkflowDoc and DiffResult dataclasses into token-efficient JSON dicts."""

    @staticmethod
    def build_from_workflow(doc: WorkflowDoc) -> dict[str, Any]:
        """Serialize a WorkflowDoc into a structured dict for LLM context.

        Returns:
            dict with keys: workflow_name, tool_count, tools, connections, topology
        """
        workflow_name = Path(doc.filepath).stem

        tools = [
            {
                "tool_id": int(node.tool_id),
                "tool_type": node.tool_type,
                "config": strip_noise(node.config),
            }
            for node in doc.nodes
        ]

        connections = [
            {
                "src_tool": int(c.src_tool),
                "src_anchor": str(c.src_anchor),
                "dst_tool": int(c.dst_tool),
                "dst_anchor": str(c.dst_anchor),
            }
            for c in doc.connections
        ]

        topology = _compute_topology(doc)

        return {
            "workflow_name": workflow_name,
            "tool_count": len(doc.nodes),
            "tools": tools,
            "connections": connections,
            "topology": topology,
        }

    @staticmethod
    def build_from_diff(result: DiffResult) -> dict[str, Any]:
        """Serialize a DiffResult into a structured dict for LLM context.

        Returns:
            dict with keys: summary, changes
        """
        summary = {
            "added_count": len(result.added_nodes),
            "removed_count": len(result.removed_nodes),
            "modified_count": len(result.modified_nodes),
            "edge_change_count": len(result.edge_diffs),
        }

        added = [
            {"tool_id": int(n.tool_id), "tool_type": n.tool_type}
            for n in result.added_nodes
        ]

        removed = [
            {"tool_id": int(n.tool_id), "tool_type": n.tool_type}
            for n in result.removed_nodes
        ]

        modified = [
            {
                "tool_id": int(nd.tool_id),
                "tool_type": nd.new_node.tool_type,
                "field_diffs": {field: list(vals) for field, vals in nd.field_diffs.items()},
            }
            for nd in result.modified_nodes
        ]

        edge_changes = [
            {
                "change_type": ed.change_type,
                "src_tool": int(ed.src_tool),
                "dst_tool": int(ed.dst_tool),
                "anchors": {"src": str(ed.src_anchor), "dst": str(ed.dst_anchor)},
            }
            for ed in result.edge_diffs
        ]

        changes = {
            "added": added,
            "removed": removed,
            "modified": modified,
            "edge_changes": edge_changes,
        }

        return {
            "summary": summary,
            "changes": changes,
        }
