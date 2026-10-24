# Pull request previews on Cloudflare Pages

Status: design, awaiting approval

## Intent and why

Course reviewers now work almost entirely in markdown diffs. They never see
what readers see: scrolly pages, editable cells, solution links, the Colab and
Kaggle buttons. Reviewers need to **test** a PR, not just read it. So every
pull request gets a public, temporary copy of the built site, and its notebook
buttons open the PR's own notebooks.

## Goals

- A reusable workflow `course-preview.yml`, called from a course's `pull_request`
  workflow, that builds the PR and deploys it to Cloudflare Pages.
- A stable URL per PR (`pr-<n>.<project>.pages.dev`), updated on every push.
- One sticky PR comment with the preview link (updated, never duplicated).
- Colab, Kaggle, solution and data-download links point at the PR's notebooks.
- Everything is removed when the PR closes (deployment and notebooks branch).
- Courses opt in by adding one job and setting two secrets and one variable.
- README, `templates/`, `AGENTS.md` and tests updated together with the code.

## Non-goals and anti-goals

- No previews for PRs from forks. Courses use the kit or a copy of the template,
  not forks, so PRs come from branches in the same repository.
- No access control: preview URLs are public (decided).
- Never write to the production `notebooks-branch` or the production Pages site
  from a PR. A PR that touches production state is a failure even if the preview works.
- No new hosting abstraction: Cloudflare Pages only.

## Decided by the human partner

- Reviewers test the preview, so interactive features must work.
- Previews are public.
- PRs come from the same repository (no forks).
- Notebook buttons must point to the **PR versions** of the notebooks.

## Design

### Workflow shape

`course-preview.yml` (`workflow_call`, same inputs as `course-publish.yml`:
`python-version`, `requirements`, `kit-version`, `working-directory`,
`kit-source`, plus `cloudflare-project`). Secrets: `CLOUDFLARE_API_TOKEN`,
`CLOUDFLARE_ACCOUNT_ID` (passed with `secrets: inherit` or explicitly).

Jobs:

1. **preview** (on `opened`, `reopened`, `synchronize`):
   `nma-kit check` -> `nma-kit notebooks` -> push notebooks to the PR branch ->
   `render-scrolly` -> `prepare-site` -> `myst build --html` ->
   `wrangler pages deploy _build/html --branch pr-<n>` -> sticky comment.
2. **cleanup** (on `closed`): delete the PR notebooks branch, delete the
   Cloudflare deployments for `pr-<n>`, and update the comment.

Concurrency group `course-preview-<repo>-<pr>`, `cancel-in-progress: true` for
the preview job, so a newer push replaces an older run.

### Per-PR notebooks (my call: branch `notebooks-pr-<n>`)

Notebook links are built from the notebooks branch setting on both sides
(`settings.notebooks_branch` in Python, `notebooksBranch` in
`shared/config.mjs`). The preview overrides that setting with the environment
variable `NMA_NOTEBOOKS_BRANCH`, read by both twins:

- `config.py` / `config.mjs`: if `NMA_NOTEBOOKS_BRANCH` is set, it wins over
  `nma.notebooks.branch`. Covered by `tests/fixtures/config/settings.json` (twin rule).
- `nma-kit publish-notebooks` already pushes to `settings.notebooks_branch`,
  so the preview job needs no new push code. It would use the same orphan-branch logic.
- The branch lives in the course repo, so Colab and Kaggle links work for
  public repos exactly as they do in production (existing limitation: raw URLs
  need a public repo).
- Cleanup deletes `notebooks-pr-<n>` with `git push --delete`.

Alternative considered: a subfolder on the production notebooks branch. Rejected
because it writes to production state from PRs and complicates cleanup.

### Cloudflare

- Direct upload with `wrangler pages deploy` (no Git integration needed). One
  Pages project per course, with its production branch left unused.
- The project is created on first use if missing (`wrangler pages project create`),
  so setup is only the token and the project name. The token needs
  *Cloudflare Pages: Edit*.
- Deleting deployments uses the Pages API (list by branch alias, then delete).
- Open point for the builder: Cloudflare branch aliases are derived from the
  branch name, so use `pr-<n>` to keep the URL predictable.

### Course setup

Repo secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`; repo variable
`CLOUDFLARE_PROJECT` (the Pages project name). `templates/course.yml` gains a
`preview` job (guarded by `github.event_name == 'pull_request'` and a same-repo
check) next to the existing `check` job, with `contents: write` and
`pull-requests: write`. The existing `check` stays; preview runs `check` itself
as its first step. Preview is skipped, with a notice, when the secrets are unset,
so courses that haven't set up Cloudflare keep a green PR.

### Base path

Cloudflare serves each preview at the domain root, so no `BASE_URL` handling is
needed. The kit's browser code already derives URLs from `import.meta.url`.

## Constraints

- Follow existing rules: one `KIT_VERSION` in every reusable workflow
  (`tests/python/test_release.py` covers the new file), `x-release-please-version` marker.
- Python/JS twins stay in sync for the new env override.
- No secrets in logs; the workflow only runs for same-repo PRs, because fork PRs
  would not get secrets and `pull_request_target` would be unsafe here.

## Docs to update (part of done)

- `README.md`: new "Pull request previews" section (setup: token, account id,
  project variable, caller job), the `nma:` block note about `NMA_NOTEBOOKS_BRANCH`,
  and the course setup steps list.
- `templates/course.yml`: the preview job. Possibly `templates/preview.yml`
  if a separate file reads better (builder's call).
- `AGENTS.md`: layout (new workflow), CI section (`course-preview.yml`), and a
  note under the twin rules for the branch override.
- Header comment of `course-preview.yml`, in the style of `course-publish.yml`.
- A note in the course template's AGENTS.md (outside this repo) is a follow-up.

## Testing

- pytest: env override for the branch, settings fixture, release-version check.
- JS test: same override on the JS side.
- Kit CI: run `course-preview.yml` against `tests/example-course` with
  `kit-source: local` up to the build step, with the Cloudflare deploy skipped
  when secrets are absent (CI cannot hold them for fork-free kit PRs unless added).
- Manual acceptance on a real course PR: link appears, cells run, scrolly works,
  Colab opens the PR notebook, closing the PR removes the branch and deployment.

## Left to the builder

Exact wrangler version pinning, comment marker format, and how to list and
delete deployments through the API.

## Risks

- Cloudflare Pages deployment limits (500 builds per month on the free plan do not
  apply to direct upload, but total deployments per project do). Cleanup on close mitigates this.
- Colab links need the PR branch to be pushed before the preview is opened.
