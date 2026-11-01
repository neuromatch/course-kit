#!/usr/bin/env bash
# Build tests/example-course/ with the kit's dev bundle, the way a course's CI does.
# Needs: node (npm ci already run in js/), and nma-kit + myst on PATH (or a
# venv at python/.venv). Leaves the site in tests/example-course/_build/html (and, with
# NMA_BUILD_INSTRUCTOR=1, the instructor site in _build/html-instructor).
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

# One build per audience: the course's own CI does the same (course-publish.yml).
build_site() { # $1 = student | instructor
  # MyST would reuse what it processed for the other audience.
  rm -rf _build/site
  NMA_AUDIENCE=$1 nma-kit render-scrolly
  NMA_AUDIENCE=$1 nma-kit prepare-site
  NMA_AUDIENCE=$1 myst build --html
  NMA_AUDIENCE=$1 nma-kit finalize-site
}

# NMA_BUILD_INSTRUCTOR=1 also builds the instructor site, into _build/html-instructor
# (the student site stays in _build/html, where the browser tests look for it).
if [ -n "${NMA_BUILD_INSTRUCTOR:-}" ]; then
  build_site instructor
  rm -rf _build/html-instructor
  mv _build/html _build/html-instructor
fi
build_site student
