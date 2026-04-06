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
    risks: list[str] = Field(description="Production concerns: data quality, config gotchas")


class ChangeNarrative(BaseModel):
    """AI-generated narrative for a diff between two Alteryx workflows."""

    narrative: str  # 2-4 paragraph prose description of what changed and why it matters
    risks: list[str] = []  # Production/data-quality concerns flagged by the LLM; may be empty
