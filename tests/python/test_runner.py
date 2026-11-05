import json

import nbformat
import pytest
from test_cli import course

from nma_kit import runner
from nma_kit.cli import main


def write_nb(path, *sources):
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(s) for s in sources])
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, path)
    return path


@pytest.mark.parametrize("state,runtime,expected", [
    ("passed", "browser", "passed"),
    ("passed", "colab", "passed"),
    ("failed", "browser", "failed"),
    ("timeout", "browser", "timeout"),
    ("failed", "colab", "needs-check"),
    ("timeout", "colab", "needs-check"),
])
def test_classify(state, runtime, expected):
    assert runner.classify(state, runtime) == expected


def test_only_failed_and_timeout_break_the_build():
    results = [runner.Result("a", "colab", "needs-check"), runner.Result("b", "browser", "passed")]
    assert not runner.has_failures(results)
    assert runner.has_failures(results + [runner.Result("c", "browser", "failed")])
    assert runner.has_failures(results + [runner.Result("c", "browser", "timeout")])


def test_run_notebook_passes(tmp_path):
    nb = write_nb(tmp_path / "ok.ipynb", "x = 1", "print(x)")
    result = runner.run_notebook(nb, "browser", timeout=120)
    assert result.state == "passed" and result.message == ""


def test_run_notebook_reports_the_failing_cell(tmp_path):
    nb = write_nb(tmp_path / "bad.ipynb", "x = 1", "y = 2\nraise ValueError('boom')")
    result = runner.run_notebook(nb, "browser", timeout=120)
    assert result.state == "failed"
    assert "cell 2" in result.where and "ValueError: boom" in result.message


EXERCISE = "def f(x):\n    raise NotImplementedError('Student exercise')"
SOLUTION = "# Solution\ndef f(x):\n    return 2 * x"


def test_exercise_cells_are_skipped_because_the_solution_cell_after_them_defines_the_same_names(tmp_path):
    nb = write_nb(tmp_path / "ex.ipynb", EXERCISE, SOLUTION, "assert f(2) == 4")
    assert runner.run_notebook(nb, "browser", timeout=120).state == "passed"


def test_a_failure_after_a_skipped_exercise_reports_the_cell_number_in_the_notebook(tmp_path):
    nb = write_nb(tmp_path / "ex.ipynb", EXERCISE, SOLUTION, "assert f(2) == 5")
    result = runner.run_notebook(nb, "browser", timeout=120)
    assert result.state == "failed" and "cell 3" in result.where


def test_failure_of_a_colab_notebook_needs_a_check(tmp_path):
    nb = write_nb(tmp_path / "gpu.ipynb", "raise RuntimeError('no CUDA')")
    result = runner.run_notebook(nb, "colab", timeout=120)
    assert result.state == "needs-check" and "no CUDA" in result.message


def test_run_notebook_times_out(tmp_path):
    nb = write_nb(tmp_path / "slow.ipynb", "import time\ntime.sleep(60)")
    result = runner.run_notebook(nb, "browser", timeout=3)
    assert result.state == "timeout"


def test_total_budget_spans_cells(tmp_path):
    nb = write_nb(tmp_path / "slow.ipynb", *["import time\ntime.sleep(1.5)"] * 6)
    assert runner.run_notebook(nb, "browser", timeout=4).state == "timeout"


def test_summary_table_lists_every_state():
    results = [runner.Result("a.ipynb", "browser", "passed", seconds=1.2),
               runner.Result("b.ipynb", "colab", "needs-check", "b.ipynb, cell 3", "RuntimeError: x")]
    text = runner.summary_markdown(results)
    assert "| a.ipynb |" in text and "needs-check" in text and "cell 3" in text
    assert "1 passed" in text and "1 need a manual check" in text


def test_list_targets(tmp_path, monkeypatch, capsys):
    root = course(tmp_path)
    (root / "tutorials" / "D" / "T.md").write_text(
        (root / "tutorials" / "D" / "T.md").read_text().replace("title: T", "title: T\nruntime: colab"))
    (root / "tutorials" / "D" / "plain.md").write_text("---\ntitle: P\n---\nText\n")
    monkeypatch.chdir(root)
    assert main(["notebooks"]) == 0
    capsys.readouterr()
    assert main(["run-notebooks", "--list"]) == 0
    matrix = json.loads(capsys.readouterr().out)["include"]
    assert [m["shard"] for m in matrix] == [1]
    assert json.loads(matrix[0]["targets"]) == [
        {"notebook": "notebooks/tutorials/D/instructor/T.ipynb", "runtime": "colab"}]
    assert main(["run-notebooks", "--list", "--runtime", "browser"]) == 0
    assert json.loads(capsys.readouterr().out) == {"include": []}


def test_run_one_notebook_writes_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_nb(tmp_path / "n.ipynb", "raise ValueError('x')")
    assert main(["run-notebooks", "--notebook", "n.ipynb", "--report", "r.json"]) == 1
    data = json.loads((tmp_path / "r.json").read_text())
    assert data[0]["notebook"] == "n.ipynb" and data[0]["state"] == "failed"
    assert main(["run-notebooks", "--notebook", "n.ipynb", "--runtime", "colab"]) == 0


def test_missing_notebooks_is_a_usage_error(tmp_path, monkeypatch):
    monkeypatch.chdir(course(tmp_path))
    assert main(["run-notebooks", "--list"]) == 2


def targets(n):
    return [{"notebook": f"n{i}.ipynb", "runtime": "browser"} for i in range(n)]


def test_shard_deals_notebooks_out_in_turn():
    groups = runner.shard(targets(5), 2)
    assert [[t["notebook"] for t in g] for g in groups] == [["n0.ipynb", "n2.ipynb", "n4.ipynb"], ["n1.ipynb", "n3.ipynb"]]


def test_shard_never_makes_empty_groups_and_handles_no_notebooks():
    assert len(runner.shard(targets(2), 4)) == 2
    assert runner.shard(targets(3), 0) == [targets(3)]
    assert runner.shard([], 4) == []


def test_list_splits_into_shards(tmp_path, monkeypatch, capsys):
    root = course(tmp_path)
    for name in ("A", "B", "C"):
        (root / "tutorials" / "D" / f"{name}.md").write_text((root / "tutorials" / "D" / "T.md").read_text())
    monkeypatch.chdir(root)
    assert main(["notebooks"]) == 0
    capsys.readouterr()
    assert main(["run-notebooks", "--list", "--shards", "2"]) == 0
    matrix = json.loads(capsys.readouterr().out)["include"]
    assert [len(json.loads(m["targets"])) for m in matrix] == [2, 2]


def test_run_targets_runs_each_and_keeps_the_report_after_every_notebook(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_nb(tmp_path / "a.ipynb", "x = 1")
    write_nb(tmp_path / "b.ipynb", "raise ValueError('x')")
    given = json.dumps([{"notebook": "a.ipynb", "runtime": "browser"}, {"notebook": "b.ipynb", "runtime": "browser"}])
    assert main(["run-notebooks", "--targets", given, "--report", "r.json"]) == 1
    assert [(r["notebook"], r["state"]) for r in json.loads((tmp_path / "r.json").read_text())] == [
        ("a.ipynb", "passed"), ("b.ipynb", "failed")]


def test_bad_targets_is_a_usage_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["run-notebooks", "--targets", "not json"]) == 2
    assert main(["run-notebooks", "--targets", '[{"notebook": "a"}]']) == 2
