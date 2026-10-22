#!/usr/bin/env bash
# Build tests/example-course/ with the kit's dev bundle, the way a course's CI does.
# Needs: node (npm ci already run in js/), and nma-kit + myst on PATH (or a
# venv at python/.venv). Leaves the site in tests/example-course/_build/html.
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ -x "$KIT/python/.venv/bin/nma-kit" ]; then
  export PATH="$KIT/python/.venv/bin:$PATH"
fi

(cd "$KIT/js" && npm run build:dev)

cd "$KIT/tests/example-course"
# prepare-site edits the pages in place; never leave that behind.
trap 'git checkout -- tutorials projects myst.yml' EXIT
nma-kit check
nma-kit render-scrolly
nma-kit prepare-site
myst build --html
