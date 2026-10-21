import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import plugin, { parseDataDirective, assetUrlFor, validateDataDirectives } from '../../js/src/assets/plugin.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const FIXTURE = JSON.parse(readFileSync(join(here, '..', 'fixtures', 'assets', 'directives.json'), 'utf8'));

for (const c of FIXTURE.parse) {
  test(`parseDataDirective: ${c.name}`, () => {
    assert.deepEqual(parseDataDirective(c.text), c.paths);
  });
}

for (const c of FIXTURE.asset_url) {
  test(`assetUrlFor: ${c.path} (day "${c.day}")`, () => {
    assert.equal(assetUrlFor(c.repo, c.branch, c.day, c.path), c.url);
  });
}

for (const c of FIXTURE.validate) {
  test(`validateDataDirectives: ${c.name}`, () => {
    assert.equal(validateDataDirectives(c.text, 'data', 'image').length, c.errors);
  });
}

test('validateDataDirectives honours custom folder names', () => {
  assert.deepEqual(validateDataDirectives(':::{nma-data}\nassets/a.npz\npics/b.png\n:::\n', 'assets', 'pics'), []);
});

test('plugin registers the nma-data directive', () => {
  assert.deepEqual(plugin.directives.map((d) => d.name), ['nma-data']);
});

// ------------------------------------------------------------- transform

import { readEmbeddedAssets, applyAssets, dataNote } from '../../js/src/assets/plugin.mjs';

const DAY = join(here, '..', 'fixtures', 'assets', 'day');

test('readEmbeddedAssets embeds bytes as base64 and skips missing or escaping paths', () => {
  const out = readEmbeddedAssets(DAY, ['data/tiny.bin', 'data/missing.npz', '../x.bin', '/etc/passwd']);
  assert.deepEqual(out, [{ path: 'data/tiny.bin', b64: Buffer.from([0, 1, 2, 255]).toString('base64') }]);
});

test('dataNote is a collapsed dropdown with raw URL links', () => {
  const node = dataNote(['data/tiny.bin'], (p) => `https://u/${p}`);
  assert.equal(node.type, 'admonition');
  assert.equal(node.kind, 'dropdown');
  assert.match(JSON.stringify(node), /Data used by this notebook/);
  assert.match(JSON.stringify(node), /https:\/\/u\/data\/tiny\.bin/);
});

test('applyAssets sets tree.data.nmaAssets only when the page declares files', () => {
  const src = ':::{nma-data}\ndata/tiny.bin\n:::\n';
  const tree = { type: 'root', children: [] };
  applyAssets(tree, src, join(DAY, 'page.md'));
  assert.equal(tree.data.nmaAssets.length, 1);
  assert.equal(tree.data.nmaAssets[0].path, 'data/tiny.bin');

  const plain = { type: 'root', children: [] };
  applyAssets(plain, 'Just prose.\n', join(DAY, 'page.md'));
  assert.equal(plain.data, undefined);
});

test('the plugin registers the nma-assets transform at document stage', () => {
  assert.deepEqual(plugin.transforms.map((t) => [t.name, t.stage]), [['nma-assets', 'document']]);
});
