// Pure helpers for {nma-data}. Python twin: nma_kit.assets (parse_data_directive,
// validate_data_directives, asset_url); both are tested against
// tests/fixtures/assets/directives.json.

const ANY_FENCE = /^(`{3,}|~{3,}|:{3,})(.*)$/;
const DIRECTIVE = /^\{nma-data\}\s*(.*?)\s*$/;

/** Top-level {nma-data} directives: [{arg, paths, start, end}] (end -1 if unclosed). */
export function findDataDirectives(text) {
  const found = [];
  let openFence = null;
  let current = null;
  let currentFence = null;
  text.split(/\r?\n/).forEach((line, i) => {
    const match = ANY_FENCE.exec(line);
    if (current) {
      if (match && match[1][0] === currentFence[0] && match[1].length >= currentFence[1] && !match[2].trim()) {
        current.end = i;
        found.push(current);
        current = null;
      } else if (line.trim()) {
        current.paths.push(line.trim());
      }
      return;
    }
    if (!match) return;
    const marker = match[1];
    const info = match[2].trim();
    if (!openFence) {
      const directive = DIRECTIVE.exec(info);
      if (directive) {
        current = { arg: directive[1], paths: [], start: i, end: -1 };
        currentFence = [marker[0], marker.length];
      } else {
        openFence = [marker[0], marker.length];
      }
    } else if (marker[0] === openFence[0] && marker.length >= openFence[1] && !info) {
      openFence = null;
    }
  });
  if (current) found.push(current);
  return found;
}

/** Ordered, de-duplicated paths declared by every {nma-data} on a page. */
export function parseDataDirective(text) {
  return [...new Set(findDataDirectives(text).flatMap((d) => d.paths))];
}

function pathErrors(path, dataDir, imageDir, where) {
  const parts = path.split('/');
  if (path.startsWith('/') || parts.includes('..')) {
    return [`${where} declares '${path}', which must stay inside the day folder`];
  }
  if (!parts[0] || ![dataDir, imageDir].includes(parts[0])) {
    return [`${where} declares '${path}', which must start with ${dataDir}/ or ${imageDir}/`];
  }
  return [];
}

export function validateDataDirectives(text, dataDir, imageDir) {
  const errors = [];
  for (const d of findDataDirectives(text)) {
    const where = `line ${d.start + 1}: {nma-data}`;
    if (d.end === -1) errors.push(`${where} is never closed`);
    if (d.arg) errors.push(`${where} takes no inline argument; list files one per line in the body`);
    if (d.paths.length === 0) errors.push(`${where} is empty; list at least one file, e.g. ${dataDir}/data.npz`);
    for (const p of d.paths) errors.push(...pathErrors(p, dataDir, imageDir, where));
  }
  return errors;
}

/** Published raw.githubusercontent URL of a day's asset file. */
export function assetUrlFor(repo, branch, day, path) {
  const tail = ['notebooks', day, path].filter(Boolean).map((s) => s.replace(/^\/+|\/+$/g, '')).filter(Boolean).join('/');
  return `https://raw.githubusercontent.com/${repo}/${branch}/${tail}`;
}
