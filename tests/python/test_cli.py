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
    assert "colab.research.google.com/github/org/repo/blob/notebooks-branch/notebooks/tutorials/D/T.ipynb" in page


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
    student = json.loads((tmp_path / "notebooks" / "tutorials" / "D" / "T.ipynb").read_text())
    assert "colab" in "".join(student["cells"][0]["source"])
    assert (tmp_path / "notebooks" / "tutorials" / "D" / "instructor" / "T.ipynb").exists()
    assert (tmp_path / "notebooks" / "tutorials" / "D" / "solutions" / "T_Solution_1.py").exists()


def with_project(root: Path, page: str = EXERCISE + SOLUTION) -> Path:
    (root / "projects" / "Neuro").mkdir(parents=True)
    (root / "projects" / "Neuro" / "P.md").write_text(page)
    return root


def test_notebooks_covers_projects_under_their_own_root(tmp_path, monkeypatch):
    monkeypatch.chdir(with_project(course(tmp_path)))
    assert main(["notebooks"]) == 0
    base = tmp_path / "notebooks"
    assert (base / "tutorials" / "D" / "T.ipynb").exists()
    project = json.loads((base / "projects" / "Neuro" / "P.ipynb").read_text())
    assert "blob/notebooks-branch/notebooks/projects/Neuro/P.ipynb" in "".join(project["cells"][0]["source"])
    assert (base / "projects" / "Neuro" / "instructor" / "P.ipynb").exists()
    solution_link = "".join(project["cells"][2]["source"])
    assert "notebooks/projects/Neuro/solutions/P_Solution_1.py" in solution_link


def test_prepare_site_adds_badges_to_projects(tmp_path, monkeypatch):
    monkeypatch.chdir(with_project(course(tmp_path)))
    assert main(["prepare-site"]) == 0
    page = (tmp_path / "projects" / "Neuro" / "P.md").read_text()
    assert "notebooks-branch/notebooks/projects/Neuro/P.ipynb" in page


def test_check_validates_projects(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(with_project(course(tmp_path), EXERCISE))
    assert main(["check"]) == 1
    assert "P.md" in capsys.readouterr().err


def test_check_rejects_ipynb_in_projects(tmp_path, monkeypatch, capsys):
    root = with_project(course(tmp_path))
    (root / "projects" / "Neuro" / "x.ipynb").write_text("{}")
    monkeypatch.chdir(root)
    assert main(["check"]) == 1
    assert "projects/Neuro/x.ipynb" in capsys.readouterr().err


def test_custom_projects_dir(tmp_path, monkeypatch):
    root = course(tmp_path)
    (root / "myst.yml").write_text((root / "myst.yml").read_text() + "nma:\n  paths:\n    projects: capstone\n")
    (root / "capstone").mkdir()
    (root / "capstone" / "P.md").write_text(EXERCISE + SOLUTION)
    monkeypatch.chdir(root)
    assert main(["notebooks"]) == 0
    assert (root / "notebooks" / "projects" / "P.ipynb").exists()  # root name, not the directory


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


def test_example_course_data_tutorial_builds_notebook_with_assets(tmp_path, monkeypatch):
    """The example course's data & images tutorial passes `check` and converts."""
    import json
    import shutil
    from pathlib import Path

    from nma_kit.config import read_settings
    from nma_kit.convert import build_notebooks, convert_md_to_notebook, validate_content

    course = Path(__file__).resolve().parents[1] / "example-course"
    shutil.copytree(course, tmp_path / "c", ignore=shutil.ignore_patterns("_build", "_nma", "notebooks"))
    monkeypatch.chdir(tmp_path / "c")
    assert validate_content() == []
    page = Path("tutorials/W1D1_GettingStarted/W1D1_Tutorial4.md")
    out = Path("notebooks/tutorials/W1D1_GettingStarted/W1D1_Tutorial4.ipynb")
    convert_md_to_notebook(page, out, dry_run=False)
    build_notebooks(page, out, "neuromatch/course-kit", False, None, read_settings())
    sources = ["".join(c["source"]) for c in json.loads(out.read_text())["cells"]]
    base = "https://raw.githubusercontent.com/neuromatch/course-kit/notebooks-branch/notebooks/tutorials/W1D1_GettingStarted/"
    assert sources[1].startswith("# @title Download course data")
    assert base in sources[1] and "'data/demo.txt'" in sources[1] and "'image/demo.png'" in sources[1]
    assert f"![A single red pixel]({base}image/demo.png)" in "\n".join(sources)
    assert (out.parent / "data" / "demo.txt").exists()
