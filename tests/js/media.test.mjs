// {nma-slides} URLs (shared fixture with tests/python/test_media.py) and the directive's output.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

import plugin from '../../js/src/media/plugin.mjs';
import { osfSlidesEmbedUrl, slideUrl } from '../../js/src/media/model.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const FIXTURE = JSON.parse(readFileSync(join(here, '..', 'fixtures', 'media', 'slide_urls.json'), 'utf8'));
const start = process.cwd();

for (const c of FIXTURE.cdn) {
  test(`slideUrl: ${c.branch} ${c.day || '(top)'}/${c.path}`, () => {
    assert.equal(slideUrl(c.repo, c.branch, c.day, c.path), c.url);
  });
}

for (const c of FIXTURE.osf) {
  test(`osfSlidesEmbedUrl: ${c.id}`, () => {
    assert.equal(osfSlidesEmbedUrl(c.id), c.url);
  });
}

const slides = plugin.directives.find((d) => d.name === 'nma-slides');

function runSlides(options, arg, { myst = 'project:\n  github: https://github.com/o/r\n', page = 'tutorials/D/T.md' } = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'nma-slides-'));
  writeFileSync(join(dir, 'myst.yml'), myst);
  process.chdir(dir);
  const messages = [];
  const vfile = {
    path: join(dir, page),
    message: (text) => {
      const m = { text };
      messages.push(m);
      return m;
    },
  };
  try {
    return { out: slides.run({ arg, options, node: {} }, vfile), messages };
  } finally {
    process.chdir(start);
  }
}

const iframes = (node) => {
  const found = [];
  (function walk(n) {
    if (n.type === 'iframe') found.push(n);
    (n.children ?? []).forEach(walk);
  })(node);
  return found;
};
const links = (node) => {
  const found = [];
  (function walk(n) {
    if (n.type === 'link') found.push(n);
    (n.children ?? []).forEach(walk);
  })(node);
  return found;
};

test('nma-slides declares an optional title and the osf and path options', () => {
  assert.notEqual(slides.arg.required, true);
  assert.deepEqual(Object.keys(slides.options).sort(), ['osf', 'path']);
});

test('nma-slides with an OSF id shows the OSF renderer and a download link', () => {
  const { out } = runSlides({ osf: 'snv4m' });
  const [frame] = iframes(out[0]);
  assert.equal(frame.src, osfSlidesEmbedUrl('snv4m'));
  assert.equal(frame.title, 'Tutorial slides');
  assert.equal(links(out[0])[0].url, 'https://osf.io/download/snv4m/');
});

test('nma-slides with a path shows the published PDF and links to it', () => {
  const { out } = runSlides({ path: 'slides/a.pdf' }, 'Day 3');
  const url = 'https://cdn.jsdelivr.net/gh/o/r@notebooks-branch/notebooks/tutorials/D/slides/a.pdf';
  assert.deepEqual(iframes(out[0]).map((f) => f.src), [url]);
  assert.equal(iframes(out[0])[0].title, 'Day 3');
  assert.deepEqual(links(out[0]).map((l) => l.url), [url]);
  assert.equal(out[0].children[1].type, 'iframe');
});

test('nma-slides with both backends makes one tab each', () => {
  const { out } = runSlides({ osf: 'snv4m', path: 'slides/a.pdf' });
  const tabs = out[0].children[1];
  assert.equal(tabs.type, 'tabSet');
  assert.deepEqual(tabs.children.map((t) => t.title), ['OSF', 'PDF']);
  assert.equal(iframes(out[0]).length, 2);
});

test('nma-slides follows NMA_NOTEBOOKS_BRANCH (PR previews)', () => {
  process.env.NMA_NOTEBOOKS_BRANCH = 'notebooks-pr-7';
  try {
    const { out } = runSlides({ path: 'slides/a.pdf' });
    assert.match(iframes(out[0])[0].src, /@notebooks-pr-7\/notebooks\/tutorials\/D\/slides\/a\.pdf$/);
  } finally {
    delete process.env.NMA_NOTEBOOKS_BRANCH;
  }
});

test('nma-slides without a source is a fatal build error', () => {
  const { out, messages } = runSlides({});
  assert.deepEqual(out, []);
  assert.match(messages[0].text, /at least one of :osf:, :path:/);
  assert.equal(messages[0].fatal, true);
});

test('nma-slides :path: without a GitHub repo is a fatal build error', () => {
  const { out, messages } = runSlides({ path: 'slides/a.pdf' }, undefined, { myst: 'version: 1\n' });
  assert.deepEqual(out, []);
  assert.match(messages[0].text, /project\.github/);
  assert.equal(messages[0].fatal, true);
});
