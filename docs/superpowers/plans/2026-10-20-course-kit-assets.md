# Course-kit data & images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let course authors keep `data/` and `image/` files in the day folder and reference them with plain relative paths (`data/x.npz`, `image/y.png`) that work unchanged on the MyST site, in browser editable cells, and in generated Colab/Kaggle notebooks, driven by one `{nma-data}` directive.

**Architecture:** A new `assets` feature (Python `nma_kit.assets` + `js/src/assets/`), following the kit's existing directive + twin pattern (modeled on `media`). The directive is the single manifest. Python expands it into a hidden `hide-cell` download cell in generated notebooks and rewrites markdown image refs to `raw.githubusercontent.com` URLs; publishing already ships the copied asset folders. The JS plugin reads the same directive, embeds the declared file bytes (base64) into the cells runtime model so the browser Pyodide FS can be pre-filled, and renders a collapsible "Data used by this notebook" note on the site.

**Tech Stack:** Python 3 (stdlib + yaml + jupytext pipeline), Node 22 ESM (MyST plugin, esbuild), pytest + node:test.

**Spec:** `docs/superpowers/specs/2026-10-20-course-kit-assets-design.md`

## Global Constraints

- **One version everywhere** — do not touch version strings; no release bump in this work.
- **Features are separate**: `js/src/assets/` imports only from itself and `shared/` (enforced by `tests/js/structure.test.mjs`). Python side uses the same feature name `assets`.
- **Python/JS twins stay in sync**, tested against a shared fixture under `tests/fixtures/assets/`: the directive parser (`parse_data_directive` / its JS twin) and the URL builder (`asset_url` / its JS twin) must return identical results for identical input.
- **Asset URL for notebooks** is exactly `https://raw.githubusercontent.com/<repo>/<branch>/notebooks/<day>/<path>` (data and rewritten markdown images alike). `<branch>` is `settings.notebooks_branch`; `<repo>` is `settings.github_repo`; `<day>` is the page's `rel_dir` from `page_location`.
- **Browser never fetches**: declared file bytes are embedded (base64) at build time; no network, no dependence on the published branch.
- **Injected content is never committed**: the download cell (notebooks) and any rewrite must never appear in a `.md` source; `validate_content` rejects it, mirroring the existing badge/fallback guards.
- **Default folder names** are `data` and `image`, overridable via `nma.assets.data` / `nma.assets.image` (string values only).
- **Strict reference pattern** for the undeclared-reference error: a code string literal matching `^(data|image)/[\w./-]+\.\w+$` (known prefix + extension, no `{`). Uses the configured folder names, not literally `data|image`, when names are overridden.

## Review Focus

- **Directive inside a fenced example** (````markdown showing `{nma-data}`) must not be treated as a real directive — covered by reusing `media`'s fence-skipping `find_directives`; test in Task 1.
- **A declared path that escapes the day folder** (`../other/x.npz`, absolute path) must be a hard error, not a silent copy outside the tree — test in Task 2 (validation) and Task 6 (publish copy never leaves `notebooks/<day>/`).
- **An f-string / dynamic load** (`np.load(f"data/{n}.npz")`) must NOT be flagged by the undeclared-reference check (contains `{`) — test in Task 2.
- **A non-path string that happens to start with the prefix** (`"data/raw"` with no extension, a `"image/png"` mimetype) must NOT be flagged — test in Task 2.
- **A page with no `{nma-data}` and no asset references** must be completely unaffected (no download cell, no runtime embed, no note) — test in Task 3 and Task 5.

---

## Task 1: `{nma-data}` directive parsing + validation (Python)

**Files:**
- Create: `python/src/nma_kit/assets.py`
- Create: `tests/fixtures/assets/directives.json` (shared twin fixture: inputs → expected file lists)
- Test: `tests/python/test_assets.py`

**Interfaces:**
- Consumes: `nma_kit.media.find_directives`-style fence handling (reimplement for the `nma-data` kind, or factor a shared helper — implementer's call; do not change `media.py`'s public behavior).
- Produces:
  - `@dataclass DataDirective { arg: str; paths: list[str]; start: int; end: int; body_extra: list[str] }` where `paths` are the non-empty body lines.
  - `find_data_directives(text: str) -> list[DataDirective]` — top-level `{nma-data}` directives in order, skipping fenced examples.
  - `parse_data_directive(text: str) -> list[str]` — the ordered, de-duplicated file paths across all `{nma-data}` directives on a page (the page manifest). This is the twin entry point.
  - `validate_data_directives(text: str, data_dir: str, image_dir: str) -> list[str]` — directive-shape errors (unclosed, has an inline arg, empty body) and per-path prefix errors (a path whose first segment is neither `data_dir` nor `image_dir`, or that contains `..`/is absolute).

- [ ] **Step 1: Write the failing tests** in `tests/python/test_assets.py`, driven partly by `tests/fixtures/assets/directives.json`:

```python
def test_parse_collects_paths():
    text = ":::{nma-data}\ndata/a.npz\nimage/b.png\n:::\n"
    assert parse_data_directive(text) == ["data/a.npz", "image/b.png"]

def test_parse_dedupes_across_blocks_in_order():
    text = ":::{nma-data}\ndata/a.npz\n:::\n\n:::{nma-data}\ndata/a.npz\ndata/c.npz\n:::\n"
    assert parse_data_directive(text) == ["data/a.npz", "data/c.npz"]

def test_fenced_example_is_ignored():
    text = "````markdown\n:::{nma-data}\ndata/a.npz\n:::\n````\n"
    assert parse_data_directive(text) == []

def test_validate_rejects_unknown_prefix_and_escape(tmp_fixture):
    text = ":::{nma-data}\nfoo/a.npz\n../x.npz\n:::\n"
    errs = validate_data_directives(text, "data", "image")
    assert len(errs) == 2

def test_validate_rejects_unclosed_and_inline_arg():
    assert validate_data_directives(":::{nma-data} oops\ndata/a.npz\n", "data", "image")
```

Add the same input/expected pairs to `tests/fixtures/assets/directives.json` so Task 4 (JS twin) asserts identical output.

- [ ] **Step 2: Run to verify fail** — `cd python && uv run pytest -q ../tests/python/test_assets.py` → FAIL (module missing).
- [ ] **Step 3: Implement** `DataDirective`, `find_data_directives`, `parse_data_directive`, `validate_data_directives` in `assets.py`. Reuse `media.py`'s `ANY_FENCE_RE` fence-skipping approach for `find_data_directives`. `{nma-data}` takes no inline arg and its body is a list of paths (one per non-blank line).
- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git add python/src/nma_kit/assets.py tests/python/test_assets.py tests/fixtures/assets/directives.json && git commit -m "feat(assets): nma-data directive parsing and validation"`

## Task 2: URL builder + strict undeclared-reference scan (Python)

**Files:**
- Modify: `python/src/nma_kit/assets.py`
- Modify: `tests/python/test_assets.py`
- Modify: `tests/fixtures/assets/directives.json` (add URL + scan cases)

**Interfaces:**
- Consumes: Task 1 parser; `nma_kit.config.Settings` fields `github_repo`, `notebooks_branch`.
- Produces:
  - `asset_url(repo: str, branch: str, day: str, path: str) -> str` — `https://raw.githubusercontent.com/{repo}/{branch}/notebooks/{day}/{path}` (twin entry point; `day` joined only when non-empty).
  - `scan_code_references(code: str, data_dir: str, image_dir: str) -> list[str]` — strict literal references in one code string: quoted strings matching `^(data_dir|image_dir)/[\w./-]+\.\w+$`, excluding any containing `{`.
  - `undeclared_reference_errors(text, data_dir, image_dir) -> list[str]` — for each code cell in the MyST source, any `scan_code_references` result not in `parse_data_directive(text)`.

- [ ] **Step 1: Write failing tests**:

```python
def test_asset_url_joins_day():
    assert asset_url("org/repo", "nb", "W1D1", "data/a.npz") == \
        "https://raw.githubusercontent.com/org/repo/nb/notebooks/W1D1/data/a.npz"

def test_scan_matches_literal_only():
    assert scan_code_references('np.load("data/a.npz")', "data", "image") == ["data/a.npz"]
    assert scan_code_references('np.load(f"data/{n}.npz")', "data", "image") == []
    assert scan_code_references('x = "data/raw"', "data", "image") == []      # no extension
    assert scan_code_references('m = "image/png"', "data", "image") == []     # not a path

def test_undeclared_reference_is_error():
    md = '---\nkernelspec: {}\n---\n```{code-cell}\nnp.load("data/a.npz")\n```\n'
    assert undeclared_reference_errors(md, "data", "image")  # a.npz not declared
```

Add the `asset_url` and `scan_code_references` cases to the shared fixture.

- [ ] **Step 2: Run to verify fail** → FAIL.
- [ ] **Step 3: Implement** the three functions. For `undeclared_reference_errors`, extract code-cell bodies with the same top-level `{code-cell}` detection the kit already uses (see `convert.has_code_cells` / `solutions.find_blocks`); reuse, don't reinvent.
- [ ] **Step 4: Run to verify pass** → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat(assets): url builder and strict undeclared-reference scan"`

## Task 3: Expand directive into the notebook download cell + rewrite markdown images (Python)

**Files:**
- Modify: `python/src/nma_kit/assets.py`
- Modify: `tests/python/test_assets.py`

**Interfaces:**
- Consumes: Task 1/2.
- Produces:
  - `download_cell_source(paths: list[str], repo, branch, day) -> str` — the Python source for the hidden download cell (uses `urllib.request.urlretrieve`, `os.makedirs`, skips existing files; `_BASE` = `asset_url(..., day, "")`). Only data/image paths that will be *read as files* — pass the full declared manifest; downloading an image the author also embeds in markdown is harmless.
  - `make_download_cell(paths, repo, branch, day, cell_id="nma-download-data") -> dict` — a code cell with `metadata.tags == ["hide-cell"]`, mirroring `media.make_code_cell`.
  - `insert_download_cell(nb: dict, paths, repo, branch, day) -> bool` — insert the cell at index 0 of `nb["cells"]` if `paths` is non-empty and no such cell exists (idempotent by `cell_id`); returns whether inserted. (The badge cell is added later at position 0 by `add_badge_cell`, which already filters by content; keep download cell ordering so badge ends up first — verify against `convert.build_notebooks`.)
  - `rewrite_markdown_images(nb: dict, repo, branch, day, image_dir) -> int` — in every markdown cell, rewrite `![alt](image_dir/..)` and `<img src="image_dir/..">` to the `asset_url`; return count.

- [ ] **Step 1: Write failing tests** asserting: the download cell source contains each path and the exact `_BASE` URL and `hide-cell` tag; `insert_download_cell` is idempotent and no-ops on empty paths; `rewrite_markdown_images` turns `![x](image/a.png)` into the raw URL and leaves `data/` and non-asset links alone.
- [ ] **Step 2: Run to verify fail** → FAIL.
- [ ] **Step 3: Implement** the four functions. Use `string.Template` for the cell source (as `media.py` does) to avoid brace-escaping.
- [ ] **Step 4: Run to verify pass** → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat(assets): notebook download cell and markdown image rewrite"`

## Task 4: JS twin — directive parse, URL builder, validation (js/src/assets/)

**Files:**
- Create: `js/src/assets/plugin.mjs`
- Create: `tests/js/assets.test.mjs`
- Modify: `js/src/index.mjs` (register the feature)

**Interfaces:**
- Consumes: shared fixture `tests/fixtures/assets/directives.json` (same file Task 1/2 use); `shared/config.mjs` for folder-name settings; `shared/paths.mjs` for the page's `rel_dir`.
- Produces (named exports from `plugin.mjs`, kept small so later tasks import them):
  - `parseDataDirective(text) -> string[]` — twin of `parse_data_directive`.
  - `assetUrlFor(repo, branch, day, path) -> string` — twin of `asset_url`.
  - `validateDataDirectives(text, dataDir, imageDir) -> string[]` — twin of the Python validator (parity on the fixture).
  - default export `{ name, directives: [nmaData], transforms: [...] }` (the directive + the Task 5 transform).

- [ ] **Step 1: Write failing test** `tests/js/assets.test.mjs` that loads `tests/fixtures/assets/directives.json` and asserts `parseDataDirective` and `assetUrlFor` match every expected value (this is the twin check), plus a `validateDataDirectives` parity case.
- [ ] **Step 2: Run to verify fail** — `cd js && node --test tests/js/assets.test.mjs` → FAIL.
- [ ] **Step 3: Implement** `parseDataDirective`, `assetUrlFor`, `validateDataDirectives` and a minimal `nmaData` directive spec in `plugin.mjs`; register `assets` in `index.mjs` `PLUGINS` (order: before `cells`, since cells consumes the embed — see Task 5). Keep imports to `./` and `../shared/` only.
- [ ] **Step 4: Run to verify pass**, and run `node --test tests/js/structure.test.mjs` to confirm the feature-isolation rule still holds.
- [ ] **Step 5: Commit** — `git commit -am "feat(assets): js twin parser, url builder, validation"`

## Task 5: Browser — embed declared bytes + render the site note + Pyodide FS pre-fill (JS)

**Files:**
- Modify: `js/src/assets/plugin.mjs` (the `document`-stage transform)
- Modify: `js/src/cells/plugin.mjs` (carry the embedded manifest onto the runtime widget model)
- Modify: `js/src/cells/src/runtime.mjs` (write embedded files into the Pyodide FS before the first run)
- Modify: `tests/js/assets.test.mjs`, `tests/js/cells.test.mjs`

**Interfaces:**
- Consumes: Task 4 `parseDataDirective`; the page's day dir (resolve declared paths relative to the day folder, read bytes with `node:fs`, base64-encode).
- Produces:
  - In `assets/plugin.mjs`: a transform that (a) replaces each `{nma-data}` block with a collapsible admonition ("Data used by this notebook") listing the files as links to `assetUrlFor(...)`, and (b) attaches the embedded manifest `[{ path, b64 }]` to the tree (e.g. `tree.data.nmaAssets`) for the cells transform to pick up. Pages with no directive get nothing.
  - In `cells/plugin.mjs` `buildBrowserPage`: include `assets: tree.data?.nmaAssets ?? []` in the runtime widget `model`.
  - In `runtime.mjs`: a `writeAssetsToFS(kernel, assets)` step run once per kernel boot, before any user cell, decoding base64 and writing each `path` into the Pyodide FS (create parent dirs). Reasonable Pyodide FS API choice is the implementer's; it must create `data/`/`image/` relative to the kernel cwd.

- [ ] **Step 1: Write failing tests**: in `assets.test.mjs`, a transform test that a page with `{nma-data}` produces an admonition whose links use the raw URL and a `nmaAssets` array with base64 for a fixture file (add a tiny binary fixture under `tests/fixtures/assets/`); a no-directive page produces neither. In `cells.test.mjs`, assert `buildBrowserPage` copies `assets` into the runtime model.
- [ ] **Step 2: Run to verify fail** → FAIL.
- [ ] **Step 3: Implement** the transform, the model wiring, and `writeAssetsToFS`. Transform order in `index.mjs` must run `assets` before `cells` so `tree.data.nmaAssets` exists when `buildBrowserPage` reads it.
- [ ] **Step 4: Run to verify pass** — `node --test tests/js/assets.test.mjs tests/js/cells.test.mjs`.
- [ ] **Step 5: Commit** — `git commit -am "feat(assets): embed declared bytes, site note, pyodide fs prefill"`

## Task 6: Wire Python into the pipeline — settings, validation, notebooks, publish (Python)

**Files:**
- Modify: `python/src/nma_kit/config.py` (read `nma.assets.data` / `nma.assets.image`)
- Modify: `python/src/nma_kit/convert.py` (`validate_content`, `build_notebooks`, copy asset folders into `notebooks/<day>/`)
- Modify: `python/src/nma_kit/cli.py` (surface new errors — no new channel; they join the existing error list)
- Modify: `tests/python/test_convert.py`, `tests/python/test_config.py`, `tests/python/test_cli.py`

**Interfaces:**
- Consumes: Tasks 1–3; `config.page_location`, `publish.publish_notebooks` (unchanged — it copies whatever `notebooks/` tree it is handed).
- Produces:
  - `Settings` gains `assets_data_dir: str = "data"` and `assets_image_dir: str = "image"` via `_setting(nma, "assets", ...)`; `config.mjs` twin reads the same (fold into Task 4 if simpler, but keep the fixture `tests/fixtures/config/settings.json` in sync — update it here).
  - `validate_content` appends `validate_data_directives(...)` and `undeclared_reference_errors(...)` per page (hard errors), and `injected_content_errors` also rejects a committed download cell (match on `cell_id`/`_BASE` sentinel).
  - `build_notebooks` calls `rewrite_markdown_images` and `insert_download_cell` on the student and instructor notebooks, and copies `tutorials/<day>/{data,image}` → `notebooks/<day>/{data,image}` (only declared files, or the whole folder — copy the whole declared-and-present set; never climb outside the day folder).

- [ ] **Step 1: Write failing tests**: `test_config` for the new settings + defaults; `test_convert` that a fixture page with `{nma-data}` yields a notebook whose first code cell is the download cell and whose markdown image is a raw URL, and that `notebooks/<day>/data/<f>` is written; `test_cli` that a page referencing an undeclared file makes `nma-kit check` exit 1 with the message, and that a committed download cell is rejected.
- [ ] **Step 2: Run to verify fail** → FAIL.
- [ ] **Step 3: Implement** the settings read, the `validate_content` additions, the `build_notebooks` wiring, the copy step, and the `injected_content_errors` guard. Keep the download cell ahead of content but after the badge cell (confirm final cell order in a test).
- [ ] **Step 4: Run to verify pass** — `cd python && uv run pytest -q ../tests/python`.
- [ ] **Step 5: Commit** — `git commit -am "feat(assets): wire nma-data into settings, check, notebooks, publish"`

## Task 7: Demonstrate in the example course + golden/e2e coverage

**Files:**
- Create: `tests/example-course/tutorials/W1D1_GettingStarted/data/demo.npz` (tiny), `.../image/demo.png` (tiny)
- Modify: a tutorial `.md` under `tests/example-course/tutorials/W1D1_GettingStarted/` to add an `{nma-data}` block, a cell that `np.load("data/demo.npz")`, and a markdown `![](image/demo.png)`
- Modify: `tests/e2e/` (add/extend a test), possibly `tests/scripts/compare_builds.py` expectations
- Modify: `tests/python/test_compare_builds.py` if needed

**Interfaces:**
- Consumes: the whole feature.

- [ ] **Step 1: Write the failing e2e/assertion**: a test that, after `tests/scripts/build-example.sh`, the generated notebook `notebooks/W1D1_GettingStarted/<tut>.ipynb` contains the download cell with the raw URL and the rewritten image URL; and a browser e2e assertion that the editable cell loading `data/demo.npz` runs without error (reuse the existing Pyodide-backed e2e harness; keep it in an existing kernel-booting test to respect the parallelism budget).
- [ ] **Step 2: Run to verify fail** (before adding the example content) → FAIL.
- [ ] **Step 3: Add** the tiny fixtures and the tutorial edits. Generate `demo.npz`/`demo.png` programmatically (a few bytes) and commit them. Ensure `build-example.sh`'s trailing `git checkout -- tutorials myst.yml` doesn't revert the new committed files (they are committed, so it won't).
- [ ] **Step 4: Run to verify pass** — `tests/scripts/build-example.sh` then the e2e subset; also `cd js && npm run build && npm test` and `npm run build:dev && npm test`.
- [ ] **Step 5: Commit** — `git commit -am "test(assets): demonstrate data & images in the example course"`

## Task 8: Docs

**Files:**
- Modify: `course-kit/AGENTS.md` (add `assets` to the feature list and twin rules), `README.md` if it enumerates features, and the course template authoring notes if present in this repo.

**Interfaces:** none (documentation).

- [ ] **Step 1: Update** AGENTS.md: add `assets/` to the layout, the `{nma-data}` directive to the feature table, and the twin obligations (`parse_data_directive`/`parseDataDirective`, `asset_url`/`assetUrlFor`, `tests/fixtures/assets/`).
- [ ] **Step 2: Verify** by re-reading that the new feature matches the described rules (no code test). 
- [ ] **Step 3: Commit** — `git commit -am "docs(assets): document the nma-data feature and twins"`

---

## Self-Review notes

- **Spec coverage:** directive (T1,T4), per-day layout + publish copy (T6), URL host raw.githubusercontent (T2), download cell hide-cell after badge (T3,T6), markdown image rewrite (T3), browser embed + FS prefill (T5), site collapsible note O4 (T5), hard-error validation no warning channel (T2,T6), settings (T6), example course + tests (T7), twins + shared fixture (T1–T4). All mapped.
- **Twin parity** is pinned by the shared `tests/fixtures/assets/directives.json` asserted on both sides (T1/T2 Python, T4 JS).
- **Review Focus** items each have an owning test (fenced example T1; path escape T1/T6; f-string & non-path T2; empty page T3/T5).
- **Open implementer choices** left deliberately: exact Pyodide FS API in T5; whether to copy the whole day asset folder vs only declared files in T6 (plan says declared-and-present set, never outside the day folder).
