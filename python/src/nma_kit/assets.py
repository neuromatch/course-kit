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
from string import Template

from nma_kit import solutions as nma_solutions

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


def asset_url(repo: str, branch: str, day: str, path: str) -> str:
    """Published raw.githubusercontent URL for a day's asset file.

    `day` is the page's directory relative to the course root ('' at the top).
    """
    segments = ["notebooks", day, path] if day else ["notebooks", path]
    tail = "/".join(s.strip("/") for s in segments if s)
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{tail}"


def _ref_pattern(data_dir: str, image_dir: str) -> re.Pattern:
    prefix = "|".join(re.escape(d) for d in (data_dir, image_dir))
    # a quoted literal path: known prefix, no '{' (so f-strings are skipped),
    # and a real file extension.
    return re.compile(
        r"""['"]((?:%s)/[\w./-]+\.\w+)['"]""" % prefix
    )


def scan_code_references(code: str, data_dir: str, image_dir: str) -> list[str]:
    """Strict literal data/image references in one code string, in order, deduped."""
    pattern = _ref_pattern(data_dir, image_dir)
    seen = {}
    for line in code.splitlines():
        for match in pattern.finditer(line):
            seen.setdefault(match.group(1), None)
    return list(seen)


def undeclared_reference_errors(text: str, data_dir: str, image_dir: str) -> list[str]:
    """Errors for strict literal references in code cells not declared by {nma-data}."""
    declared = set(parse_data_directive(text))
    errors = []
    for block in nma_solutions.find_blocks(text):
        if block.kind not in ("code-cell", "exercise") or block.nested:
            continue
        code = "\n".join(block.body_lines)
        for ref in scan_code_references(code, data_dir, image_dir):
            if ref not in declared:
                errors.append(
                    f"line {block.start + 1}: code uses {ref!r} but no {{nma-data}} "
                    f"directive on the page declares it"
                )
    return errors


DOWNLOAD_CELL_ID = "nma-download-data"

_DOWNLOAD_TEMPLATE = Template('''\
# @title Download course data
import os, urllib.request

_BASE = "$base"
for _f in [$files]:
    if not os.path.exists(_f):
        os.makedirs(os.path.dirname(_f), exist_ok=True)
        urllib.request.urlretrieve(_BASE + _f, _f)
del _f''')


def download_cell_source(paths: list[str], repo: str, branch: str, day: str) -> str:
    """Python source for the hidden Colab/Kaggle download cell."""
    base = asset_url(repo, branch, day, "") + "/"
    files = ", ".join(repr(p) for p in paths)
    return _DOWNLOAD_TEMPLATE.substitute(base=base, files=files)


def make_download_cell(paths: list[str], repo: str, branch: str, day: str,
                       cell_id: str = DOWNLOAD_CELL_ID) -> dict:
    """A hidden code cell that downloads the declared files. Cf. media.make_code_cell."""
    source = download_cell_source(paths, repo, branch, day)
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {"cellView": "form", "tags": ["hide-cell"]},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def insert_download_cell(nb: dict, paths: list[str], repo: str, branch: str, day: str,
                         cell_id: str = DOWNLOAD_CELL_ID) -> bool:
    """Insert the download cell at index 0 if there are paths and it is not already there.

    Idempotent by `cell_id`. Returns whether a cell was inserted. The badge cell
    is prepended later (convert.add_badge_cell), so it ends up ahead of this one.
    """
    if not paths:
        return False
    if any(c.get("id") == cell_id for c in nb["cells"]):
        return False
    nb["cells"].insert(0, make_download_cell(paths, repo, branch, day, cell_id))
    return True


def _image_rewriter(repo: str, branch: str, day: str, image_dir: str):
    md_re = re.compile(r"(!\[[^\]]*\]\()(%s/[\w./-]+)(\))" % re.escape(image_dir))
    html_re = re.compile(r"""(<img[^>]*\ssrc=["'])(%s/[\w./-]+)(["'])""" % re.escape(image_dir))
    count = 0

    def repl(match):
        nonlocal count
        count += 1
        return match.group(1) + asset_url(repo, branch, day, match.group(2)) + match.group(3)

    def rewrite(text: str) -> str:
        return html_re.sub(repl, md_re.sub(repl, text))

    def total() -> int:
        return count

    return rewrite, total


def rewrite_markdown_images(nb: dict, repo: str, branch: str, day: str, image_dir: str) -> int:
    """Rewrite relative image references in markdown cells to published URLs. Returns count."""
    rewrite, total = _image_rewriter(repo, branch, day, image_dir)
    for cell in nb["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        source = cell["source"]
        text = "".join(source) if isinstance(source, list) else source
        cell["source"] = rewrite(text).splitlines(keepends=True)
    return total()
