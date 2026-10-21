# Course-kit asset handling: data & images

Status: design, awaiting approval
Date: 2026-10-20

## Intent and why

Course authors want to keep data files and images **next to the tutorials that
use them** and reference them with short, obvious relative paths:

```python
arr = np.load("data/data.npz")
img = plt.imread("image/atlas.png")
```
```markdown
![a test figure](image/test.png)
```

Today the kit has **no asset handling at all**, so a relative reference like this
only resolves in one of the places a tutorial actually runs. This design makes
those authored strings work unchanged across every runtime.

The author declares, once per tutorial, which files that notebook needs, using a
new `{nma-data}` directive. That one declaration is the single source of truth
that drives every runtime. The author never writes a different path for Colab
than for the site.

## The three runtimes (the actual problem)

A reference such as `data/data.npz` or `image/test.png` must resolve in three
very different environments. Only one works today:

| Runtime | `![](image/x.png)` | `np.load("data/x.npz")` |
|---|---|---|
| **MyST site** (static rendered pages) | works — MyST resolves the relative path at build, copies the file into `_build`, rewrites the link | n/a |
| **Editable cells** (JupyterLite / Pyodide, one kernel per page) | n/a | **fails** — Pyodide boots a fresh, empty virtual filesystem |
| **Colab / Kaggle** (generated `.ipynb`) | **fails** — the repo is not on disk, and Jupyter markdown will not render a local-file path even if it were | **fails** — the repo is not on disk |

Two consequences shape the whole design:

1. **Markdown images can never stay as local paths in a notebook.** Jupyter
   (Colab, Kaggle, classic) renders a markdown image only from a URL or an
   embedded attachment, never from a sibling file path. Markdown image
   references are therefore rewritten to absolute URLs in the generated
   notebooks (a trivial regex rewrite, independent of the directive).
2. **Code that reads files needs the files to physically exist** in the
   runtime's working directory — both in the Pyodide FS (browser cells) and on
   the Colab/Kaggle VM. The author's code string stays verbatim; the kit makes
   `./data/...` and `./image/...` exist before the code runs, from the files the
   `{nma-data}` directive declares.

## Layout: per-day shared asset folders

Assets live in `data/` and `image/` folders inside the **day folder**, shared by
all tutorials in that day. Tutorials stay flat in the day folder (no per-tutorial
subdirectories), so this is not a layout change for existing courses — only new
folders are added.

```
tutorials/W1D1_Intro/W1D1_Tutorial1.md     ->  notebooks/W1D1_Intro/W1D1_Tutorial1.ipynb
tutorials/W1D1_Intro/W1D1_Tutorial2.md     ->  notebooks/W1D1_Intro/W1D1_Tutorial2.ipynb
tutorials/W1D1_Intro/data/data.npz         ->  notebooks/W1D1_Intro/data/data.npz   (published)
tutorials/W1D1_Intro/image/atlas.png       ->  notebooks/W1D1_Intro/image/atlas.png (published)
```

Because `data/` and `image/` sit beside both the `.md` and the generated
`.ipynb`, the authored string `data/data.npz` is relative to each without change.
Data shared by several tutorials in a day lives in the folder once; each tutorial
declares the files it uses, so there is no duplication.

The asset folders are published to the `notebooks-branch` alongside the
notebooks, reusing `nma_kit.publish.publish_notebooks` (which already copies
whatever tree it is handed). Published URLs:

- **Data and images fetched by code / downloaded for Colab:**
  `https://raw.githubusercontent.com/<repo>/<branch>/notebooks/<day>/<path>`
- **Markdown images rewritten in notebooks:** the same
  `raw.githubusercontent.com` URL (chosen over a CDN for one consistent host and
  no cache surprises during authoring).

The folder names `data` and `image` are defaults; see Settings.

## The `{nma-data}` directive (the manifest)

The author declares, in each tutorial that needs files, exactly which files to
make available. Both `data/` and `image/` entries are allowed in the same
directive — one manifest covers code that reads data *and* code that reads
images (e.g. `plt.imread`). Markdown-only images need not be listed; they are
handled by the URL rewrite.

```markdown
:::{nma-data}
data/spikes.npz
data/lfp.npz
image/atlas.png
:::
```

This directive is the **single source of truth**. It drives all three runtimes
from one list, and because it is an explicit declaration there is no code
parsing: dynamic loads, loops, `os.path.join`, and widget-chosen filenames all
work, because the author declared the files rather than the kit inferring them.

The directive follows the kit's existing directive idiom (`{nma-video}`,
`{nma-solution}`, `{nma-feedback}`), with a Python/JS twin:

- **Python (`nma_kit.assets`, build time):** parse the directive; validate the
  files exist; expand it into a hidden download cell in the generated notebook
  (the twin of `media.py`'s `expand_notebook`); copy the referenced files into
  the local `notebooks/<day>/{data,image}` tree so publishing ships them.
- **JS (`js/src/assets/plugin.mjs`, build time):** read the same directive from
  the mdast and emit the file list onto the page so the cells runtime can
  pre-fill the Pyodide FS. On the rendered site the directive produces either
  nothing or a small "Data used by this notebook" note (O4 below).

### What each runtime does with it

- **Colab / Kaggle:** the directive expands into a hidden `hide-cell` download
  cell near the top of the generated notebook, which fetches exactly the listed
  files from `raw.githubusercontent.com/<repo>/<branch>/notebooks/<day>/...`
  into `./data` / `./image`. The author's verbatim code then works:

  ```python
  # @title Download course data  [tags: hide-cell]
  import os, urllib.request
  _BASE = "https://raw.githubusercontent.com/<repo>/<branch>/notebooks/<day>/"
  for _f in ["data/spikes.npz", "data/lfp.npz", "image/atlas.png"]:  # from the directive
      if not os.path.exists(_f):
          os.makedirs(os.path.dirname(_f), exist_ok=True)
          urllib.request.urlretrieve(_BASE + _f, _f)
  del _f
  ```

  Like the kit's other injected content (badges, the run-all fallback cell),
  this is generated into the notebook, never committed to source, and is
  idempotent / removable.

- **Editable cells (browser):** the JS plugin reads each declared file from
  disk at build time (it already reads the page source) and **embeds its bytes
  (base64) into the runtime widget model** on the page. Before a Run, the cells
  runtime decodes them and writes them into the Pyodide FS under `data/` /
  `image/`. No network fetch, no CORS, and no dependence on the notebooks branch
  being published — so it works identically in dev builds, the e2e suite, forks,
  and production. This satisfies the requirement that data loads work in browser
  editable cells. (Embedding suits tutorial-sized files; large datasets are a
  non-goal and belong on an external host via the author's own download cell.)

- **MyST site:** markdown images already resolve via MyST's own relative-path
  handling. The directive renders as nothing or a small note (O4).

## Python / JS twin obligations

New twins, tested against a shared fixture under `tests/fixtures/assets/` (per
the kit's twin rule):

- **Directive parser**: `parse_data_directive(text) -> list[str]` in
  `python/src/nma_kit/assets.py` and its counterpart in `js/src/assets/`. Same
  input, same ordered file list.
- **URL builder**: `asset_url(repo, branch, day, path)` on both sides, matching
  exactly (cf. the existing `media` and `solutions` twins).
- **Validation** of the directive (known prefixes only, non-empty, closed, no
  stray body) lives in `assets.py` and is surfaced by `validate_content`.

## `nma-kit check`: validation (hard errors only)

No warning channel is introduced. The checks are plain hard errors, added to the
existing `validate_content` error list, so they fail `check`, `notebooks`, and
`prepare-site` exactly like every other content-rule violation today (exit 1,
printed under the existing `Content rule violations:` heading in `cli.py`). CI's
`course-check.yml` runs `check` on every PR, so a mistake is caught at build time
instead of on Colab.

Two hard errors:

- A `{nma-data}` entry that does not exist under the day's asset folder (a dead
  link). Plus the usual directive-shape errors (unknown prefix, unclosed, body
  present).
- A **strict** literal `data/...` / `image/...` reference in a code cell that is
  **not** declared in that page's `{nma-data}`. "Strict" means the literal must
  match `^(data|image)/[\w./-]+\.\w+$` — a known prefix **and** a real file
  extension, with no `{` — so f-strings and other dynamic paths are skipped
  (never falsely flagged), and ordinary non-path strings (dict keys, labels)
  don't trip it. Dynamic loads produce no literal to flag, so the author simply
  declares those files in `{nma-data}` by hand, as before.

**Deliberately not checked:** an orphan file in a day's asset folder that no
tutorial declares. It can't be a hard error (you add the file, then the
directive, and the build would fail in between) and there is no warning channel;
an unused file is published harmlessly. Dropped in v1.

**False-positive escape:** if the strict pattern ever flags a real non-path
string, the author cannot declare it (no such file), so the match must stay
tight enough that this does not happen in practice; the pattern above is chosen
for that. (If a case is ever found, revisit by requiring the string to be a
direct argument to a known loader — out of scope for v1.)

## Settings

Optional block in `myst.yml`'s `nma:` section, read by the `config.py` /
`config.mjs` twins (string values only, per the kit's config rules):

```yaml
nma:
  assets:
    data: data        # folder name for data files (default: data)
    image: image      # folder name for image files (default: image)
```

Defaults make the feature zero-config; names are validated like other `nma:`
settings.

## Example course

The feature ships demonstrated in `tests/example-course`, which CI builds and
the e2e suite exercises:

- Add a day asset folder, e.g. `tutorials/W1D1_GettingStarted/data/` with a
  small `.npz` and `tutorials/W1D1_GettingStarted/image/` with a small `.png`.
- Add an `{nma-data}` directive plus cells that `np.load` the data and
  `plt.imread` / markdown-embed the image, in an existing tutorial.
- Extend the golden/e2e checks so the generated notebook contains the download
  cell and the rewritten image URL, and the editable cell loads the data in the
  browser. `tests/scripts/build-example.sh` must restore any files
  `prepare-site` touches (it already does `git checkout -- tutorials myst.yml`).

## Goals / non-goals / anti-goals

**Goals**
- Authored relative paths (`data/...`, `image/...`) work unchanged on the MyST
  site, in browser editable cells, and in generated Colab/Kaggle notebooks.
- One explicit `{nma-data}` declaration per tutorial is the single manifest.
- Per-day shared folders: no duplication, no per-tutorial layout change.
- Reuse the publish-to-notebooks-branch and build-time notebook post-processing
  machinery; follow the directive + Python/JS twin pattern.
- Demonstrated in the example course and covered by tests.

**Non-goals**
- Hosting large datasets. This targets tutorial-sized files committed to the
  repo; multi-hundred-MB datasets still belong on OSF/an external host (authors
  download them with their own cell, unchanged by this design).
- Auto-detecting undeclared files to *drive* behavior. Code is never parsed to
  decide what to ship; the strict literal scan only validates that code
  references are declared.
- Changing the `{nma-video}`/`{nma-slides}` (OSF) media directives.

**Anti-goals (would make this a failure even if it "works")**
- Authors writing a different path for Colab than for the site.
- A committed source file ever containing the generated download cell or a
  rewritten image URL.
- The browser pre-fill depending on the notebooks branch being published, a
  network fetch, or a root-absolute URL (any of which breaks dev/e2e/forks); it
  must embed the declared bytes at build time instead.
- The undeclared-reference check false-positiving on a non-path string literal
  and hard-blocking a build with no escape (keep the match strict).

## Resolved decisions

- **O4 — directive rendering on the site:** render `{nma-data}` as a small
  collapsible "Data used by this notebook" note listing the files with download
  links to the published `raw.githubusercontent.com` URLs. Approved.
- **O5 — download cell placement on Colab:** immediately after the badge cell
  (first thing that runs), `hide-cell` visibility.
