"""
Parse {nma-data} directives and resolve asset (data / image) references.

A course keeps shared files in a day folder's `data/` and `image/` folders and
declares, per tutorial, which files it needs:

    :::{nma-data}
    data/spikes.npz
    data/lfp.npz
    image/atlas.png
    :::

That declaration is the single manifest for the tutorial. It drives:
  - the hidden "Download data" cell injected into generated Colab/Kaggle
    notebooks (nma_kit.convert),
  - copying the files into the published notebooks tree,
  - and, via the JS twin (js/src/assets/), embedding the bytes into the page so
    browser editable cells can pre-fill the Pyodide filesystem.

The website renders the same directive with js/src/assets/plugin.mjs. The
directive parser and the asset URL template here and in that file must stay in
sync; both are tested against tests/fixtures/assets/directives.json.
"""

import re
from dataclasses import dataclass, field

ANY_FENCE_RE = re.compile(r"^(`{3,}|~{3,}|:{3,})(.*)$")
DIRECTIVE_RE = re.compile(r"^\{(nma-data)\}\s*(.*?)\s*$")


@dataclass
class DataDirective:
    arg: str                 # inline argument (always an error; the directive takes none)
    paths: list              # declared file paths (non-blank body lines)
    start: int               # 0-based line index of the opening fence
    end: int = -1            # 0-based line index of the closing fence; -1 if unclosed


def find_data_directives(text: str) -> list[DataDirective]:
    """
    Return the top-level {nma-data} directives in `text`, in order.

    Anything inside another fence (```, ~~~ or :::) is skipped, so a syntax
    example on a documentation page is not treated as a real directive.
    """
    found = []
    open_fence = None   # (char, length) of a non-data fence we're inside
    current = None
    current_fence = None

    for i, line in enumerate(text.splitlines()):
        match = ANY_FENCE_RE.match(line)

        if current is not None:
            if (match and match.group(1)[0] == current_fence[0]
                    and len(match.group(1)) >= current_fence[1]
                    and not match.group(2).strip()):
                current.end = i
                found.append(current)
                current = None
                continue
            if line.strip():
                current.paths.append(line.strip())
            continue

        if not match:
            continue
        marker, info = match.group(1), match.group(2).strip()
        if open_fence is None:
            directive = DIRECTIVE_RE.match(info)
            if directive:
                current = DataDirective(directive.group(2), [], i)
                current_fence = (marker[0], len(marker))
            else:
                open_fence = (marker[0], len(marker))
        elif marker[0] == open_fence[0] and len(marker) >= open_fence[1] and not info:
            open_fence = None

    if current is not None:
        found.append(current)  # unclosed; validate reports it
    return found


def parse_data_directive(text: str) -> list[str]:
    """Ordered, de-duplicated file paths declared by every {nma-data} on a page."""
    seen = {}
    for d in find_data_directives(text):
        for path in d.paths:
            seen.setdefault(path, None)
    return list(seen)


def _path_errors(path: str, data_dir: str, image_dir: str, where: str) -> list[str]:
    errors = []
    parts = path.split("/")
    if path.startswith("/") or ".." in parts:
        errors.append(f"{where} declares {path!r}, which must stay inside the day folder")
        return errors
    if parts[0] not in (data_dir, image_dir):
        errors.append(
            f"{where} declares {path!r}, which must start with {data_dir}/ or {image_dir}/"
        )
    return errors


def validate_data_directives(text: str, data_dir: str, image_dir: str) -> list[str]:
    """Return human-readable errors for every {nma-data} directive on a page."""
    errors = []
    for d in find_data_directives(text):
        where = f"line {d.start + 1}: {{nma-data}}"
        if d.end == -1:
            errors.append(f"{where} is never closed")
        if d.arg:
            errors.append(f"{where} takes no inline argument; list files one per line in the body")
        if not d.paths:
            errors.append(f"{where} is empty; list at least one file, e.g. {data_dir}/data.npz")
        for path in d.paths:
            errors += _path_errors(path, data_dir, image_dir, where)
    return errors
