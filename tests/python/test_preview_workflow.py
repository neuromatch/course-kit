"""Structure of the PR preview workflow and its caller template. The Cloudflare
calls need a real token (checked by hand on a course PR); these tests pin the
rules that keep a preview from touching production or leaking input into a shell."""

import re
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parents[2]
PREVIEW = KIT / ".github" / "workflows" / "course-preview.yml"
TEMPLATE = KIT / "templates" / "course.yml"
MARKER = "<!-- nma-kit-preview -->"


def workflow() -> dict:
    return yaml.safe_load(PREVIEW.read_text())


def test_publish_notebooks_only_with_the_pr_branch_set():
    jobs = workflow()["jobs"]
    publishing = [n for n, j in jobs.items() if any("publish-notebooks" in s.get("run", "") for s in j["steps"])]
    assert publishing == ["preview"]
    assert jobs["preview"]["env"]["NMA_NOTEBOOKS_BRANCH"] == "notebooks-pr-${{ inputs.pr-number }}"


def test_no_pull_request_target():
    assert "pull_request_target" not in PREVIEW.read_text()
    assert "pull_request_target" not in TEMPLATE.read_text()


def test_pr_number_and_project_not_interpolated_into_scripts():
    for job in workflow()["jobs"].values():
        for step in job["steps"]:
            run = step.get("run", "")
            assert "inputs.pr-number" not in run and "inputs.cloudflare-project" not in run, step


def test_jobs_are_limited_to_same_repo_pull_requests():
    for job in workflow()["jobs"].values():
        assert "github.event.pull_request.head.repo.full_name == github.repository" in job["if"]


def test_comment_is_sticky():
    wf = workflow()
    assert wf["env"]["MARKER"] == MARKER
    steps = wf["jobs"]["preview"]["steps"]
    comment = next(s for s in steps if s.get("name") == "Comment the preview link")["run"]
    assert "PATCH" in comment and "POST" in comment and "$MARKER" in comment


def test_cloudflare_is_optional():
    wf = workflow()
    secrets = wf[True]["workflow_call"]["secrets"]
    assert all(not v.get("required") for v in secrets.values())
    steps = wf["jobs"]["preview"]["steps"]
    deploy = next(s for s in steps if s.get("name") == "Deploy to Cloudflare Pages")
    assert deploy["if"] == "steps.cf.outputs.enabled == 'true'"


def test_template_has_preview_job():
    text = TEMPLATE.read_text()
    template = yaml.safe_load(text)
    assert set(template[True]["pull_request"]["types"]) >= {"opened", "synchronize", "reopened", "closed"}
    job = template["jobs"]["preview"]
    assert job["uses"] == "neuromatch/course-kit/.github/workflows/course-preview.yml@v0.1"
    assert "head.repo.full_name == github.repository" in job["if"]
    assert job["permissions"] == {"contents": "write", "pull-requests": "write"}
    assert job["secrets"] == "inherit"
    assert set(job["with"]) >= {"pr-number", "action", "cloudflare-project"}
    assert re.search(r"closed.*cleanup.*deploy", job["with"]["action"])
