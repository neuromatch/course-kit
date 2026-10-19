# Changelog

Maintained by release-please from conventional commit messages.

## [0.1.1](https://github.com/neuromatch/course-kit/compare/v0.1.0...v0.1.1) (2026-10-19)


### Bug Fixes

* build-example.sh finds the repo root after moving under tests/ ([17d31b6](https://github.com/neuromatch/course-kit/commit/17d31b6c5379cf4b4cd830816f7aededec0d5e24))
* don't force provenance in package.json (CI passes --provenance) ([5199e87](https://github.com/neuromatch/course-kit/commit/5199e875c476013ebcf573ce721e4460382fce07))
* reorganize repo, add release manifest and package metadata ([b1a96c7](https://github.com/neuromatch/course-kit/commit/b1a96c725a5c94ceefd08cf8d1ac61e180a3c381))

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
