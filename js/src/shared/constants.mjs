// Constants shared with the Python CLI. The values live in
// python/src/nma_kit/constants.json (read by nma_kit/constants.py); esbuild
// inlines the file into the bundle, so the two languages cannot drift.

import data from '../../../python/src/nma_kit/constants.json' with { type: 'json' };

export const DEFAULT_TUTORIALS_DIR = data.default_tutorials_dir;
export const DEFAULT_PROJECTS_DIR = data.default_projects_dir;
export const DEFAULT_NOTEBOOKS_BRANCH = data.default_notebooks_branch;
export const NOTEBOOKS_BRANCH_ENV = data.notebooks_branch_env;
export const DEFAULT_DATA_DIR = data.default_data_dir;
export const DEFAULT_IMAGE_DIR = data.default_image_dir;
export const DEFAULT_SLIDES_DIR = data.default_slides_dir;
export const MAX_EMBED_BYTES = data.max_embed_bytes;
export const NO_FALLBACK_MARKER = data.no_fallback_marker;
