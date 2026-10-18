// Course settings (myst.yml) and page paths. The same cases run in Python
// (tests/python/test_config.py) against fixtures/config/settings.json.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { loadSettings, readNmaConfig } from '../../js/src/shared/config.mjs';
import { pageLocation, notebookUrls, solutionUrl, courseSettings } from '../../js/src/shared/paths.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const { cases } = JSON.parse(readFileSync(join(here, '..', '..', 'fixtures', 'config', 'settings.json'), 'utf8'));
const start = process.cwd();

function inCourse(myst, fn) {
  const dir = mkdtempSync(join(tmpdir(), 'nma-course-'));
  writeFileSync(join(dir, 'myst.yml'), myst);
  process.chdir(dir);
  try {
    return fn(dir);
  } finally {
    process.chdir(start);
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
      assert.deepEqual(location, { relDir: c.expect.relDir, stem: c.expect.stem });
      assert.deepEqual(notebookUrls(page), { colabUrl: c.expect.colab, kaggleUrl: c.expect.kaggle });
      const s = courseSettings();
      assert.equal(solutionUrl(s.githubRepo, location.relDir, `${location.stem}_Solution_1.py`, s.notebooksBranch), c.expect.solution1);
    });
  });
}

test('defaults without an nma block', () => {
  assert.deepEqual(loadSettings('project:\n  github: https://github.com/o/r\n'), {
    githubRepo: 'o/r',
    tutorialsDir: 'tutorials',
    notebooksBranch: 'notebooks-branch',
    nma: {},
  });
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
