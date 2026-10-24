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
    helper = next(s for s in steps if s.get("name") == "Write the comment helper")["run"]
    assert "PATCH" in helper and "POST" in helper and "$MARKER" in helper
    names = [s.get("name") for s in steps]
    assert names.index("Comment that the preview is building") < names.index("Comment the preview link")
    failed = next(s for s in steps if s.get("name") == "Comment that the preview failed")
    assert "failure()" in failed["if"]


def test_cloudflare_secrets_only_on_steps_that_need_them():
    job = workflow()["jobs"]["preview"]
    assert "CLOUDFLARE_API_TOKEN" not in job["env"]
    with_secret = {s["name"] for s in job["steps"] if "CLOUDFLARE_API_TOKEN" in s.get("env", {})}
    assert with_secret == {"Check Cloudflare setup", "Ensure the Pages project exists", "Deploy to Cloudflare Pages"}


def test_wrangler_is_pinned_exactly():
    text = PREVIEW.read_text()
    assert re.search(r"WRANGLER_VERSION: \d+\.\d+\.\d+", text)
    assert "wrangler@4 " not in text and "wrangler@4\n" not in text


def test_project_create_does_not_swallow_errors():
    steps = workflow()["jobs"]["preview"]["steps"]
    ensure = next(s for s in steps if s.get("name") == "Ensure the Pages project exists")["run"]
    assert "|| true" not in ensure


def test_previews_are_noindex():
    steps = workflow()["jobs"]["preview"]["steps"]
    deploy = next(s for s in steps if s.get("name") == "Deploy to Cloudflare Pages")["run"]
    assert "X-Robots-Tag: noindex" in deploy


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


def test_summary_and_exact_build_url():
    steps = workflow()["jobs"]["preview"]["steps"]
    deploy = next(s for s in steps if s.get("name") == "Deploy to Cloudflare Pages")
    assert "WRANGLER_OUTPUT_FILE_PATH" in deploy["run"] and "url=" in deploy["run"]
    comment = next(s for s in steps if s.get("name") == "Comment the preview link")
    assert "GITHUB_STEP_SUMMARY" in comment["run"]


def test_ci_lints_workflows():
    ci = (KIT / ".github" / "workflows" / "ci.yml").read_text()
    assert "rhysd/actionlint:" in ci


def test_steps_before_checkout_do_not_use_the_course_directory():
    # defaults.run.working-directory is the course folder, which only exists after checkout.
    steps = workflow()["jobs"]["preview"]["steps"]
    for step in steps:
        if "actions/checkout" in step.get("uses", ""):
            break
        if "run" in step:
            assert step.get("working-directory") == "${{ github.workspace }}", step["name"]
