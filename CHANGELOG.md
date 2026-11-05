# Changelog

Maintained by release-please from conventional commit messages.

## [0.4.2](https://github.com/neuromatch/course-kit/compare/v0.4.1...v0.4.2) (2026-11-05)


### Bug Fixes

* skip the exercise cells when running instructor notebooks ([4a4671e](https://github.com/neuromatch/course-kit/commit/4a4671e905686469e59e76c55dbad20cf587e65f))
* skip the exercise cells when running instructor notebooks ([5bb3164](https://github.com/neuromatch/course-kit/commit/5bb3164136842f2760fa9ca9366ddedff0bb06b6))

## [0.4.1](https://github.com/neuromatch/course-kit/compare/v0.4.0...v0.4.1) (2026-11-05)


### Features

* optional nightly.yml template for courses ([c4df32c](https://github.com/neuromatch/course-kit/commit/c4df32c1fab4bd6cb9b3dc55c95239074849694b))
* run the nightly notebooks in shards so the Colab image is pulled once per shard ([03172ce](https://github.com/neuromatch/course-kit/commit/03172ce658f7dc8513ddb55e31f363195d29f628))
* run-notebooks command and course-nightly workflow ([aaadb26](https://github.com/neuromatch/course-kit/commit/aaadb269cd5b958e3e02d7f09213e03ad90fc51b))

## [0.4.0](https://github.com/neuromatch/course-kit/compare/v0.3.0...v0.4.0) (2026-11-03)


### ⚠ BREAKING CHANGES

* nma.paths.tutorials and nma.paths.projects are no longer read and there are no defaults. Add `nma: {content: [tutorials, projects]}`.

### Features

* declare content folders explicitly in nma.content ([f5548d4](https://github.com/neuromatch/course-kit/commit/f5548d46539116dc0be7ddb3c5db428aa8e85e05))

## [0.3.0](https://github.com/neuromatch/course-kit/compare/v0.2.1...v0.3.0) (2026-11-02)


### ⚠ BREAKING CHANGES

* publish referenced images without a {nma-data} declaration
* rename the default image folder from image to images

### Features

* publish referenced images without a {nma-data} declaration ([8a5b551](https://github.com/neuromatch/course-kit/commit/8a5b55105385597d09c44516f0479b1e2bbf2e70))
* Rename image dir to images ([3c9f403](https://github.com/neuromatch/course-kit/commit/3c9f4039b9f89743cd33082d2ebdfae2e6d994f1))
* rename the default image folder from image to images ([4e98cda](https://github.com/neuromatch/course-kit/commit/4e98cda1efb11ed25120780389028468406e77c5))

## [0.2.1](https://github.com/neuromatch/course-kit/compare/v0.2.0...v0.2.1) (2026-11-02)


### Features

* chore/release 0.2.1 ([bef5402](https://github.com/neuromatch/course-kit/commit/bef5402acfbc38e024f1b40cddf168a47c78c9d0))


### Miscellaneous Chores

* release 0.2.1 ([6259708](https://github.com/neuromatch/course-kit/commit/62597088233541db38231b73b19578b03b919ed1))
* release 0.2.1 ([ed2d6b0](https://github.com/neuromatch/course-kit/commit/ed2d6b00ea0e19e5913dbe6640379e431e0ab1c4))

## [0.2.0](https://github.com/neuromatch/course-kit/compare/v0.1.9...v0.2.0) (2026-10-30)


### ⚠ BREAKING CHANGES

* **media:** {nma-slides} <osf id> and :title: are gone; use {nma-slides} Title with :osf: <id>.

### Features

* choose the {nma-slides} backend: OSF or a PDF in the cou… ([fa06be5](https://github.com/neuromatch/course-kit/commit/fa06be5b44fdd653696c9df594ba28c66174fa88))
* **media:** add zoom, fit and page navigation to the Colab slides viewer ([9c8998b](https://github.com/neuromatch/course-kit/commit/9c8998b85f4129aa1cf632f90840d46b393aec0a))
* **media:** choose the {nma-slides} backend: OSF or a PDF in the course repo ([4f4c392](https://github.com/neuromatch/course-kit/commit/4f4c392cb125c8db789fba16de59bb6dcc4aa0a1))


### Bug Fixes

* **media:** draw slide PDFs in Colab with PDF.js ([106026f](https://github.com/neuromatch/course-kit/commit/106026f82e42dc04e254e9965a71b209268ed993))
* **media:** link to slide PDFs in Colab, which can't draw a PDF in its sandboxed output frame ([e441ee8](https://github.com/neuromatch/course-kit/commit/e441ee8b564284c4d3ac1714b7cf7ff967bd1475))
* **media:** show slide PDFs inline in Colab through the OSF renderer ([eb5095a](https://github.com/neuromatch/course-kit/commit/eb5095a6b8b2a37f7e93e9932c8b13cd8179c612))

## [0.1.9](https://github.com/neuromatch/course-kit/compare/v0.1.8...v0.1.9) (2026-10-25)


### Features

* add nma-kit init to scaffold a starter course ([6adeec7](https://github.com/neuromatch/course-kit/commit/6adeec718bb73994b1d55ec37a05413baa8ca177))
* add nma-kit init to scaffold a starter course ([f90f480](https://github.com/neuromatch/course-kit/commit/f90f4806b424f5fbf91c602c2de1e2ddaa86e886))

## [0.1.8](https://github.com/neuromatch/course-kit/compare/v0.1.7...v0.1.8) (2026-10-25)


### Bug Fixes

* make dist-js work on a fresh runner ([b626ac0](https://github.com/neuromatch/course-kit/commit/b626ac0dffecc55bc476983f18179bcd1581bd35))
* make dist-js work on a fresh runner ([fe297bb](https://github.com/neuromatch/course-kit/commit/fe297bbd8f1d69313e0de7ef08827c71f4faac17))

## [0.1.7](https://github.com/neuromatch/course-kit/compare/v0.1.6...v0.1.7) (2026-10-25)


### Features

* Chore/tooling ([a0c15b6](https://github.com/neuromatch/course-kit/commit/a0c15b611ccfccdaeedd02fb4bc58c9385a8aa65))
* share constants between the CLI and the plugin, document the public API ([35353e0](https://github.com/neuromatch/course-kit/commit/35353e03e1e18826dc04c80de33197073e520e01))

## [0.1.6](https://github.com/neuromatch/course-kit/compare/v0.1.5...v0.1.6) (2026-10-24)


### Features

* update preview workflow ([b235e2f](https://github.com/neuromatch/course-kit/commit/b235e2fd358bc4fc83704530d67353ce7a8dc50d))

## [0.1.5](https://github.com/neuromatch/course-kit/compare/v0.1.4...v0.1.5) (2026-10-24)


### Features

* course-preview workflow (Cloudflare Pages PR previews) ([1e4095e](https://github.com/neuromatch/course-kit/commit/1e4095ec2d5d70d1b82da8290ca2aad92dd9d1ff))
* NMA_NOTEBOOKS_BRANCH overrides the notebooks branch ([ad7f2e2](https://github.com/neuromatch/course-kit/commit/ad7f2e2d7558c8d4a138ffffec47b4f52c418934))

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
