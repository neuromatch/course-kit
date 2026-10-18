// Editable cells (MyST plugin, document stage).
//
// Browser pages (kernelspec, not scrolly, not `runtime: colab`): every code cell
// becomes an anywidget panel (assets/cells/panel.mjs) and one hidden
// runtime widget carries the manifest of all cells. Colab pages keep MyST's
// static code and get a banner. Scrolly pages and pages without kernelspec are
// left alone.
//
// Asset paths come from shared/assets.mjs: MyST source paths or CDN URLs that
// MyST downloads at build time, never browser URLs.

import { readFileSync } from 'node:fs';

import { assetUrl } from '../shared/assets.mjs';
import { isScrolly } from '../shared/frontmatter.mjs';
import { notebookUrls } from '../shared/paths.mjs';
import { runtimeOf, modeOf, isExercise, frontmatterOf } from './src/model.mjs';

const PANEL_ESM = assetUrl('cells/panel.mjs');
const RUNTIME_ESM = assetUrl('cells/runtime-widget.mjs');
const PANEL_CSS = assetUrl('cells/cells.css');
const PAGE_CSS = assetUrl('cells/page.css');

const isCodeBlock = (n) => n.type === 'block' && n.kind === 'notebook-code';
const codeOf = (b) => (b.children ?? []).find((c) => c.type === 'code')?.value ?? '';
const tagsOf = (b) => [b.data?.tags ?? []].flat();

/** Rebuild a browser page in place. Returns the number of code cells. */
export function buildBrowserPage(tree) {
  const cells = [];
  const walk = (node) => {
    node.children = (node.children ?? []).flatMap((child) => {
      if (!isCodeBlock(child)) {
        walk(child);
        return [child];
      }
      const code = codeOf(child);
      const cell = {
        index: cells.length,
        code,
        mode: modeOf(tagsOf(child)),
        exercise: isExercise(code),
      };
      cells.push(cell);
      if (cell.mode === 'hidden') return []; // runs from the manifest, no panel
      return [
        {
          type: 'block',
          children: [
            {
              type: 'anywidget',
              esm: PANEL_ESM,
              css: PANEL_CSS,
              class: 'nma-cell',
              id: `nma-cell-${cell.index}`,
              model: { ...cell },
            },
          ],
        },
      ];
    });
  };
  walk(tree);
  const runtime = {
    type: 'anywidget',
    esm: RUNTIME_ESM,
    css: PAGE_CSS,
    class: 'nma-cells-runtime',
    id: 'nma-cells-runtime',
    model: { cells: cells.map(({ index, code, mode, exercise }) => ({ index, code, mode, exercise })) },
  };
  tree.children = [{ type: 'block', children: [runtime] }, ...(tree.children ?? [])];
  return cells.length;
}

const text = (value) => ({ type: 'text', value });
const link = (url, label) => ({ type: 'link', url, children: [text(label)] });

/** Colab page: keep MyST's static code, add a banner at the top. */
export function buildColabPage(tree, { colabUrl, kaggleUrl }) {
  const banner = {
    type: 'admonition',
    kind: 'important',
    class: 'nma-colab-banner',
    children: [
      { type: 'admonitionTitle', children: [text('Do this tutorial in Colab')] },
      {
        type: 'paragraph',
        children: [
          text('This tutorial needs more computing power than your browser has, so its code can’t run on this page. '),
          link(colabUrl, 'Open in Colab'),
          text(' or '),
          link(kaggleUrl, 'Kaggle'),
          text(' to edit and run it.'),
        ],
      },
    ],
  };
  tree.children = [{ type: 'block', children: [banner] }, ...(tree.children ?? [])];
}

const cellsTransform = {
  name: 'nma-cells',
  doc: 'Editable, runnable code cells on browser pages; a Colab banner on runtime: colab pages.',
  stage: 'document',
  plugin: () => (tree, vfile) => {
    let source = '';
    try {
      source = readFileSync(vfile.path, 'utf8');
    } catch {
      return;
    }
    if (!/^kernelspec:/m.test(frontmatterOf(source)) || isScrolly(source)) return;
    if (runtimeOf(source) === 'colab') buildColabPage(tree, notebookUrls(vfile.path));
    else buildBrowserPage(tree);
  },
};

export default { name: 'Neuromatch editable cells', transforms: [cellsTransform] };
