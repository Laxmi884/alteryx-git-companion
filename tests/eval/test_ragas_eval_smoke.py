"""Smoke tests for tests/eval/ragas_eval.py helper functions.

Tests validate env-var guarding, context serialization, and pipeline bridge
WITHOUT requiring a live LLM or ragas installed. The module must be importable
without [llm] extras (Pitfall 5 compliance).
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tests.eval.ragas_eval import (
    _build_llm_from_env,
    _context_to_strings,
    _workflow_bytes_to_context,
)


# ---------------------------------------------------------------------------
# Env-var guard tests (_build_llm_from_env)
# ---------------------------------------------------------------------------


def test_missing_env_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    """_build_llm_from_env exits(1) when required env var is not set."""
    monkeypatch.delenv("ACD_LLM_MODEL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        _build_llm_from_env("ACD_LLM_MODEL", required=True)

    assert exc_info.value.code == 1


def test_optional_env_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """_build_llm_from_env returns None when optional env var is not set."""
    monkeypatch.delenv("RAGAS_CRITIC_MODEL", raising=False)

    result = _build_llm_from_env("RAGAS_CRITIC_MODEL", required=False)

    assert result is None


def test_invalid_format_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    """_build_llm_from_env exits(1) when env var has no 'provider:model' colon separator."""
    monkeypatch.setenv("ACD_LLM_MODEL", "no-colon")

    with pytest.raises(SystemExit) as exc_info:
        _build_llm_from_env("ACD_LLM_MODEL")

    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Context serialization tests (_context_to_strings)
# ---------------------------------------------------------------------------


def test_context_to_strings_returns_list_of_str() -> None:
    """_context_to_strings returns a list[str] of JSON chunks, one per key."""
    context = {"workflow_name": "Test", "tool_count": 2}
    result = _context_to_strings(context)

    assert isinstance(result, list)
    assert len(result) == 2
    for item in result:
        assert isinstance(item, str)
        parsed = json.loads(item)
        assert isinstance(parsed, dict)
        assert len(parsed) == 1


def test_context_to_strings_no_raw_xml() -> None:
    """_context_to_strings output must not contain XML angle brackets.

    Enforces D-03: ContextBuilder structured output (not raw XML) as contexts.
    """
    context = {"workflow_name": "Test", "tools": [{"tool_id": 1}]}
    result = _context_to_strings(context)

    for chunk in result:
        assert "<" not in chunk, f"XML '<' found in context chunk: {chunk!r}"
        assert ">" not in chunk, f"XML '>' found in context chunk: {chunk!r}"


# ---------------------------------------------------------------------------
# Pipeline bridge test (_workflow_bytes_to_context)
# ---------------------------------------------------------------------------


def test_workflow_bytes_to_context_returns_expected_keys(tmp_path: pathlib.Path) -> None:
    """parse_one + ContextBuilder pipeline returns dict with all expected keys."""
    from tests.fixtures.pipeline import MINIMAL_YXMD_A

    context = _workflow_bytes_to_context(MINIMAL_YXMD_A, "smoke_test")

    assert isinstance(context, dict)
    expected_keys = {"workflow_name", "tool_count", "tools", "connections", "topology"}
    assert expected_keys == set(context.keys()), (
        f"Missing keys: {expected_keys - set(context.keys())}"
    )
