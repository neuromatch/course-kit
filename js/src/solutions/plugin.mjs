// {nma-solution} / {nma-explanation}: render as a "Click for ..." link to the
// solution file that nma_kit.solutions writes to the notebooks branch.
// The solution text itself is never put on the page.
//
// The directives only emit a placeholder. The transform below numbers the
// placeholders in document order and builds the links. The file naming and URL
// rules must stay in sync with nma_kit.solutions.

import { courseSettings, pageLocation, solutionUrl } from '../shared/paths.mjs';
import { findPlaceholders, replaceNode, text } from '../shared/tree.mjs';

const SOLUTION_KINDS = {
  'nma-solution': { label: 'Click for solution', file: (stem, n) => `${stem}_Solution_${n}.py` },
  'nma-explanation': {
    label: 'Click for explanation',
    file: (stem, n) => `${stem}_Explanation_${n}.md`,
  },
};
const PLACEHOLDER = 'nmaSolutionRef';

const solutionDirective = (name, doc) => ({
  name,
  doc,
  body: { type: String, required: true, doc: 'Hidden on the site; see nma_kit.solutions.' },
  run(data) {
    return [{ type: PLACEHOLDER, kind: name, position: data.node.position }];
  },
});

const solutionLinks = {
  name: 'nma-solution-links',
  doc: 'Turn nma-solution/nma-explanation placeholders into links to the solution files.',
  stage: 'document',
  plugin: () => (tree, vfile) => {
    const found = findPlaceholders(tree, PLACEHOLDER);
    if (found.length === 0) return;

    const { githubRepo: repo, notebooksBranch: branch } = courseSettings();
    const location = pageLocation(vfile.path);
    const counters = {};
    for (const [node, topLevel] of found) {
      const replaceWith = (children, extra = {}) =>
        replaceNode(node, { type: 'div', children, ...extra });
      const kind = node.kind;
      const fatal = (message) => {
        const msg = vfile.message(message, node, 'nma-plugin');
        msg.fatal = true;
        replaceWith([]);
      };
      if (!topLevel) {
        fatal(`${kind} must be at the top level of the page, not inside another directive`);
        continue;
      }
      if (!repo) {
        fatal(`${kind} needs project.github (a github.com URL) in myst.yml`);
        continue;
      }
      if (!location) {
        fatal(`${kind} is only supported in pages under ${courseSettings().tutorialsDir}/`);
        continue;
      }
      counters[kind] = (counters[kind] ?? 0) + 1;
      const { label, file } = SOLUTION_KINDS[kind];
      const url = solutionUrl(repo, location.relDir, file(location.stem, counters[kind]), branch);
      replaceWith(
        [
          {
            type: 'paragraph',
            children: [{ type: 'link', url, children: [{ type: 'emphasis', children: [text(label)] }] }],
          },
        ],
        { class: 'nma-solution-link' },
      );
    }
  },
};

export default {
  name: 'Neuromatch solutions',
  directives: [
    solutionDirective('nma-solution', 'Exercise solution, shown as a link to the solution file.'),
    solutionDirective('nma-explanation', 'Discussion answer, shown as a link to the explanation file.'),
  ],
  transforms: [solutionLinks],
};
