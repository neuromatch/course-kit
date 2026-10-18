// Plugins are organised by feature (js/src/<feature>/) and bundled together by
// js/src/index.mjs. A feature may import from shared/ but never from another
// feature, so each one can be read, tested and (later) shipped on its own.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, dirname, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, '..', '..', 'js', 'src');
const FEATURES = ['media', 'solutions', 'feedback', 'scrolly', 'cells'];

function files(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (name === 'node_modules' || name === 'dist') return [];
    return statSync(path).isDirectory() ? files(path) : path.endsWith('.mjs') ? [path] : [];
  });
}

test('every feature has its own plugin.mjs', () => {
  for (const feature of FEATURES) {
    assert.ok(statSync(join(src, feature, 'plugin.mjs')).isFile(), feature);
  }
});

test('features import only from themselves and shared/', () => {
  for (const feature of FEATURES) {
    for (const file of files(join(src, feature))) {
      const imports = [...readFileSync(file, 'utf8').matchAll(/\bfrom\s+['"](\.[^'"]+)['"]/g)].map((m) => m[1]);
      for (const spec of imports) {
        const target = relative(src, join(dirname(file), spec)).split(sep)[0];
        assert.ok(target === feature || target === 'shared', `${relative(src, file)} imports ${spec}`);
      }
    }
  }
});

test('shared/ imports no feature', () => {
  for (const file of files(join(src, 'shared'))) {
    const imports = [...readFileSync(file, 'utf8').matchAll(/\bfrom\s+['"](\.[^'"]+)['"]/g)].map((m) => m[1]);
    for (const spec of imports) {
      assert.equal(relative(src, join(dirname(file), spec)).split(sep)[0], 'shared', `${relative(src, file)} imports ${spec}`);
    }
  }
});

test('index.mjs bundles every directive and keeps the transform order', async () => {
  const { default: kit } = await import(join(src, 'index.mjs'));
  assert.deepEqual(
    kit.directives.map((d) => d.name),
    ['nma-video', 'nma-slides', 'nma-solution', 'nma-explanation', 'nma-feedback', 'step', 'stage'],
  );
  // Same order as the old myst.yml plugin list: nma.mjs (solution links,
  // feedback widgets), then scrolly, then cells.
  assert.deepEqual(
    kit.transforms.map((t) => t.name),
    ['nma-solution-links', 'nma-feedback-widgets', 'nma-scrolly', 'nma-cells'],
  );
});
