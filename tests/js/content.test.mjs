// The build stops when myst.yml declares no nma.content.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import plugin from '../../js/src/content/plugin.mjs';

const start = process.cwd();

function run(myst) {
  const dir = mkdtempSync(join(tmpdir(), 'nma-course-'));
  writeFileSync(join(dir, 'myst.yml'), myst);
  process.chdir(dir);
  try {
    const messages = [];
    const vfile = { path: join(dir, 'a.md'), message: (m) => { const x = { m }; messages.push(x); return x; } };
    plugin.transforms[0].plugin()({ type: 'root', children: [] }, vfile);
    return messages;
  } finally {
    process.chdir(start);
  }
}

test('no nma.content: one fatal message that shows how to declare it', () => {
  for (const myst of ['', 'nma:\n  notebooks: {branch: x}\n', 'nma:\n  content: []\n', 'nma:\n  content: [..]\n']) {
    const messages = run(myst);
    assert.equal(messages.length, 1, myst);
    assert.equal(messages[0].fatal, true);
    assert.match(messages[0].m, /nma\.content/);
  }
});

test('a declared content root is enough', () => {
  assert.deepEqual(run('nma:\n  content: [guide]\n'), []);
});
