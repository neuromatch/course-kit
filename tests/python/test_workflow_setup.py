"""The reusable course workflows share their setup through one local action.

course-check, course-publish and course-preview check out this repository at
their own commit (`job.workflow_sha`) and run `.github/actions/setup-course`.
The two steps that do that are the only thing the workflows repeat, so they
must stay identical and agree with the action's inputs, and the setup itself
must not creep back into the workflow files.
"""

from pathlib import Path

import pytest
import yaml

KIT = Path(__file__).resolve().parents[2]
WORKFLOWS = KIT / ".github" / "workflows"
ACTION_DIR = ".github/actions/setup-course"
ACTION = yaml.safe_load((KIT / ACTION_DIR / "action.yml").read_text(encoding="utf-8"))
FILES = ["course-check.yml", "course-publish.yml", "course-preview.yml"]


def _steps(name: str) -> list[dict]:
    jobs = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))["jobs"]
    return [step for job in jobs.values() for step in job.get("steps", [])]


def _one(name: str, predicate) -> dict:
    matches = [s for s in _steps(name) if predicate(s)]
    assert len(matches) == 1, f"{name}: expected exactly one matching step, found {len(matches)}"
    return matches[0]


def _fetch(step: dict) -> bool:
    return step.get("with", {}).get("repository") == "${{ job.workflow_repository }}"


def _use(step: dict) -> bool:
    return str(step.get("uses", "")).startswith("./") and step["uses"].endswith(ACTION_DIR)


@pytest.mark.parametrize("selector", [_fetch, _use], ids=["fetch", "use"])
def test_the_two_setup_steps_are_identical_in_every_course_workflow(selector):
    first = _one(FILES[0], selector)
    for name in FILES[1:]:
        assert _one(name, selector) == first, f"{name} differs from {FILES[0]}"


@pytest.mark.parametrize("name", FILES)
def test_fetch_step_checks_out_exactly_the_action(name):
    fetch, use = _one(name, _fetch), _one(name, _use)
    assert fetch["with"]["ref"] == "${{ job.workflow_sha }}"
    # Only what the action reads (not cone mode, which would also pull every top-level file).
    assert fetch["with"]["sparse-checkout"].split() == [ACTION_DIR, ".tool-versions", ".release-please-manifest.json"]
    assert fetch["with"]["sparse-checkout-cone-mode"] is False
    assert fetch["with"]["persist-credentials"] is False
    assert use["uses"] == f"./{fetch['with']['path']}/{ACTION_DIR}"


@pytest.mark.parametrize("name", FILES)
def test_workflow_passes_the_actions_inputs(name):
    passed = set(_one(name, _use)["with"])
    declared = set(ACTION["inputs"])
    required = {k for k, v in ACTION["inputs"].items() if v.get("required")}
    assert passed <= declared, f"{name} passes unknown inputs: {passed - declared}"
    assert required <= passed, f"{name} omits required inputs: {required - passed}"
    assert "kit-version" in passed


@pytest.mark.parametrize("name", FILES)
def test_setup_is_not_repeated_in_the_workflow(name):
    for step in _steps(name):
        assert not str(step.get("uses", "")).startswith(("astral-sh/setup-uv@", "actions/setup-node@")), (
            f"{name}: uv and Node are set up by the action"
        )
        assert "neuromatch-course-kit" not in step.get("run", ""), f"{name}: the kit is installed by the action"


def test_the_action_exists_where_the_workflows_look():
    assert (KIT / ACTION_DIR / "action.yml").is_file()
    assert ACTION["runs"]["using"] == "composite"
