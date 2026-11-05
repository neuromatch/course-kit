"""Structure of course-nightly.yml. The Colab image and the issue calls need a real run on GitHub
(checked by hand on a course); these tests pin the rules that keep the job safe and cheap."""

from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parents[2]
NIGHTLY = KIT / ".github" / "workflows" / "course-nightly.yml"


def workflow() -> dict:
    return yaml.safe_load(NIGHTLY.read_text())


def run_script(job: str, name: str) -> str:
    return next(s["run"] for s in workflow()["jobs"][job]["steps"] if s.get("name") == name)


def test_it_is_a_reusable_workflow_that_never_publishes():
    call = workflow()[True]["workflow_call"]  # PyYAML reads the key `on` as True
    assert call["inputs"]["runtime"]["default"] == ""
    text = NIGHTLY.read_text()
    assert "publish-notebooks" not in text and "pages: write" not in text and "contents: write" not in text


def test_notebooks_are_generated_once_and_run_one_job_each():
    jobs = workflow()["jobs"]
    assert "nma-kit notebooks" in run_script("plan", "Generate the notebooks")
    assert jobs["run"]["needs"] == "plan"
    assert jobs["run"]["strategy"]["fail-fast"] is False
    assert "fromJSON(needs.plan.outputs.matrix)" in jobs["run"]["strategy"]["matrix"]
    assert jobs["run"]["timeout-minutes"]


def test_notebooks_run_in_the_colab_image_with_the_kit_installed_without_dependencies():
    script = run_script("run", "Run the notebook in the Colab image")
    assert "docker run" in script and '"$IMAGE"' in script
    assert "--no-deps" in script, "the kit must not change the packages the notebooks see"
    assert "run-notebooks --notebook" in script
    default = workflow()[True]["workflow_call"]["inputs"]["colab-image"]["default"]
    assert default.startswith("us-docker.pkg.dev/colab-images/public/runtime")


def test_the_report_job_runs_even_when_notebooks_fail_and_is_the_only_one_with_issue_rights():
    jobs = workflow()["jobs"]
    assert jobs["report"]["needs"] == ["plan", "run"]
    assert "always()" in jobs["report"]["if"]
    assert jobs["report"]["permissions"] == {"issues": "write"}
    assert all("permissions" not in jobs[j] for j in ("plan", "run"))


def test_the_kit_version_comes_from_the_manifest_like_the_other_workflows():
    text = NIGHTLY.read_text()
    assert ".release-please-manifest.json" in text and "KIT_VERSION" not in text


def test_the_course_template_calls_this_workflow_on_the_release_line():
    text = (KIT / "templates" / "nightly.yml").read_text()
    template = yaml.safe_load(text)
    job = template["jobs"]["notebooks"]
    assert job["uses"] == "neuromatch/course-kit/.github/workflows/course-nightly.yml@v0.4"
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    crons = [s["cron"] for s in template[True]["schedule"]]
    assert "0 5 * * 0" in crons, "the weekly cron the runtime expression tests for"
    assert "workflow_dispatch" in template[True]
