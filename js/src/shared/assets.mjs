// Where the browser assets (widget JS, CSS) are, as MyST anywidget paths.
//
// - release bundle: build.mjs defines __NMA_ASSET_BASE__ as the exact-version
//   CDN URL. MyST downloads the assets at build time and serves them itself.
// - dev bundle (__NMA_BUNDLED__, no base): dist/assets/ next to the bundle,
//   as a course-root-relative path ("/course-kit/js/dist/assets/...").
// - unbundled source (tests): js/dist/assets/.

import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

/* global __NMA_ASSET_BASE__, __NMA_BUNDLED__ */
const BASE = typeof __NMA_ASSET_BASE__ === 'string' ? __NMA_ASSET_BASE__ : null;
const BUNDLED = typeof __NMA_BUNDLED__ !== 'undefined';

function assetsDir() {
  const here = dirname(fileURLToPath(import.meta.url));
  return BUNDLED ? join(here, 'assets') : join(here, '..', '..', 'dist', 'assets');
}

/** 'cells/panel.mjs' -> the path or URL MyST should load it from. */
export function assetUrl(rel) {
  if (BASE) return BASE + rel;
  return '/' + relative(process.cwd(), join(assetsDir(), rel)).split(sep).join('/');
}
