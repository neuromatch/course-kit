import subprocess
from pathlib import Path

from nma_kit.publish import publish_notebooks


def git(cwd, *args) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def repo_with_remote(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    work = tmp_path / "work"
    git(tmp_path, "init", "-q", "-b", "main", str(work))
    git(work, "config", "user.email", "t@example.org")
    git(work, "config", "user.name", "T")
    (work / "README.md").write_text("course\n")
    git(work, "add", "README.md")
    git(work, "commit", "-qm", "init")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "-q", "origin", "main")
    (work / "notebooks" / "D").mkdir(parents=True)
    (work / "notebooks" / "D" / "T.ipynb").write_text("{}\n")
    return work


def remote_log(tmp_path: Path, branch: str) -> list[str]:
    return git(tmp_path / "remote.git", "log", "--format=%s", branch).splitlines()


def test_creates_orphan_branch_when_missing(tmp_path, monkeypatch):
    work = repo_with_remote(tmp_path)
    monkeypatch.chdir(work)
    assert publish_notebooks(Path("notebooks"), "notebooks-branch", "origin", "regen") is True
    assert remote_log(tmp_path, "notebooks-branch") == ["regen"]  # orphan: no main history
    files = git(tmp_path / "remote.git", "ls-tree", "-r", "--name-only", "notebooks-branch").splitlines()
    assert files == ["notebooks/D/T.ipynb"]


def test_rerun_without_changes_makes_no_commit(tmp_path, monkeypatch):
    work = repo_with_remote(tmp_path)
    monkeypatch.chdir(work)
    publish_notebooks(Path("notebooks"), "notebooks-branch", "origin", "first")
    assert publish_notebooks(Path("notebooks"), "notebooks-branch", "origin", "second") is False
    assert remote_log(tmp_path, "notebooks-branch") == ["first"]


def test_changed_notebook_adds_one_commit_and_removes_stale_files(tmp_path, monkeypatch):
    work = repo_with_remote(tmp_path)
    monkeypatch.chdir(work)
    (work / "notebooks" / "D" / "Old.ipynb").write_text("{}\n")
    publish_notebooks(Path("notebooks"), "notebooks-branch", "origin", "first")
    (work / "notebooks" / "D" / "Old.ipynb").unlink()
    (work / "notebooks" / "D" / "T.ipynb").write_text('{"changed": true}\n')
    assert publish_notebooks(Path("notebooks"), "notebooks-branch", "origin", "second") is True
    assert remote_log(tmp_path, "notebooks-branch") == ["second", "first"]
    files = git(tmp_path / "remote.git", "ls-tree", "-r", "--name-only", "notebooks-branch").splitlines()
    assert files == ["notebooks/D/T.ipynb"]
