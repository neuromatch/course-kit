// The {nma-solution} link transform, run on a hand-built tree.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import plugin from '../../js/src/solutions/plugin.mjs';

const start = process.cwd();
const MYST = 'project:\n  github: https://github.com/o/r\nnma:\n  content: [tutorials, projects]\n';

function run(page, { audience, placeholder = {}, myst = MYST } = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'nma-course-'));
  writeFileSync(join(dir, 'myst.yml'), myst);
  process.chdir(dir);
  const saved = process.env.NMA_AUDIENCE;
  if (audience) process.env.NMA_AUDIENCE = audience;
  else delete process.env.NMA_AUDIENCE;
  try {
    const tree = { type: 'root', children: [{ type: 'nmaSolutionRef', kind: 'nma-solution', ...placeholder }] };
    const messages = [];
    const vfile = { path: join(dir, page), message: (m) => { const x = { m }; messages.push(x); return x; } };
    plugin.transforms[0].plugin()(tree, vfile);
    return { tree, messages };
  } finally {
    process.chdir(start);
    if (saved === undefined) delete process.env.NMA_AUDIENCE;
    else process.env.NMA_AUDIENCE = saved;
  }
}

const SOLUTION_CODE = { type: 'code', lang: 'python', value: 'x = 1' };
const find = (node, type) =>
  node.type === type ? [node] : (node.children ?? []).flatMap((c) => find(c, type));
const textOf = (node) => (node.value ?? '') + (node.children ?? []).map(textOf).join('');

test('links to the solution under the page content root', () => {
  for (const [page, dir] of [
    ['tutorials/D/T.md', 'tutorials/D'],
    ['projects/Neuro/P.md', 'projects/Neuro'],
  ]) {
    const { tree, messages } = run(page);
    assert.equal(messages.length, 0);
    const link = JSON.stringify(tree);
    assert.ok(link.includes(`notebooks/${dir}/solutions/${page.split('/').pop().replace('.md', '')}_Solution_1.py`), link);
  }
});

test('links under a root whose name differs from its folder', () => {
  const myst = 'project:\n  github: https://github.com/o/r\nnma:\n  content: [{name: guide, path: docs/guide}]\n';
  const { tree, messages } = run('docs/guide/setup/Intro.md', { myst });
  assert.equal(messages.length, 0);
  assert.ok(JSON.stringify(tree).includes('notebooks/guide/setup/solutions/Intro_Solution_1.py'));
});

test('pages outside every content dir get a fatal message naming them', () => {
  const { messages } = run('other/X.md');
  assert.equal(messages.length, 1);
  assert.match(messages[0].m, /tutorials\/ or projects\//);
  assert.match(run('tutorials/D/T.md', { myst: 'project:\n  github: https://github.com/o/r\n' }).messages[0].m, /nma\.content folder/);
});

test('student: still a link, and the body is not in the tree', () => {
  const { tree } = run('tutorials/D/T.md', { placeholder: { children: [SOLUTION_CODE] } });
  const json = JSON.stringify(tree);
  assert.ok(json.includes('T_Solution_1.py'));
  assert.ok(!json.includes('x = 1'));
});

test('instructor: the solution is an inline dropdown with the code and no link', () => {
  const { tree, messages } = run('tutorials/D/T.md', { audience: 'instructor', placeholder: { children: [SOLUTION_CODE] } });
  assert.equal(messages.length, 0);
  const [box] = find(tree, 'admonition');
  assert.equal(box.kind, 'dropdown');
  assert.equal(textOf(find(box, 'admonitionTitle')[0]), 'Solution');
  assert.equal(find(box, 'code')[0].value, 'x = 1');
  assert.equal(find(tree, 'link').length, 0);
});

test('instructor: the explanation dropdown is titled Explanation', () => {
  const { tree } = run('tutorials/D/T.md', {
    audience: 'instructor',
    placeholder: { kind: 'nma-explanation', children: [{ type: 'paragraph', children: [{ type: 'text', value: 'because' }] }] },
  });
  const [box] = find(tree, 'admonition');
  assert.equal(textOf(find(box, 'admonitionTitle')[0]), 'Explanation');
  assert.ok(textOf(box).includes('because'));
});

test('instructor: a page with no solutions is untouched', () => {
  const tree = { type: 'root', children: [{ type: 'paragraph', children: [] }] };
  const before = JSON.stringify(tree);
  const dir = mkdtempSync(join(tmpdir(), 'nma-course-'));
  writeFileSync(join(dir, 'myst.yml'), MYST);
  process.chdir(dir);
  process.env.NMA_AUDIENCE = 'instructor';
  try {
    plugin.transforms[0].plugin()(tree, { path: join(dir, 'tutorials/D/T.md'), message: () => ({}) });
  } finally {
    process.chdir(start);
    delete process.env.NMA_AUDIENCE;
  }
  assert.equal(JSON.stringify(tree), before);
});

test('the directive only parses its body for the instructor audience', () => {
  const [solution] = plugin.directives;
  const calls = [];
  const ctx = { parseMyst: (source) => { calls.push(source); return { children: [SOLUTION_CODE] }; } };
  const data = { node: { position: {} }, body: '```python\nx = 1\n```' };
  const dir = mkdtempSync(join(tmpdir(), 'nma-course-'));
  writeFileSync(join(dir, 'myst.yml'), MYST);
  process.chdir(dir);
  try {
    delete process.env.NMA_AUDIENCE;
    assert.deepEqual(solution.run(data, {}, ctx)[0].children, undefined);
    assert.equal(calls.length, 0);
  } finally {
    process.chdir(start);
  }
  const dir2 = mkdtempSync(join(tmpdir(), 'nma-course-'));
  writeFileSync(join(dir2, 'myst.yml'), MYST);
  process.chdir(dir2);
  process.env.NMA_AUDIENCE = 'instructor';
  try {
    const [placeholder] = solution.run(data, {}, ctx);
    assert.deepEqual(calls, [data.body]);
    assert.deepEqual(placeholder.children, [SOLUTION_CODE]);
  } finally {
    process.chdir(start);
    delete process.env.NMA_AUDIENCE;
  }
});
