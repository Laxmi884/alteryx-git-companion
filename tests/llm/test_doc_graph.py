"""Unit tests for DocumentationGraph pipeline (doc_graph.py).

Tests use mock LLM from conftest.py to avoid real LLM calls.
Async tests use asyncio.run() directly (no pytest-asyncio required).
"""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("langchain")

from alteryx_diff.llm.models import WorkflowDocumentation
from tests.llm.conftest import sample_workflow_documentation


def _make_mock_llm(
    structured_return: Any = None,
    ainvoke_return_content: str = "topology notes",
) -> MagicMock:
    """Create a fully-configured mock LLM for pipeline tests."""
    if structured_return is None:
        structured_return = sample_workflow_documentation()
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content=ainvoke_return_content))
    structured_chain = MagicMock()
    structured_chain.ainvoke = AsyncMock(return_value=structured_return)
    llm.with_structured_output = MagicMock(return_value=structured_chain)
    return llm


# ---------------------------------------------------------------------------
# Test 1: build_doc_graph returns a compiled graph with ainvoke
# ---------------------------------------------------------------------------


def test_build_doc_graph_returns_compiled(mock_llm: MagicMock) -> None:
    """build_doc_graph(mock_llm) returns an object with an ainvoke method."""
    from alteryx_diff.llm.doc_graph import build_doc_graph

    graph = build_doc_graph(mock_llm)
    assert hasattr(graph, "ainvoke"), "Compiled graph must expose ainvoke"


# ---------------------------------------------------------------------------
# Test 2: generate_documentation returns a WorkflowDocumentation instance
# ---------------------------------------------------------------------------


def test_generate_documentation_returns_model(
    mock_llm: MagicMock, sample_context: dict
) -> None:
    """generate_documentation returns a WorkflowDocumentation with all fields."""
    from alteryx_diff.llm.doc_graph import generate_documentation

    doc = asyncio.run(generate_documentation(sample_context, mock_llm))
    assert isinstance(doc, WorkflowDocumentation)
    assert doc.workflow_name
    assert doc.intent
    assert doc.data_flow
    assert isinstance(doc.tool_notes, list)
    assert isinstance(doc.risks, list)


# ---------------------------------------------------------------------------
# Test 3: workflow_name matches context["workflow_name"]
# ---------------------------------------------------------------------------


def test_generate_documentation_workflow_name(
    mock_llm: MagicMock, sample_context: dict
) -> None:
    """Returned doc.workflow_name matches context['workflow_name']."""
    from alteryx_diff.llm.doc_graph import generate_documentation

    doc = asyncio.run(generate_documentation(sample_context, mock_llm))
    assert doc.workflow_name == sample_context["workflow_name"]


# ---------------------------------------------------------------------------
# Test 4: pipeline actually invokes the LLM
# ---------------------------------------------------------------------------


def test_pipeline_calls_llm(mock_llm: MagicMock, sample_context: dict) -> None:
    """After generate_documentation, the LLM was actually called (ainvoke or with_structured_output)."""
    from alteryx_diff.llm.doc_graph import generate_documentation

    asyncio.run(generate_documentation(sample_context, mock_llm))
    # Either with_structured_output or ainvoke must have been called
    called = mock_llm.with_structured_output.called or mock_llm.ainvoke.called
    assert called, "LLM must be invoked during pipeline execution"


# ---------------------------------------------------------------------------
# Test 5: single retry on ValidationError
# ---------------------------------------------------------------------------


def test_retry_on_validation_error(sample_context: dict) -> None:
    """When assemble_doc returns invalid JSON on first call and valid JSON on second, generate_documentation succeeds."""
    from alteryx_diff.llm.doc_graph import generate_documentation

    valid_doc = sample_workflow_documentation()

    # Bad doc returns invalid JSON that won't validate as WorkflowDocumentation
    bad_doc = MagicMock()
    bad_doc.model_dump_json = MagicMock(return_value='{"bad": "json"}')

    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content='["risk1"]'))

    annotate_chain = MagicMock()
    annotate_chain.ainvoke = AsyncMock(return_value=[])

    assemble_chain_bad = MagicMock()
    assemble_chain_bad.ainvoke = AsyncMock(return_value=bad_doc)

    assemble_chain_good = MagicMock()
    assemble_chain_good.ainvoke = AsyncMock(return_value=valid_doc)

    # with_structured_output is called:
    # call 1: annotate_tools (first pass)
    # call 2: assemble_doc (first pass) -> bad
    # call 3: annotate_tools (retry pass)
    # call 4: assemble_doc (retry pass) -> good
    llm.with_structured_output = MagicMock(
        side_effect=[
            annotate_chain,
            assemble_chain_bad,
            annotate_chain,
            assemble_chain_good,
        ]
    )

    doc = asyncio.run(generate_documentation(sample_context, llm))
    assert isinstance(doc, WorkflowDocumentation)
    assert doc.workflow_name == valid_doc.workflow_name


# ---------------------------------------------------------------------------
# Test 6: retry exhausted raises ValidationError
# ---------------------------------------------------------------------------


def test_retry_exhausted_raises(sample_context: dict) -> None:
    """When assemble_doc returns invalid JSON on both calls, ValidationError is raised."""
    from pydantic import ValidationError

    from alteryx_diff.llm.doc_graph import generate_documentation

    bad_doc = MagicMock()
    bad_doc.model_dump_json = MagicMock(return_value='{"bad": "json"}')

    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content='["risk1"]'))

    annotate_chain = MagicMock()
    annotate_chain.ainvoke = AsyncMock(return_value=[])

    assemble_chain_bad = MagicMock()
    assemble_chain_bad.ainvoke = AsyncMock(return_value=bad_doc)

    llm.with_structured_output = MagicMock(
        side_effect=[
            annotate_chain,
            assemble_chain_bad,
            annotate_chain,
            assemble_chain_bad,
        ]
    )

    with pytest.raises(ValidationError):
        asyncio.run(generate_documentation(sample_context, llm))


# ---------------------------------------------------------------------------
# Test 7: provider-agnostic (any object with ainvoke + with_structured_output)
# ---------------------------------------------------------------------------


def test_provider_agnostic(sample_context: dict) -> None:
    """generate_documentation works with any object that has ainvoke and with_structured_output."""
    from alteryx_diff.llm.doc_graph import generate_documentation

    # Simulate a different provider (e.g., ChatOllama shape)
    valid_doc = sample_workflow_documentation()

    provider_llm = MagicMock()
    provider_llm.ainvoke = AsyncMock(return_value=MagicMock(content='["risk from provider"]'))
    structured_chain = MagicMock()
    structured_chain.ainvoke = AsyncMock(return_value=valid_doc)
    provider_llm.with_structured_output = MagicMock(return_value=structured_chain)

    doc = asyncio.run(generate_documentation(sample_context, provider_llm))
    assert isinstance(doc, WorkflowDocumentation)
    assert provider_llm.with_structured_output.called or provider_llm.ainvoke.called
