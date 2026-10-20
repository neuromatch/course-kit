# Neuromatch course kit

The tooling behind Neuromatch courses built with [MyST](https://mystmd.org),
in one versioned package:

- **MyST plugin**: `{nma-video}`, `{nma-slides}`, `{nma-solution}`,
  `{nma-explanation}`, `{nma-feedback}`, scrollytelling pages (`{step}`,
  `{stage}`) and editable, runnable code cells.
- **`nma-kit` CLI**: content checks, notebook generation (student, instructor,
  solutions), scrolly pre-rendering, site preparation, notebook publishing.
- **Site branding**: the Neuromatch stylesheet, Rubik font, logos and favicon,
  written into a course by `nma-kit sync-assets`.
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
   site:
     template: book-theme
     options:
       folders: true
       logo_text: My Course Title    # your course's name next to the logo
       # The kit's branding, written to _nma/ by `nma-kit sync-assets`:
       style: _nma/site.css
       logo: _nma/logo.svg
       logo_dark: _nma/logo-dark.svg
       favicon: _nma/favicon.png
   ```

2. Copy [`templates/course.yml`](templates/course.yml) to
   `.github/workflows/course.yml`. Pull requests are checked; pushes to `main`
   publish the notebooks (to `notebooks-branch`, created automatically) and
   the site.
3. In the repo's **Settings → Pages**, set **Source** to **GitHub Actions**
   (and the custom domain, if any; no `CNAME` file needed).
4. Generate the branding files once for local previews (CI does it for you):

   ```bash
   uv run nma-kit sync-assets
   ```

   This writes `_nma/` (stylesheet, logos, favicon). The folder ignores itself,
   so nothing gets committed. Re-run it after upgrading the kit. See
   [Site branding](#site-branding).

5. List the packages your tutorials import in `requirements.txt` (CI installs
   them next to the kit; `nma-kit render-scrolly` executes scrolly pages).

Optional settings, in the `nma:` block of `myst.yml` (defaults shown, except
`brand` and `style`, which are unset by default):

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
  brand:                          # colours, see "Site branding"
    primary: "#008CBF"
  style:
    extra: _static/extra.css      # your own CSS, appended after the kit's
```

## Site branding

The kit carries the Neuromatch look: the colour palette, the Rubik font
(embedded in the stylesheet, so the kit's own CSS makes no font requests), the
logos and the favicon. It also styles the kit's own widgets (editable cells,
scrollytelling) and hides JupyterLite's toolbar, so courses no longer carry
that rule themselves.

`nma-kit sync-assets` writes these files to `_nma/` in the course:

| File | Used as |
|---|---|
| `_nma/site.css` | `site.options.style`: the kit stylesheet, then your colour overrides, then your own CSS |
| `_nma/logo.svg`, `_nma/logo-dark.svg` | `site.options.logo`, `logo_dark` |
| `_nma/favicon.png` | `site.options.favicon` |

CI runs it as part of `nma-kit prepare-site`. Locally, run it once and again
after upgrading the kit. MyST accepts a single `style` file, which is why the
kit stylesheet and your own CSS are combined into `_nma/site.css`.

**Change the colours** with the `nma.brand` block (all keys optional, each a
`"#RRGGBB"` string):

```yaml
nma:
  brand:
    primary: "#D9480F"       # links, accents, buttons
    primary_hover: "#A63700" # default: primary, 25% darker
    primary_light: "#FF8A57" # accent on dark backgrounds, default: primary, 35% lighter
    secondary: "#45429C"     # header surface, tips
    accent: "#FA7A7A"        # exercise cells
```

**Add your own CSS** with `nma.style.extra`: the file (relative to the course
root) is appended after the kit's CSS, so its rules win. The brand colours are
CSS variables (`--nma-brand-primary`, ...), so your CSS can use them too.

`nma-kit check` reports unknown keys and malformed colours. The course title
and `logo_text` stay in your `myst.yml`.

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
uv run nma-kit sync-assets      # site branding, written to _nma/
uv run nma-kit render-scrolly   # optional: real outputs on scrolly pages
uv run myst start
```

## Developing the kit

See [AGENTS.md](AGENTS.md) for the layout, the Python/JS twin rules and the
test commands. In short:

```bash
(cd python && uv venv && uv pip install -e '.[test]' -r ../tests/example-course/requirements.txt && uv run pytest -q ../tests/python)
(cd js && npm ci && npm run build && npm test && npm run build:dev && npm test)
tests/scripts/build-example.sh   # build tests/example-course with the dev bundle
```

To try a kit change in a course without releasing, point the course's
`project.plugins` at a local dev bundle (`npm run build:dev`) and install the
CLI with `uv pip install -e <kit>/python`.

## Releasing

Commits on `main` use conventional messages (`fix:`, `feat:`, `feat!:`).
release-please keeps a release PR open; merging it tags `vX.Y.Z`, publishes
npm and PyPI, and moves the `vX.Y` and `vX` tags.

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

## License

BSD-3-Clause.
