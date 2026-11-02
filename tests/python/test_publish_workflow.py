"""Structure of course-publish.yml: the student fix and the optional instructor job. The
Cloudflare calls need a real token (checked by hand on a course); these tests pin the rules
that keep the instructor site from blocking the student site or leaking a secret."""

from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parents[2]
PUBLISH = KIT / ".github" / "workflows" / "course-publish.yml"
TEMPLATE = KIT / "templates" / "course.yml"
CF_SECRET_STEPS = {"Check Cloudflare setup", "Ensure the Pages project exists", "Deploy to Cloudflare Pages"}


def workflow() -> dict:
    return yaml.safe_load(PUBLISH.read_text())


def names(job: str) -> list:
    return [s.get("name") or s.get("uses") for s in workflow()["jobs"][job]["steps"]]


def step(job: str, name: str) -> dict:
    return next(s for s in workflow()["jobs"][job]["steps"] if s.get("name") == name)


def test_the_student_build_finishes_the_site_before_uploading_it():
    steps = workflow()["jobs"]["build"]["steps"]
    index = {s.get("name"): i for i, s in enumerate(steps)}
    finish = next(i for i, s in enumerate(steps) if s.get("run") == "nma-kit finalize-site")
    upload = next(i for i, s in enumerate(steps) if str(s.get("uses", "")).startswith("actions/upload-pages-artifact"))
    assert index["Build the site"] < finish < upload
    assert "NMA_AUDIENCE" not in workflow()["jobs"]["build"].get("env", {})


def test_instructor_needs_the_build_not_the_deploy():
    jobs = workflow()["jobs"]
    needs = jobs["instructor"]["needs"]
    assert needs in ("build", ["build"])
    assert "instructor" not in (jobs["deploy"]["needs"] if isinstance(jobs["deploy"]["needs"], list) else [jobs["deploy"]["needs"]])


def test_the_deploy_does_not_wait_for_the_instructor_job():
    assert workflow()["jobs"]["deploy"]["needs"] in ("build", ["build"])


def test_instructor_inputs_and_optional_secrets_are_declared():
    call = workflow()[True]["workflow_call"]  # PyYAML reads the key `on` as True
    assert call["inputs"]["instructor-cloudflare-project"]["default"] == ""
    assert call["secrets"]["CLOUDFLARE_API_TOKEN"]["required"] is False
    assert call["secrets"]["CLOUDFLARE_ACCOUNT_ID"]["required"] is False


def test_an_unconfigured_instructor_job_is_skipped_not_failed():
    job = workflow()["jobs"]["instructor"]
    assert "inputs.instructor-cloudflare-project" in job["if"]
    steps = job["steps"]
    assert steps[0]["name"] == "Check Cloudflare setup"
    assert all("steps.cf.outputs.enabled == 'true'" in s["if"] for s in steps[1:]), "every later step is gated"


def test_instructor_builds_with_the_instructor_audience_and_never_publishes_notebooks():
    job = workflow()["jobs"]["instructor"]
    assert job["env"]["NMA_AUDIENCE"] == "instructor"
    runs = " ".join(s.get("run", "") for s in job["steps"])
    assert "publish-notebooks" not in runs and "nma-kit notebooks" not in runs


def test_instructor_steps_run_in_order():
    order = names("instructor")
    wanted = ["Check Cloudflare setup", "Pre-render scrolly pages", "Prepare pages", "Build the site",
              "Finish the site", "Ensure the Pages project exists", "Deploy to Cloudflare Pages"]
    positions = [order.index(n) for n in wanted]
    assert positions == sorted(positions)
    assert step("instructor", "Finish the site")["run"] == "nma-kit finalize-site"


def test_cloudflare_secrets_only_on_steps_that_need_them():
    job = workflow()["jobs"]["instructor"]
    assert "CLOUDFLARE_API_TOKEN" not in job.get("env", {})
    with_secret = {s["name"] for s in job["steps"] if "CLOUDFLARE_API_TOKEN" in s.get("env", {})}
    assert with_secret == CF_SECRET_STEPS
    assert "CLOUDFLARE_API_TOKEN" not in yaml.dump(workflow()["jobs"]["build"])


def test_the_deploy_goes_to_production_and_the_project_is_not_interpolated():
    job = workflow()["jobs"]["instructor"]
    deploy = step("instructor", "Deploy to Cloudflare Pages")["run"]
    assert "--branch main" in deploy and '"$PROJECT"' in deploy and "_build/html" in deploy
    for s in job["steps"]:
        assert "inputs.instructor-cloudflare-project" not in s.get("run", ""), s
    assert job["env"]["PROJECT"] == "${{ inputs.instructor-cloudflare-project }}"


def test_template_passes_the_project_and_the_secrets():
    publish = yaml.safe_load(TEMPLATE.read_text())["jobs"]["publish"]
    assert publish["secrets"] == "inherit"
    assert publish["with"]["instructor-cloudflare-project"] == "${{ vars.CLOUDFLARE_INSTRUCTOR_PROJECT }}"
