// Pure helpers for editable cells (no imports: used by Node tests, the MyST
// plugin and the browser bundles).

export const NO_FALLBACK_MARKER = 'nma-no-fallback'; // sync: nma_kit.solutions
export const UNFINISHED_RE = /^[ \t]*raise NotImplementedError/m; // sync: nma_kit.solutions

export const isExercise = (code) => UNFINISHED_RE.test(code);

/** Append the marker as a trailing comment line (doesn't shift tracebacks). */
export const withNoFallback = (src) =>
  src.includes(NO_FALLBACK_MARKER) ? src : `${src.replace(/\s*$/, '')}\n# ${NO_FALLBACK_MARKER}\n`;

/** edit | collapsed | output | hidden, from a code cell's tags. */
export function modeOf(tags) {
  if (tags.includes('remove-cell')) return 'hidden';
  if (tags.includes('remove-input')) return 'output';
  if (tags.includes('hide-input') || tags.includes('hide-cell')) return 'collapsed';
  return 'edit';
}

/** The frontmatter text (between the first two `---` lines), or ''. */
export function frontmatterOf(text) {
  if (!text.startsWith('---')) return '';
  const end = text.indexOf('\n---', 3);
  return end === -1 ? '' : text.slice(3, end);
}

const RUNTIME_RE = /^runtime:\s*(['"]?)([A-Za-z]+)\1\s*(#.*)?$/m; // sync: nma_kit.cells

/** 'browser' (default) or 'colab' (or the raw invalid value). */
export function runtimeOf(text) {
  const m = RUNTIME_RE.exec(frontmatterOf(text));
  return m ? m[2] : 'browser';
}

export const thebeId = (index) => `nma-cell-${index}`;

/** thebe's scripts sit at the site root; the bundles are served from <base>/build/. */
export function thebeScriptUrls(bundleUrl) {
  return {
    core: new URL('../thebe-core.min.js', bundleUrl).href,
    lite: new URL('../thebe-lite.min.js', bundleUrl).href,
  };
}

/** Status-line copy for a runtime event. */
export function statusText(e) {
  if (e.kernel === 'starting') return e.message ?? '';
  if (e.state === 'running') return 'Running…';
  if (e.state === 'error') return `[${e.count ?? ' '}] ✗ ${e.error?.ename ?? 'Error'}`;
  if (e.state === 'done') return `[${e.count}] ✓`;
  return '';
}
