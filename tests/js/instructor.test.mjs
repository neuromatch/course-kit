// {nma-instructor}: teaching notes, shown only in the instructor build.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import plugin from '../../js/src/instructor/plugin.mjs';

const start = process.cwd();
const [directive] = plugin.directives;

function runIn(audience, body) {
  const dir = mkdtempSync(join(tmpdir(), 'nma-course-'));
  writeFileSync(join(dir, 'myst.yml'), 'project:\n  github: https://github.com/o/r\n');
  process.chdir(dir);
  const saved = process.env.NMA_AUDIENCE;
  if (audience) process.env.NMA_AUDIENCE = audience;
  else delete process.env.NMA_AUDIENCE;
  const parsed = [];
  const ctx = {
    parseMyst: (source) => {
      parsed.push(source);
      return { children: [{ type: 'paragraph', children: [{ type: 'text', value: source }] }] };
    },
  };
  try {
    return { nodes: directive.run({ node: { position: {} }, body }, {}, ctx), parsed };
  } finally {
    process.chdir(start);
    if (saved === undefined) delete process.env.NMA_AUDIENCE;
    else process.env.NMA_AUDIENCE = saved;
  }
}

const textOf = (node) => (node.value ?? '') + (node.children ?? []).map(textOf).join('');

test('the plugin registers one directive, nma-instructor, with a required body', () => {
  assert.deepEqual(plugin.directives.map((d) => d.name), ['nma-instructor']);
  assert.equal(directive.body.required, true);
});

test('student: nothing is rendered and the body is never parsed', () => {
  const { nodes, parsed } = runIn(undefined, 'secret note');
  assert.deepEqual(nodes, []);
  assert.deepEqual(parsed, []);
});

test('instructor: one admonition titled Instructor notes with the parsed body', () => {
  const body = 'Math $x^2$.\n\n```python\nprint(1)\n```\n\n:::{note}\nnested\n:::';
  const { nodes, parsed } = runIn('instructor', body);
  assert.deepEqual(parsed, [body]);
  assert.equal(nodes.length, 1);
  const [box] = nodes;
  assert.equal(box.type, 'admonition');
  assert.equal(box.kind, 'note');
  assert.ok(box.class.includes('nma-instructor'));
  assert.equal(textOf(box.children[0]), 'Instructor notes');
  assert.equal(box.children[0].type, 'admonitionTitle');
  assert.equal(textOf(box.children[1]), body);
});
