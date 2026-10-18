"""Editable cells: the `runtime:` frontmatter key (Python side).

`runtime_of` has a JavaScript twin, `runtimeOf` in js/src/cells/src/model.mjs.
Both are tested against fixtures/cells/runtime.json.
"""

import re

from nma_kit import scrolly as nma_scrolly

RUNTIMES = ("browser", "colab")
RUNTIME_RE = re.compile(r"""^runtime:\s*(['"]?)([A-Za-z]+)\1\s*(#.*)?$""", re.M)


def runtime_of(text: str) -> str:
    """'browser' (default) or 'colab' (or the raw invalid value, for validate())."""
    m = RUNTIME_RE.search(nma_scrolly.frontmatter_text(text))
    return m.group(2) if m else "browser"


def validate(text: str) -> list[str]:
    errors = []
    runtime = runtime_of(text)
    if runtime not in RUNTIMES:
        errors.append(f"runtime: {runtime!r} must be one of {', '.join(RUNTIMES)}")
    if runtime == "colab" and nma_scrolly.is_scrolly(text):
        errors.append("runtime: colab can't be combined with layout: scrolly")
    return errors
