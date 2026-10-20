# AGENTS.md (course kit)

Context for AI agents working on the Neuromatch course kit. Authoring
conventions for course content (directives, frontmatter, exercises, scrolly
pages) live in the course template's AGENTS.md; this file covers how the kit
implements them.

## What the kit is

One project, one version, three deliverables:

| Deliverable | Source | Published as | Used by courses via |
|---|---|---|---|
| MyST plugin (one bundled file) + browser assets | `js/` | npm `@neuromatch/course-kit` (`dist/`) | `extend: https://cdn.jsdelivr.net/npm/@neuromatch/course-kit@0.1/dist/nma.yml` |
| `nma-kit` CLI (notebooks, checks, site prep) | `python/` | PyPI `neuromatch-course-kit` | installed by the reusable workflows |
| Reusable GitHub workflows | `.github/workflows/course-*.yml` | git tags `vX.Y.Z`, floating `vX.Y`/`vX` | `uses: neuromatch/course-kit/.github/workflows/course-publish.yml@v0.1` |

Versioning: 0.x until stable. release-please bumps breaking changes to the
next minor (0.1 -> 0.2) and features/fixes to the patch, so a `v0.MINOR` line
is the compatible line. See README.md.

## Layout

```
js/
  src/
    index.mjs                 # merges every feature plugin (transform order: solutions, feedback, scrolly, cells)
    shared/                   # config.mjs (myst.yml settings, YAML), paths.mjs (page location, notebook/solution URLs),
                              # assets.mjs (assetUrl), frontmatter.mjs (isScrolly), tree.mjs (mdast helpers)
    media/plugin.mjs          # {nma-video}, {nma-slides} -> static iframes / tab sets
    solutions/plugin.mjs      # {nma-solution}, {nma-explanation} -> "Click for ..." links
    feedback/plugin.mjs       # {nma-feedback} -> anywidget; assets/widget.mjs posts to datatops
    scrolly/plugin.mjs        # {step}/{stage}, stage/card layout; assets/{engine,runnable}.mjs, *.css
    cells/plugin.mjs          # editable cells on browser pages, Colab banner on runtime: colab pages
    cells/src/                # browser code bundled into assets/cells/{panel,runtime-widget}.mjs (CodeMirror 6, thebe-lite)
    cells/assets/             # cells.css (shadow root), page.css (copied into <head>)
  build.mjs                   # esbuild: dist/nma.mjs + dist/assets/<feature>/ (+ dist/nma.yml on release)
  nma.yml.tmpl                # the config courses `extend:`
python/src/nma_kit/
  cli.py                      # nma-kit check | notebooks | render-scrolly | prepare-site | publish-notebooks
  config.py                   # Settings from myst.yml (github repo, nma.paths.tutorials, nma.notebooks.branch)
  convert.py                  # content rules, jupytext conversion, badges, prepare-site
  media.py solutions.py feedback.py scrolly.py cells.py   # Python side of each feature
  pin.py                      # pin course-kit CDN URLs in myst.yml to one version
  branding.py                 # sync-assets: _nma/site.css (+ brand colours, extra CSS), logos, favicon
  assets/                     # the branding source: site.css, logos, favicon, fonts/ (Rubik, OFL)
  publish.py                  # push notebooks/ to the notebooks branch (orphan branch if missing)
tests/
  python/ js/ e2e/            # unit tests (pytest, node:test) and the browser smoke test
  fixtures/                   # shared by Python and JS tests (nma_config, scrolly, cells, config)
  example-course/             # minimal course: built by CI with the dev bundle, target of the e2e tests
  scripts/build-example.sh    # build the example course like a course's CI does
  scripts/compare_builds.py   # golden check: two course builds produce the same notebooks and pages
templates/course.yml          # the workflow courses copy (calls the reusable workflows @v0.1)
templates/wheels.yml          # optional caller for course-wheels.yml
.github/workflows/            # course-check.yml, course-publish.yml, course-wheels.yml (reusable), ci.yml, release.yml
```

## Rules

- **Features are separate.** `js/src/<feature>/` imports only from itself and
  `shared/` (enforced by `tests/js/structure.test.mjs`). The Python side uses
  the same feature names.
- **Python/JS twins stay in sync**, tested against the same fixtures:
  - URL templates (`VIDEO_SOURCES` in `media/plugin.mjs` and `media.py`).
  - Solution file naming and URLs (`solutions/plugin.mjs`, `shared/paths.mjs` / `solutions.py`).
  - Course settings and page location (`shared/config.mjs`, `shared/paths.mjs` / `config.py`), `tests/fixtures/config/settings.json`.
  - The `nma:` block reader (`readNmaConfig` / `read_nma_block`, both YAML), `tests/fixtures/nma_config/`.
    `nma-kit check` still rejects non-string values, lists and deeper nesting.
  - `isScrolly`/`is_scrolly`, `cellKey`/`cell_key`, `parseParams`/`parse_params`, `tests/fixtures/scrolly/`.
    `cell_key` = first 16 hex chars of sha256 of the code with CRLF -> LF,
    trailing spaces/tabs stripped per line, outer blank lines stripped.
  - `runtimeOf`/`runtime_of`, `tests/fixtures/cells/runtime.json`. `NO_FALLBACK_MARKER`
    in `solutions.py` and `cells/src/model.mjs` must match.
- **Asset URLs** come from `shared/assets.mjs`:
  - release build: `https://cdn.jsdelivr.net/npm/@neuromatch/course-kit@<exact version>/dist/assets/<rel>`.
    MyST downloads these at build time and serves them from the site (`build/<md5>.mjs`),
    so readers' browsers never hit the CDN.
  - dev build: `dist/assets/` next to the bundle, as a course-root-relative path (`/course-kit/js/dist/assets/...`).
    Paths may climb out of the course root (`/../../js/dist/assets/...` for `example-course`).
  - Never an alias (`@0.1`, `@latest`) at build time: jsDelivr caches aliases for 7 days.
- **Browser code** never uses root-absolute URLs (forks deploy under `github.io/<repo>/`):
  derive them from `import.meta.url`. The cells bundle finds thebe at `../thebe-core.min.js`
  relative to itself, which holds because MyST puts all widget assets in `build/`.
- **Bundles are built, not committed.** `js/dist/` is gitignored. The plugin
  bundle includes a `createRequire` shim because bundled CommonJS (`yaml`)
  calls `require()` for Node built-ins.
- **Settings are cached per working directory** (`courseSettings()`), because
  MyST runs plugins from the course root and tests switch courses.
- **One version everywhere.** `tests/python/test_release.py` checks that
  `js/package.json`, `python/pyproject.toml`, `nma_kit.__version__`,
  `.release-please-manifest.json` and `KIT_VERSION` in the reusable workflows agree.
- The toolbar rule `.myst-jp-nb-toolbar { display: none !important; }`
  (editable cells replace JupyterLite's power button) is in the kit's
  `site.css`; courses no longer carry it.

## Site branding (internals)

- **Source of truth**: `python/src/nma_kit/assets/` (`site.css`, logos, favicon,
  `fonts/`). It lives inside the Python package, not in a top-level folder,
  because `uv build` makes the wheel from the sdist, which can't include files
  from outside `python/`. `tests/python/test_branding.py` checks they ship.
- **`nma-kit sync-assets`** (also run by `prepare-site`, not by `--dry-run`)
  writes `_nma/` in the course: `site.css`, `logo.svg`, `logo-dark.svg`,
  `favicon.png`, and a `.gitignore` containing `*`, so courses never commit it.
- **Courses name the files themselves** in `site.options` (`style`, `logo`,
  `logo_dark`, `favicon`). The kit's `nma.yml` does not set them: MyST lets the
  course's values win over an extended file's, and how it resolves relative
  file paths of a *remote* extended config is unverified. Don't move them into
  `nma.yml` without testing that in a real course.
- **One `style` slot**: `site.css` = kit CSS (Rubik embedded as data URIs, so
  no relative `url()` depends on where MyST serves the file and the kit's CSS
  makes no font requests; the YouTube players embedded by `{nma-video}`
  fetch Roboto from Google inside their own iframes, which
  `tests/e2e/test_branding_browser.py` deliberately doesn't count)
  + `:root` overrides from `nma.brand` + the course's
  `nma.style.extra` file.
- **CSS variables are the API**: `--nma-brand-*` (the five colours a course may
  change), `--nma-cell-*` and `--nma-tok-*` (read by `cells/assets/cells.css`).
  Syntax-token colours are fixed on purpose (chosen for contrast).
- Settings are validated by `branding.brand_errors` inside `check`.
- `tests/scripts/build-example.sh` ends with `git checkout -- tutorials myst.yml`
  to undo `prepare-site`: stage (`git add`) edits to the example course's
  `myst.yml` before running it, or they are reverted too.

## Editable cells (internals)

- Runs on the JupyterLite kernel MyST already ships (thebe-lite, Pyodide 0.27),
  one kernel per page. Courses keep `project.jupyter.lite: true` (the kit's
  `nma.yml` sets it), since MyST only emits the thebe assets with it.
- **A Run** works like a notebook: earlier cells that haven't run go first,
  then the target. An earlier unfinished exercise runs its `{nma-solution}`
  through the kernel-side fallback cell from `prepare-site`. The explicitly run
  cell gets a trailing `# nma-no-fallback` line, so a partly edited exercise
  shows `NotImplementedError`, never the solution. Running stops at the first
  earlier cell that fails.
- **Modes by tag**: none = editor + output, `hide-input`/`hide-cell` = editor
  behind "Show code", `remove-input` = output only, `remove-cell` = no panel,
  runs as an earlier cell.
- **Styling**: CSS variables with light/dark defaults, overridable from the
  course's CSS (`--nma-cell-*`, `--nma-tok-*`; see `cells/assets/cells.css`).
- **Outside services** readers' browsers must reach: `cdn.jsdelivr.net`
  (Pyodide, widget JS), `cdnjs.cloudflare.com` (require.js, MathJax,
  font-awesome), `pypi.org`/`files.pythonhosted.org` (micropip). Scrolly pages
  load their own, newer Pyodide (`nma.scrolly.pyodide_url`).

## Scrolly (internals)

- The section sits between the book theme's TOC sidebar and outline
  (`.scrolly-col` in `scrolly.css`) and uses container queries on its own width
  (stage beside the cards from 760px, `WIDE` in `engine.mjs`).
- **Colours follow the site.** `scrolly.css` defines `--sc-*` tokens on `.scrolly`
  (light) and overrides them under `.dark .scrolly`; `runnable.css` and the HUD
  styles in `engine.mjs` read the same tokens (custom properties inherit into
  the shadow DOM, so no JS switches modes). Brand colours come from the kit
  stylesheet's `--nma-brand-*`, so `nma.brand` recolours scrolly pages too;
  syntax colours reuse `--nma-tok-*` (shared with the editable cells). Hex
  values in `var(..., #hex)` are the Neuromatch defaults for courses that
  don't load `site.css`. `tests/js/scrolly.test.mjs` checks that every
  `--sc-*` in use is defined and that dark mode only overrides known tokens.
  Don't add fixed colours: add a token.
- Engine (HUD), stage and steps share one grid cell (`grid-area: 1 / 1`), not
  negative margins (a sticky element with `margin-bottom: -height` covered the
  footer links; regression test in `tests/js/scrolly.test.mjs`).
- `nma-kit render-scrolly` runs each scrolly page's instructor notebook
  (exercise cells removed, `# @param` at defaults, cwd = page dir) and writes
  `_build/scrolly/<relDir>/<stem>.json` = `{cell_key: {stdout, images, error}}`.
  A raising cell fails CI with `file:line`.

## Commands

```bash
# Python
cd python && uv venv && uv pip install -e '.[test]' -r ../tests/example-course/requirements.txt
uv run pytest -q ../tests/python

# JS (Node 22)
cd js && npm ci
npm run build && npm test        # release build: CDN asset URLs, dist/nma.yml
npm run build:dev && npm test    # dev build: local asset paths

# Example course + browser smoke test
tests/scripts/build-example.sh
(cd tests/example-course/_build/html && python3 -m http.server 8765 &)
python/.venv/bin/playwright install chromium
NMA_E2E_URL=http://localhost:8765 python/.venv/bin/pytest -q --reruns 1 -n 4 tests/e2e
# NMA_E2E_COURSE=<course root> tests another course's build;
# NMA_E2E_REQUIREJS=<path to require.js> if cdnjs is blocked.

# Golden check for a change: build a course before and after, then
python3 tests/scripts/compare_builds.py <before course root> <after course root>
```

Every page with editable cells boots its own Pyodide kernel (about a minute
or more in CI, CPU time, not downloads: a shared browser context did not help),
so the e2e tests run in parallel (`-n 4`) and tests that don't need a kernel
(the branding checks) use the `runtime: colab` tutorial, which loads in about
a second. Keep it that way when adding tests.

The e2e suite is timing-sensitive on cold caches (first Pyodide/JupyterLite
downloads); CI retries failed tests once.

## CI

- `ci.yml` runs on pull requests only (branch protection requires PRs to be up
  to date with `main`): pytest; JS release + dev builds with tests; example
  course build + e2e (skipped on the release-please PR, which only changes
  version strings); the reusable `course-check.yml` run against
  `tests/example-course` with `kit-source: local`.
- `release.yml`: release-please PR -> tag `vX.Y.Z` -> npm (provenance) and
  PyPI (trusted publishing) -> move `vX.Y` and `vX`. release-please uses the
  `RELEASE_PLEASE_TOKEN` secret (a PAT or app token with Contents, Pull
  requests and Workflows access), because it edits `KIT_VERSION` in
  `.github/workflows/` and the default token may not; the token also makes CI
  run on the release PR. Setup: README, "Releasing".
- `course-publish.yml` job order: check -> notebooks -> publish-notebooks ->
  render-scrolly -> prepare-site -> myst build -> Pages deploy. One run per
  repository at a time (notebook pushes never race). No CNAME step: with the
  Pages "GitHub Actions" source the custom domain is a repo setting.
