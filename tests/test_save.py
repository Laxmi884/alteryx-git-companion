"""Tests for Phase 13 Save Version.

Covers git_commit_files, git_undo_last_commit, git_discard_files,
and /api/save endpoints.
"""

from __future__ import annotations

import subprocess

import pytest

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_git_repo(path):
    """Create a minimal git repo with one commit in `path` and return `path`."""
    workflow = path / "workflow.yxmd"
    workflow.write_text("v1")
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


# ---------------------------------------------------------------------------
# git_ops unit tests — SAVE-01: git_commit_files
# ---------------------------------------------------------------------------


def test_git_commit_files(tmp_path):
    """SAVE-01: git_commit_files stages specific files and creates a commit."""
    try:
        from app.services.git_ops import git_commit_files  # noqa: F401
    except ImportError:
        pytest.fail("git_commit_files not yet implemented in git_ops.py")
    pytest.fail("Stub — implement git_commit_files and update this test")


def test_commit_only_selected_files(tmp_path):
    """SAVE-01: when two files changed, only the selected one appears in the commit."""
    try:
        from app.services.git_ops import git_commit_files  # noqa: F401
    except ImportError:
        pytest.fail("git_commit_files not yet implemented in git_ops.py")
    pytest.fail(
        "Stub — implement git_commit_files (selected-files) and update this test"
    )


def test_git_commit_files_empty_files_list(tmp_path):
    """SAVE-01: empty files list raises CalledProcessError or returns gracefully."""
    try:
        from app.services.git_ops import git_commit_files  # noqa: F401
    except ImportError:
        pytest.fail("git_commit_files not yet implemented in git_ops.py")
    pytest.fail("Stub — implement git_commit_files (empty list) and update this test")


# ---------------------------------------------------------------------------
# git_ops unit tests — SAVE-02: git_undo_last_commit
# ---------------------------------------------------------------------------


def test_git_undo_last_commit(tmp_path):
    """SAVE-02: after soft reset, commit count decreases by 1."""
    try:
        from app.services.git_ops import git_undo_last_commit  # noqa: F401
    except ImportError:
        pytest.fail("git_undo_last_commit not yet implemented in git_ops.py")
    pytest.fail("Stub — implement git_undo_last_commit and update this test")


def test_git_undo_preserves_file_content(tmp_path):
    """SAVE-02: file bytes before undo == file bytes after undo."""
    try:
        from app.services.git_ops import git_undo_last_commit  # noqa: F401
    except ImportError:
        pytest.fail("git_undo_last_commit not yet implemented in git_ops.py")
    pytest.fail(
        "Stub — implement git_undo_last_commit (file preservation) and update this test"
    )


# ---------------------------------------------------------------------------
# git_ops unit tests — SAVE-03: git_discard_files
# ---------------------------------------------------------------------------


def test_git_discard_files_backup(tmp_path):
    """SAVE-03: before checkout, file appears in .acd-backup/."""
    try:
        from app.services.git_ops import git_discard_files  # noqa: F401
    except ImportError:
        pytest.fail("git_discard_files not yet implemented in git_ops.py")
    pytest.fail("Stub — implement git_discard_files (backup) and update this test")


def test_git_discard_files_restore(tmp_path):
    """SAVE-03: tracked file restored to HEAD content."""
    try:
        from app.services.git_ops import git_discard_files  # noqa: F401
    except ImportError:
        pytest.fail("git_discard_files not yet implemented in git_ops.py")
    pytest.fail("Stub — implement git_discard_files (restore) and update this test")


def test_git_discard_untracked(tmp_path):
    """SAVE-03: untracked file copied to .acd-backup/ then removed from working dir."""
    try:
        from app.services.git_ops import git_discard_files  # noqa: F401
    except ImportError:
        pytest.fail("git_discard_files not yet implemented in git_ops.py")
    pytest.fail("Stub — implement git_discard_files (untracked) and update this test")


# ---------------------------------------------------------------------------
# Endpoint tests — SAVE-01, SAVE-02, SAVE-03
# ---------------------------------------------------------------------------


def test_commit_endpoint(client, tmp_path):
    """SAVE-01: POST /api/save/commit returns 200 {"ok": true}."""
    try:
        import app.routers.save  # noqa: F401
    except ImportError:
        pytest.fail("app.routers.save not yet implemented")
    pytest.fail("Stub — implement /api/save/commit endpoint and update this test")


def test_commit_empty_files(client, tmp_path):
    """SAVE-01: POST /api/save/commit with files: [] returns 400."""
    try:
        import app.routers.save  # noqa: F401
    except ImportError:
        pytest.fail("app.routers.save not yet implemented")
    pytest.fail(
        "Stub — implement /api/save/commit empty-files validation and update this test"
    )


def test_undo_endpoint(client, tmp_path):
    """SAVE-02: POST /api/save/undo returns 200 {"ok": true}."""
    try:
        import app.routers.save  # noqa: F401
    except ImportError:
        pytest.fail("app.routers.save not yet implemented")
    pytest.fail("Stub — implement /api/save/undo endpoint and update this test")


def test_discard_endpoint(client, tmp_path):
    """SAVE-03: POST /api/save/discard returns 200 {"ok": true}."""
    try:
        import app.routers.save  # noqa: F401
    except ImportError:
        pytest.fail("app.routers.save not yet implemented")
    pytest.fail("Stub — implement /api/save/discard endpoint and update this test")
