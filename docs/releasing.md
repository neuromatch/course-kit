# Releasing the kit

Commits on `main` use conventional messages (`fix:`, `feat:`, `feat!:`).
release-please keeps a release PR open; merging it tags `vX.Y.Z`, publishes
npm and PyPI, and moves the `vX.Y` and `vX` tags.

To see what a release would publish without publishing anything, run
`make dist`. It builds the release bundle and writes the wheel, the sdist and
the npm tarball to `dist/`, so you can inspect them (`tar tzf dist/*.tgz`,
`python3 -m zipfile -l dist/*.whl`). The release workflow does not call it yet;
the publish steps themselves (npm provenance, PyPI trusted publishing) stay in
GitHub Actions.

The release flow is already set up. This is what it depends on, in case it
has to be rebuilt:

1. **npm**: the `neuromatch` organization owns `@neuromatch/course-kit`. The
   first version was published by hand
   (`cd js && npm run build && npm publish --otp=<code>`), because npm trusted
   publishing can only be configured on an existing package. The package has a
   trusted publisher: repository `neuromatch/course-kit`, workflow
   `release.yml`, no environment, direct publishing allowed (the workflow runs
   a plain `npm publish --provenance`), dist-tag management off.
2. **PyPI**: the project `neuromatch-course-kit` has a trusted publisher:
   repository `neuromatch/course-kit`, workflow `release.yml`, environment
   `release`.
3. Create the `release` environment in the repo settings.
4. Add a second owner/maintainer on npm and PyPI.
5. Create a fine-grained personal access token (or GitHub App) for this repo
   with read/write on Contents, Pull requests and Workflows, and save it as
   the repository secret `RELEASE_PLEASE_TOKEN`. release-please edits
   `KIT_VERSION` in `.github/workflows/`, which the default `GITHUB_TOKEN`
   may not do.
6. Branch protection on `main`: require pull requests, the CI checks, and
   "Require branches to be up to date before merging". CI runs on pull
   requests only.
