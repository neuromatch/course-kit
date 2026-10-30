// Course settings from the course's myst.yml.
// Twin in Python: nma_kit.config (load_settings, read_nma_block); shared
// fixtures in tests/fixtures/config/ and tests/fixtures/nma_config/.
//
//   nma:
//     paths:
//       tutorials: tutorials        # where the course's tutorial .md pages live
//       projects: projects          # where the course's project .md pages live
//     notebooks:
//       branch: notebooks-branch    # where generated notebooks are published
//                                   # (the env var NMA_NOTEBOOKS_BRANCH overrides it: PR previews)
//     assets:
//       data: data                  # folder (in each day folder) for data files
//       image: image                # folder (in each day folder) for images
//       slides: slides              # folder (in each day folder) for slide PDFs

import { parse } from 'yaml';

import {
  DEFAULT_DATA_DIR,
  DEFAULT_IMAGE_DIR,
  DEFAULT_NOTEBOOKS_BRANCH,
  DEFAULT_PROJECTS_DIR,
  DEFAULT_SLIDES_DIR,
  DEFAULT_TUTORIALS_DIR,
  NOTEBOOKS_BRANCH_ENV,
} from './constants.mjs';

const GITHUB_RE = /github\.com\/([^\s'"]+?)\/?$/;

const isMapping = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

function parseYaml(text) {
  try {
    const data = parse(text);
    return isMapping(data) ? data : {};
  } catch {
    return {};
  }
}

/** The top-level `nma:` block of myst.yml ({} if absent or not a mapping). */
export function readNmaConfig(text) {
  const block = parseYaml(text).nma;
  return isMapping(block) ? block : {};
}

function setting(nma, section, key, fallback) {
  const value = isMapping(nma[section]) ? nma[section][key] : undefined;
  return typeof value === 'string' && value.trim() ? value : fallback;
}

/** {githubRepo, tutorialsDir, projectsDir, notebooksBranch, assetsDataDir, assetsImageDir, assetsSlidesDir, nma} from myst.yml text. */
export function loadSettings(text, env = process.env) {
  const data = parseYaml(text);
  const nma = readNmaConfig(text);
  const url = isMapping(data.project) ? data.project.github : undefined;
  const match = typeof url === 'string' ? url.trim().match(GITHUB_RE) : null;
  return {
    githubRepo: match ? match[1] : null,
    tutorialsDir: setting(nma, 'paths', 'tutorials', DEFAULT_TUTORIALS_DIR).replace(/^\/+|\/+$/g, ''),
    projectsDir: setting(nma, 'paths', 'projects', DEFAULT_PROJECTS_DIR).replace(/^\/+|\/+$/g, ''),
    notebooksBranch: (env[NOTEBOOKS_BRANCH_ENV] || '').trim() || setting(nma, 'notebooks', 'branch', DEFAULT_NOTEBOOKS_BRANCH),
    assetsDataDir: setting(nma, 'assets', 'data', DEFAULT_DATA_DIR).replace(/^\/+|\/+$/g, ''),
    assetsImageDir: setting(nma, 'assets', 'image', DEFAULT_IMAGE_DIR).replace(/^\/+|\/+$/g, ''),
    assetsSlidesDir: setting(nma, 'assets', 'slides', DEFAULT_SLIDES_DIR).replace(/^\/+|\/+$/g, ''),
    nma,
  };
}

/** The value of a frontmatter `key: value` line (quotes and trailing comment removed), or null. */
export function scalar(raw) {
  raw = raw.trim();
  if (!raw || raw.startsWith('#')) return null;
  if (raw[0] === '"' || raw[0] === "'") {
    const end = raw.indexOf(raw[0], 1);
    return end === -1 ? raw : raw.slice(1, end);
  }
  return raw.replace(/\s+#.*$/, '');
}
