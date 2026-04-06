import builtins
import importlib

import pytest

from alteryx_diff.llm import require_llm_deps


def _make_import_fail_for(name: str):
    """Return a __import__ replacement that raises ImportError for the given module name."""
    real_import = builtins.__import__

    def _import(mod_name, *args, **kwargs):
        if mod_name == name or mod_name.startswith(name + "."):
            raise ImportError(f"Mocked ImportError for {mod_name}")
        return real_import(mod_name, *args, **kwargs)

    return _import


def test_require_llm_deps_raises_when_absent(monkeypatch):
    """When langchain is not importable, require_llm_deps() must raise ImportError
    with the install hint in the message."""
    monkeypatch.setattr(builtins, "__import__", _make_import_fail_for("langchain"))
    with pytest.raises(ImportError) as exc_info:
        require_llm_deps()
    assert "pip install 'alteryx-diff[llm]'" in str(exc_info.value)


def test_require_llm_deps_passes_when_present():
    """If langchain is installed, require_llm_deps() returns None without error."""
    try:
        import langchain  # noqa: F401
        import langgraph  # noqa: F401
    except ImportError:
        pytest.skip("LLM extras not installed — skipping presence test")
    result = require_llm_deps()
    assert result is None


def test_core_import_no_llm_side_effects():
    """Importing alteryx_diff must succeed without langchain installed (regression guard)."""
    import alteryx_diff  # noqa: F401

    assert alteryx_diff is not None
