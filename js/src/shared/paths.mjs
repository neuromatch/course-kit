// Where a course page and its generated files live.
// Twins in Python: nma_kit.config.page_location, nma_kit.convert.make_badge_html,
// nma_kit.solutions.solution_url; shared fixtures in fixtures/config/.

import { readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

import { loadSettings } from './config.mjs';

// MyST runs plugins from the course root; tests change directory between
// courses, so the settings are cached per working directory.
const cache = new Map();

/** Settings of the course in the current working directory. */
export function courseSettings() {
  const cwd = process.cwd();
  if (!cache.has(cwd)) {
    let text = '';
    try {
      text = readFileSync(join(cwd, 'myst.yml'), 'utf8');
    } catch {
      // no myst.yml: defaults, no repo
    }
    cache.set(cwd, loadSettings(text));
  }
  return cache.get(cwd);
}

export const githubRepo = () => courseSettings().githubRepo;

// tutorials/W2D1_Examples/W2D1_Tutorial1.md -> { relDir: 'W2D1_Examples', stem: 'W2D1_Tutorial1' }
export function pageLocation(filePath) {
  const prefix = `${courseSettings().tutorialsDir}/`;
  const rel = relative(process.cwd(), filePath).split(sep).join('/');
  if (!rel.startsWith(prefix)) return null;
  const parts = rel.slice(prefix.length).split('/');
  const stem = parts.pop().replace(/\.[^.]+$/, '');
  return { relDir: parts.join('/'), stem };
}

/** Colab and Kaggle URLs of a page's generated notebook (same as make_badge_html). */
export function notebookUrls(filePath) {
  const { githubRepo: repo, notebooksBranch: branch } = courseSettings();
  const location = pageLocation(filePath);
  if (!repo || !location) return { colabUrl: 'https://colab.research.google.com/', kaggleUrl: 'https://www.kaggle.com/' };
  const path = ['notebooks', location.relDir, `${location.stem}.ipynb`].filter(Boolean).join('/');
  return {
    colabUrl: `https://colab.research.google.com/github/${repo}/blob/${branch}/${path}`,
    kaggleUrl: `https://kaggle.com/kernels/welcome?src=https://raw.githubusercontent.com/${repo}/${branch}/${path}`,
  };
}

/** GitHub URL of a solution/explanation file on the notebooks branch. */
export function solutionUrl(repo, relDir, filename, branch) {
  const path = ['notebooks', relDir, 'solutions', filename].filter(Boolean).join('/');
  return `https://github.com/${repo}/blob/${branch}/${path}`;
}
