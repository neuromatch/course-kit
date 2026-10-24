# Changelog

Maintained by release-please from conventional commit messages.

## [0.1.4](https://github.com/neuromatch/course-kit/compare/v0.1.3...v0.1.4) (2026-10-24)


### Features

* **assets:** embed declared bytes, site note, pyodide fs prefill ([8716cac](https://github.com/neuromatch/course-kit/commit/8716caceda115622df74ad867c936b92059d89bf))
* **assets:** figure/image directives, scrolly data, undeclared-image/dynamic-path checks, embed size guard ([daee7bc](https://github.com/neuromatch/course-kit/commit/daee7bc6f2f2b41b5ad8f51d5d62bf0e8144ae98))
* **assets:** js twin parser, url builder, validation ([1a7c50b](https://github.com/neuromatch/course-kit/commit/1a7c50b1e812ce355de9eb22780aabacbd7b7441))
* **assets:** nma-data directive parsing and validation ([c4f8271](https://github.com/neuromatch/course-kit/commit/c4f827165a04b2179c9730e3b180b7d1606eb7e4))
* **assets:** notebook download cell and markdown image rewrite ([120b43c](https://github.com/neuromatch/course-kit/commit/120b43c173dca28d766c16159c1ce6ebdc13f619))
* **assets:** url builder and strict undeclared-reference scan ([c4d6c08](https://github.com/neuromatch/course-kit/commit/c4d6c0844e1e80521cbe288ca11bc31a24bc5268))
* **assets:** wire nma-data into settings, check, notebooks, publish ([9a0bee5](https://github.com/neuromatch/course-kit/commit/9a0bee5a7fff7304fe27f7baa8fbd546d1609c37))


### Bug Fixes

* **assets:** rewrite markdown images that carry a title ([d67b8ba](https://github.com/neuromatch/course-kit/commit/d67b8bae036c5d51ae6bdb98655fbd747b66ff45))

## [0.1.3](https://github.com/neuromatch/course-kit/compare/v0.1.2...v0.1.3) (2026-10-20)


### Features

* **scrolly:** follow the site's light/dark mode and brand colours ([ddac309](https://github.com/neuromatch/course-kit/commit/ddac30936f12dd5861dcb0795a70d73cd091b7b2))

## [0.1.2](https://github.com/neuromatch/course-kit/compare/v0.1.1...v0.1.2) (2026-10-20)


### Bug Fixes

* package READMEs, refresh README/AGENTS/changelog, lint fixes; c… ([5e3956e](https://github.com/neuromatch/course-kit/commit/5e3956edcbb90709022f67850c7a8f34a48c7976))

## [0.1.1](https://github.com/neuromatch/course-kit/compare/v0.1.0...v0.1.1) (2026-10-19)


### Bug Fixes

* build-example.sh finds the repo root after moving under tests/ ([17d31b6](https://github.com/neuromatch/course-kit/commit/17d31b6c5379cf4b4cd830816f7aededec0d5e24))
* don't force provenance in package.json (CI passes --provenance) ([5199e87](https://github.com/neuromatch/course-kit/commit/5199e875c476013ebcf573ce721e4460382fce07))
* reorganize repo, add release manifest and package metadata ([b1a96c7](https://github.com/neuromatch/course-kit/commit/b1a96c725a5c94ceefd08cf8d1ac61e180a3c381))

## 0.1.0

First version, extracted from `neuromatch/course-template`:

* MyST plugin bundled into one file, organised by feature (media, solutions,
  feedback, scrolly, cells), browser assets served from exact-version CDN URLs.
* `nma-kit` CLI: `check`, `notebooks`, `render-scrolly`, `prepare-site`
  (pins the kit URL in `myst.yml`), `publish-notebooks` (creates the notebooks
  branch if missing).
* Optional `nma.paths.tutorials` and `nma.notebooks.branch` settings.
* Reusable workflows: `course-check.yml` (pull requests), `course-publish.yml`
  (notebooks + GitHub Pages in one gated chain), `course-wheels.yml`.
