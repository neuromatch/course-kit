# Changelog

Maintained by release-please from conventional commit messages.

## 0.1.0 (unreleased)

First version, extracted from `neuromatch/course-template`:

* MyST plugin bundled into one file, organised by feature (media, solutions,
  feedback, scrolly, cells), browser assets served from exact-version CDN URLs.
* `nma-kit` CLI: `check`, `notebooks`, `render-scrolly`, `prepare-site`
  (pins the kit URL in `myst.yml`), `publish-notebooks` (creates the notebooks
  branch if missing).
* Optional `nma.paths.tutorials` and `nma.notebooks.branch` settings.
* Reusable workflows: `course-check.yml` (pull requests), `course-publish.yml`
  (notebooks + GitHub Pages in one gated chain), `course-wheels.yml`.
