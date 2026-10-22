// {nma-data}: declares the data/image files a tutorial needs.
// nma_kit.assets (Python) turns the same declaration into the Colab/Kaggle
// download cell. The parser and URL template in both must stay in sync.
//
// On the site the directive renders as a collapsed "Data used by this notebook"
// note. A document-stage transform also reads the declared files from disk and
// hands their bytes (base64) to the cells feature as tree.data.nmaAssets, so
// browser cells can write them into the kernel's filesystem without any fetch.

import { existsSync, readFileSync, statSync } from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';

import { courseSettings, notebookDir, pageLocation } from '../shared/paths.mjs';
import { assetUrlFor, parseDataDirective, validateDataDirectives } from './model.mjs';

export { parseDataDirective, validateDataDirectives, assetUrlFor };

// Python twin: MAX_EMBED_BYTES in nma_kit.assets. `nma-kit check` reports it as an error.
export const MAX_EMBED_BYTES = 2 * 1024 * 1024;

const text = (value) => ({ type: 'text', value });
const link = (url, label) => ({ type: 'link', url, children: [text(label)] });

/** Collapsed dropdown listing the declared files with links to their published URLs. */
export function dataNote(paths, urlOf) {
  return {
    type: 'admonition',
    kind: 'dropdown',
    class: 'nma-data dropdown',
    children: [
      { type: 'admonitionTitle', children: [text('Data used by this notebook')] },
      {
        type: 'list',
        ordered: false,
        children: paths.map((p) => ({
          type: 'listItem',
          children: [{ type: 'paragraph', children: [link(urlOf(p), p)] }],
        })),
      },
    ],
  };
}

/** [{path, b64}] for the declared files that exist inside `dayDir`. Others are skipped (`nma-kit check` reports them). */
export function readEmbeddedAssets(dayDir, paths) {
  const root = resolve(dayDir);
  const out = [];
  for (const path of paths) {
    const full = resolve(root, path);
    const rel = relative(root, full);
    if (isAbsolute(path) || rel.startsWith('..') || isAbsolute(rel)) continue;
    if (!existsSync(full) || !statSync(full).isFile()) continue;
    out.push({ path, b64: readFileSync(full).toString('base64') });
  }
  return out;
}

/**
 * Attach the embedded files of a page's {nma-data} declarations to the tree.
 * Returns a warning when they are too big to embed (nothing is attached then).
 */
export function applyAssets(tree, source, pagePath) {
  const paths = parseDataDirective(source);
  if (paths.length === 0) return null;
  const assets = readEmbeddedAssets(dirname(pagePath), paths);
  const bytes = assets.reduce((sum, a) => sum + Buffer.byteLength(a.b64, 'base64'), 0);
  if (bytes > MAX_EMBED_BYTES) {
    return (
      `{nma-data} files total ${(bytes / 1024 / 1024).toFixed(1)} MB, over the ` +
      `${MAX_EMBED_BYTES / 1024 / 1024} MB embed limit: browser cells will not have them`
    );
  }
  tree.data = { ...(tree.data ?? {}), nmaAssets: assets };
  return null;
}

function urlFor(filePath) {
  const { githubRepo, notebooksBranch } = courseSettings();
  const location = pageLocation(filePath);
  if (!githubRepo || !location) return (p) => p;
  return (p) => assetUrlFor(githubRepo, notebooksBranch, notebookDir(location), p);
}

const nmaData = {
  name: 'nma-data',
  doc: 'Declare the data and image files this tutorial uses, one path per line.',
  body: { type: String, doc: 'File paths (data/..., image/...), one per line.' },
  run(data, vfile) {
    const paths = parseDataDirective(`:::{nma-data}\n${data.body ?? ''}\n:::\n`);
    if (paths.length === 0) return [];
    return [dataNote(paths, urlFor(vfile.path ?? ''))];
  },
};

const assetsTransform = {
  name: 'nma-assets',
  doc: 'Embed the files declared by {nma-data} for the browser cells.',
  stage: 'document',
  plugin: () => (tree, vfile) => {
    let source = '';
    try {
      source = readFileSync(vfile.path, 'utf8');
    } catch {
      return;
    }
    const warning = applyAssets(tree, source, vfile.path);
    if (warning) vfile.message(warning, null, 'nma-assets');
  },
};

export default {
  name: 'Neuromatch assets',
  directives: [nmaData],
  transforms: [assetsTransform],
};
