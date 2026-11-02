// {nma-solution} / {nma-explanation}: render as a "Click for ..." link to the
// solution file that nma_kit.solutions writes to the notebooks branch.
// The student build never puts the solution text on the page. The instructor
// build (NMA_AUDIENCE=instructor) shows each one inline, as a collapsed dropdown.
//
// The directives only emit a placeholder. The transform below numbers the
// placeholders in document order and builds the links. The file naming and URL
// rules must stay in sync with nma_kit.solutions.

import { contentRoots, courseSettings, notebookDir, pageLocation, solutionUrl } from '../shared/paths.mjs';
import { findPlaceholders, replaceNode, text } from '../shared/tree.mjs';

const SOLUTION_KINDS = {
  'nma-solution': { label: 'Click for solution', title: 'Solution', file: (stem, n) => `${stem}_Solution_${n}.py` },
  'nma-explanation': {
    label: 'Click for explanation',
    title: 'Explanation',
    file: (stem, n) => `${stem}_Explanation_${n}.md`,
  },
};
const PLACEHOLDER = 'nmaSolutionRef';

const isInstructor = () => courseSettings().audience === 'instructor';

const solutionDirective = (name, doc) => ({
  name,
  doc,
  body: {
    type: String,
    required: true,
    doc: 'Hidden on the student site (a link to the solution file); inline on the instructor site. See nma_kit.solutions.',
  },
  run(data, _vfile, ctx) {
    const placeholder = { type: PLACEHOLDER, kind: name, position: data.node.position };
    // Only the instructor build needs the body: parse it then, never for students.
    if (isInstructor()) placeholder.children = ctx.parseMyst(data.body).children;
    return [placeholder];
  },
});

/** Instructor build: the solution/explanation inline, in a collapsed dropdown. */
const inlineSolution = (kind, body) => ({
  type: 'admonition',
  kind: 'dropdown',
  class: 'nma-solution-inline dropdown',
  children: [{ type: 'admonitionTitle', children: [text(SOLUTION_KINDS[kind].title)] }, ...body],
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
        fatal(`${kind} is only supported in pages under ${contentRoots().map(([, dir]) => `${dir}/`).join(' or ')}`);
        continue;
      }
      counters[kind] = (counters[kind] ?? 0) + 1;
      if (isInstructor()) {
        replaceNode(node, inlineSolution(kind, node.children ?? []));
        continue;
      }
      const { label, file } = SOLUTION_KINDS[kind];
      const url = solutionUrl(repo, notebookDir(location), file(location.stem, counters[kind]), branch);
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

/** The solutions plugin: the two directives and the transform that numbers them and links the files. */
export default {
  name: 'Neuromatch solutions',
  directives: [
    solutionDirective('nma-solution', 'Exercise solution, shown as a link to the solution file.'),
    solutionDirective('nma-explanation', 'Discussion answer, shown as a link to the explanation file.'),
  ],
  transforms: [solutionLinks],
};
