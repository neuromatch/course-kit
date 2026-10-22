# @neuromatch/course-kit

The [MyST](https://mystmd.org) plugin for Neuromatch courses: one bundled
file plus the browser assets it uses. It is one half of the
[Neuromatch course kit](https://github.com/neuromatch/course-kit); the other
half is the [`nma-kit`](https://pypi.org/project/neuromatch-course-kit/)
command line, which checks content and generates notebooks. Both ship under
the same version.

You normally don't install this package. A course's `myst.yml` loads it from
jsDelivr:

```yaml
version: 1
extend: https://cdn.jsdelivr.net/npm/@neuromatch/course-kit@0.1/dist/nma.yml
project:
  github: https://github.com/<org>/<course>
```

`dist/nma.yml` adds the plugin and turns on `project.jupyter.lite`. In CI,
`nma-kit prepare-site` rewrites `@0.1` to the exact version of the CLI, so the
plugin, its assets and the CLI always match. See the
[kit README](https://github.com/neuromatch/course-kit#using-the-kit-in-a-course)
for the full course setup.

## What it adds to MyST

| Directive / feature | What it does on the site |
|---|---|
| `{nma-video}`, `{nma-slides}` | Embedded YouTube, Bilibili or OSF videos and slide decks |
| `{nma-solution}`, `{nma-explanation}` | A "Click for solution" link; the solution text itself is never on the page |
| `{nma-feedback}` | A feedback widget that posts to datatops from the browser |
| `layout: scrolly`, `{step}`, `{stage}` | Scrollytelling pages with live Python (Pyodide) |
| Editable cells | Code cells become editable and runnable in the browser on pages with a `kernelspec`; `runtime: colab` pages get a Colab banner instead |

Examples:

```markdown
:::{nma-video} Video 1: Linear dynamical systems
:youtube: vPYQPI4nKT8
:bilibili: BV1up4y1S7wj
:::

:::{nma-feedback} Linear_Dynamical_Systems_Video
:::
```

Directives must be at the top level of a page. Their options are checked by
`nma-kit check`.

Settings live in the `nma:` block of `myst.yml` (all optional):

```yaml
nma:
  paths:
    tutorials: tutorials
    projects: projects
  notebooks:
    branch: notebooks-branch
  feedback: { url: https://..., project: ..., user_key: ... }
  scrolly:
    pyodide_url: https://cdn.jsdelivr.net/pyodide/v314.0.7/full/
```

A plugin can't add site-wide CSS, so the Neuromatch look (colours, Rubik font,
logos, favicon, and the rule that hides JupyterLite's toolbar) comes from the
`nma-kit sync-assets` command in the PyPI package instead. It writes `_nma/`,
which the course's `myst.yml` lists under `site.options` (`style`, `logo`,
`logo_dark`, `favicon`). See the
[kit README](https://github.com/neuromatch/course-kit#site-branding).

## What's in the package

```
dist/nma.mjs         the plugin (all features, one file)
dist/nma.yml         the config courses `extend:`
dist/assets/<name>/  browser widgets and CSS, one folder per feature
dist/build-info.json {mode, version}
```

Asset URLs inside the bundle point at this exact version on jsDelivr. MyST
downloads them at build time and serves them from the course's own site, so
readers' browsers don't contact the CDN for them. The one exception is
the Python runtime: editable cells and scrolly pages load Pyodide from
`cdn.jsdelivr.net`, and micropip installs packages from PyPI.

## Versions

The kit is on 0.x. A breaking change bumps the minor version, so `@0.1` only
receives compatible fixes. Don't use `@latest` in `myst.yml`: jsDelivr caches
alias URLs for up to 7 days and `@latest` crosses major versions.

## Development

Source, tests and release process: <https://github.com/neuromatch/course-kit>.

BSD-3-Clause.
