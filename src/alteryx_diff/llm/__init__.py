"""LLM subpackage for alteryx-diff.

Install extras to enable: pip install 'alteryx-diff[llm]'
"""
from __future__ import annotations

__all__ = ["require_llm_deps"]


def require_llm_deps() -> None:
    """Check that LLM extras are installed; raise ImportError with install hint if not.

    Call this at the top of any function that uses langchain/langgraph to give
    users a clear, actionable error message.

    Raises:
        ImportError: When langchain or langgraph are not installed.
    """
    try:
        import langchain  # noqa: F401
    except ImportError:
        raise ImportError(
            "LLM features require optional dependencies. "
            "Install them with: pip install 'alteryx-diff[llm]'"
        ) from None

    try:
        import langgraph  # noqa: F401
    except ImportError:
        raise ImportError(
            "LLM features require optional dependencies. "
            "Install them with: pip install 'alteryx-diff[llm]'"
        ) from None
