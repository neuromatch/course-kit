// Course settings from the course's myst.yml.
// Twin in Python: nma_kit.config (load_settings, read_nma_block); shared
// fixtures in fixtures/config/ and fixtures/nma_config/.
//
//   nma:
//     paths:
//       tutorials: tutorials        # where the course's .md pages live
//     notebooks:
//       branch: notebooks-branch    # where generated notebooks are published

import { parse } from 'yaml';

export const DEFAULT_TUTORIALS_DIR = 'tutorials';
export const DEFAULT_NOTEBOOKS_BRANCH = 'notebooks-branch';
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

/** {githubRepo, tutorialsDir, notebooksBranch, nma} from myst.yml text. */
export function loadSettings(text) {
  const data = parseYaml(text);
  const nma = readNmaConfig(text);
  const url = isMapping(data.project) ? data.project.github : undefined;
  const match = typeof url === 'string' ? url.trim().match(GITHUB_RE) : null;
  return {
    githubRepo: match ? match[1] : null,
    tutorialsDir: setting(nma, 'paths', 'tutorials', DEFAULT_TUTORIALS_DIR).replace(/^\/+|\/+$/g, ''),
    notebooksBranch: setting(nma, 'notebooks', 'branch', DEFAULT_NOTEBOOKS_BRANCH),
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
