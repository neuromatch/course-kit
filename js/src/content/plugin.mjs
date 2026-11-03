// Content roots: stops the build when the course declares none.
//
// Every kit feature locates pages through `nma.content` in myst.yml (there are no
// defaults), so a course without it would build with no notebooks, badges or solution
// links and nothing to say why. nma_kit.config.content_errors explains the setting
// to `nma-kit check`; this makes the MyST build fail with the same advice.

import { contentRoots } from '../shared/paths.mjs';

const requireContent = {
  name: 'nma-require-content',
  doc: 'Fail the build when myst.yml has no nma.content.',
  stage: 'document',
  plugin: () => (_tree, vfile) => {
    if (contentRoots().length > 0) return;
    const msg = vfile.message(
      'myst.yml has no nma.content: list the folders that hold your pages, for example `nma: {content: [tutorials, projects]}`',
      undefined,
      'nma-plugin',
    );
    msg.fatal = true;
  },
};

/** The content plugin: the check that nma.content is declared. */
export default {
  name: 'Neuromatch content roots',
  transforms: [requireContent],
};
