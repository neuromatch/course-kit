// The built plugin (run `npm run build` or `npm run build:dev` in js/ first).
// Release-only checks are skipped for dev builds.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const js = join(here, '..', '..', 'js');
const dist = join(js, 'dist');
const info = existsSync(join(dist, 'build-info.json'))
  ? JSON.parse(readFileSync(join(dist, 'build-info.json'), 'utf8'))
  : null;
const version = JSON.parse(readFileSync(join(js, 'package.json'), 'utf8')).version;
const ASSETS = [
  'feedback/widget.mjs',
  'scrolly/engine.mjs', 'scrolly/runnable.mjs', 'scrolly/runnable.css', 'scrolly/scrolly.css',
  'cells/panel.mjs', 'cells/runtime-widget.mjs', 'cells/cells.css', 'cells/page.css',
];

test('dist/ has been built', () => assert.ok(info, 'run npm run build (or build:dev) in js/'));

test('the bundle exports the same plugin as src/index.mjs', { skip: !info }, async () => {
  const { default: bundle } = await import(pathToFileURL(join(dist, 'nma.mjs')).href);
  const { default: source } = await import(pathToFileURL(join(js, 'src', 'index.mjs')).href);
  assert.deepEqual(bundle.directives.map((d) => d.name), source.directives.map((d) => d.name));
  assert.deepEqual(bundle.transforms.map((t) => t.name), source.transforms.map((t) => t.name));
});

test('every browser asset is in dist/assets', { skip: !info }, () => {
  for (const rel of ASSETS) assert.ok(existsSync(join(dist, 'assets', rel)), rel);
  assert.equal(info.version, version);
});

test('release bundle points at exact-version CDN assets', { skip: info?.mode !== 'release' }, () => {
  const code = readFileSync(join(dist, 'nma.mjs'), 'utf8');
  const base = `https://cdn.jsdelivr.net/npm/@neuromatch/course-kit@${version}/dist/assets/`;
  assert.ok(code.includes(base), base);
  assert.ok(!code.includes('/plugins/') && !code.includes('/course-kit/js/'), 'no repo-relative asset paths');
  const yml = readFileSync(join(dist, 'nma.yml'), 'utf8');
  assert.match(yml, new RegExp(`course-kit@${version.replace(/\./g, '\\.')}/dist/nma\\.mjs`));
  assert.match(yml, /lite: true/);
});

test('dev bundle resolves assets next to itself', { skip: info?.mode !== 'dev' }, async () => {
  const { assetUrl } = await import(pathToFileURL(join(js, 'src', 'shared', 'assets.mjs')).href);
  assert.equal(assetUrl('cells/panel.mjs'), '/dist/assets/cells/panel.mjs'); // npm test runs in js/
  assert.ok(!existsSync(join(dist, 'nma.yml')), 'nma.yml is release-only');
});
