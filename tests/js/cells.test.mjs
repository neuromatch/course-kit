// Run with: node --test tests/js/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { assetUrl } from '../../js/src/shared/assets.mjs';

import {
  NO_FALLBACK_MARKER, isExercise, withNoFallback, modeOf, runtimeOf, thebeId, thebeScriptUrls, statusText,
} from '../../js/src/cells/src/model.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, '..', '..', 'fixtures', 'cells');

// The same fixture is checked in tests/test_nma_cells.py.
for (const c of JSON.parse(readFileSync(join(fixtures, 'runtime.json'), 'utf8'))) {
  test(`runtimeOf: ${c.name}`, () => assert.equal(runtimeOf(c.text), c.runtime));
}

test('modeOf', () => {
  assert.equal(modeOf([]), 'edit');
  assert.equal(modeOf(['remove-cell']), 'hidden');
  assert.equal(modeOf(['remove-input']), 'output');
  assert.equal(modeOf(['hide-input']), 'collapsed');
  assert.equal(modeOf(['hide-cell']), 'collapsed');
  assert.equal(modeOf(['remove-cell', 'hide-input']), 'hidden');
});

test('isExercise', () => {
  assert.ok(isExercise('def f():\n    raise NotImplementedError("x")'));
  assert.ok(!isExercise('# raise NotImplementedError'));
  assert.ok(!isExercise('x = 1'));
});

test('withNoFallback appends the marker once', () => {
  assert.equal(NO_FALLBACK_MARKER, 'nma-no-fallback');
  assert.equal(withNoFallback('x = 1\n\n'), 'x = 1\n# nma-no-fallback\n');
  assert.equal(withNoFallback(withNoFallback('x = 1\n\n')), 'x = 1\n# nma-no-fallback\n');
});

test('thebeId', () => assert.equal(thebeId(7), 'nma-cell-7'));

test('thebeScriptUrls resolves relative to the bundle', () => {
  assert.deepEqual(thebeScriptUrls('https://org.github.io/repo/build/panel-abc.mjs'), {
    core: 'https://org.github.io/repo/thebe-core.min.js',
    lite: 'https://org.github.io/repo/thebe-lite.min.js',
  });
  assert.equal(thebeScriptUrls('https://x.org/build/p.mjs').core, 'https://x.org/thebe-core.min.js');
});

test('statusText', () => {
  assert.equal(statusText({ state: 'running' }), 'Running…');
  assert.equal(statusText({ state: 'done', count: 3 }), '[3] ✓');
  assert.equal(statusText({ state: 'error', count: 4, error: { ename: 'NotImplementedError' } }), '[4] ✗ NotImplementedError');
  assert.equal(statusText({ state: 'error', count: null, error: { ename: 'X' } }), '[ ] ✗ X');
});

// ------------------------------------------------------------------ runtime

import { PageRuntime, pageRuntime, ensureThebeLoaded } from '../../js/src/cells/src/runtime.mjs';

function fakeThebe({ failOn = [], ename = 'NotImplementedError' } = {}) {
  const log = [];
  const cells = new Map();
  let count = 0;
  const session = {};
  const api = {
    makeEvents: () => ({}),
    makeConfiguration: (opts) => ({ opts, mathjax: {} }),
    makeServer: () => ({
      connectToJupyterLiteServer: async () => {
        log.push(['connect']);
        await new Promise((r) => setTimeout(r, 5));
      },
      startNewSession: async () => {
        log.push(['session']);
        return session;
      },
      shutdownAllSessions: async () => log.push(['shutdown']),
      dispose: () => log.push(['dispose']),
    }),
    makeRenderMimeRegistry: () => ({}),
    setupNotebookFromBlocks: (blocks) => {
      for (const b of blocks) {
        cells.set(b.id, {
          executionCount: null,
          attachToDOM(el) { log.push(['attach', b.id, el]); },
          async execute(src) {
            log.push(['exec', b.id, src]);
            this.executionCount = ++count;
            return failOn.includes(b.id) ? { error: [{ ename }] } : {};
          },
        });
      }
      return { attachSession: (s) => log.push(['attachSession', s]), getCellById: (id) => cells.get(id) };
    },
  };
  return { api, log };
}

const EXERCISE = 'def f():\n    raise NotImplementedError("x")';
const CELLS = [
  { index: 0, code: 'setup()', mode: 'hidden', exercise: false },
  { index: 1, code: 'a = 1', mode: 'edit', exercise: false },
  { index: 2, code: EXERCISE, mode: 'edit', exercise: true },
  { index: 3, code: 'f()', mode: 'edit', exercise: false },
];

function setup(opts) {
  const fake = fakeThebe(opts);
  globalThis.window = { thebeCore: { api: fake.api }, thebeLite: {} };
  globalThis.location = { pathname: '/p/' };
  const rt = new PageRuntime('/p/');
  rt.setCells(CELLS);
  const execs = () => fake.log.filter((e) => e[0] === 'exec').map((e) => [e[1], e[2]]);
  return { ...fake, rt, execs };
}

test('run executes earlier cells first, only the target gets the marker', async () => {
  const { rt, execs } = setup();
  await rt.run(3, 'f()');
  assert.deepEqual(execs(), [
    ['nma-cell-0', 'setup()'],
    ['nma-cell-1', 'a = 1'],
    ['nma-cell-2', EXERCISE],
    ['nma-cell-3', withNoFallback('f()')],
  ]);
  assert.ok(!execs().slice(0, 3).some(([, s]) => s.includes(NO_FALLBACK_MARKER)));
});

test('run uses edits for earlier cells', async () => {
  const { rt, execs } = setup();
  rt.edits[1] = 'a = 2';
  await rt.run(3, 'f()');
  assert.deepEqual(execs()[1], ['nma-cell-1', 'a = 2']);
});

test('already-run cells are skipped', async () => {
  const { rt, execs } = setup();
  await rt.run(1, 'a = 1');
  await rt.run(3, 'f()');
  const ids = execs().map(([id]) => id);
  assert.equal(ids.filter((i) => i === 'nma-cell-0').length, 1);
  assert.equal(ids.filter((i) => i === 'nma-cell-1').length, 1);
});

test('the explicitly run exercise carries the marker, earlier cells do not', async () => {
  const { rt, execs } = setup();
  await rt.run(2, EXERCISE);
  const e = Object.fromEntries(execs());
  assert.ok(e['nma-cell-2'].includes(NO_FALLBACK_MARKER));
  assert.ok(!e['nma-cell-0'].includes(NO_FALLBACK_MARKER));
  assert.ok(!e['nma-cell-1'].includes(NO_FALLBACK_MARKER));
});

test('runAll executes every cell top to bottom, fallback left on everywhere', async () => {
  const { rt, execs } = setup();
  const res = await rt.runAll();
  assert.deepEqual(execs(), [
    ['nma-cell-0', 'setup()'],
    ['nma-cell-1', 'a = 1'],
    ['nma-cell-2', EXERCISE],
    ['nma-cell-3', 'f()'],
  ]);
  assert.ok(!execs().some(([, s]) => s.includes(NO_FALLBACK_MARKER)));
  assert.equal(res.failedIndex, null);
});

test('runAll applies in-memory edits', async () => {
  const { rt, execs } = setup();
  rt.edits[1] = 'a = 2';
  await rt.runAll();
  assert.deepEqual(execs()[1], ['nma-cell-1', 'a = 2']);
});

test('runAll stops at the first cell that errors', async () => {
  const { rt, execs } = setup({ failOn: ['nma-cell-1'] });
  const res = await rt.runAll();
  assert.deepEqual(execs().map(([id]) => id), ['nma-cell-0', 'nma-cell-1']);
  assert.equal(res.failedIndex, 1);
});

test('an earlier error stops the run', async () => {
  const { rt, execs } = setup({ failOn: ['nma-cell-1'] });
  const events = [];
  rt.subscribe((e) => events.push(e));
  await rt.run(3, 'f()');
  assert.deepEqual(execs().map(([id]) => id), ['nma-cell-0', 'nma-cell-1']);
  assert.ok(events.some((e) => e.index === 1 && e.state === 'error'));
});

test("thebe's <class 'X'> exception names are normalised", async () => {
  const { rt } = setup({ failOn: ['nma-cell-1'], ename: "<class 'NotImplementedError'>" });
  const events = [];
  rt.subscribe((e) => events.push(e));
  await rt.run(1, 'a = 1');
  assert.equal(events.find((e) => e.state === 'error').error.ename, 'NotImplementedError');
});

test('concurrent runs boot once and run each earlier cell once, in call order', async () => {
  const { rt, execs, log } = setup();
  const order = [];
  await Promise.all([
    rt.run(3, 'f()').then(() => order.push('a')),
    rt.run(3, 'f()').then(() => order.push('b')),
    rt.run(1, 'a = 1').then(() => order.push('c')),
  ]);
  assert.equal(log.filter((e) => e[0] === 'connect').length, 1);
  const ids = execs().map(([id]) => id);
  const n = (id) => ids.filter((i) => i === id).length;
  assert.equal(n('nma-cell-0'), 1);
  assert.equal(n('nma-cell-2'), 1);
  assert.equal(n('nma-cell-3'), 2); // explicit runs
  assert.equal(n('nma-cell-1'), 2); // implicit once, then the explicit run(1)
  assert.deepEqual(order, ['a', 'b', 'c']);
});

test('register twice (hydration): the latest element is attached, once', async () => {
  const { rt, log } = setup();
  const elA = { name: 'A' };
  const elB = { name: 'B' };
  const offA = rt.register(1, elA);
  rt.register(1, elB);
  offA(); // must not drop elB
  await rt.boot();
  const attaches = log.filter((e) => e[0] === 'attach' && e[1] === 'nma-cell-1');
  assert.equal(attaches.length, 1);
  assert.equal(attaches[0][2], elB);
});

test('register after boot attaches immediately', async () => {
  const { rt, log } = setup();
  await rt.boot();
  const el = {};
  rt.register(2, el);
  assert.ok(log.some((e) => e[0] === 'attach' && e[1] === 'nma-cell-2' && e[2] === el));
});

test('restart clears ran and starts a fresh session', async () => {
  const { rt, execs, log } = setup();
  await rt.run(1, 'a = 1');
  await rt.restart();
  assert.ok(log.some((e) => e[0] === 'shutdown'));
  assert.equal(log.filter((e) => e[0] === 'session').length, 2);
  await rt.run(1, 'a = 1');
  assert.equal(execs().filter(([id]) => id === 'nma-cell-0').length, 2);
});

test('pageRuntime is per path; a path change disposes the old runtime', async () => {
  const { log } = setup();
  const a = pageRuntime();
  assert.equal(pageRuntime(), a);
  a.setCells(CELLS);
  await a.boot();
  location.pathname = '/q/';
  const b = pageRuntime();
  assert.notEqual(a, b);
  await new Promise((r) => setTimeout(r, 20));
  assert.ok(log.some((e) => e[0] === 'shutdown'));
  assert.ok(log.some((e) => e[0] === 'dispose'));
});

test('dispose waits for a pending boot', async () => {
  const { rt, log } = setup();
  const booting = rt.boot();
  await rt.dispose();
  await booting;
  assert.ok(log.some((e) => e[0] === 'shutdown') && log.some((e) => e[0] === 'dispose'));
});

test('ensureThebeLoaded resolves at once when the globals exist', async () => {
  setup();
  await ensureThebeLoaded('https://x.org/build/p.mjs');
});

// ------------------------------------------------------------------ plugin

import { buildBrowserPage, buildColabPage } from '../../js/src/cells/plugin.mjs';

const t = (value) => ({ type: 'text', value });
const p = (value) => ({ type: 'paragraph', children: [t(value)] });
const code = (value, tags) => ({
  type: 'block',
  kind: 'notebook-code',
  ...(tags ? { data: { tags } } : {}),
  children: [{ type: 'code', lang: 'python', executable: true, value }, { type: 'outputs', children: [] }],
});
const widgets = (tree, cls) => {
  const found = [];
  const walk = (n) => {
    if (n.type === 'anywidget' && n.class === cls) found.push(n);
    (n.children ?? []).forEach(walk);
  };
  walk(tree);
  return found;
};

test('buildBrowserPage: manifest, panels, hidden cells without a panel', () => {
  const intro = p('intro');
  const tree = {
    type: 'root',
    children: [
      { type: 'block', children: [intro] },
      code('import x', ['remove-cell']),
      code('a = 1'),
      code(EXERCISE),
      code('plt.plot()', ['hide-input']),
    ],
  };
  assert.equal(buildBrowserPage(tree), 4);
  const [runtime] = widgets(tree, 'nma-cells-runtime');
  assert.equal(tree.children[0].children[0], runtime);
  assert.deepEqual(runtime.model.cells.map((c) => c.mode), ['hidden', 'edit', 'edit', 'collapsed']);
  assert.deepEqual(runtime.model.cells.map((c) => c.exercise), [false, false, true, false]);
  assert.deepEqual(runtime.model.cells.map((c) => c.index), [0, 1, 2, 3]);
  const panels = widgets(tree, 'nma-cell');
  assert.deepEqual(panels.map((w) => w.id), ['nma-cell-1', 'nma-cell-2', 'nma-cell-3']);
  assert.equal(panels[0].esm, assetUrl('cells/panel.mjs'));
  assert.equal(panels[0].css, assetUrl('cells/cells.css'));
  assert.equal(runtime.esm, assetUrl('cells/runtime-widget.mjs'));
  assert.equal(runtime.css, assetUrl('cells/page.css'));
  assert.ok(!JSON.stringify(tree).includes('notebook-code'));
  assert.ok(JSON.stringify(tree).includes('intro'));
});

test('buildBrowserPage finds nested cells and keeps their order', () => {
  const tree = {
    type: 'root',
    children: [code('first'), { type: 'container', children: [code('second'), code('third')] }],
  };
  assert.equal(buildBrowserPage(tree), 3);
  const [runtime] = widgets(tree, 'nma-cells-runtime');
  assert.deepEqual(runtime.model.cells.map((c) => c.code), ['first', 'second', 'third']);
  assert.deepEqual(widgets(tree, 'nma-cell').map((w) => w.id), ['nma-cell-0', 'nma-cell-1', 'nma-cell-2']);
});

test('buildColabPage adds a banner and keeps the code blocks', () => {
  const tree = { type: 'root', children: [code('a = 1')] };
  buildColabPage(tree, { colabUrl: 'https://colab/x', kaggleUrl: 'https://kaggle/x' });
  const banner = tree.children[0].children[0];
  assert.equal(banner.type, 'admonition');
  assert.equal(banner.kind, 'important');
  assert.equal(banner.children[0].children[0].value, 'Do this tutorial in Colab');
  const links = banner.children[1].children.filter((c) => c.type === 'link');
  assert.deepEqual(links.map((l) => l.url), ['https://colab/x', 'https://kaggle/x']);
  assert.ok(tree.children.some((c) => c.kind === 'notebook-code'));
  assert.equal(widgets(tree, 'nma-cell').length, 0);
});
