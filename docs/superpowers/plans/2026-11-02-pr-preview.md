# PR Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every same-repo pull request on a course gets a public Cloudflare Pages preview whose notebook buttons open the PR's own notebooks.

**Architecture:** A new reusable workflow `course-preview.yml` builds the PR like `course-publish.yml`, pushes notebooks to `notebooks-pr-<n>`, deploys `_build/html` with wrangler as Pages branch `pr-<n>`, and comments the URL. On close it deletes the branch and deployments. Both config twins honour an `NMA_NOTEBOOKS_BRANCH` env override so every generated link uses the PR branch.

**Tech Stack:** GitHub Actions (reusable workflow), wrangler / Cloudflare Pages API, Python (`nma_kit.config`), JS (`shared/config.mjs`), pytest, node:test.

**Spec:** `docs/superpowers/specs/2026-11-02-pr-preview-design.md`

## Global Constraints

- Env var name: `NMA_NOTEBOOKS_BRANCH`. When set and non-blank it wins over `nma.notebooks.branch` and the default.
- Notebooks branch per PR: `notebooks-pr-<n>`. Pages branch alias: `pr-<n>`. URL: `pr-<n>.<project>.pages.dev`.
- Secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`; variable `CLOUDFLARE_PROJECT` (also an input `cloudflare-project`).
- Same-repo PRs only; never `pull_request_target`; never write to the production notebooks branch or the production Pages site.
- Missing secrets: skip deploy with a notice, job stays green.
- One version everywhere: `KIT_VERSION: x.y.z # x-release-please-version` in the new workflow, registered in `release-please-config.json` and `tests/python/test_release.py`.
- Python/JS twins stay in sync, tested on one fixture file.
- Reusable-workflow inputs match `course-publish.yml`: `python-version`, `requirements`, `kit-version`, `working-directory`, `kit-source`.
- Docs are part of done: `README.md`, `templates/`, `AGENTS.md`, workflow header comment.

## Review Focus

- Blank or whitespace `NMA_NOTEBOOKS_BRANCH` must fall back to the myst.yml value, not produce an empty branch (Task 1).
- Env override must not leak between cached JS settings and tests that switch it (Task 1).
- PR number must never reach a shell unquoted; branch names are built from `github.event.pull_request.number` via `env:` (Task 2).
- The preview job must not run `publish-notebooks` against the production branch, even when the env var is absent (Task 2).
- A repeated push must update the one comment, not add another (Task 2).

---

### Task 1: `NMA_NOTEBOOKS_BRANCH` override in both config twins

**Files:**
- Modify: `python/src/nma_kit/config.py` (`load_settings`, `read_settings`)
- Modify: `js/src/shared/config.mjs` (`loadSettings`, header comment) and wherever `courseSettings()` calls it (`js/src/shared/paths.mjs`)
- Modify: `tests/fixtures/config/settings.json`
- Test: `tests/python/test_config.py`, `tests/js/config.test.mjs`

**Interfaces:**
- Produces: `load_settings(myst_text: str, env: Mapping[str, str] | None = None) -> Settings` and `loadSettings(text, env = process.env)`. `env=None` in Python means `os.environ`. `read_settings(path)` passes the real environment. Later tasks only set the env var in workflows.

- [ ] **Step 1: Add fixture cases** to `settings.json`: a case with `"env": {"NMA_NOTEBOOKS_BRANCH": "notebooks-pr-7"}` over the defaults myst (expect `colab`, `kaggle`, `solution1` URLs with `notebooks-pr-7`); one where the myst sets `branch: nb` and env also set (env wins); one with env `"  "` (expect myst/default branch). Update the `_doc` string to mention `env`.
- [ ] **Step 2: Make both test files pass `case.get("env")`** through to the loaders (default `{}`, so existing cases don't read the real environment). Run `uv run pytest -q ../tests/python/test_config.py` and `cd js && npm test`; expect the new cases FAIL.
- [ ] **Step 3: Implement the override** in both twins: `notebooks_branch = env value if str and non-blank (stripped) else _setting(...)`. Update the `nma:` header comment in `config.mjs` and the docstring in `config.py` to name the variable.
- [ ] **Step 4: Check the JS cache** (`courseSettings()` caches per working directory): the cache key stays the directory; add a `config.test.mjs` test that `loadSettings(text, {NMA_NOTEBOOKS_BRANCH: 'x'}).notebooksBranch === 'x'` and that omitting the env argument in a clean `process.env` returns the default.
- [ ] **Step 5: Run** `cd python && uv run pytest -q ../tests/python` and `cd js && npm run build && npm test`; expect PASS. Also run `npm run build:dev && npm test`.
- [ ] **Step 6: Commit** `feat: NMA_NOTEBOOKS_BRANCH overrides the notebooks branch`

### Task 2: `course-preview.yml`

**Files:**
- Create: `.github/workflows/course-preview.yml`
- Modify: `release-please-config.json` (add the file to `extra-files`)
- Modify: `tests/python/test_release.py` (add `course-preview.yml` to `REUSABLE`)
- Test: `tests/python/test_preview_workflow.py` (new, structural, loads the YAML)

**Interfaces:**
- Consumes: `NMA_NOTEBOOKS_BRANCH` (Task 1); existing `nma-kit check | notebooks | publish-notebooks | render-scrolly | prepare-site`.
- Produces: `workflow_call` with the shared inputs plus `cloudflare-project: string` (default `""`, falls back to `vars.CLOUDFLARE_PROJECT` in the caller), secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` (both `required: false`), and `pr-number: number` input (the caller passes `github.event.pull_request.number`) and `action: string` (`deploy` or `cleanup`, from `github.event.action`).

- [ ] **Step 1: Write failing tests** in `test_preview_workflow.py`:
  - `test_preview_registered_for_releases`: `KIT_VERSION` line carries the marker and the file is in `release-please-config.json`.
  - `test_never_publishes_to_production`: the text contains `NMA_NOTEBOOKS_BRANCH: notebooks-pr-` on the job `env`, and the `publish-notebooks` step runs only inside a job whose `env` sets it.
  - `test_no_pull_request_target`: `pull_request_target` absent.
  - `test_pr_number_not_interpolated_in_run`: no `run:` block contains `${{ inputs.pr-number }}` (it is passed through `env:`).
  - `test_comment_is_sticky`: a step uses a fixed marker string (`<!-- nma-kit-preview -->`) to find and update the comment.
  Run `uv run pytest -q ../tests/python/test_preview_workflow.py`; expect FAIL (file missing).
- [ ] **Step 2: Create the workflow.** Copy the install and build steps from `course-publish.yml` (same inputs, same `kit-source` handling). Two jobs, each with `if` on `inputs.action`:
  - `preview` (`action != 'cleanup'`): `concurrency: group: course-preview-${{ github.repository }}-${{ inputs.pr-number }}`, `cancel-in-progress: true`; job `env` sets `NMA_NOTEBOOKS_BRANCH: notebooks-pr-<n>`; steps check, notebooks, `nma-kit publish-notebooks`, render-scrolly, prepare-site, `myst build --html`; then, only when both secrets are non-empty, `npx wrangler@<pinned> pages deploy _build/html --project-name <project> --branch pr-<n>` (create the project first with `wrangler pages project create ... --production-branch main` if `wrangler pages project list` lacks it); then upsert the sticky comment with `gh api` (find by marker, PATCH or POST). When secrets are missing, `echo "::notice::..."` and skip deploy and comment.
  - `cleanup` (`action == 'cleanup'`): `git push origin --delete notebooks-pr-<n>` (tolerate absence); list deployments through the Pages API (`GET /accounts/$ID/pages/projects/$PROJECT/deployments`), delete those whose `deployment_trigger.metadata.branch == pr-<n>` (`DELETE .../deployments/<id>?force=true`); mark the comment as closed.
  - Permissions: `contents: write`, `pull-requests: write`. Header comment in the style of `course-publish.yml` showing the caller and the setup (secrets, variable).
- [ ] **Step 3: Register for releases:** add the file path to `extra-files` in `release-please-config.json` mirroring `course-publish.yml`; add it to `REUSABLE` in `test_release.py`; set `KIT_VERSION` to the current version.
- [ ] **Step 4: Validate:** `uv run pytest -q ../tests/python` expect PASS; run `actionlint` if available (`npx --yes @action-validator/cli` is an alternative), expect no errors.
- [ ] **Step 5: Commit** `feat: course-preview workflow (Cloudflare Pages PR previews)`

### Task 3: Caller template, kit CI, docs

**Files:**
- Modify: `templates/course.yml`, `tests/python/test_release.py::test_course_template_calls_the_v0_1_line` only if its regex needs it
- Modify: `README.md`, `AGENTS.md`
- Test: `tests/python/test_preview_workflow.py` (template assertions)

**Interfaces:**
- Consumes: the Task 2 inputs and secrets.

- [ ] **Step 1: Failing tests:** `test_template_has_preview_job` (a job calling `course-preview.yml@v0.1`, guarded by `github.event.pull_request.head.repo.full_name == github.repository`, with `permissions` `contents: write` and `pull-requests: write`, `secrets: inherit`, and `pull_request` types including `closed`), and the existing `@v0.1` check still passes. Run, expect FAIL.
- [ ] **Step 2: Update `templates/course.yml`:** `pull_request` gets `types: [opened, synchronize, reopened, closed]`; `check` runs when the PR is not closed; new `preview` job passes `pr-number`, `action: ${{ github.event.action == 'closed' && 'cleanup' || 'deploy' }}` and `cloudflare-project: ${{ vars.CLOUDFLARE_PROJECT }}`.
- [ ] **Step 3: Kit CI (dropped):** no preview job in `ci.yml`: it would push `notebooks-pr-<n>` branches to the kit repo, and the build steps are the same ones `course-check` already runs on the example course.
- [ ] **Step 4: README:** add "Pull request previews" (what it does; setup steps: create the Cloudflare API token with *Cloudflare Pages: Edit*, add the two secrets and the `CLOUDFLARE_PROJECT` variable, copy the updated template; behaviour: public URL, per-PR notebooks branch, cleanup on close, same-repo PRs only, public repo needed for Colab/Kaggle links). Add it to the "Using the kit in a course" steps and document `NMA_NOTEBOOKS_BRANCH` next to the `notebooks.branch` setting.
- [ ] **Step 5: AGENTS.md:** add `course-preview.yml` to the layout tree and the CI section; add the env override to the twin-rules list (config bullet) and a short "PR previews (internals)" section: branch naming, cleanup, why `pull_request_target` is not used.
- [ ] **Step 6: Verify:** `uv run pytest -q ../tests/python`, `cd js && npm test`; `rg -n "course-publish" README.md AGENTS.md` and confirm each place that lists the reusable workflows also lists the preview one.
- [ ] **Step 7: Commit** `docs: PR previews in template, README and AGENTS`

### Task 4: Manual acceptance (no code)

- [ ] On a real course repo with the secrets set, open a same-repo PR: the comment appears with a `pr-<n>` URL; editable cells run; a scrolly page runs; "Open in Colab" opens `notebooks-pr-<n>`; pushing again updates the same comment; closing deletes the branch and deployments. Record findings in the PR.
