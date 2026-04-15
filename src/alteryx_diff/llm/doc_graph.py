"""LangGraph 4-node documentation pipeline for Alteryx workflows.

Build a provider-agnostic documentation generation pipeline using LangGraph.

Exports:
    DocState: TypedDict for the graph state
    build_doc_graph: factory function that returns a compiled LangGraph
    generate_documentation: async convenience wrapper with single-retry on
        ValidationError
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from alteryx_diff.llm.models import (
    ChangeNarrative,
    DeveloperDocumentation,
    ToolNote,
    WorkflowDocumentation,
)

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

__all__ = [
    "build_doc_graph",
    "generate_documentation",
    "generate_change_narrative",
    "generate_workflow_documentation",
    "DocState",
]


class DocState(TypedDict):
    """State passed between LangGraph nodes in the documentation pipeline."""

    context: dict  # ContextBuilder output dict
    topology_notes: str  # analyze_topology output
    tool_annotations: str  # annotate_tools output (JSON string of tool notes)
    risk_notes: str  # risk_scan output
    raw_doc_json: str  # assemble_doc output — JSON string of WorkflowDocumentation
    validation_error: str  # empty on first pass; str(ValidationError) on retry


def build_doc_graph(llm: BaseChatModel) -> CompiledStateGraph:
    """Build and compile a LangGraph 4-node documentation pipeline.

    The pipeline runs linearly:
        START -> analyze_topology -> annotate_tools -> risk_scan -> assemble_doc -> END

    The llm argument is captured in a closure by each LLM-calling node.
    Any BaseChatModel subclass works — provider-agnostic by design.

    Args:
        llm: Any LangChain BaseChatModel (ChatOllama, ChatOpenAI, etc.)

    Returns:
        A compiled LangGraph StateGraph ready for ainvoke.
    """
    from langgraph.graph import END, START, StateGraph

    # --------------------------------------------------------------------------
    # Node 1: analyze_topology — pure Python, no LLM call
    # --------------------------------------------------------------------------

    async def analyze_topology(state: DocState) -> dict[str, Any]:
        """Summarize workflow topology from context. No LLM call."""
        topology = state["context"].get("topology", {})
        workflow_name = state["context"].get("workflow_name", "Unknown")
        tool_count = state["context"].get("tool_count", 0)

        source_tools = topology.get("source_tools", [])
        sink_tools = topology.get("sink_tools", [])
        branch_points = topology.get("branch_points", [])
        connections = topology.get("connections", [])

        lines = [
            f"Workflow: {workflow_name}",
            f"Total tools: {tool_count}",
            f"Entry points (source tools): {source_tools}",
            f"Exit points (sink tools): {sink_tools}",
        ]

        if branch_points:
            lines.append(f"Branch points (fan-out tools): {branch_points}")
        else:
            lines.append("Data flow: linear (no branching)")

        if connections:
            conn_desc = [
                f"  Tool {c['src_tool']} ({c['src_anchor']})"
                f" -> Tool {c['dst_tool']} ({c['dst_anchor']})"
                for c in connections
            ]
            lines.append("Connections:")
            lines.extend(conn_desc)

        return {"topology_notes": "\n".join(lines)}

    # --------------------------------------------------------------------------
    # Node 2: annotate_tools — single LLM call for all tools
    # --------------------------------------------------------------------------

    async def annotate_tools(state: DocState) -> dict[str, Any]:
        """Annotate each tool with a one-sentence role using structured LLM output."""
        tools = state["context"].get("tools", [])
        topology_notes = state["topology_notes"]

        system_msg = SystemMessage(
            content=(
                "You are a technical documentation assistant for Alteryx workflows. "
                "Only use information from the provided context — "
                "never invent tool names, IDs, or behaviors not present in the data.\n"
                "Rules:\n"
                "1. Set tool_type to the EXACT tool_type string from the tools list — "
                "copy it character-for-character. Never substitute anchor names "
                "(Output, Input, Left, Right, Join, True, False) for tool_type.\n"
                "2. Only describe what the config explicitly shows. "
                "Do not infer connection strings, database schemas, query details, "
                "or file formats beyond what is in the config.\n"
                "3. Describe the tool's specific role in this workflow using actual "
                "config values (expressions, aliases, modes, field names) — "
                "not generic descriptions of what the tool type does."
            )
        )
        # Build a compact type reference so the LLM copies types accurately.
        type_ref = ", ".join(f"{t['tool_id']}={t['tool_type']}" for t in tools)
        human_msg = HumanMessage(
            content=(
                f"Topology context:\n{topology_notes}\n\n"
                f"Tools:\n{json.dumps(tools, indent=2)}\n\n"
                f"Required tool_type values (copy exactly): {type_ref}\n\n"
                "For each tool: set tool_id and tool_type exactly as listed above, "
                "then write a one-sentence role based solely on the actual config "
                "values (expressions, aliases, modes, field names). "
                "Do not guess values that are absent from the config."
            )
        )

        try:
            structured_llm = llm.with_structured_output(
                list[ToolNote], method="json_schema"
            )
            result: list[ToolNote] = await structured_llm.ainvoke(
                [system_msg, human_msg]
            )
            annotations = json.dumps([note.model_dump() for note in result])
        except Exception:
            # Fallback: pass empty annotations; assemble_doc will handle
            annotations = json.dumps([])

        return {"tool_annotations": annotations}

    # --------------------------------------------------------------------------
    # Node 3: risk_scan — single LLM call for production risks
    # --------------------------------------------------------------------------

    async def risk_scan(state: DocState) -> dict[str, Any]:
        """Identify production risks using LLM."""
        context = state["context"]
        topology_notes = state["topology_notes"]

        system_msg = SystemMessage(
            content=(
                "You are a data quality and workflow reliability expert. "
                "Only identify risks that are directly evidenced by the provided "
                "workflow configuration — do not add generic best-practice advice "
                "(no monitoring, logging, retry, or permissions warnings unless the "
                "config explicitly shows a gap). "
                "Each risk must cite the specific tool ID or config value that "
                "motivates it. "
                "Return a JSON array of strings, each describing one production"
                " concern."
            )
        )
        human_msg = HumanMessage(
            content=(
                f"Topology:\n{topology_notes}\n\n"
                f"Workflow context:\n{json.dumps(context, indent=2)}\n\n"
                "List only risks grounded in the actual config: missing error paths, "
                "hardcoded file paths, filter conditions that may produce empty"
                " output, join modes that may drop records, or outputs with no"
                " downstream sink. Return as a JSON array of strings. "
                "If no grounded risks exist, return an empty array []."
            )
        )

        result = await llm.ainvoke([system_msg, human_msg])
        return {"risk_notes": result.content}

    # --------------------------------------------------------------------------
    # Node 4: assemble_doc — combine all prior analysis into WorkflowDocumentation
    # --------------------------------------------------------------------------

    async def assemble_doc(state: DocState) -> dict[str, Any]:
        """Assemble the final WorkflowDocumentation using structured LLM output."""
        context = state["context"]
        topology_notes = state["topology_notes"]
        tool_annotations = state["tool_annotations"]
        risk_notes = state["risk_notes"]
        validation_error = state.get("validation_error", "")

        system_content = (
            "You are a technical documentation writer for Alteryx workflows. "
            "Generate documentation based solely on the provided analysis — "
            "never invent workflow names, tool IDs, tool types, field names, "
            "expressions, file paths, or behaviors not present in the data.\n"
            "Rules:\n"
            "1. workflow_name must be taken verbatim from the context.\n"
            "2. In tool_notes, copy tool_id and tool_type exactly from the tool "
            "annotations — never use connection anchor names (Output, Input, Left, "
            "Right, Join, True, False) as tool_type.\n"
            "3. data_flow must follow the actual connections: describe tools in "
            "source-to-sink order as shown in the topology, referencing tool IDs.\n"
            "4. Do not infer schema, query, or connection details beyond what is "
            "explicitly in the config. If a value is absent, omit it rather than"
            " guess.\n"
            "5. risks must reference specific tool IDs or config values — no generic "
            "advice."
        )
        if validation_error:
            system_content += (
                f"\n\nPrevious attempt failed validation: {validation_error}. "
                "Fix the output to match the required schema exactly."
            )

        system_msg = SystemMessage(content=system_content)
        human_msg = HumanMessage(
            content=(
                f"Workflow name: {context.get('workflow_name', 'Unknown')}\n\n"
                f"Topology analysis:\n{topology_notes}\n\n"
                f"Tool annotations:\n{tool_annotations}\n\n"
                f"Risk analysis:\n{risk_notes}\n\n"
                "Generate complete WorkflowDocumentation with: "
                "workflow_name, intent (2-3 sentences), data_flow (prose), "
                "tool_notes (list with tool_id/tool_type/role),"
                " and risks (list of strings)."
            )
        )

        structured_llm = llm.with_structured_output(
            WorkflowDocumentation, method="json_schema"
        )
        result: WorkflowDocumentation = await structured_llm.ainvoke(
            [system_msg, human_msg]
        )
        return {"raw_doc_json": result.model_dump_json()}

    # --------------------------------------------------------------------------
    # Wire up the graph nodes in sequence
    # --------------------------------------------------------------------------

    builder: StateGraph = StateGraph(DocState)
    builder.add_node("analyze_topology", analyze_topology)
    builder.add_node("annotate_tools", annotate_tools)
    builder.add_node("risk_scan", risk_scan)
    builder.add_node("assemble_doc", assemble_doc)

    builder.add_edge(START, "analyze_topology")
    builder.add_edge("analyze_topology", "annotate_tools")
    builder.add_edge("annotate_tools", "risk_scan")
    builder.add_edge("risk_scan", "assemble_doc")
    builder.add_edge("assemble_doc", END)

    return builder.compile()


async def generate_documentation(
    context: dict,
    llm: BaseChatModel,
) -> WorkflowDocumentation:
    """Generate workflow documentation using the 4-node LangGraph pipeline.

    Runs the pipeline once. If the assembled document fails Pydantic validation,
    retries exactly once with the validation error appended to the state so the
    assemble_doc node can correct its output.

    Args:
        context: ContextBuilder output dict (workflow_name, tools, connections,
            topology)
        llm: Any LangChain BaseChatModel (provider-agnostic)

    Returns:
        A validated WorkflowDocumentation instance.

    Raises:
        pydantic.ValidationError: If both the first attempt and the retry fail
            validation.
    """
    from pydantic import ValidationError

    graph = build_doc_graph(llm)
    initial_state: DocState = {
        "context": context,
        "topology_notes": "",
        "tool_annotations": "",
        "risk_notes": "",
        "raw_doc_json": "",
        "validation_error": "",
    }

    state = await graph.ainvoke(initial_state)
    try:
        return WorkflowDocumentation.model_validate_json(state["raw_doc_json"])
    except ValidationError as e:
        # Single retry: re-run the full pipeline with validation error in state
        retry_state: DocState = {**initial_state, "validation_error": str(e)}
        state = await graph.ainvoke(retry_state)
        return WorkflowDocumentation.model_validate_json(state["raw_doc_json"])


async def generate_change_narrative(
    context: dict,
    llm: BaseChatModel,
) -> ChangeNarrative:
    """Generate a change narrative for a diff using a single structured LLM call.

    Unlike generate_documentation(), this does not use a LangGraph multi-node
    pipeline — the input context is already a compact summary+changes dict, so
    a single structured_output call is sufficient.

    Args:
        context: ContextBuilder.build_from_diff() output dict with {summary, changes}.
        llm: Any LangChain BaseChatModel.

    Returns:
        A validated ChangeNarrative instance.
    """
    system_msg = SystemMessage(
        content=(
            "Only describe changes present in the provided diff context. "
            "Do not invent tools, IDs, or behaviors. "
            "Be concrete about what was added, removed, or modified."
        )
    )
    human_msg = HumanMessage(
        content=(
            "Diff context:\n"
            f"{json.dumps(context, indent=2)}\n\n"
            "Provide:\n"
            "1. A 2-4 paragraph narrative explaining the functional impact"
            " of these changes.\n"
            "2. A list of production/risk concerns (may be empty if none apply)."
        )
    )
    structured_llm = llm.with_structured_output(ChangeNarrative, method="json_schema")
    result: ChangeNarrative = await structured_llm.ainvoke([system_msg, human_msg])
    return result


async def generate_workflow_documentation(
    context: dict,
    llm: BaseChatModel,
) -> DeveloperDocumentation:
    """Generate comprehensive developer-grade documentation for a new workflow.

    Used for initial commits. Uses explicit JSON prompting for broad provider
    compatibility.
    """
    import re

    from pydantic import ValidationError

    business_context = context.get("business_context", "")
    bc_section = f"Business context: {business_context}\n" if business_context else ""

    schema_example = json.dumps(
        {
            "workflow_name": "ExampleWorkflow",
            "overview": (
                "4-6 sentence purpose, business context, scope, and intended audience."
            ),
            "assumptions": "1. First assumption.\n2. Second assumption.",
            "data_sources": (
                "1. Tool 1 (DbFileInput): Queries SCHEMA.TABLE for FIELD1, FIELD2"
                " where CONDITION.\n2. Tool 2 (DbFileInput): ..."
            ),
            "transformations": (
                "1. Step name (Tool N): What it does and why."
                "\n2. Step name (Tool N): ..."
            ),
            "data_flow": (
                "Main flow: Source A → Join (Tool N) → Filter (Tool N) → Output."
                "\nValidation flow: ..."
            ),
            "outputs": (
                "1. Primary Output (Tool N): Path, format, delimiter, schema, purpose."
                "\n2. ..."
            ),
            "data_dictionary": (
                "1. FIELD_NAME (String): Description. Example: 'ABC123'."
                "\n2. FIELD_NAME (Integer): ..."
            ),
            "tool_inventory": (
                "1. Tool 1 (ToolType): Specific role in this workflow."
                "\n2. Tool 2 (ToolType): ..."
            ),
            "dependencies": (
                "1. ConnectionAlias: System, schema/path, access required.\n2. ..."
            ),
            "configuration_notes": (
                "1. PARAMETER_NAME: Current value. Update to X for quarterly run Y."
                "\n2. ..."
            ),
            "execution_guide": (
                "1. Open workflow in Alteryx Designer."
                "\n2. Update snapshot_month parameter.\n3. ..."
            ),
            "error_handling": (
                "1. Tool N Test: Checks X, expects Y. If fails: do Z.\n2. ..."
            ),
            "risks": ["Specific production risk with impact and recommendation."],
        },
        indent=2,
    )

    system_msg = SystemMessage(
        content=(
            "You are a senior data engineer writing comprehensive developer"
            " documentation for an Alteryx workflow. "
            "Respond ONLY with a single valid JSON object —"
            " no markdown fences, no explanation outside the JSON. "
            "Be thorough and specific. Only use facts from the provided context."
        )
    )
    tools_json = json.dumps(context.get("tools", []), indent=2)
    conns_json = json.dumps(context.get("connections", []), indent=2)
    topo_json = json.dumps(context.get("topology", {}), indent=2)
    human_msg = HumanMessage(
        content=(
            f"Workflow: {context.get('workflow_name', 'Unknown')}\n"
            f"{bc_section}"
            f"Tools ({context.get('tool_count', 0)}):\n{tools_json}\n\n"
            f"Connections:\n{conns_json}\n\n"
            f"Topology: {topo_json}\n\n"
            f"Return a JSON object exactly matching this schema:\n{schema_example}"
        )
    )
    response = await llm.ainvoke([system_msg, human_msg])
    raw = response.content if hasattr(response, "content") else str(response)

    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw.strip())

    try:
        return DeveloperDocumentation.model_validate_json(raw.strip())
    except (ValidationError, ValueError):
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return DeveloperDocumentation.model_validate_json(match.group())
        raise
