// The {nma-solution} link transform, run on a hand-built tree.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import plugin from '../../js/src/solutions/plugin.mjs';

const start = process.cwd();
const MYST = 'project:\n  github: https://github.com/o/r\n';

function run(page) {
  const dir = mkdtempSync(join(tmpdir(), 'nma-course-'));
  writeFileSync(join(dir, 'myst.yml'), MYST);
  process.chdir(dir);
  try {
    const tree = { type: 'root', children: [{ type: 'nmaSolutionRef', kind: 'nma-solution' }] };
    const messages = [];
    const vfile = { path: join(dir, page), message: (m) => { const x = { m }; messages.push(x); return x; } };
    plugin.transforms[0].plugin()(tree, vfile);
    return { tree, messages };
  } finally {
    process.chdir(start);
  }
}

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

test('pages outside every content dir get a fatal message naming them', () => {
  const { messages } = run('other/X.md');
  assert.equal(messages.length, 1);
  assert.match(messages[0].m, /tutorials\/ or projects\//);
});
