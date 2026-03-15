"""Git operations service — subprocess wrappers for git commands."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
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
    """Return Alteryx workflow files that need saving.

    For non-git folders: all workflow files (everything needs a first save).
    For git repos: files modified vs HEAD (staged, unstaged, and untracked).
    """
    from pathlib import Path

    if not is_git_repo(folder):
        # No git repo yet — every workflow file is pending a first save
        return [
            f.name
            for f in Path(folder).iterdir()
            if f.is_file() and f.suffix in WORKFLOW_SUFFIXES
        ]

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

    Handles the initial commit case (no parent) by deleting the branch ref
    so the repo returns to an unborn state with files still on disk.
    """
    has_parent = (
        subprocess.run(
            ["git", "-C", folder, "rev-parse", "--verify", "HEAD~1"],
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )

    if has_parent:
        subprocess.run(
            ["git", "-C", folder, "reset", "--soft", "HEAD~1"],
            capture_output=True,
            text=True,
            check=True,
        )
    else:
        # Initial commit — delete the branch ref, leaving files unstaged
        subprocess.run(
            ["git", "-C", folder, "update-ref", "-d", "HEAD"],
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


def git_log(folder: str) -> list[dict]:
    """Return commit history for the git repo at folder, newest first.

    Each entry contains:
    - sha: full 40-char hex commit hash
    - message: commit subject line
    - author: author name
    - timestamp: ISO-8601 author date string
    - files_changed: workflow files changed in that commit (WORKFLOW_SUFFIXES only)
    - has_parent: True if the commit has a parent (not the initial commit)

    Returns [] when the repo has no commits.
    Uses two-pass approach: first gets headers, then per-SHA gets diff-tree for files.
    """
    if not git_has_commits(folder):
        return []

    # Pass 1: get commit headers
    result = subprocess.run(
        ["git", "-C", folder, "log", "--pretty=format:%H\x1f%s\x1f%an\x1f%aI"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []

    entries: list[dict] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f", 3)
        if len(parts) < 4:
            continue
        sha, message, author, timestamp = parts

        # Pass 2a: check has_parent via rev-parse of parent ref
        has_parent = (
            subprocess.run(
                ["git", "-C", folder, "rev-parse", "--verify", f"{sha}~1"],
                capture_output=True,
                text=True,
            ).returncode
            == 0
        )

        # Pass 2b: get files changed in this commit (diff-tree)
        diff_result = subprocess.run(
            [
                "git",
                "-C",
                folder,
                "diff-tree",
                "--no-commit-id",
                "-r",
                "--name-only",
                sha,
            ],
            capture_output=True,
            text=True,
        )
        files_changed = [
            f
            for f in diff_result.stdout.splitlines()
            if f and Path(f).suffix in WORKFLOW_SUFFIXES
        ]

        entries.append(
            {
                "sha": sha,
                "message": message,
                "author": author,
                "timestamp": timestamp,
                "files_changed": files_changed,
                "has_parent": has_parent,
            }
        )

    return entries


def git_fetch(folder: str, remote_url: str, token: str) -> None:
    """Fetch from remote_url using GIT_ASKPASS credential injection.

    Non-zero returncode is ignored — remote may be unreachable.
    Uses same GIT_ASKPASS temp-script pattern as git_push.
    """
    fd, askpass_path = tempfile.mkstemp(
        suffix=".bat" if sys.platform == "win32" else ".sh"
    )
    try:
        if sys.platform == "win32":
            script_content = f"@echo off\necho {token}\n"
        else:
            script_content = f"#!/bin/sh\necho '{token}'\n"

        with os.fdopen(fd, "w") as f:
            f.write(script_content)

        os.chmod(askpass_path, 0o700)

        env = dict(os.environ)
        env["GIT_ASKPASS"] = askpass_path
        env["GIT_TERMINAL_PROMPT"] = "0"

        subprocess.run(
            ["git", "-C", folder, "fetch", "origin"],
            capture_output=True,
            text=True,
            env=env,
        )
    finally:
        with contextlib.suppress(OSError):
            os.unlink(askpass_path)


def git_push(folder: str, remote_url: str, token: str) -> None:
    """Push current branch to remote_url using GIT_ASKPASS credential injection.

    Keeps token out of .git/config and process command-line arguments.
    Uses a temporary GIT_ASKPASS script so the token is never passed on the
    command line or embedded in the remote URL.
    """
    # Write a temporary askpass script that echoes the token.
    # On Windows, write a .bat; on Unix, write a shell script.
    fd, askpass_path = tempfile.mkstemp(
        suffix=".bat" if sys.platform == "win32" else ".sh"
    )
    try:
        if sys.platform == "win32":
            script_content = f"@echo off\necho {token}\n"
        else:
            script_content = f"#!/bin/sh\necho '{token}'\n"

        with os.fdopen(fd, "w") as f:
            f.write(script_content)

        # Make the script executable (no-op on Windows)
        os.chmod(askpass_path, 0o700)

        env = dict(os.environ)
        env["GIT_ASKPASS"] = askpass_path
        env["GIT_TERMINAL_PROMPT"] = "0"

        subprocess.run(
            ["git", "-C", folder, "push", remote_url],
            capture_output=True,
            text=True,
            env=env,
        )
    finally:
        with contextlib.suppress(OSError):
            os.unlink(askpass_path)


def git_ahead_behind(folder: str) -> tuple[int, int]:
    """Return (ahead, behind) commit counts vs. upstream tracking branch.

    Returns (0, 0) if no upstream is set.
    """
    # Get the name of the upstream tracking branch
    upstream_result = subprocess.run(
        ["git", "-C", folder, "rev-parse", "--abbrev-ref", "@{u}"],
        capture_output=True,
        text=True,
    )
    if upstream_result.returncode != 0:
        return (0, 0)

    upstream = upstream_result.stdout.strip()

    # Count commits ahead (local has but upstream does not)
    ahead_result = subprocess.run(
        ["git", "-C", folder, "rev-list", "--count", f"{upstream}..HEAD"],
        capture_output=True,
        text=True,
    )
    # Count commits behind (upstream has but local does not)
    behind_result = subprocess.run(
        ["git", "-C", folder, "rev-list", "--count", f"HEAD..{upstream}"],
        capture_output=True,
        text=True,
    )

    try:
        ahead = int(ahead_result.stdout.strip()) if ahead_result.returncode == 0 else 0
        behind = (
            int(behind_result.stdout.strip()) if behind_result.returncode == 0 else 0
        )
    except ValueError:
        ahead, behind = 0, 0

    return (ahead, behind)


def git_show_file(folder: str, sha: str, filepath: str) -> bytes:
    """Return the raw bytes of filepath at the given commit sha.

    Raises FileNotFoundError if the file does not exist at that commit.
    """
    result = subprocess.run(
        ["git", "-C", folder, "show", f"{sha}:{filepath}"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise FileNotFoundError(f"{filepath} not found at {sha}")
    return result.stdout
