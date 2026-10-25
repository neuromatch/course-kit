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
import shutil
from dataclasses import dataclass
from pathlib import Path
from string import Template

from nma_kit import solutions as nma_solutions
from nma_kit.constants import MAX_EMBED_BYTES

ANY_FENCE_RE = re.compile(r"^(`{3,}|~{3,}|:{3,})(.*)$")
DIRECTIVE_RE = re.compile(r"^\{(nma-data)\}\s*(.*?)\s*$")


@dataclass
class DataDirective:
    """One top-level `{nma-data}` directive found in a page (see `find_data_directives`)."""
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


def _dynamic_pattern(data_dir: str, image_dir: str) -> re.Pattern:
    prefix = "|".join(re.escape(d) for d in (data_dir, image_dir))
    # f"data/{name}.npz" or "data/{}.npz".format(...): the path is built at run time
    return re.compile(r"""\bf?['"]((?:%s))/[^'"]*\{[^'"]*['"]""" % prefix)


def dynamic_reference_errors(text: str, data_dir: str, image_dir: str) -> list[str]:
    """Errors for code that builds a data/image path at run time under a folder nothing declares.

    The exact file can't be known, so this only requires the page to declare at
    least one file in that folder (the author then lists every file the code can reach).
    """
    declared_dirs = {p.split("/", 1)[0] for p in parse_data_directive(text)}
    pattern = _dynamic_pattern(data_dir, image_dir)
    errors = []
    for block in nma_solutions.find_blocks(text):
        if block.kind not in ("code-cell", "exercise") or block.nested:
            continue
        reported = set()
        for line in block.body_lines:
            for match in pattern.finditer(line):
                folder = match.group(1)
                if folder not in declared_dirs and folder not in reported:
                    reported.add(folder)
                    errors.append(
                        f"line {block.start + 1}: code builds a path under {folder}/ at run time, "
                        f"but no {{nma-data}} directive declares any {folder}/ file; "
                        f"declare every file the code can read"
                    )
    return errors


# Files declared by {nma-data} are embedded (base64) in the page for browser cells.
# MAX_EMBED_BYTES is shared with the JS plugin: see constants.json.


def embed_size_errors(text: str, day_dir: Path) -> list[str]:
    """Error when the declared files together are too big to embed in the page."""
    total = 0
    for path in parse_data_directive(text):
        full = Path(day_dir) / path
        if _well_formed(path) and full.is_file():
            total += full.stat().st_size
    if total <= MAX_EMBED_BYTES:
        return []
    return [
        f"{{nma-data}} files total {total / 1024 / 1024:.1f} MB, more than the "
        f"{MAX_EMBED_BYTES // 1024 // 1024} MB that can be embedded in the page for browser cells. "
        f"Declare only small files; fetch large datasets with your own download cell"
    ]


DOWNLOAD_CELL_ID = "nma-download-data"
DOWNLOAD_SENTINEL = "# @title Download course data"

_DOWNLOAD_TEMPLATE = Template('''\
$sentinel
import os, urllib.request

_BASE = "$base"
for _f in [$files]:
    if not os.path.exists(_f):
        os.makedirs(os.path.dirname(_f), exist_ok=True)
        try:
            urllib.request.urlretrieve(_BASE + _f, _f)
        except OSError as _e:
            raise RuntimeError(f"Could not download {_f} ({_e}). On Kaggle, turn Internet on in the notebook settings.") from None
del _f''')


def download_cell_source(paths: list[str], repo: str, branch: str, day: str) -> str:
    """Python source for the hidden Colab/Kaggle download cell."""
    base = asset_url(repo, branch, day, "") + "/"
    files = ", ".join(repr(p) for p in paths)
    return _DOWNLOAD_TEMPLATE.substitute(sentinel=DOWNLOAD_SENTINEL, base=base, files=files)


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
    md_re = re.compile(r"""(!\[[^\]]*\]\()(%s/[\w./-]+)(\s+["'][^)]*["'])?(\))""" % re.escape(image_dir))
    html_re = re.compile(r"""(<img[^>]*\ssrc=["'])(%s/[\w./-]+)(["'])""" % re.escape(image_dir))
    count = 0

    def repl(match):
        nonlocal count
        count += 1
        url = asset_url(repo, branch, day, match.group(2))
        return match.group(1) + url + "".join(g or "" for g in match.groups()[2:])

    def rewrite(text: str) -> str:
        return html_re.sub(repl, md_re.sub(repl, text))

    def total() -> int:
        return count

    return rewrite, total


IMAGE_DIRECTIVE_RE = re.compile(r"^\{(figure|image)\}\s*(.*?)\s*$")
_OPTION_RE = re.compile(r"^:([\w-]+):\s*(.*?)\s*$")


@dataclass
class ImageDirective:
    """One top-level `{figure}` or `{image}` directive found in a page."""
    kind: str                # "figure" or "image"
    path: str                # the directive argument (image path or URL)
    options: dict            # :alt:, :width:, ... (as written)
    caption: str             # figure caption (markdown), '' for {image}
    start: int               # 0-based line index of the opening fence
    end: int                 # 0-based line index of the closing fence


def _scan_top_level(text: str):
    """Yield ('line', i, line) outside any fence and ('fence', i, (marker, info, end)) for each top-level fence.

    A fence's end is the index of its closing line (len(lines) when unclosed).
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = ANY_FENCE_RE.match(lines[i])
        if not match:
            yield "line", i, lines[i]
            i += 1
            continue
        marker, info = match.group(1), match.group(2).strip()
        j = i + 1
        while j < len(lines):
            close = ANY_FENCE_RE.match(lines[j])
            if (close and close.group(1)[0] == marker[0] and len(close.group(1)) >= len(marker)
                    and not close.group(2).strip()):
                break
            j += 1
        yield "fence", i, (marker, info, j, lines[i + 1:j])
        i = j + 1


def find_image_directives(text: str) -> list[ImageDirective]:
    """Top-level {figure} / {image} directives, with their options and caption."""
    found = []
    for kind, i, payload in _scan_top_level(text):
        if kind != "fence":
            continue
        _marker, info, end, body = payload
        match = IMAGE_DIRECTIVE_RE.match(info)
        if not match:
            continue
        options, rest = {}, list(body)
        if rest and rest[0].strip() == "---":           # YAML options block
            close = next((k for k in range(1, len(rest)) if rest[k].strip() == "---"), None)
            if close is not None:
                for line in rest[1:close]:
                    key, _, value = line.partition(":")
                    if key.strip():
                        options[key.strip()] = value.strip().strip("\"'")
                rest = rest[close + 1:]
        else:
            while rest and _OPTION_RE.match(rest[0]):
                m = _OPTION_RE.match(rest.pop(0))
                options[m.group(1)] = m.group(2)
        caption = "\n".join(rest).strip() if match.group(1) == "figure" else ""
        found.append(ImageDirective(match.group(1), match.group(2), options, caption, i, end))
    return found


_MD_IMAGE_RE = re.compile(r"""!\[[^\]]*\]\(\s*([^\s)]+)""")
_HTML_IMAGE_RE = re.compile(r"""<img[^>]*\ssrc=["']([^"']+)["']""")


def image_references(text: str, image_dir: str) -> list[str]:
    """Image paths under `image_dir` referenced by markdown, <img> or {figure}/{image}, in order, deduped."""
    prefix = image_dir + "/"
    seen = {}
    for kind, _i, payload in _scan_top_level(text):
        if kind == "line":
            refs = _MD_IMAGE_RE.findall(payload) + _HTML_IMAGE_RE.findall(payload)
        else:
            match = IMAGE_DIRECTIVE_RE.match(payload[1])
            refs = [match.group(2)] if match else []
        for ref in refs:
            if ref.startswith(prefix):
                seen.setdefault(ref, None)
    return list(seen)


def undeclared_image_errors(text: str, image_dir: str) -> list[str]:
    """Errors for page images under `image_dir` that no {nma-data} declares.

    An undeclared image works on the site but is never published for Colab/Kaggle.
    """
    declared = set(parse_data_directive(text))
    return [
        f"{ref!r} is used as an image but no {{nma-data}} directive on the page declares it"
        for ref in image_references(text, image_dir) if ref not in declared
    ]


def _html_attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;")


def _image_directive_html(d: ImageDirective, url: str) -> str:
    attrs = [f'src="{_html_attr(url)}"']
    alt = d.options.get("alt")
    if alt:
        attrs.append(f'alt="{_html_attr(alt)}"')
    width = d.options.get("width")
    if width:
        attrs.append(f'width="{_html_attr(width)}"')
    html = f"<img {' '.join(attrs)}>"
    if d.kind == "figure" and d.caption:
        html += f"\n\n*{' '.join(d.caption.split())}*"
    return html


def convert_image_directives(text: str, repo: str, branch: str, day: str, image_dir: str) -> tuple[str, int]:
    """Replace {figure}/{image} directives with <img> (+ italic caption) that Colab renders.

    Paths under `image_dir` become published URLs; other paths are kept as written.
    Returns (new text, number converted).
    """
    directives = find_image_directives(text)
    if not directives:
        return text, 0
    lines = text.splitlines()
    out, cursor = [], 0
    for d in directives:
        out.extend(lines[cursor:d.start])
        path = d.path
        url = asset_url(repo, branch, day, path) if path.startswith(image_dir + "/") else path
        out.extend(_image_directive_html(d, url).split("\n"))
        cursor = d.end + 1
    out.extend(lines[cursor:])
    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), len(directives)


def rewrite_markdown_images(nb: dict, repo: str, branch: str, day: str, image_dir: str) -> int:
    """Make image references in markdown cells point at published URLs. Returns count.

    {figure}/{image} directives become <img> tags; markdown and <img> references
    under `image_dir` are rewritten in place.
    """
    rewrite, total = _image_rewriter(repo, branch, day, image_dir)
    converted = 0
    for cell in nb["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        source = cell["source"]
        text = "".join(source) if isinstance(source, list) else source
        text, n = convert_image_directives(text, repo, branch, day, image_dir)
        converted += n
        cell["source"] = rewrite(text).splitlines(keepends=True)
    return total() + converted


def _well_formed(path: str) -> bool:
    return bool(path) and not path.startswith("/") and ".." not in path.split("/")


def missing_file_errors(text: str, day_dir: Path) -> list[str]:
    """Errors for declared files that do not exist under the page's day folder.

    Malformed paths (absolute, `..`) are skipped here: validate_data_directives
    reports them, and nothing outside the day folder is probed.
    """
    errors = []
    for d in find_data_directives(text):
        for path in d.paths:
            if _well_formed(path) and not (Path(day_dir) / path).is_file():
                errors.append(f"line {d.start + 1}: {{nma-data}} declares {path!r}, but {day_dir}/{path} does not exist")
    return errors


def strip_data_directives(nb: dict) -> int:
    """Remove {nma-data} directives from markdown cells, dropping cells left empty.

    The download cell replaces them in generated notebooks. Returns the number removed.
    """
    new_cells, removed = [], 0
    for cell in nb["cells"]:
        if cell.get("cell_type") != "markdown":
            new_cells.append(cell)
            continue
        source = cell["source"]
        text = "".join(source) if isinstance(source, list) else source
        directives = find_data_directives(text)
        if not directives:
            new_cells.append(cell)
            continue
        lines = text.splitlines(keepends=True)
        drop = {i for d in directives for i in range(d.start, (d.end if d.end != -1 else len(lines) - 1) + 1)}
        kept = "".join(line for i, line in enumerate(lines) if i not in drop)
        kept = re.sub(r"\n{3,}", "\n\n", kept).strip("\n")
        removed += len(directives)
        if kept.strip():
            cell["source"] = kept.splitlines(keepends=True)
            new_cells.append(cell)
    nb["cells"] = new_cells
    return removed


def copy_declared_files(paths: list[str], src_day: Path, dest_day: Path) -> int:
    """Copy the declared, existing files from the source day folder into the notebooks tree."""
    count = 0
    for path in paths:
        source = Path(src_day) / path
        if not _well_formed(path) or not source.is_file():
            continue
        target = Path(dest_day) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        count += 1
    return count
