"""The reusable course workflows share one setup (uv, Node, install the kit).

The same steps are written in each workflow file because a reusable workflow
cannot share steps with another one safely (see CONTRIBUTING.md). This test is
the guard: they must stay identical, or a fix lands in one workflow only.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
FILES = ["course-check.yml", "course-publish.yml", "course-preview.yml"]
INSTALL = "Install the course kit and the course's packages"


def _steps(name: str) -> list[dict]:
    jobs = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))["jobs"]
    return [step for job in jobs.values() for step in job.get("steps", [])]


def _find(name: str, predicate) -> dict:
    matches = [s for s in _steps(name) if predicate(s)]
    assert len(matches) == 1, f"{name}: expected exactly one matching step, found {len(matches)}"
    return matches[0]


SELECTORS = {
    "install": lambda s: s.get("name") == INSTALL,
    "setup-uv": lambda s: str(s.get("uses", "")).startswith("astral-sh/setup-uv@"),
    "setup-node": lambda s: str(s.get("uses", "")).startswith("actions/setup-node@"),
}


@pytest.mark.parametrize("step", SELECTORS)
def test_setup_step_is_identical_in_every_course_workflow(step):
    first = _find(FILES[0], SELECTORS[step])
    for name in FILES[1:]:
        assert _find(name, SELECTORS[step]) == first, f"{name} differs from {FILES[0]} in the {step} step"
