// Run with: npm test (in js/)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { readNmaConfig } from '../../js/src/shared/config.mjs';
import { isScrolly } from '../../js/src/shared/frontmatter.mjs';
import { notebookUrls } from '../../js/src/shared/paths.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const kit = join(here, '..', '..');
const fixtures = join(kit, 'fixtures', 'nma_config');

// The same fixtures are checked against PyYAML in tests/python/test_feedback.py.
for (const name of readdirSync(fixtures).filter((f) => f.endsWith('.yml'))) {
  test(`readNmaConfig matches ${name}`, () => {
    const text = readFileSync(join(fixtures, name), 'utf8');
    const expected = JSON.parse(readFileSync(join(fixtures, name.replace(/\.yml$/, '.json')), 'utf8'));
    assert.deepEqual(readNmaConfig(text), expected);
  });
}

test("the example course's myst.yml has complete feedback settings", () => {
  const text = readFileSync(join(kit, 'example-course', 'myst.yml'), 'utf8');
  const { feedback } = readNmaConfig(text);
  for (const key of ['url', 'project', 'user_key']) assert.ok(feedback?.[key], key);
});

test('isScrolly is re-exported by the scrolly plugin', async () => {
  const scrolly = await import('../../js/src/scrolly/plugin.mjs');
  assert.equal(scrolly.isScrolly, isScrolly);
});

test('notebookUrls matches make_badge_html', () => {
  const course = join(kit, 'example-course');
  process.chdir(course);
  const { colabUrl, kaggleUrl } = notebookUrls(join(course, 'tutorials/W2D1_Examples/W2D1_Tutorial1.md'));
  assert.equal(
    colabUrl,
    'https://colab.research.google.com/github/neuromatch/course-kit/blob/notebooks-branch/notebooks/W2D1_Examples/W2D1_Tutorial1.ipynb',
  );
  assert.ok(
    kaggleUrl.endsWith('raw.githubusercontent.com/neuromatch/course-kit/notebooks-branch/notebooks/W2D1_Examples/W2D1_Tutorial1.ipynb'),
  );
});
