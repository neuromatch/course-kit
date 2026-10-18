// {nma-feedback}: a 🙂/😐/🙁 widget that posts to datatops from the browser
// (assets/widget.mjs, rendered through MyST's anywidget node, so no
// kernel is needed). nma_kit.feedback builds the matching notebook cells.
//
// Settings come from the top-level `nma:` block in myst.yml:
//
//   nma:
//     feedback:
//       url: https://...
//       project: neuromatch_cn
//       user_key: ...
//
// readNmaConfig() lives in shared/config.mjs; `nma-kit check` validates the
// block (nma_kit.feedback.config_errors).

import { readFileSync } from 'node:fs';

import { assetUrl } from '../shared/assets.mjs';
import { scalar } from '../shared/config.mjs';
import { courseSettings } from '../shared/paths.mjs';
import { findPlaceholders, replaceNode } from '../shared/tree.mjs';

const FEEDBACK_PLACEHOLDER = 'nmaFeedbackRef';
const FEEDBACK_ESM = assetUrl('feedback/widget.mjs');
const NAME_RE = /^[A-Za-z0-9_]+$/;
const FEEDBACK_KEYS = ['url', 'project', 'user_key'];

function feedbackConfig() {
  const config = courseSettings().nma.feedback ?? {};
  return FEEDBACK_KEYS.every((k) => config[k]) ? config : null;
}

/** W2D1_Tutorial1 -> W2D1_T1; anything else is used as is. */
export function defaultPrefix(stem) {
  const match = stem.match(/^(W\d+D\d+)_Tutorial(\d+)$/);
  return match ? `${match[1]}_T${match[2]}` : stem;
}

/** `feedback_prefix` from the page frontmatter, else derived from the filename. */
export function pagePrefix(text, stem) {
  if (text.startsWith('---')) {
    const end = text.indexOf('\n---', 3);
    const frontmatter = end === -1 ? '' : text.slice(3, end);
    const match = frontmatter.match(/^feedback_prefix:\s*(.*?)\s*$/m);
    const value = match ? scalar(match[1]) : null;
    if (value !== null) return value;
  }
  return defaultPrefix(stem);
}

const nmaFeedback = {
  name: 'nma-feedback',
  doc: 'Feedback widget (🙂/😐/🙁) for one section; posts to datatops.',
  arg: { type: String, required: true, doc: 'Section name, e.g. Linear_Dynamical_Systems_Video.' },
  run(data) {
    return [{ type: FEEDBACK_PLACEHOLDER, section: data.arg ?? '', position: data.node.position }];
  },
};

const feedbackWidgets = {
  name: 'nma-feedback-widgets',
  doc: 'Turn nma-feedback placeholders into anywidget nodes with the datatops settings.',
  stage: 'document',
  plugin: () => (tree, vfile) => {
    const found = findPlaceholders(tree, FEEDBACK_PLACEHOLDER);
    if (found.length === 0) return;

    const config = feedbackConfig();
    let source = '';
    try {
      source = readFileSync(vfile.path, 'utf8');
    } catch {
      // no frontmatter prefix then
    }
    const stem = (vfile.path ?? '').split(/[\\/]/).pop().replace(/\.[^.]+$/, '');
    const prefix = pagePrefix(source, stem);
    const seen = new Set();

    found.forEach(([node, topLevel], n) => {
      const fatal = (message) => {
        const msg = vfile.message(message, node, 'nma-plugin');
        msg.fatal = true;
        replaceNode(node, { type: 'div', children: [] });
      };
      const section = node.section;
      if (!topLevel) return fatal('nma-feedback must be at the top level of the page, not inside another directive');
      if (!NAME_RE.test(section)) {
        return fatal(`nma-feedback section name must use only letters, digits and underscores (got "${section}")`);
      }
      if (seen.has(section)) return fatal(`nma-feedback section ${section} is used twice on this page`);
      seen.add(section);
      if (!NAME_RE.test(prefix)) {
        return fatal(`feedback_prefix must use only letters, digits and underscores (got "${prefix}")`);
      }
      if (!config) return fatal('nma-feedback needs nma.feedback.{url,project,user_key} in myst.yml');
      replaceNode(node, {
        type: 'anywidget',
        esm: FEEDBACK_ESM,
        model: {
          section_id: `${prefix}_${section}`,
          url: config.url,
          project: config.project,
          user_key: config.user_key,
        },
        class: 'nma-feedback',
        id: `nma-feedback-${n + 1}`,
      });
    });
  },
};

export default {
  name: 'Neuromatch feedback',
  directives: [nmaFeedback],
  transforms: [feedbackWidgets],
};
