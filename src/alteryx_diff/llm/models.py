"""Pydantic output models for LLM-generated workflow documentation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolNote(BaseModel):
    tool_id: int
    tool_type: str
    role: str = Field(description="One sentence: what this tool does in context")


class WorkflowDocumentation(BaseModel):
    workflow_name: str
    intent: str = Field(description="2-3 sentences: what the workflow accomplishes")
    data_flow: str = Field(description="Prose: how data moves source-to-sink")
    tool_notes: list[ToolNote]
    risks: list[str] = Field(
        description="Production concerns: data quality, config gotchas"
    )


class DeveloperDocumentation(BaseModel):
    """Comprehensive developer-grade documentation for an Alteryx workflow."""

    workflow_name: str
    overview: str = Field(
        description=(
            "Purpose, business context, scope, and intended audience — 4-6 sentences"
        )
    )
    assumptions: str = Field(
        description=(
            "Numbered list of business/technical assumptions"
            " baked into the workflow logic"
        )
    )
    data_sources: str = Field(
        description=(
            "Numbered list: each source on its own line with system, schema.table,"
            " fields retrieved, and filter conditions"
        )
    )
    transformations: str = Field(
        description=(
            "Numbered list: each transformation step on its own line with tool ID,"
            " logic, and output"
        )
    )
    data_flow: str = Field(
        description=(
            "End-to-end narrative: main flow and all validation/error sub-flows"
            " described stage by stage"
        )
    )
    outputs: str = Field(
        description=(
            "Numbered list: each output on its own line with path, format, schema,"
            " encoding, and purpose"
        )
    )
    data_dictionary: str = Field(
        description=(
            "Numbered list: each output field on its own line — field name, data type,"
            " description, and example value"
        )
    )
    tool_inventory: str = Field(
        description=(
            "Numbered list: each tool on its own line — Tool ID, tool type, and"
            " specific role in this workflow"
        )
    )
    dependencies: str = Field(
        description=(
            "Numbered list: each dependency on its own line — connection alias, system,"
            " schemas/paths, and access required"
        )
    )
    configuration_notes: str = Field(
        description=(
            "Numbered list: each configurable item on its own line — parameter,"
            " current value, and what to change per run"
        )
    )
    execution_guide: str = Field(
        description=(
            "Step-by-step instructions for running this workflow each quarterly cycle"
        )
    )
    error_handling: str = Field(
        description=(
            "Numbered list: each validation check on its own line — what it checks,"
            " expected result, and mitigation if it fails"
        )
    )
    risks: list[str] = Field(
        description=(
            "Production concerns: performance, data quality, config gotchas,"
            " known bugs, scheduling notes"
        )
    )


class ChangeNarrative(BaseModel):
    """AI-generated narrative for a diff between two Alteryx workflows."""

    narrative: str  # 2-4 paragraph prose description of what changed and why it matters
    risks: list[
        str
    ] = []  # Production/data-quality concerns flagged by the LLM; may be empty
