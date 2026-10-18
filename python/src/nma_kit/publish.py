"""Publish generated notebooks to their own branch (default `notebooks-branch`).

The branch holds only `notebooks/`. It is created as an orphan branch the
first time (a fresh fork has none). Uses a temporary git worktree, so the
course checkout is never switched.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

BOT = ["-c", "user.name=github-actions[bot]",
       "-c", "user.email=github-actions[bot]@users.noreply.github.com"]


class PublishError(Exception):
    """A git command failed; the message holds the command and git's output."""


def _git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        raise PublishError(f"`git {' '.join(args)}` failed (exit {result.returncode}): {output}")
    return result


def _remote_has_branch(remote: str, branch: str) -> bool:
    return bool(_git("ls-remote", "--heads", remote, branch).stdout.strip())


def publish_notebooks(src: Path, branch: str, remote: str, message: str) -> bool:
    """Make `branch` on `remote` contain exactly `src` as `notebooks/`.

    Returns True if a commit was pushed, False if nothing changed.
    """
    src = Path(src).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="nma-notebooks-"))
    worktree = tmp / "wt"
    temp_branch = None
    try:
        if _remote_has_branch(remote, branch):
            _git("fetch", "-q", remote, f"+refs/heads/{branch}:refs/nma-kit/{branch}")
            _git("worktree", "add", "-q", "--detach", str(worktree), f"refs/nma-kit/{branch}")
        else:
            temp_branch = f"nma-kit-publish-{os.getpid()}"
            _git("worktree", "add", "-q", "--orphan", "-b", temp_branch, str(worktree))

        target = worktree / "notebooks"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target)

        _git("add", "-A", "notebooks", cwd=worktree)
        if _git("diff", "--cached", "--quiet", cwd=worktree, check=False).returncode == 0:
            return False
        _git(*BOT, "commit", "-q", "-m", message, cwd=worktree)
        _git("push", "-q", remote, f"HEAD:refs/heads/{branch}", cwd=worktree)
        return True
    finally:
        _git("worktree", "remove", "--force", str(worktree), check=False)
        if temp_branch:
            _git("branch", "-D", temp_branch, check=False)
        _git("update-ref", "-d", f"refs/nma-kit/{branch}", check=False)
        shutil.rmtree(tmp, ignore_errors=True)
