// The course kit's MyST plugin: every feature plugin, merged into one plugin
// object. esbuild bundles this file into dist/nma.mjs (MyST loads a remote
// plugin as a single file). Transform order matters: solution links and
// feedback widgets first, then assets (embeds declared files for cells), then scrolly layout, then editable cells.

import media from './media/plugin.mjs';
import solutions from './solutions/plugin.mjs';
import feedback from './feedback/plugin.mjs';
import assets from './assets/plugin.mjs';
import scrolly from './scrolly/plugin.mjs';
import cells from './cells/plugin.mjs';

/** Every feature plugin, in transform order (see the comment at the top of this file). */
export const PLUGINS = [media, solutions, feedback, assets, scrolly, cells];

/** The merged MyST plugin: the directives, roles and transforms of every feature. */
export default {
  name: 'Neuromatch course kit',
  directives: PLUGINS.flatMap((p) => p.directives ?? []),
  roles: PLUGINS.flatMap((p) => p.roles ?? []),
  transforms: PLUGINS.flatMap((p) => p.transforms ?? []),
};
