// {nma-instructor}: teaching notes for the instructor site.
//
// In the instructor build (NMA_AUDIENCE=instructor) the body renders as an
// "Instructor notes" admonition. In the student build the directive renders
// nothing and its body is never parsed. nma_kit.instructor (Python) validates
// the directive and strips it from the generated notebooks.

import { courseSettings } from '../shared/paths.mjs';
import { text } from '../shared/tree.mjs';

const instructorDirective = {
  name: 'nma-instructor',
  doc: 'Teaching notes: shown only on the instructor site, never in the student site or the notebooks.',
  body: { type: String, required: true, doc: 'Markdown, shown in an "Instructor notes" box.' },
  run(data, _vfile, ctx) {
    if (courseSettings().audience !== 'instructor') return [];
    return [
      {
        type: 'admonition',
        kind: 'note',
        class: 'nma-instructor',
        children: [{ type: 'admonitionTitle', children: [text('Instructor notes')] }, ...ctx.parseMyst(data.body).children],
      },
    ];
  },
};

/** The instructor plugin: the {nma-instructor} directive. */
export default {
  name: 'Neuromatch instructor notes',
  directives: [instructorDirective],
};
