// Course settings from the course's myst.yml.
// Twin in Python: nma_kit.config (load_settings, read_nma_block); shared
// fixtures in tests/fixtures/config/ and tests/fixtures/nma_config/.
//
//   nma:
//     content:                      # content roots: folders (inside the course) holding pages; required
//       - tutorials                 # shorthand: name = path
//       - {name: guide, path: docs/guide}   # name = first folder under notebooks/
//     notebooks:
//       branch: notebooks-branch    # where generated notebooks are published
//                                   # (the env var NMA_NOTEBOOKS_BRANCH overrides it: PR previews)
//     assets:
//       data: data                  # folder (in each day folder) for data files
//       image: images             # folder (in each day folder) for images
//       slides: slides              # folder (in each day folder) for slide PDFs
//
// Environment: NMA_NOTEBOOKS_BRANCH (above) and NMA_AUDIENCE ('student', the
// default, or 'instructor'; there is no myst.yml key).

import { parse } from 'yaml';

import {
  AUDIENCE_ENV,
  DEFAULT_AUDIENCE,
  DEFAULT_DATA_DIR,
  DEFAULT_IMAGE_DIR,
  DEFAULT_NOTEBOOKS_BRANCH,
  DEFAULT_SLIDES_DIR,
  NOTEBOOKS_BRANCH_ENV,
  RESERVED_CONTENT_DIRS,
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

const NAME_RE = /^[A-Za-z0-9_-]+(\/[A-Za-z0-9_-]+)*$/;

/** Why `path` cannot be a content root folder (null if it can): a folder strictly inside the course. Twin of content_path_problem. */
export function contentPathProblem(path) {
  if (!path) return 'is empty';
  if (path.startsWith('/') || /^[A-Za-z]:/.test(path)) return 'must be relative to the course root';
  const parts = path.split('/');
  if (parts.includes('.') || parts.includes('..')) return "must be a folder inside the course (no '.' or '..')";
  if (parts[0].startsWith('.') || RESERVED_CONTENT_DIRS.includes(parts[0])) {
    return `cannot be under ${parts[0]}/ (the kit or the build owns it)`;
  }
  return null;
}

function contentEntry(item) {
  let path;
  let name;
  if (typeof item === 'string') path = item;
  else if (isMapping(item)) ({ path, name } = item);
  else return null;
  if (typeof path !== 'string' || (name != null && typeof name !== 'string')) return null;
  path = path.trim().replace(/^(\.\/)+|\/+$/g, '');
  name = (name || path).trim().replace(/^\/+|\/+$/g, '');
  return [name, path];
}

/** The valid `nma.content` entries as [name, path] (malformed ones are skipped; `nma-kit check` reports them). Twin of content_roots_from. */
export function contentRootsFrom(nma) {
  if (!Array.isArray(nma.content)) return [];
  return nma.content.map(contentEntry).filter((e) => e && !contentPathProblem(e[1]) && NAME_RE.test(e[0]));
}

/** {githubRepo, contentRoots, notebooksBranch, assetsDataDir, assetsImageDir, assetsSlidesDir, audience, nma} from myst.yml text. */
export function loadSettings(text, env = process.env) {
  const data = parseYaml(text);
  const nma = readNmaConfig(text);
  const url = isMapping(data.project) ? data.project.github : undefined;
  const match = typeof url === 'string' ? url.trim().match(GITHUB_RE) : null;
  return {
    githubRepo: match ? match[1] : null,
    contentRoots: contentRootsFrom(nma),
    notebooksBranch: (env[NOTEBOOKS_BRANCH_ENV] || '').trim() || setting(nma, 'notebooks', 'branch', DEFAULT_NOTEBOOKS_BRANCH),
    assetsDataDir: setting(nma, 'assets', 'data', DEFAULT_DATA_DIR).replace(/^\/+|\/+$/g, ''),
    assetsImageDir: setting(nma, 'assets', 'image', DEFAULT_IMAGE_DIR).replace(/^\/+|\/+$/g, ''),
    assetsSlidesDir: setting(nma, 'assets', 'slides', DEFAULT_SLIDES_DIR).replace(/^\/+|\/+$/g, ''),
    audience: (env[AUDIENCE_ENV] || '').trim() || DEFAULT_AUDIENCE,
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
