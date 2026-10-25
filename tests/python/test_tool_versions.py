"""`.tool-versions` is the single source for Node, uv and Python.

The kit's CI and release workflows and the shared setup action read it
(`setup-node` and `setup-uv` accept the file), and `mise`/`asdf` read it for
contributors. The only places that cannot read a file keep a literal, and this
test keeps that literal equal: the uv version in course-wheels.yml.
"""

import re
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parents[2]
TOOLS = dict(
    line.split()[:2] for line in (KIT / ".tool-versions").read_text(encoding="utf-8").splitlines() if line.strip()
)
WORKFLOW_FILES = sorted((KIT / ".github" / "workflows").glob("*.yml"))
ACTION = KIT / ".github" / "actions" / "setup-course" / "action.yml"


def _steps(path: Path) -> list[dict]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if "runs" in doc:
        return doc["runs"]["steps"]
    return [s for job in doc.get("jobs", {}).values() for s in job.get("steps", [])]


def _uses(prefix: str) -> list[tuple[Path, dict]]:
    return [(p, s) for p in [*WORKFLOW_FILES, ACTION] for s in _steps(p) if str(s.get("uses", "")).startswith(prefix)]


def test_versions_are_declared():
    assert set(TOOLS) >= {"nodejs", "uv", "python"}
    assert re.fullmatch(r"\d+\.\d+\.\d+", TOOLS["nodejs"]) and re.fullmatch(r"\d+\.\d+\.\d+", TOOLS["uv"])
    assert re.fullmatch(r"\d+\.\d+(\.\d+)?", TOOLS["python"])


def test_setup_node_reads_the_file_everywhere():
    steps = _uses("actions/setup-node@")
    assert steps
    for path, step in steps:
        assert step["with"].get("node-version-file", "").endswith(".tool-versions"), path.name
        assert "node-version" not in step["with"], f"{path.name} hard-codes Node"


def test_setup_uv_is_one_pinned_release_that_reads_the_file():
    steps = _uses("astral-sh/setup-uv@")
    assert len({s["uses"] for _, s in steps}) == 1, "pin one setup-uv release everywhere"
    for path, step in steps:
        if path.name == "course-wheels.yml":
            assert step["with"]["version"] == TOOLS["uv"], "course-wheels.yml cannot read the file: keep its literal equal"
        else:
            assert step["with"].get("version-file", "").endswith(".tool-versions"), path.name
            assert "version" not in step["with"], f"{path.name} hard-codes uv"


def test_no_workflow_pins_python_itself():
    for path in [*WORKFLOW_FILES, ACTION]:
        text = path.read_text(encoding="utf-8")
        assert "--python" not in text, f"{path.name}: Python comes from .tool-versions (UV_PYTHON)"
