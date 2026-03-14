"""Git operations service — subprocess wrappers for git commands."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def is_git_repo(folder: str) -> bool:
    """Return True if the folder is inside a git repository."""
    result = subprocess.run(
        ["git", "-C", folder, "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def git_init(folder: str) -> None:
    """Initialise a new git repository in the given folder."""
    subprocess.run(
        ["git", "-C", folder, "init"],
        capture_output=True,
        text=True,
        check=True,
    )


def get_git_identity() -> dict:
    """Return global git user.name and user.email as {'name': ..., 'email': ...}."""

    def _get(key: str) -> str | None:
        r = subprocess.run(
            ["git", "config", "--global", key],
            capture_output=True,
            text=True,
        )  # check=False intentional — exit 1 means key not set, not an error
        return r.stdout.strip() or None

    return {"name": _get("user.name"), "email": _get("user.email")}


def set_git_identity(name: str, email: str) -> None:
    """Set global git user.name and user.email."""
    subprocess.run(["git", "config", "--global", "user.name", name], check=True)
    subprocess.run(["git", "config", "--global", "user.email", email], check=True)


WORKFLOW_SUFFIXES = frozenset({".yxmd", ".yxwz", ".yxmc", ".yxzp", ".yxapp"})


def git_changed_workflows(folder: str) -> list[str]:
    """Return Alteryx workflow files modified vs git HEAD (git status --porcelain v1).

    Includes staged modifications, unstaged modifications, and untracked new files.
    Does NOT include files that are only in git's index with no changes.
    """
    result = subprocess.run(
        ["git", "-C", folder, "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    changed: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        filename = line[3:].strip()
        # Handle rename format: "ORIG_PATH -> NEW_PATH" — take the new path
        if " -> " in filename:
            filename = filename.split(" -> ")[-1].strip()
        from pathlib import Path

        if Path(filename).suffix in WORKFLOW_SUFFIXES:
            changed.append(filename)
    return changed


def count_workflows(folder: str) -> int:
    """Count all Alteryx workflow files in folder (recursive)."""
    from pathlib import Path

    p = Path(folder)
    return sum(1 for f in p.rglob("*") if f.is_file() and f.suffix in WORKFLOW_SUFFIXES)


def git_has_commits(folder: str) -> bool:
    """Return True if the repo has at least one commit (HEAD exists).

    SAFE: git rev-parse HEAD exits with code 128 on a repo with no commits.
    Do NOT change the returncode check — 'HEAD' appearing in stdout is not a
    reliable signal (it also appears on an empty repo in some git versions).
    """
    result = subprocess.run(
        ["git", "-C", folder, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def git_commit_files(folder: str, files: list[str], message: str) -> None:
    """Stage specific files and create a commit.

    Only the explicitly passed files are staged — respects user checkbox selection.
    Raises ValueError for empty files list.
    Raises subprocess.CalledProcessError if git commit fails.
    Empty message defaults to 'Save' to avoid git commit rejection.
    """
    if not files:
        raise ValueError("files list must not be empty")
    subprocess.run(
        ["git", "-C", folder, "add", "--"] + files,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", folder, "commit", "-m", message or "Save"],
        capture_output=True,
        text=True,
        check=True,
    )


def git_undo_last_commit(folder: str) -> None:
    """Remove the last commit, keep working tree changes (soft reset).

    Raises subprocess.CalledProcessError if no parent commit exists.
    """
    subprocess.run(
        ["git", "-C", folder, "reset", "--soft", "HEAD~1"],
        capture_output=True,
        text=True,
        check=True,
    )


def _is_tracked(folder: str, rel_path: str) -> bool:
    """Return True if rel_path is tracked by git (not untracked/new)."""
    r = subprocess.run(
        ["git", "-C", folder, "ls-files", "--error-unmatch", rel_path],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def git_discard_files(folder: str, files: list[str]) -> None:
    """Copy files to .acd-backup, then restore tracked files to HEAD.

    For untracked files: copy to backup then delete from working dir.
    For tracked files: copy to backup then git checkout -- to restore HEAD version.
    .acd-backup is flat (files placed by basename). Name collision is acceptable
    for v1 — users can recover manually from backup folder.
    Always copies BEFORE removing — never destructive without backup.
    """
    backup_dir = Path(folder) / ".acd-backup"
    backup_dir.mkdir(exist_ok=True)

    tracked_files: list[str] = []
    untracked_files: list[str] = []

    for rel_path in files:
        src = Path(folder) / rel_path
        if src.exists():
            shutil.copy2(src, backup_dir / src.name)
        if _is_tracked(folder, rel_path):
            tracked_files.append(rel_path)
        else:
            untracked_files.append(rel_path)

    if tracked_files:
        subprocess.run(
            ["git", "-C", folder, "checkout", "--"] + tracked_files,
            capture_output=True,
            text=True,
            check=True,
        )

    for rel_path in untracked_files:
        src = Path(folder) / rel_path
        if src.exists():
            src.unlink()
