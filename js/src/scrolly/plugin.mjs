// Scrollytelling pages: `layout: scrolly`, {step} and {stage}.
//
// The page stays a flat MyST tutorial. {step} and {stage} only leave markers
// in the tree. On pages with `layout: scrolly` in the frontmatter, a
// document-stage transform regroups the top-level nodes into
//
//   block.scrolly-col > div.scrolly > engine widget
//                                  + div.scrolly-stage > div.scrolly-view (one per stage)
//                                  + div.scrolly-steps > div.scrolly-step > div.scrolly-card
//
// and turns every code cell into a runnable widget (runnable.mjs) that runs
// Python in the reader's browser (Pyodide). Starting outputs come from
// _build/scrolly/<relDir>/<stem>.json, written in CI by
// `nma-kit render-scrolly`.
//
// nma_kit.scrolly is the Python side. These must stay in sync:
//   isScrolly <-> is_scrolly, cellKey <-> cell_key, parseParams <-> parse_params
// (shared fixtures in fixtures/scrolly/).

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

import { assetUrl } from '../shared/assets.mjs';
import { courseSettings, pageLocation } from '../shared/paths.mjs';
import { isScrolly } from '../shared/frontmatter.mjs';

export { isScrolly };

export const DEFAULT_PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';
const ENGINE_ESM = assetUrl('scrolly/engine.mjs');
const RUNNABLE_ESM = assetUrl('scrolly/runnable.mjs');
const RUNNABLE_CSS = assetUrl('scrolly/runnable.css');
// Page layout. engine.mjs copies it from its shadow root into <head>.
const LAYOUT_CSS = assetUrl('scrolly/scrolly.css');
const STEP = 'scrollyStep';
const STAGE = 'scrollyStage';

// ---------------------------------------------------------------- shared rules

/** CRLF -> LF, trailing spaces/tabs removed per line, outer blank lines removed. */
export function canonicalCode(code) {
  return code
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((l) => l.replace(/[ \t]+$/, ''))
    .join('\n')
    .replace(/^\n+|\n+$/g, '');
}

/** Identifies a code cell between the page, the render file and the plugin. */
export function cellKey(code) {
  return createHash('sha256').update(canonicalCode(code), 'utf8').digest('hex').slice(0, 16);
}

const PARAM_MARK_RE = /(?:^|\s)#\s*@param\b/;
const PARAM_LINE_RE = /^([A-Za-z_]\w*)\s*=\s*(.+?)\s*#\s*@param\s*(.*?)\s*$/;
const NUMBER_RE = /^-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$/;
const SLIDER_KEYS = new Set(['type', 'min', 'max', 'step']);
const CONSTANTS = { True: true, False: false, None: null };

function number(raw) {
  raw = raw.trim();
  if (!NUMBER_RE.test(raw)) throw new Error(`'${raw}' is not a number`);
  return Number(raw);
}

function splitTop(raw) {
  const parts = [];
  let current = '';
  let quote = null;
  for (const ch of raw) {
    if (quote) {
      current += ch;
      if (ch === quote) quote = null;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
      current += ch;
    } else if (ch === ',') {
      parts.push(current);
      current = '';
    } else current += ch;
  }
  if (quote) throw new Error('unclosed quote');
  parts.push(current);
  return parts.map((s) => s.trim());
}

function literal(raw) {
  raw = raw.trim();
  if (raw.length >= 2 && (raw[0] === '"' || raw[0] === "'") && raw.at(-1) === raw[0]) return raw.slice(1, -1);
  if (raw in CONSTANTS) return CONSTANTS[raw];
  return number(raw);
}

function parseSlider(name, valueRaw, spec) {
  const fields = {};
  for (const part of splitTop(spec.slice(1, -1))) {
    if (!part) continue;
    const i = part.indexOf(':');
    if (i === -1) throw new Error(`expected key:value, got '${part}'`);
    fields[part.slice(0, i).trim().replace(/^['"]|['"]$/g, '')] = part.slice(i + 1).trim();
  }
  const kind = (fields.type ?? '').replace(/^['"]|['"]$/g, '');
  if (kind !== 'slider') throw new Error(`only type:"slider" is supported (got ${kind || 'no type'})`);
  const unknown = Object.keys(fields).filter((k) => !SLIDER_KEYS.has(k)).sort();
  if (unknown.length) throw new Error(`unknown slider key(s): ${unknown.join(', ')}`);
  for (const key of ['min', 'max']) if (!(key in fields)) throw new Error(`slider needs ${key}`);
  return {
    name,
    kind: 'slider',
    value: number(valueRaw),
    min: number(fields.min),
    max: number(fields.max),
    step: 'step' in fields ? number(fields.step) : 1,
    options: null,
  };
}

function parseDropdown(name, valueRaw, spec) {
  const inner = spec.slice(1, -1).trim();
  if (!inner) throw new Error('dropdown needs at least one option');
  const options = splitTop(inner).map(literal);
  const value = literal(valueRaw);
  if (!options.some((o) => o === value)) throw new Error(`default ${valueRaw} is not one of the options`);
  return { name, kind: 'dropdown', value, min: null, max: null, step: null, options };
}

function parseParamLine(line) {
  if (/^\s/.test(line)) throw new Error('must not be indented (it has to be a top-level assignment)');
  const m = line.match(PARAM_LINE_RE);
  if (!m) throw new Error('must be an assignment: `name = value  # @param ...`');
  const [, name, valueRaw, spec] = m;
  if (spec.startsWith('{') && spec.endsWith('}')) return parseSlider(name, valueRaw, spec);
  if (spec.startsWith('[') && spec.endsWith(']')) return parseDropdown(name, valueRaw, spec);
  throw new Error('expected {type:"slider", min:..., max:..., step:...} or [option, ...]');
}

/** The `# @param` controls in a code cell. Throws naming the 1-based line in the cell. */
export function parseParams(code) {
  const params = [];
  code
    .replace(/\r\n/g, '\n')
    .split('\n')
    .forEach((line, i) => {
      if (!PARAM_MARK_RE.test(line)) return;
      try {
        params.push(parseParamLine(line));
      } catch (e) {
        throw new Error(`line ${i + 1}: # @param ${e.message}`);
      }
    });
  return params;
}

// ---------------------------------------------------------------- solutions from the source

const FENCE_RE = /^(`{3,}|~{3,}|:{3,})(.*)$/;
const DIRECTIVE_RE = /^\{([\w-]+)\}\s*(.*?)\s*$/;
const OPTION_RE = /^:([A-Za-z][\w-]*):\s*(.*?)\s*$/;
const LITERAL_DIRECTIVES = new Set(['code-cell', 'code', 'code-block']);
const EXERCISE_RE = /^\s*raise NotImplementedError\b/m;

/**
 * [{exercise, solution}] for each top-level exercise code cell directly
 * followed by an {nma-solution}. A small copy of nma_solutions.find_blocks:
 * code fences are opaque, so syntax examples are ignored.
 */
export function exercisePairs(text) {
  const lines = text.split(/\r?\n/);
  const blocks = [];
  const stack = [];
  lines.forEach((line, i) => {
    const m = line.match(FENCE_RE);
    if (!m) return;
    const char = m[1][0];
    const length = m[1].length;
    const info = m[2].trim();
    const top = stack.at(-1);
    if (top && !info && char === top.char && length >= top.length) {
      stack.pop();
      if (top.block) top.block.end = i;
      return;
    }
    if (top && top.literal) return;
    const d = char === ':' || info.startsWith('{') ? info.match(DIRECTIVE_RE) : null;
    const name = d ? d[1] : null;
    const literal = char !== ':' && (name === null || LITERAL_DIRECTIVES.has(name));
    let block = null;
    if (!stack.length && (name === 'code-cell' || name === 'nma-solution')) {
      block = { name, start: i, end: -1 };
      blocks.push(block);
    }
    stack.push({ char, length, literal, block });
  });

  const body = (b) => {
    const inner = lines.slice(b.start + 1, b.end);
    let k = 0;
    if (inner[0]?.trim() === '---') {
      const close = inner.findIndex((l, j) => j > 0 && l.trim() === '---');
      if (close !== -1) k = close + 1;
    } else while (k < inner.length && OPTION_RE.test(inner[k])) k++;
    return inner.slice(k);
  };
  const isBlank = (from, to) => lines.slice(from, to).every((l) => !l.trim());

  const pairs = [];
  blocks.forEach((ex, i) => {
    const sol = blocks[i + 1];
    if (ex.name !== 'code-cell' || ex.end === -1 || !sol || sol.name !== 'nma-solution' || sol.end === -1) return;
    const exercise = body(ex).join('\n').replace(/^\n+|\n+$/g, '');
    if (!EXERCISE_RE.test(exercise) || !isBlank(ex.end + 1, sol.start)) return;
    const solLines = body(sol);
    while (solLines.length && !solLines[0].trim()) solLines.shift();
    while (solLines.length && !solLines.at(-1).trim()) solLines.pop();
    if (solLines.length < 2 || !/^(`{3,}|~{3,})\s*python\s*$/.test(solLines[0])) return;
    pairs.push({ exercise, solution: solLines.slice(1, -1).join('\n').replace(/^\n+|\n+$/g, '') });
  });
  return pairs;
}

// ---------------------------------------------------------------- tree building

const text = (value) => ({ type: 'text', value });
const div = (cls, children = []) => ({ type: 'div', class: cls, children });
const kicker = (value) => div('scrolly-kicker', [{ type: 'paragraph', children: [text(String(value))] }]);
const STAGE_DIVS = ['nma-video', 'nma-slides'];

const isCodeBlock = (n) => n.type === 'block' && n.kind === 'notebook-code';
const codeOf = (block) => (block.children || []).find((c) => c.type === 'code')?.value ?? '';
const tagsOf = (block) => {
  const tags = block.data?.tags ?? [];
  return Array.isArray(tags) ? tags : [tags];
};

function modeOf(tags) {
  if (tags.includes('remove-cell')) return 'hidden';
  if (tags.includes('remove-input')) return 'output';
  if (tags.includes('hide-input') || tags.includes('hide-cell')) return 'collapsed';
  return 'edit';
}

function isStageNode(n) {
  if (isCodeBlock(n) || n.type === STAGE || n.type === 'image') return true;
  if (n.type === 'container' && n.kind === 'figure') return true;
  if (n.type === 'div' && typeof n.class === 'string') return n.class.split(' ').some((c) => STAGE_DIVS.includes(c));
  return false;
}

/** Top-level nodes in order: code blocks stay whole, prose blocks are opened up. */
function flatten(tree) {
  const items = [];
  for (const node of tree.children ?? []) {
    if (node.type === 'block' && !isCodeBlock(node)) items.push(...(node.children ?? []));
    else items.push(node);
  }
  return items;
}

/**
 * Rebuild a scrolly page's tree in place. Returns a list of warning messages.
 * options: {renders: {key: output}, solutions: {exerciseKey: code}, config: {pyodideUrl}}
 */
export function buildScrolly(tree, { renders = {}, solutions = {}, config = {} } = {}) {
  const messages = [];
  const items = flatten(tree);
  const first = items.findIndex((n) => n.type === STEP);
  if (first === -1) return messages;

  const header = [];
  let pending = [];
  const flush = () => {
    if (pending.length) header.push({ type: 'block', children: pending });
    pending = [];
  };

  const cells = [];
  const runnable = (block) => {
    const code = codeOf(block);
    const key = cellKey(code);
    const mode = modeOf(tagsOf(block));
    const exercise = EXERCISE_RE.test(code);
    let params = [];
    try {
      params = parseParams(code);
    } catch (e) {
      messages.push(`code cell ${cells.length + 1}: ${e.message}`);
    }
    const cell = { index: cells.length, code, mode, fallback: (exercise && solutions[key]) || null };
    cells.push(cell);
    if (mode === 'hidden') return null;
    return {
      type: 'anywidget',
      esm: RUNNABLE_ESM,
      css: RUNNABLE_CSS,
      class: 'scrolly-runnable',
      id: `scrolly-cell-${cell.index}`,
      model: {
        code,
        mode,
        params,
        index: cell.index,
        exercise,
        fallback: cell.fallback,
        initial: exercise ? null : renders[key] ?? null,
      },
    };
  };

  // Content before the first {step}: a normal page header.
  for (const node of items.slice(0, first)) {
    if (isCodeBlock(node)) {
      flush();
      const w = runnable(node);
      if (w) header.push({ type: 'block', children: [w] });
    } else pending.push(node);
  }
  flush();

  // Group the rest into steps.
  const steps = [];
  for (const node of items.slice(first)) {
    if (node.type === STEP) steps.push({ marker: node, nodes: [] });
    else steps.at(-1).nodes.push(node);
  }

  const views = [];
  const cards = [];
  const map = [];
  const hero = [];
  const sections = [];
  for (const { marker, nodes } of steps) {
    const o = marker.options ?? {};
    const isHero = marker.arg === 'hero';
    const stage = [];
    const card = [];
    let stageClass = '';
    for (const node of nodes) {
      if (isCodeBlock(node)) {
        const w = runnable(node);
        if (w) stage.push(w);
      } else if (node.type === STAGE) {
        const so = node.options ?? {};
        if (so.style) stageClass += ` is-${so.style}`;
        if (so.class) stageClass += ` ${so.class}`;
        stage.push(...(node.children ?? []));
      } else if (isStageNode(node)) stage.push(node);
      else card.push(node);
    }

    if (isHero) {
      const content = [...(o.kicker ? [kicker(o.kicker)] : []), ...card, ...stage];
      views.push(div(`scrolly-view is-hero${stageClass}`, content));
      cards.push(div('scrolly-step is-hero'));
    } else {
      if (stage.length) views.push(div(`scrolly-view${stageClass}`, stage));
      cards.push(div('scrolly-step', [div('scrolly-card', [...(o.kicker ? [kicker(o.kicker)] : []), ...card])]));
    }
    map.push(views.length - 1);
    hero.push(isHero);
    sections.push(o.section ? String(o.section) : sections.at(-1) ?? '');
  }

  const engine = {
    type: 'anywidget',
    esm: ENGINE_ESM,
    css: LAYOUT_CSS,
    class: 'scrolly-engine',
    id: 'scrolly-engine',
    model: {
      n: cards.length,
      map,
      hero,
      sections,
      pyodideUrl: config.pyodideUrl || DEFAULT_PYODIDE_URL,
      cells: cells.map(({ index, code, mode, fallback }) => ({ index, code, mode, fallback })),
    },
  };
  const section = div('scrolly', [engine, div('scrolly-stage', views), div('scrolly-steps', cards)]);
  // .scrolly-col (scrolly.css) places the section between the TOC sidebar and the outline.
  tree.children = [...header, { type: 'block', class: 'scrolly-col', children: [section] }];
  return messages;
}

/** Remove markers from a page without `layout: scrolly` (Python CI reports it). */
function unwrapMarkers(node) {
  if (!node.children) return;
  node.children = node.children.flatMap((c) => {
    if (c.type === STEP) return [];
    if (c.type === STAGE) return c.children ?? [];
    unwrapMarkers(c);
    return [c];
  });
}

/** Markers as [node, top level]. Top level = a child of the root or of a root block. */
function findMarkers(tree) {
  const found = [];
  const walk = (node, depth) => {
    for (const c of node.children ?? []) {
      if (c.type === STEP || c.type === STAGE) found.push([c, depth <= 1]);
      walk(c, depth + 1);
    }
  };
  walk(tree, 0);
  return found;
}

/** Unwrap markers below the top level, leaving top-level ones alone. */
function unwrapNested(tree) {
  for (const block of tree.children ?? []) {
    for (const node of block.children ?? []) unwrapMarkers(node);
  }
}

// ---------------------------------------------------------------- MyST hooks

function scrollyConfig() {
  return { pyodideUrl: courseSettings().nma.scrolly?.pyodide_url || DEFAULT_PYODIDE_URL };
}

// tutorials/W2D1_Examples/W2D1_Tutorial2.md -> _build/scrolly/W2D1_Examples/W2D1_Tutorial2.json
// (same as render_path in nma_kit.scrolly; the tutorials dir comes from myst.yml)
function renderFile(filePath) {
  const location = pageLocation(filePath);
  const parts = location
    ? [...(location.relDir ? location.relDir.split('/') : []), location.stem]
    : relative(process.cwd(), filePath).split(sep).join('/').replace(/\.[^.]+$/, '').split('/');
  const stem = parts.pop();
  return join(process.cwd(), '_build', 'scrolly', ...parts, `${stem}.json`);
}

const stepDirective = {
  name: 'step',
  doc: 'Scrollytelling step marker (pages with `layout: scrolly`). Content after it, up to the next marker, is the step.',
  arg: { type: String, doc: '`hero` for a full-screen title or closing step (no card).' },
  options: {
    section: { type: String, doc: 'Section name in the progress bar (carries forward).' },
    kicker: { type: String, doc: 'Small label above the card.' },
  },
  run: (data) => [{ type: STEP, arg: data.arg ?? '', options: data.options ?? {}, position: data.node.position }],
};

const stageDirective = {
  name: 'stage',
  doc: 'Markdown shown only on the pinned stage for the current step (pages with `layout: scrolly`).',
  options: {
    style: { type: String, doc: '`list` turns lists into large numbered chips.' },
    class: { type: String, doc: 'Extra CSS classes for the stage view.' },
  },
  body: { type: 'myst', doc: 'Stage content.' },
  run: (data) => [{ type: STAGE, options: data.options ?? {}, children: data.body ?? [], position: data.node.position }],
};

const scrollyTransform = {
  name: 'nma-scrolly',
  doc: 'Lay out `layout: scrolly` pages as a pinned stage with scrolling cards.',
  stage: 'document',
  plugin: () => (tree, vfile) => {
    let source = '';
    try {
      source = readFileSync(vfile.path, 'utf8');
    } catch {
      // not a file on disk
    }
    const markers = findMarkers(tree);
    if (!isScrolly(source)) {
      if (markers.length) {
        vfile.message('{step}/{stage} only work on pages with `layout: scrolly` in the frontmatter', markers[0][0], 'nma-scrolly');
        unwrapMarkers(tree);
      }
      return;
    }
    const nested = markers.find(([, topLevel]) => !topLevel);
    if (nested) {
      const msg = vfile.message('{step}/{stage} must be at the top level of the page', nested[0], 'nma-scrolly');
      msg.fatal = true;
      unwrapNested(tree);
    }

    let renders = {};
    const file = renderFile(vfile.path);
    try {
      renders = JSON.parse(readFileSync(file, 'utf8'));
    } catch {
      vfile.message(
        `no pre-rendered outputs (${relative(process.cwd(), file)}); panels show "Run to see output". ` +
          'Run `nma-kit render-scrolly` to create them.',
        null,
        'nma-scrolly',
      );
    }
    const solutions = Object.fromEntries(exercisePairs(source).map((p) => [cellKey(p.exercise), p.solution]));
    for (const message of buildScrolly(tree, { renders, solutions, config: scrollyConfig() })) {
      vfile.message(message, null, 'nma-scrolly');
    }
  },
};

export default {
  name: 'Neuromatch scrollytelling pages',
  directives: [stepDirective, stageDirective],
  transforms: [scrollyTransform],
};
