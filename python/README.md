# neuromatch-course-kit

The `nma-kit` command line for Neuromatch courses written in
[MyST](https://mystmd.org) Markdown. It is one half of the
[Neuromatch course kit](https://github.com/neuromatch/course-kit); the other
half is the MyST plugin on npm,
[`@neuromatch/course-kit`](https://www.npmjs.com/package/@neuromatch/course-kit).
Both ship under the same version.

Courses usually don't install this by hand: the reusable GitHub workflows in
the kit repository do. To use it locally:

```bash
uv venv && uv pip install -r requirements.txt "neuromatch-course-kit==0.1.*"
uv run nma-kit check
uv run myst start
```

Requires Python 3.10 or newer. Run every command from the course root (the
folder with `myst.yml`).

## Commands

| Command | What it does |
|---|---|
| `nma-kit check` | Validate the content rules and the `nma:` block of `myst.yml` |
| `nma-kit notebooks [--dry-run]` | Generate student and instructor notebooks and the solution files into `notebooks/` |
| `nma-kit render-scrolly` | Run each scrolly page's instructor notebook and save outputs to `_build/scrolly/` |
| `nma-kit prepare-site [--dry-run] [--kit-version V]` | Add badges and fallback cells to the pages and pin the kit URL in `myst.yml`. **CI only: it edits files in place, never commit the result** |
| `nma-kit publish-notebooks [--remote R] [--message M]` | Push `notebooks/` to the notebooks branch (created if missing) |

Exit codes: `0` ok, `1` content problems or a failed publish, `2` usage or
configuration errors.

## Settings

Read from `myst.yml`: `project.github` gives the repository, and the optional
top-level `nma:` block holds the rest.

```yaml
nma:
  paths:
    tutorials: tutorials          # where the .md pages live
  notebooks:
    branch: notebooks-branch      # where generated notebooks are published
  feedback:                       # required if any page uses {nma-feedback}
    url: https://...
    project: ...
    user_key: ...
```

Values in `nma:` must be plain strings in one level of sections.

## Versions

The kit is on 0.x. A breaking change bumps the minor version, so
`==0.1.*` only receives compatible fixes. The CLI and the npm plugin always
share a version number, and `prepare-site` pins the plugin URL to the CLI's
own version.

Source, docs and release process:
<https://github.com/neuromatch/course-kit>.

BSD-3-Clause.
