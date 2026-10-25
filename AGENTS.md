# AGENTS.md (course kit)

Human contributors: start with [CONTRIBUTING.md](CONTRIBUTING.md); this file is the internals reference.

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
  biome.json                  # JS lint config
  src/
    index.mjs                 # merges every feature plugin (transform order: solutions, feedback, scrolly, cells)
    shared/                   # config.mjs (myst.yml settings, YAML), paths.mjs (page location, notebook/solution URLs),
                              # assets.mjs (assetUrl), frontmatter.mjs (isScrolly), tree.mjs (mdast helpers)
    media/plugin.mjs          # {nma-video}, {nma-slides} -> static iframes / tab sets
    solutions/plugin.mjs      # {nma-solution}, {nma-explanation} -> "Click for ..." links
    assets/plugin.mjs         # {nma-data} -> "Data used by this notebook" note; embeds declared files (base64) for cells
    feedback/plugin.mjs       # {nma-feedback} -> anywidget; assets/widget.mjs posts to datatops
    scrolly/plugin.mjs        # {step}/{stage}, stage/card layout; assets/{engine,runnable}.mjs, *.css
    cells/plugin.mjs          # editable cells on browser pages, Colab banner on runtime: colab pages
    cells/src/                # browser code bundled into assets/cells/{panel,runtime-widget}.mjs (CodeMirror 6, thebe-lite)
    cells/assets/             # cells.css (shadow root), page.css (copied into <head>)
  build.mjs                   # esbuild: dist/nma.mjs + dist/assets/<feature>/ (+ dist/nma.yml on release)
  nma.yml.tmpl                # the config courses `extend:`
python/src/nma_kit/
  cli.py                      # nma-kit check | notebooks | render-scrolly | sync-assets | prepare-site | publish-notebooks
  constants.json, constants.py  # values shared with the JS plugin (single source, see Rules)
  config.py                   # Settings from myst.yml (github repo, nma.paths.tutorials, nma.notebooks.branch)
  convert.py                  # content rules, jupytext conversion, badges, prepare-site
  media.py solutions.py feedback.py scrolly.py cells.py assets.py   # Python side of each feature
  pin.py                      # pin course-kit CDN URLs in myst.yml to one version
  branding.py                 # sync-assets: _nma/site.css (+ brand colours, extra CSS), logos, favicon
  assets/                     # the branding source: site.css, logos, favicon, fonts/ (Rubik, OFL)
  publish.py                  # push notebooks/ to the notebooks branch (orphan branch if missing)
tests/
  python/ js/ e2e/            # unit tests (pytest, node:test) and the browser smoke test
  fixtures/                   # shared by Python and JS tests (nma_config, scrolly, cells, config, assets)
  twins.json                  # registry of Python/JS twins, checked by tests/python/test_twins.py
  example-course/             # minimal course: built by CI with the dev bundle, target of the e2e tests
  scripts/build-example.sh    # build the example course like a course's CI does
  scripts/compare_builds.py   # golden check: two course builds produce the same notebooks and pages
docs/releasing.md             # maintainers: how releases are set up (CONTRIBUTING.md is the contributor guide)
Makefile, ruff.toml           # contributor tasks (make help); Python lint config (JS: js/biome.json)
.pre-commit-config.yaml       # runs the linters on commit (installed by make setup)
templates/course.yml          # the workflow courses copy (calls the reusable workflows @v0.1)
templates/wheels.yml          # optional caller for course-wheels.yml
.github/actions/setup-course/   # shared setup (uv, Node, install the kit) used by the course-*.yml workflows
.github/actionlint.yaml        # ignores the job.workflow_* property errors (actionlint doesn't know them yet)
.github/workflows/            # course-check.yml, course-publish.yml, course-preview.yml, course-wheels.yml (reusable), ci.yml, release.yml
```

## Rules

- **Features are separate.** `js/src/<feature>/` imports only from itself and
  `shared/` (enforced by `tests/js/structure.test.mjs`). The Python side uses
  the same feature names.
- **Shared values live in one file.** Constants both languages need are in
  `python/src/nma_kit/constants.json` (read by `constants.py`, inlined by
  `js/src/shared/constants.mjs`). Never redeclare them on one side.
- **Python/JS twins stay in sync**, tested against the same fixtures. Every twin is
  listed in `tests/twins.json` (symbols, fixture) and `tests/python/test_twins.py` fails when
  one is renamed, removed or untested; add an entry when you write a twin
  (see CONTRIBUTING.md). Current pairs:
  - URL templates (`VIDEO_SOURCES` in `media/plugin.mjs` and `media.py`).
  - `{nma-data}` parsing/validation and the asset URL (`assets/model.mjs` / `assets.py`: `parseDataDirective`/`parse_data_directive`,
    `validateDataDirectives`/`validate_data_directives`, `assetUrlFor`/`asset_url`), `tests/fixtures/assets/directives.json`.
    The strict code-reference scan and the notebook download cell are Python-only.
  - Solution file naming and URLs (`solutions/plugin.mjs`, `shared/paths.mjs` / `solutions.py`).
  - Course settings and page location (`shared/config.mjs`, `shared/paths.mjs` / `config.py`), `tests/fixtures/config/settings.json`.
  - The notebooks branch: `NMA_NOTEBOOKS_BRANCH` overrides `nma.notebooks.branch` in
    `load_settings` / `loadSettings` (blank is ignored), `tests/fixtures/config/settings.json` (`env`).
  - The `nma:` block reader (`readNmaConfig` / `read_nma_block`, both YAML), `tests/fixtures/nma_config/`.
    `nma-kit check` still rejects non-string values, lists and deeper nesting.
  - `isScrolly`/`is_scrolly`, `cellKey`/`cell_key`, `parseParams`/`parse_params`, `tests/fixtures/scrolly/`.
    `cell_key` = first 16 hex chars of sha256 of the code with CRLF -> LF,
    trailing spaces/tabs stripped per line, outer blank lines stripped.
  - `runtimeOf`/`runtime_of`, `tests/fixtures/cells/runtime.json`. `NO_FALLBACK_MARKER` is
    shared through `constants.json`.
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

## Content roots (internals)

- Pages live in **content roots**: `tutorials` (`nma.paths.tutorials`) and
  `projects` (`nma.paths.projects`). `Settings.content_roots` /
  `contentRoots()` list `(name, directory)`; the *name* is fixed, the
  directory is configurable. A missing directory is just empty.
- Everything generated is scoped by the root name:
  `notebooks/<root>/<relDir>/<stem>.ipynb` (+ `instructor/`, `solutions/`),
  `_build/scrolly/<root>/<relDir>/<stem>.json`. `page_location` /
  `pageLocation` return the root too, and `PageLocation.notebook_dir` /
  `notebookDir()` give the folder under `notebooks/`. The deepest matching
  directory wins when roots are nested.
- `nma-kit notebooks | prepare-site | render-scrolly | check` all go through
  `process_content` / the roots, so a feature added to tutorials works in projects.
  The twins are tested with `tests/fixtures/config/settings.json`.

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
- `tests/scripts/build-example.sh` ends with `git checkout -- tutorials projects myst.yml`
  to undo `prepare-site`: stage (`git add`) edits to the example course's
  `myst.yml` before running it, or they are reverted too.

## Data and images (internals)

- Files live in the day folder (`tutorials/<day>/data/`, `image/`; names from `nma.assets.data|image`).
  A tutorial declares what it uses with `{nma-data}` (one path per line, `data/` or `image/` prefix, no `..`).
- **Notebooks** (`build_notebooks`): the directive is stripped, a hidden `hide-cell` download cell
  (`# @title Download course data`, right after the badge cell) fetches the declared files from
  `raw.githubusercontent.com/<repo>/<branch>/notebooks/<root>/<day>/`, markdown images (`image/..`) are
  rewritten to the same URLs, and declared files are copied to `notebooks/<root>/<day>/` so `publish-notebooks` ships them.
- **Browser cells**: the plugin reads declared files at build time and embeds them (base64) in the runtime
  widget model; `PageRuntime.writeAssets` writes them into the kernel through a Python prelude before the first cell
  (and after a restart). No fetch, so it works without the notebooks branch and under any base path.
- **Scrolly pages**: the assets transform runs before scrolly, so `buildScrolly` puts the files in the engine model;
  `engine.mjs` publishes them on `window.NMA_SCROLLY.assets` and `runnable.mjs` (`writeAssets`) writes them with
  `py.FS` right after `loadPyodide`.
- **`{figure}` / `{image}`** in notebooks become `<img>` (+ italic caption) with the published URL
  (`convert_image_directives`, run by `rewrite_markdown_images`); markdown `![]()` and `<img>` are rewritten in place.
- `nma-kit check` errors: bad/missing declared files; code that uses a strict literal `data/x.ext` / `image/x.ext`
  that no `{nma-data}` declares; f-string paths (`f"data/{x}.npz"`) under a folder where the page declares no file;
  page images (markdown, `<img>`, `{figure}`) under `image/` that aren't declared (they'd work on the site but never
  reach Colab); declared files over `MAX_EMBED_BYTES` (2 MB total, `max_embed_bytes` in `constants.json`; `assets/plugin.mjs` skips
  embedding with a warning). Other dynamic paths can't be detected: declare every file the code can reach.
- The embedded bytes grow the page: keep tutorial files small; large datasets use the author's own download cell.
- Limits: the download cell needs Internet (on Kaggle it must be turned on; the cell says so on failure), and raw
  URLs don't work for a private repo.

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
  `_build/scrolly/<root>/<relDir>/<stem>.json` = `{cell_key: {stdout, images, error}}`.
  A raising cell fails CI with `file:line`.

## Commands

`make help` lists the shortcuts (`make setup`, `make test`, `make lint`, `make example`); `ruff.toml`
and `js/biome.json` configure the linters (CI runs the same). The underlying commands:

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

## PR previews (internals)

- `course-preview.yml` (called from the course's `pull_request` workflow, `action`
  = `deploy` or `cleanup`) builds the PR like `course-publish.yml`, but its job
  sets `NMA_NOTEBOOKS_BRANCH=notebooks-pr-<n>`. `nma-kit publish-notebooks`, the
  badges, solution links and the download cell all read `settings.notebooks_branch`,
  so the override is the only coupling; no preview-specific code in the CLI or plugin.
- Deploy: `wrangler pages deploy --branch pr-<n>` (direct upload; the project is
  created on first use). Cleanup uses the GitHub and Cloudflare APIs, not a
  checkout (a closed PR's merge ref may be gone).
- Never `pull_request_target` (it would hand secrets to PR code); jobs are limited
  to same-repo PRs. `tests/python/test_preview_workflow.py` pins these rules; the
  Cloudflare calls themselves are only checked on a real course PR.
- The kit previews its own PRs through `preview.yml` (example course, `kit-source: local`),
  separate from `ci.yml` so CI does not rerun when a PR closes. The example course publishes
  to this repo, so each open PR has a `notebooks-pr-<n>` branch here until it closes. It is
  skipped for the release-please PR (version strings only), like the e2e job in `ci.yml`; both match
  the branch prefix `release-please--`, not the full name (which encodes the target branch and component).
- Registered for releases like the other reusable workflows (`KIT_VERSION` marker,
  `release-please-config.json`, `REUSABLE` in `test_release.py`).

## CI

- `ci.yml` runs on pull requests only (branch protection requires PRs to be up
  to date with `main`), through the Makefile (`make lint | test-py | test-js`): lint; pytest; JS dev + release builds with tests; example
  course build + e2e (skipped on the release-please PR, which only changes
  version strings); the reusable `course-check.yml` run against
  `tests/example-course` with `kit-source: local`.
- `release.yml`: release-please PR -> tag `vX.Y.Z` -> npm (provenance) and
  PyPI (trusted publishing) -> move `vX.Y` and `vX`. The jobs build with
  `make test-js`, `make dist-js` and `make dist-py` (the publish steps stay in Actions). release-please uses the
  `RELEASE_PLEASE_TOKEN` secret (a PAT or app token with Contents, Pull
  requests and Workflows access), because it edits `KIT_VERSION` in
  `.github/workflows/` and the default token may not; the token also makes CI
  run on the release PR. Setup: docs/releasing.md.
- **Shared setup.** `course-check`, `course-publish` and `course-preview` fetch this repo at
  `job.workflow_sha` (sparse checkout of `.github/actions/setup-course` into `.course-kit/`) and run
  it as a local composite action: uv, Node, the course's packages and the kit. That pins the setup to
  the workflow's own commit without a tag. The kit's own CI exercises it through
  `ci.yml` (`course-check`) and `preview.yml`. `tests/python/test_workflow_setup.py` pins the shape.
- `course-publish.yml` job order: check -> notebooks -> publish-notebooks ->
  render-scrolly -> prepare-site -> myst build -> Pages deploy. One run per
  repository at a time (notebook pushes never race). No CNAME step: with the
  Pages "GitHub Actions" source the custom domain is a repo setting.
