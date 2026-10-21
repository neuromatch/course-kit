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
