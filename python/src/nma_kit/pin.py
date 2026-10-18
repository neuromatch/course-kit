"""Pin the course kit's CDN URLs in a course's myst.yml to one exact version.

Courses commit an alias such as `.../course-kit@0.1/dist/nma.yml` for local
previews. On CI, `nma-kit prepare-site` rewrites it to the CLI's own version,
so the plugin, its assets and the CLI always come from the same release
(jsDelivr caches alias URLs for days; exact versions never change).
"""

import re

KIT_URL_RE = re.compile(r"(https://cdn\.jsdelivr\.net/npm/@neuromatch/course-kit@)[^/\s'\"]+(/)")


def pin_kit_url(myst_text: str, version: str) -> str:
    """Replace the version of every course-kit CDN URL in myst_text with `version`."""
    return KIT_URL_RE.sub(lambda m: f"{m.group(1)}{version}{m.group(2)}", myst_text)
