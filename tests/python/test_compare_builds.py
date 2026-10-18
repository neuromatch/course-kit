import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "compare_builds.py"


def course(root: Path, notebook: str = "{}", esm: str = "/panel-0123456789abcdef0123456789abcdef.mjs",
           model: dict | None = None) -> Path:
    (root / "notebooks" / "D").mkdir(parents=True)
    (root / "notebooks" / "D" / "T.ipynb").write_text(notebook)
    content = root / "_build" / "site" / "content"
    content.mkdir(parents=True)
    page = {"mdast": {"type": "root", "children": [
        {"type": "anywidget", "esm": esm, "css": "/cells-ffffffffffffffffffffffffffffffff.css",
         "model": model or {"cells": 1}}]}}
    (content / "p.json").write_text(json.dumps(page))
    return root


def run(a: Path, b: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(a), str(b)], capture_output=True, text=True)


def test_identical_builds(tmp_path):
    assert run(course(tmp_path / "a"), course(tmp_path / "b")).returncode == 0


def test_asset_file_names_are_normalised(tmp_path):
    a = course(tmp_path / "a")
    b = course(tmp_path / "b", esm="/0123456789abcdef0123456789abcdef.mjs")
    assert run(a, b).returncode == 0


def test_changed_notebook_is_reported(tmp_path):
    result = run(course(tmp_path / "a"), course(tmp_path / "b", notebook='{"x": 1}'))
    assert result.returncode == 1 and "notebooks/D/T.ipynb" in result.stdout


def test_changed_widget_model_is_reported(tmp_path):
    result = run(course(tmp_path / "a"), course(tmp_path / "b", model={"cells": 2}))
    assert result.returncode == 1 and "p.json" in result.stdout and "model" in result.stdout


def test_missing_page_is_reported(tmp_path):
    a, b = course(tmp_path / "a"), course(tmp_path / "b")
    (b / "_build" / "site" / "content" / "p.json").unlink()
    assert run(a, b).returncode == 1


def test_notebook_cell_ids_are_ignored(tmp_path):
    # jupytext gives cells random ids on every run.
    a = course(tmp_path / "a", notebook=json.dumps({"cells": [{"id": "aaaa1111", "source": "x"}]}))
    b = course(tmp_path / "b", notebook=json.dumps({"cells": [{"id": "bbbb2222", "source": "x"}]}))
    assert run(a, b).returncode == 0


def test_notebook_source_change_still_reported(tmp_path):
    a = course(tmp_path / "a", notebook=json.dumps({"cells": [{"id": "a", "source": "x"}]}))
    b = course(tmp_path / "b", notebook=json.dumps({"cells": [{"id": "a", "source": "y"}]}))
    assert run(a, b).returncode == 1


def test_hashed_static_file_names_are_normalised(tmp_path):
    a, b = course(tmp_path / "a"), course(tmp_path / "b")
    for root, h in ((a, "0" * 32), (b, "f" * 32)):
        page = root / "_build" / "site" / "content" / "p.json"
        data = json.loads(page.read_text())
        data["frontmatter"] = {"exports": [{"url": f"/T1-{h}.md"}]}
        page.write_text(json.dumps(data))
    assert run(a, b).returncode == 0


def test_random_mdast_keys_are_ignored(tmp_path):
    a, b = course(tmp_path / "a"), course(tmp_path / "b")
    for root, key in ((a, "IYnsA9NxST"), (b, "LNtCdI8gW8")):
        page = root / "_build" / "site" / "content" / "p.json"
        data = json.loads(page.read_text())
        data["mdast"]["children"][0]["key"] = key
        page.write_text(json.dumps(data))
    assert run(a, b).returncode == 0


def test_random_outputs_ids_are_ignored(tmp_path):
    a, b = course(tmp_path / "a"), course(tmp_path / "b")
    for root, oid in ((a, "E3uQN7NwJeBHaTPcv4oT6"), (b, "iHMsIeWHq1jvJHXmRX9c9")):
        page = root / "_build" / "site" / "content" / "p.json"
        data = json.loads(page.read_text())
        data["mdast"]["children"].append({"type": "outputs", "id": oid, "children": []})
        page.write_text(json.dumps(data))
    assert run(a, b).returncode == 0
