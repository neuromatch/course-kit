// Course settings (myst.yml) and page paths. The same cases run in Python
// (tests/python/test_config.py) against tests/fixtures/config/settings.json.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { loadSettings, readNmaConfig } from '../../js/src/shared/config.mjs';
import { pageLocation, notebookDir, notebookUrls, solutionUrl, courseSettings } from '../../js/src/shared/paths.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const { cases } = JSON.parse(readFileSync(join(here, '..', 'fixtures', 'config', 'settings.json'), 'utf8'));
const start = process.cwd();

function inCourse(myst, fn, env = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'nma-course-'));
  writeFileSync(join(dir, 'myst.yml'), myst);
  process.chdir(dir);
  const saved = process.env.NMA_NOTEBOOKS_BRANCH;
  delete process.env.NMA_NOTEBOOKS_BRANCH;
  Object.assign(process.env, env);
  try {
    return fn(dir);
  } finally {
    process.chdir(start);
    if (saved === undefined) delete process.env.NMA_NOTEBOOKS_BRANCH;
    else process.env.NMA_NOTEBOOKS_BRANCH = saved;
  }
}

for (const c of cases) {
  test(`shared fixture: ${c.name}`, () => {
    inCourse(c.myst, (dir) => {
      const page = join(dir, c.page);
      mkdirSync(dirname(page), { recursive: true });
      const location = pageLocation(page);
      if (c.expect === null) {
        assert.equal(location, null);
        return;
      }
      assert.deepEqual(location, { root: c.expect.root, relDir: c.expect.relDir, stem: c.expect.stem });
      assert.equal(notebookDir(location), c.expect.notebookDir);
      assert.deepEqual(notebookUrls(page), { colabUrl: c.expect.colab, kaggleUrl: c.expect.kaggle });
      const s = courseSettings();
      assert.equal(solutionUrl(s.githubRepo, notebookDir(location), `${location.stem}_Solution_1.py`, s.notebooksBranch), c.expect.solution1);
    }, c.env);
  });
}

test('defaults without an nma block', () => {
  assert.deepEqual(loadSettings('project:\n  github: https://github.com/o/r\n'), {
    githubRepo: 'o/r',
    tutorialsDir: 'tutorials',
    projectsDir: 'projects',
    notebooksBranch: 'notebooks-branch',
    assetsDataDir: 'data',
    assetsImageDir: 'image',
    nma: {},
  });
});

test('NMA_NOTEBOOKS_BRANCH: explicit env wins, blank is ignored', () => {
  const myst = 'nma:\n  notebooks:\n    branch: nb\n';
  assert.equal(loadSettings(myst, { NMA_NOTEBOOKS_BRANCH: 'x' }).notebooksBranch, 'x');
  assert.equal(loadSettings(myst, { NMA_NOTEBOOKS_BRANCH: ' ' }).notebooksBranch, 'nb');
  assert.equal(loadSettings('', {}).notebooksBranch, 'notebooks-branch');
});

test('settings are re-read when the working directory changes', () => {
  inCourse('project:\n  github: https://github.com/a/one\n', () => assert.equal(courseSettings().githubRepo, 'a/one'));
  inCourse('project:\n  github: https://github.com/b/two\n', () => assert.equal(courseSettings().githubRepo, 'b/two'));
});

test('readNmaConfig uses a YAML parser', () => {
  assert.equal(readNmaConfig('nma:\n  a:\n    b: "1"\n').a.b, '1');
  assert.deepEqual(readNmaConfig('nma:\n  feedback: {url: u, project: p}\n'), { feedback: { url: 'u', project: 'p' } });
  assert.deepEqual(readNmaConfig('nma: [1]\n'), {});
  assert.deepEqual(readNmaConfig('not: [valid'), {});
});

test('asset folder names default to data/image and can be overridden', () => {
  const d = loadSettings('project:\n  github: https://github.com/o/r\n');
  assert.deepEqual([d.assetsDataDir, d.assetsImageDir], ['data', 'image']);
  const c = loadSettings('nma:\n  assets:\n    data: files\n    image: pics/\n');
  assert.deepEqual([c.assetsDataDir, c.assetsImageDir], ['files', 'pics']);
});
