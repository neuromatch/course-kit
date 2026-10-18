// Frontmatter rules shared by the plugins.

/** True if the frontmatter has a plain top-level `layout: scrolly` line (twin: nma_kit.scrolly.is_scrolly). */
export function isScrolly(text) {
  if (!text.startsWith('---')) return false;
  const end = text.indexOf('\n---', 3);
  if (end === -1) return false;
  return /^layout:\s*(['"]?)scrolly\1\s*(#.*)?$/m.test(text.slice(3, end));
}
