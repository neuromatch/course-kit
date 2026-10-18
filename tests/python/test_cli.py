import json
from pathlib import Path

from nma_kit.cli import main

KIT = "https://cdn.jsdelivr.net/npm/@neuromatch/course-kit"
EXERCISE = """---
title: T
kernelspec:
  name: python3
  display_name: Python 3
---

```{code-cell} python
def f(x):
  raise NotImplementedError("Student exercise")
```
"""
SOLUTION = """
::::{nma-solution}
```python
def f(x):
  return 2 * x
```
::::
"""


def course(root: Path, page: str = EXERCISE + SOLUTION) -> Path:
    (root / "myst.yml").write_text(
        f"version: 1\nextend: {KIT}@0.1/dist/nma.yml\nproject:\n  github: https://github.com/org/repo\n")
    (root / "tutorials" / "D").mkdir(parents=True)
    (root / "tutorials" / "D" / "T.md").write_text(page)
    return root


def test_no_myst_yml_is_a_usage_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["check"]) == 2
    err = capsys.readouterr().err.strip()
    assert len(err.splitlines()) == 1 and "myst.yml" in err and "Traceback" not in err


def test_no_command_is_a_usage_error(capsys):
    assert main([]) == 2


def test_check_passes_on_valid_course(tmp_path, monkeypatch):
    monkeypatch.chdir(course(tmp_path))
    assert main(["check"]) == 0


def test_check_fails_on_exercise_without_solution(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(course(tmp_path, EXERCISE))
    assert main(["check"]) == 1
    assert "T.md" in capsys.readouterr().err


def test_prepare_site_pins_kit_url_and_adds_badges(tmp_path, monkeypatch):
    monkeypatch.chdir(course(tmp_path))
    assert main(["prepare-site", "--kit-version", "9.9.9"]) == 0
    assert f"{KIT}@9.9.9/dist/nma.yml" in (tmp_path / "myst.yml").read_text()
    page = (tmp_path / "tutorials" / "D" / "T.md").read_text()
    assert "colab.research.google.com/github/org/repo/blob/notebooks-branch/notebooks/D/T.ipynb" in page


def test_prepare_site_defaults_to_own_version(tmp_path, monkeypatch):
    from nma_kit import __version__

    monkeypatch.chdir(course(tmp_path))
    assert main(["prepare-site"]) == 0
    assert f"{KIT}@{__version__}/dist/nma.yml" in (tmp_path / "myst.yml").read_text()


def test_notebooks_dry_run_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(course(tmp_path))
    assert main(["notebooks", "--dry-run"]) == 0
    assert not (tmp_path / "notebooks").exists()


def test_notebooks_writes_student_and_instructor(tmp_path, monkeypatch):
    monkeypatch.chdir(course(tmp_path))
    assert main(["notebooks"]) == 0
    student = json.loads((tmp_path / "notebooks" / "D" / "T.ipynb").read_text())
    assert "colab" in "".join(student["cells"][0]["source"])
    assert (tmp_path / "notebooks" / "D" / "instructor" / "T.ipynb").exists()
    assert (tmp_path / "notebooks" / "D" / "solutions" / "T_Solution_1.py").exists()


def test_render_scrolly_without_scrolly_pages(tmp_path, monkeypatch):
    monkeypatch.chdir(course(tmp_path))
    assert main(["render-scrolly"]) == 0


def test_publish_notebooks_reports_git_errors_without_traceback(tmp_path, monkeypatch, capsys):
    import subprocess

    monkeypatch.chdir(course(tmp_path))
    subprocess.run(["git", "init", "-q"], check=True)
    (tmp_path / "notebooks").mkdir()
    assert main(["publish-notebooks"]) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "git ls-remote" in err and "origin" in err  # the failing command and git's own message
