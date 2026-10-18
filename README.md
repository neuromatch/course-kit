# Neuromatch course kit

The tooling behind Neuromatch courses built with [MyST](https://mystmd.org),
in one versioned package:

- **MyST plugin**: `{nma-video}`, `{nma-slides}`, `{nma-solution}`,
  `{nma-explanation}`, `{nma-feedback}`, scrollytelling pages (`{step}`,
  `{stage}`) and editable, runnable code cells.
- **`nma-kit` CLI**: content checks, notebook generation (student, instructor,
  solutions), scrolly pre-rendering, site preparation, notebook publishing.
- **Reusable GitHub workflows**: check pull requests, publish notebooks and the
  site to GitHub Pages.

Courses *use* a version of the kit instead of carrying a copy, so a fix
ships once. Start a course from
[neuromatch/course-template](https://github.com/neuromatch/course-template),
which teaches the authoring conventions.

## Using the kit in a course

1. In `myst.yml`, extend the kit's config (it adds the plugin and turns on
   JupyterLite):

   ```yaml
   version: 1
   extend: https://cdn.jsdelivr.net/npm/@neuromatch/course-kit@0.1/dist/nma.yml
   project:
     github: https://github.com/<org>/<course>
     # ...
   ```

2. Copy [`templates/course.yml`](templates/course.yml) to
   `.github/workflows/course.yml`. Pull requests are checked; pushes to `main`
   publish the notebooks (to `notebooks-branch`, created automatically) and
   the site.
3. In the repo's **Settings → Pages**, set **Source** to **GitHub Actions**
   (and the custom domain, if any; no `CNAME` file needed).
4. Keep this rule in your site CSS (a plugin can't add site-wide CSS):

   ```css
   .myst-jp-nb-toolbar { display: none !important; }
   ```

5. List the packages your tutorials import in `requirements.txt` (CI installs
   them next to the kit; `nma-kit render-scrolly` executes scrolly pages).

Optional settings, in the `nma:` block of `myst.yml` (defaults shown):

```yaml
nma:
  paths:
    tutorials: tutorials          # where the .md pages live
  notebooks:
    branch: notebooks-branch      # where generated notebooks are published
  feedback:                       # needed if any page uses {nma-feedback}
    url: https://...
    project: ...
    user_key: ...
  scrolly:
    pyodide_url: https://cdn.jsdelivr.net/pyodide/v314.0.7/full/
```

## Versions and updates

The kit is on **0.x** until it is stable. A breaking change bumps the minor
version (0.1 → 0.2); features and fixes bump the patch (0.1.0 → 0.1.1). So a
`v0.MINOR` line only gets compatible changes.

**The ref in your workflow file is the only knob.** Each release of the
reusable workflows installs that exact CLI version, and `nma-kit prepare-site`
rewrites the `extend:` URL in `myst.yml` to the same exact version before the
build, so the plugin, its assets and the CLI always come from one release.

| You want | Workflow ref | What happens |
|---|---|---|
| Live, safe updates (recommended) | `@v0.1` | Every build uses the newest 0.1.x |
| Live updates including breaking changes | `@v0` | Newest 0.x, whatever it is |
| Bleeding edge | `@main` | The kit's main branch |
| A frozen course | `@v0.1.3` or a commit SHA | Never changes (Dependabot can propose bumps) |

From 1.0 on, the safe live ref is `@v1`.

**About "latest":** GitHub Actions has no automatic latest ref; the floating
tags above are "latest within a line". jsDelivr does serve `@latest`, but it
caches alias URLs (`@0.1`, `@latest`) for up to 7 days and `@latest` crosses
major versions, so don't put `@latest` in `myst.yml`. The alias you commit
there only matters for local previews (CI pins it). To force the newest
release on CI, pass `kit-version: latest` to the workflow.

Local previews cache the downloaded plugin for 30 days in `_build/cache`;
`myst clean --cache` refreshes it.

## Local preview of a course

```bash
uv venv && uv pip install -r requirements.txt neuromatch-course-kit==0.1.*
uv run nma-kit check
uv run nma-kit render-scrolly   # optional: real outputs on scrolly pages
uv run myst start
```

## Developing the kit

See [AGENTS.md](AGENTS.md) for the layout, the Python/JS twin rules and the
test commands. In short:

```bash
cd python && uv venv && uv pip install -e '.[test]' -r ../example-course/requirements.txt && uv run pytest -q ../tests/python
cd js && npm ci && npm run build && npm test && npm run build:dev && npm test
scripts/build-example.sh   # build example-course with the dev bundle
```

To try a kit change in a course without releasing, point the course's
`project.plugins` at a local dev bundle (`npm run build:dev`) and install the
CLI with `uv pip install -e <kit>/python`.

## Releasing

Commits on `main` use conventional messages (`fix:`, `feat:`, `feat!:`).
release-please keeps a release PR open; merging it tags `vX.Y.Z`, publishes
npm and PyPI, and moves the `vX.Y` and `vX` tags.

One-time setup (after this repo exists as `neuromatch/course-kit`):

1. **npm**: create the free npm organization `neuromatch`. Publish the first
   version by hand (`cd js && npm run build && npm publish --access public`),
   because npm trusted publishing can only be configured on an existing
   package. Then add a trusted publisher: repository `neuromatch/course-kit`,
   workflow `release.yml`.
2. **PyPI**: add a *pending publisher* for project `neuromatch-course-kit`:
   repository `neuromatch/course-kit`, workflow `release.yml`, environment
   `release`. The first release creates the project.
3. Create the `release` environment in the repo settings.
4. Add a second owner/maintainer on npm and PyPI.

## License

BSD-3-Clause.
