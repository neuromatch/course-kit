// Run with: node --test tests/js/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { assetUrl } from '../../js/src/shared/assets.mjs';

import { cellKey, canonicalCode, parseParams, isScrolly, exercisePairs, buildScrolly } from '../../js/src/scrolly/plugin.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, '..', '..', 'fixtures', 'scrolly');
const load = (name) => JSON.parse(readFileSync(join(fixtures, name), 'utf8'));

// The same fixtures are checked in tests/test_nma_scrolly.py.
for (const c of load('cell_keys.json')) {
  test(`cellKey: ${c.name}`, () => {
    assert.equal(canonicalCode(c.code), c.canonical);
    assert.equal(cellKey(c.code), c.key);
  });
}

for (const c of load('params.json')) {
  test(`parseParams: ${c.name}`, () => {
    if (c.error) assert.throws(() => parseParams(c.code), new RegExp(c.error));
    else assert.deepEqual(parseParams(c.code), c.params);
  });
}

test('isScrolly reads a plain frontmatter line', () => {
  assert.ok(isScrolly('---\ntitle: T\nlayout: scrolly\n---\n'));
  assert.ok(isScrolly("---\nlayout: 'scrolly'  # c\n---\n"));
  assert.ok(!isScrolly('---\ntitle: T\n---\nlayout: scrolly\n'));
  assert.ok(!isScrolly('---\nsite:\n  layout: scrolly\n---\n'));
});

const PAGE = `---
layout: scrolly
---

\`\`\`{code-cell} python
def f():
    raise NotImplementedError("x")
\`\`\`

::::{nma-solution}
\`\`\`python
def f():
    return 1
\`\`\`
::::

\`\`\`\`markdown
\`\`\`{code-cell} python
raise NotImplementedError
\`\`\`

::::{nma-solution}
\`\`\`python
example = 1
\`\`\`
::::
\`\`\`\`

\`\`\`{code-cell} python
:tags: [hide-input]
x = 1
\`\`\`
`;

test('exercisePairs pairs top-level exercises with the following solution, ignoring examples', () => {
  assert.deepEqual(exercisePairs(PAGE), [
    { exercise: 'def f():\n    raise NotImplementedError("x")', solution: 'def f():\n    return 1' },
  ]);
});

// --- buildScrolly ---------------------------------------------------------------

const t = (value) => ({ type: 'text', value });
const p = (value) => ({ type: 'paragraph', children: [t(value)] });
const code = (value, tags) => ({
  type: 'block',
  kind: 'notebook-code',
  ...(tags ? { data: { tags } } : {}),
  children: [{ type: 'code', lang: 'python', executable: true, value }, { type: 'outputs', children: [] }],
});
const step = (arg, options = {}) => ({ type: 'scrollyStep', arg, options });

const EXERCISE = 'def f():\n    raise NotImplementedError("x")';

function sampleTree() {
  return {
    type: 'root',
    children: [
      { type: 'block', children: [p('badges')] },
      code('import numpy as np', ['remove-cell']),
      {
        type: 'block',
        children: [
          step('hero', { kicker: 'hello' }),
          { type: 'heading', depth: 2, children: [t('Big title')] },
          p('Credits.'),
          step(undefined, { section: 'S1', kicker: 'Exercise 1' }),
          { type: 'heading', depth: 3, children: [t('Card heading')] },
          p('Card text.'),
          { type: 'scrollyStage', options: { style: 'list' }, children: [{ type: 'list', children: [] }] },
        ],
      },
      code('a = 1  # @param [1, 2]\nprint(a)', ['hide-input']),
      code(EXERCISE),
      {
        type: 'block',
        children: [
          { type: 'div', class: 'nma-solution-link', children: [p('Click for solution')] },
          step(undefined, {}),
          p('Only prose here.'),
          step(undefined, { section: 'S2' }),
          { type: 'div', class: 'nma-video', children: [] },
          { type: 'image', url: 'fig.png' },
          { type: 'anywidget', esm: assetUrl('feedback/widget.mjs'), model: {}, class: 'nma-feedback' },
        ],
      },
      code('plt.plot()', ['remove-input']),
    ],
  };
}

const find = (node, pred, out = []) => {
  if (pred(node)) out.push(node);
  (node.children || []).forEach((c) => find(c, pred, out));
  return out;
};
const byClass = (node, cls) => find(node, (n) => typeof n.class === 'string' && n.class.split(' ').includes(cls));

function build() {
  const tree = sampleTree();
  const renders = {
    [cellKey('a = 1  # @param [1, 2]\nprint(a)')]: { stdout: '1\n', images: [], error: null },
    [cellKey('plt.plot()')]: { stdout: '', images: ['iVBOR'], error: null },
    [cellKey(EXERCISE)]: { stdout: 'should be ignored', images: [], error: null },
  };
  const solutions = { [cellKey(EXERCISE)]: 'def f():\n    return 1' };
  const messages = buildScrolly(tree, { renders, solutions, config: { pyodideUrl: 'https://cdn/x/' } });
  return { tree, messages };
}

test('buildScrolly keeps content before the first step as a header', () => {
  const { tree } = build();
  assert.equal(tree.children.length, 2);
  assert.deepEqual(tree.children[0], { type: 'block', children: [p('badges')] });
  assert.equal(tree.children[1].class, 'scrolly-col');
});

test('buildScrolly engine model', () => {
  const { tree } = build();
  const [engine] = byClass(tree, 'scrolly-engine');
  assert.equal(engine.type, 'anywidget');
  assert.equal(engine.esm, assetUrl('scrolly/engine.mjs'));
  assert.equal(engine.css, assetUrl('scrolly/scrolly.css'));
  const m = engine.model;
  assert.equal(m.n, 4);
  assert.deepEqual(m.hero, [true, false, false, false]);
  assert.deepEqual(m.sections, ['', 'S1', 'S1', 'S2']);
  assert.deepEqual(m.map, [0, 1, 1, 2]); // step 3 has no stage content, so the previous stage stays
  assert.equal(m.pyodideUrl, 'https://cdn/x/');
  assert.deepEqual(
    m.cells.map((c) => [c.index, c.mode, !!c.fallback]),
    [[0, 'hidden', false], [1, 'collapsed', false], [2, 'edit', true], [3, 'output', false]],
  );
  assert.equal(m.cells[0].code, 'import numpy as np');
});

test('buildScrolly splits stage and card', () => {
  const { tree } = build();
  const views = byClass(tree, 'scrolly-view');
  assert.equal(views.length, 3);
  assert.ok(views[0].class.includes('is-hero'));
  assert.equal(byClass(views[0], 'scrolly-kicker').length, 1);
  assert.ok(views[1].class.includes('is-list'));
  // step 2's view: the stage list plus two runnables
  const runnables = (v) => find(v, (n) => n.type === 'anywidget' && n.esm === assetUrl('scrolly/runnable.mjs'));
  assert.equal(runnables(views[1]).length, 2);
  assert.equal(find(views[1], (n) => n.type === 'list').length, 1);
  // step 4's view: video, image and the remove-input cell
  assert.equal(byClass(views[2], 'nma-video').length, 1);
  assert.equal(find(views[2], (n) => n.type === 'image').length, 1);
  assert.equal(runnables(views[2])[0].model.mode, 'output');

  const steps = byClass(tree, 'scrolly-step');
  assert.equal(steps.length, 4);
  assert.ok(steps[0].class.includes('is-hero') && steps[0].children.length === 0);
  const card1 = byClass(steps[1], 'scrolly-card')[0];
  assert.ok(find(card1, (n) => n.value === 'Card text.').length);
  assert.ok(byClass(card1, 'nma-solution-link').length); // solution links stay on the card
  assert.ok(byClass(card1, 'scrolly-kicker').length);
  const card3 = byClass(steps[3], 'scrolly-card')[0];
  assert.ok(byClass(card3, 'nma-feedback').length); // feedback stays on the card
  assert.equal(find(tree, (n) => n.type === 'scrollyStep' || n.type === 'scrollyStage').length, 0);
});

test('buildScrolly runnable models', () => {
  const { tree } = build();
  const widgets = find(tree, (n) => n.esm === assetUrl('scrolly/runnable.mjs'));
  assert.equal(widgets.length, 3); // remove-cell has no widget
  const [demo, exercise, out] = widgets.map((w) => w.model);
  assert.equal(demo.mode, 'collapsed');
  assert.equal(demo.params[0].name, 'a');
  assert.deepEqual(demo.initial, { stdout: '1\n', images: [], error: null });
  assert.equal(exercise.exercise, true);
  assert.equal(exercise.fallback, 'def f():\n    return 1');
  assert.equal(exercise.initial, null);
  assert.deepEqual(out.initial.images, ['iVBOR']);
  assert.equal(widgets[0].css, assetUrl('scrolly/runnable.css'));
});

test('buildScrolly reports bad params and leaves the cell without controls', () => {
  const tree = { type: 'root', children: [{ type: 'block', children: [step()] }, code('a = 1  # @param [3]')] };
  const messages = buildScrolly(tree, { renders: {}, solutions: {}, config: {} });
  assert.equal(messages.length, 1);
  assert.match(messages[0], /# @param/);
  const [w] = find(tree, (n) => n.esm === assetUrl('scrolly/runnable.mjs'));
  assert.deepEqual(w.model.params, []);
});

test('fenced example markers are text, not nodes', () => {
  // MyST turns a ````markdown fence into a code node, so there is no scrollyStep to find.
  const tree = { type: 'root', children: [{ type: 'block', children: [step(), { type: 'code', lang: 'markdown', value: ':::{step}\n:::' }] }] };
  buildScrolly(tree, { renders: {}, solutions: {}, config: {} });
  assert.equal(byClass(tree, 'scrolly-step').length, 1);
  assert.equal(find(tree, (n) => n.type === 'code' && n.lang === 'markdown').length, 1);
});

// --- runnable.mjs pure helpers -------------------------------------------------

import { highlight, applyParams, pyLiteral, codeForEarlierCell, formatValue } from '../../js/src/scrolly/assets/runnable.mjs';
import { readNmaConfig } from '../../js/src/shared/config.mjs';

test('highlight escapes HTML and marks tokens', () => {
  const html = highlight('def f(x):  # a < b\n    return "<s>" + 1');
  assert.match(html, /<i class="tk-k">def<\/i>/);
  assert.match(html, /<i class="tk-f">f<\/i>/);
  assert.match(html, /<i class="tk-c"># a &lt; b<\/i>/);
  assert.match(html, /<i class="tk-s">"&lt;s&gt;"<\/i>/);
  assert.match(html, /<i class="tk-n">1<\/i>/);
  assert.ok(!html.includes('<s>'));
  // the text content is unchanged
  assert.equal(html.replace(/<[^>]+>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>'), 'def f(x):  # a < b\n    return "<s>" + 1');
});

test('applyParams rewrites only param lines and keeps the comment', () => {
  const code = 'a = -0.5   # @param {type:"slider", min:-2.5, max:1.5}\nmode = "x"  # @param ["x", "y"]\nb = a  # not a param\nflag = True # @param [True, False]';
  assert.equal(
    applyParams(code, { a: 1.25, mode: 'y', flag: false, b: 9 }),
    'a = 1.25   # @param {type:"slider", min:-2.5, max:1.5}\nmode = "y"  # @param ["x", "y"]\nb = a  # not a param\nflag = False # @param [True, False]',
  );
});

test('pyLiteral and formatValue', () => {
  assert.equal(pyLiteral(null), 'None');
  assert.equal(pyLiteral(true), 'True');
  assert.equal(pyLiteral('it\'s "q"'), '"it\'s \\"q\\""');
  assert.equal(pyLiteral(0.001), '0.001');
  assert.equal(formatValue(0.1 + 0.2), '0.3');
  assert.equal(formatValue('a'), 'a');
});

test('earlier unfinished exercises run their solution', () => {
  const cell = { index: 2, code: 'def f():\n    raise NotImplementedError("x")', fallback: 'def f():\n    return 1' };
  assert.deepEqual(codeForEarlierCell(cell, {}), { code: 'def f():\n    return 1', fallback: true });
  assert.deepEqual(codeForEarlierCell(cell, { 2: 'def f():\n    return 2' }), { code: 'def f():\n    return 2', fallback: false });
  assert.deepEqual(codeForEarlierCell(cell, { 2: 'def f():\n    # raise NotImplementedError\n    return 3' }).fallback, false);
  assert.deepEqual(codeForEarlierCell({ index: 0, code: 'raise NotImplementedError', fallback: null }, {}).fallback, false);
});

test("the example course's myst.yml sets nma.scrolly.pyodide_url", () => {
  const text = readFileSync(join(here, '..', '..', 'example-course', 'myst.yml'), 'utf8');
  assert.match(readNmaConfig(text).scrolly?.pyodide_url ?? '', /^https:\/\/.+\/$/);
});

test('the how-to page: only its real exercise is paired, examples are ignored', () => {
  const text = readFileSync(join(here, '..', '..', 'fixtures', 'scrolly', 'doc_page.md'), 'utf8');
  assert.ok(isScrolly(text));
  const pairs = exercisePairs(text);
  assert.equal(pairs.length, 1);
  assert.match(pairs[0].exercise, /^def cube\(x\):/);
  assert.equal(pairs[0].solution, 'def cube(x):\n  return x ** 3');
});

// ---- layout regressions (scrolly.css) ----
// Innermost `selector { decls }` rules; @media/@container wrappers are skipped.
const cssRules = (css) =>
  [...css.replace(/\/\*[\s\S]*?\*\//g, '').matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({ sel: m[1].trim(), body: m[2] }));
const scrollyCss = readFileSync(join(here, '..', '..', 'js', 'src', 'scrolly', 'assets', 'scrolly.css'), 'utf8');

test('the pinned stage and HUD stop at the end of the section (no negative margins)', () => {
  // A sticky element with margin-bottom: -height has a 0px margin box, so it
  // keeps sticking for a whole screen past the section and covers the footer.
  for (const { sel, body } of cssRules(scrollyCss)) {
    if (!/\.scrolly-(stage|engine)\b/.test(sel)) continue;
    assert.doesNotMatch(body, /margin[^:;]*:[^;]*-/, `negative margin in "${sel}"`);
    assert.doesNotMatch(body, /(^|[\s;])height:\s*0\s*[;}]?/, `zero height in "${sel}"`);
  }
  const stacked = cssRules(scrollyCss).filter(({ body }) => /grid-area:\s*1\s*\/\s*1/.test(body)).map((r) => r.sel).join(' ');
  for (const part of ['scrolly-engine', 'scrolly-stage', 'scrolly-steps']) assert.match(stacked, new RegExp(part), `${part} not in the shared grid cell`);
});

test('cards stay in their column when they hold wide content (code blocks)', () => {
  // The step is a flex row; a flex item's default min-width: auto is its
  // longest unwrapped line, so a ```python fence pushed the card over the stage.
  const card = cssRules(scrollyCss).find(({ sel }) => sel === '.scrolly-card');
  assert.match(card.body, /min-width:\s*0/);
  const pre = cssRules(scrollyCss).find(({ sel }) => /\.scrolly-card pre\b/.test(sel));
  assert.ok(pre, 'no .scrolly-card pre rule');
  assert.match(pre.body, /overflow-x:\s*auto/);
});
