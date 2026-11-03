"""Constants shared with the JavaScript plugin, read from constants.json.

The JS side imports the same file (js/src/shared/constants.mjs), so a value
cannot drift between the two languages.
"""

import json
from pathlib import Path

_DATA = json.loads((Path(__file__).with_name("constants.json")).read_text(encoding="utf-8"))

RESERVED_CONTENT_DIRS: tuple[str, ...] = tuple(_DATA["reserved_content_dirs"])
DEFAULT_NOTEBOOKS_BRANCH: str = _DATA["default_notebooks_branch"]
NOTEBOOKS_BRANCH_ENV: str = _DATA["notebooks_branch_env"]
AUDIENCE_ENV: str = _DATA["audience_env"]
AUDIENCES: tuple[str, ...] = tuple(_DATA["audiences"])
DEFAULT_AUDIENCE: str = _DATA["default_audience"]
DEFAULT_DATA_DIR: str = _DATA["default_data_dir"]
DEFAULT_IMAGE_DIR: str = _DATA["default_image_dir"]
DEFAULT_SLIDES_DIR: str = _DATA["default_slides_dir"]
MAX_EMBED_BYTES: int = _DATA["max_embed_bytes"]
NO_FALLBACK_MARKER: str = _DATA["no_fallback_marker"]
