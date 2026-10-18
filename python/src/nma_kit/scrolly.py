"""
Scrollytelling pages: `layout: scrolly`, {step} and {stage}.

A scrolly page is an ordinary tutorial page with `layout: scrolly` in its
frontmatter. `{step}` markers split it into steps, and an optional `{stage}`
block holds markdown that only appears on the pinned stage:

    :::{step} hero
    :kicker: neuromatch academy
    :::
    # Title

    :::{step}
    :section: One dimension
    :kicker: Coding Exercise 1
    :::
    Card text. Code cells after the marker go on the stage.

    :::{stage}
    :style: list
    1. An objective
    :::

Interactive demos use Colab form syntax, one assignment per line:

    a = -0.5   # @param {type:"slider", min:-2.5, max:1.5, step:0.25}
    option = 1 # @param [1, 2, 3, 4]

The website side is js/src/scrolly/plugin.mjs. These rules must match it:
  - is_scrolly()     <-> isScrolly()
  - cell_key()       <-> cellKey()       (fixture fixtures/scrolly/cell_keys.json)
  - parse_params()   <-> parseParams()   (fixture fixtures/scrolly/params.json)
  - render file path _build/scrolly/<relDir>/<stem>.json
"""

import hashlib
import re
import sys

from nma_kit.solutions import Block, find_blocks

STEP = "step"
STAGE = "stage"
KINDS = (STEP, STAGE)
STEP_OPTIONS = {"section", "kicker"}
STAGE_OPTIONS = {"style", "class"}
STAGE_STYLES = {"list"}

LAYOUT_RE = re.compile(r"""^layout:\s*(['"]?)scrolly\1\s*(#.*)?$""", re.M)


def _frontmatter_text(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


frontmatter_text = _frontmatter_text  # public alias (used by nma_cells)


def is_scrolly(text: str) -> bool:
    """True if the frontmatter has a plain top-level `layout: scrolly` line."""
    return bool(LAYOUT_RE.search(_frontmatter_text(text)))


def find_markers(text: str) -> list[Block]:
    """The {step} and {stage} directives in `text`, in order (code cells excluded)."""
    return [b for b in find_blocks(text, KINDS) if b.kind in KINDS]


# --- cell keys ----------------------------------------------------------------

def canonical_code(code: str) -> str:
    """CRLF -> LF, trailing spaces/tabs removed per line, outer blank lines removed."""
    lines = [line.rstrip(" \t") for line in code.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip("\n")


def cell_key(code: str) -> str:
    """Identifies a code cell between the page, the render file and the plugin."""
    return hashlib.sha256(canonical_code(code).encode("utf-8")).hexdigest()[:16]


# --- # @param -----------------------------------------------------------------

PARAM_MARK_RE = re.compile(r"(?:^|\s)#\s*@param\b")
PARAM_LINE_RE = re.compile(r"^([A-Za-z_]\w*)\s*=\s*(.+?)\s*#\s*@param\s*(.*?)\s*$")
NUMBER_RE = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$")
SLIDER_KEYS = {"type", "min", "max", "step"}
CONSTANTS = {"True": True, "False": False, "None": None}


def _number(raw: str):
    raw = raw.strip()
    if not NUMBER_RE.match(raw):
        raise ValueError(f"{raw!r} is not a number")
    return int(raw) if re.match(r"^-?\d+$", raw) else float(raw)


def _split_top(raw: str) -> list[str]:
    """Split on commas that aren't inside quotes."""
    parts, current, quote = [], "", None
    for ch in raw:
        if quote:
            current += ch
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            current += ch
        elif ch == ",":
            parts.append(current)
            current = ""
        else:
            current += ch
    if quote:
        raise ValueError("unclosed quote")
    parts.append(current)
    return [p.strip() for p in parts]


def _literal(raw: str):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] in "'\"" and raw[-1] == raw[0]:
        return raw[1:-1]
    if raw in CONSTANTS:
        return CONSTANTS[raw]
    return _number(raw)


def _parse_slider(name: str, value_raw: str, spec: str) -> dict:
    fields = {}
    for part in _split_top(spec[1:-1]):
        if not part:
            continue
        key, sep, raw = part.partition(":")
        key = key.strip().strip("'\"")
        if not sep:
            raise ValueError(f"expected key:value, got {part!r}")
        fields[key] = raw.strip()
    kind = fields.get("type", "").strip("'\"")
    if kind != "slider":
        raise ValueError(f'only type:"slider" is supported (got {kind or "no type"})')
    unknown = sorted(set(fields) - SLIDER_KEYS)
    if unknown:
        raise ValueError(f"unknown slider key(s): {', '.join(unknown)}")
    for key in ("min", "max"):
        if key not in fields:
            raise ValueError(f"slider needs {key}")
    return {
        "name": name, "kind": "slider", "value": _number(value_raw),
        "min": _number(fields["min"]), "max": _number(fields["max"]),
        "step": _number(fields["step"]) if "step" in fields else 1,
        "options": None,
    }


def _parse_dropdown(name: str, value_raw: str, spec: str) -> dict:
    inner = spec[1:-1].strip()
    if not inner:
        raise ValueError("dropdown needs at least one option")
    options = [_literal(p) for p in _split_top(inner)]
    value = _literal(value_raw)
    # Same as JS `===`: 1 matches 1.0, but True doesn't match 1.
    if not any(value == o and isinstance(value, bool) == isinstance(o, bool) for o in options):
        raise ValueError(f"default {value_raw} is not one of the options")
    return {"name": name, "kind": "dropdown", "value": value,
            "min": None, "max": None, "step": None, "options": options}


def parse_param_line(line: str) -> dict:
    """Parse one `name = value  # @param ...` line. Raises ValueError."""
    if line[:1].isspace():
        raise ValueError("must not be indented (it has to be a top-level assignment)")
    match = PARAM_LINE_RE.match(line)
    if not match:
        raise ValueError("must be an assignment: `name = value  # @param ...`")
    name, value_raw, spec = match.groups()
    if spec.startswith("{") and spec.endswith("}"):
        return _parse_slider(name, value_raw, spec)
    if spec.startswith("[") and spec.endswith("]"):
        return _parse_dropdown(name, value_raw, spec)
    raise ValueError('expected {type:"slider", min:..., max:..., step:...} or [option, ...]')


def is_param_line(line: str) -> bool:
    return bool(PARAM_MARK_RE.search(line))


def parse_params(code: str) -> list[dict]:
    """
    The `# @param` controls in a code cell, in order. Raises ValueError naming
    the (1-based) line within the cell for the first malformed one.
    """
    params = []
    for number, line in enumerate(code.replace("\r\n", "\n").split("\n"), start=1):
        if not is_param_line(line):
            continue
        try:
            params.append(parse_param_line(line))
        except ValueError as exc:
            raise ValueError(f"line {number}: # @param {exc}") from None
    return params


# --- validation -----------------------------------------------------------------

def _code_offset(lines: list[str], block: Block) -> int:
    """0-based page line of the first code line of a code cell (after options)."""
    stop = block.end if block.end != -1 else len(lines)
    body = lines[block.start + 1:stop]
    return block.start + 1 + len(body) - len(block.body_lines)


def validate(text: str) -> list[str]:
    """Human-readable errors for the page, each prefixed with its line."""
    scrolly = is_scrolly(text)
    lines = text.splitlines()
    blocks = find_blocks(text, KINDS)
    markers = [b for b in blocks if b.kind in KINDS]
    errors = []

    if not scrolly:
        for m in markers:
            errors.append(
                f"line {m.start + 1}: {{{m.kind}}} only works on pages with `layout: scrolly` "
                f"in the frontmatter"
            )
        return errors

    steps_seen = 0
    stage_in_step = False
    for b in markers:
        where = f"line {b.start + 1}:"
        name = f"{{{b.kind}}}"
        if b.nested:
            errors.append(f"{where} {name} must be at the top level of the page, not inside another directive")
            continue
        if b.end == -1:
            errors.append(f"{where} {name} is never closed")
            continue
        if b.kind == STEP:
            steps_seen += 1
            stage_in_step = False
            if b.arg not in ("", "hero"):
                errors.append(f"{where} {name} takes no argument or `hero` (got {b.arg!r})")
            for option in sorted(set(b.options) - STEP_OPTIONS):
                errors.append(f"{where} {name} has unknown option :{option}: (allowed: :section:, :kicker:)")
            if any(line.strip() for line in b.body_lines):
                errors.append(f"{where} {name} has no body. Put the step's content after the closing fence")
        else:
            if steps_seen == 0:
                errors.append(f"{where} {name} comes before the first {{step}}")
            elif stage_in_step:
                errors.append(f"{where} step has more than one {{stage}}")
            stage_in_step = True
            if b.arg:
                errors.append(f"{where} {name} takes no argument (got {b.arg!r})")
            for option in sorted(set(b.options) - STAGE_OPTIONS):
                errors.append(f"{where} {name} has unknown option :{option}: (allowed: :style:, :class:)")
            style = b.options.get("style")
            if style is not None and style not in STAGE_STYLES:
                errors.append(f"{where} {name} :style: must be `list` (got {style!r})")

    if steps_seen == 0 and not any(b.nested for b in markers):
        errors.append("line 1: page has `layout: scrolly` but no {step} markers")

    for b in blocks:
        if b.kind not in ("code-cell", "exercise") or b.nested:
            continue
        offset = _code_offset(lines, b)
        for number, line in enumerate(b.body_lines):
            if not is_param_line(line):
                continue
            try:
                parse_param_line(line)
            except ValueError as exc:
                errors.append(f"line {offset + number + 1}: # @param {exc}")
    return errors


# --- notebooks ---------------------------------------------------------------------

def flatten_for_notebook(text: str) -> str:
    """
    The page as a linear tutorial, for jupytext. {step} markers are removed
    (a :kicker: becomes an italic line) and {stage} blocks are unwrapped into
    plain markdown. Other pages are returned unchanged. Assumes validate() passed.
    """
    if not is_scrolly(text):
        return text
    lines = text.split("\n")
    for b in reversed([m for m in find_markers(text) if not m.nested and m.end != -1]):
        if b.kind == STEP:
            kicker = b.options.get("kicker", "").strip()
            replacement = [f"*{kicker}*", ""] if kicker else []
        else:
            replacement = ["", *b.body_lines, ""]
        lines[b.start:b.end + 1] = replacement
    return "\n".join(lines)


FORM_LINE_RE = re.compile(r"^#\s*@(title|markdown)\b")


def _widget(p: dict) -> str:
    if p["kind"] == "dropdown":
        return f"widgets.Dropdown(options={p['options']!r}, value={p['value']!r})"
    numbers = [p[k] for k in ("value", "min", "max", "step")]
    cls = "IntSlider" if all(isinstance(v, int) and not isinstance(v, bool) for v in numbers) else "FloatSlider"
    return (f"widgets.{cls}(value={p['value']!r}, min={p['min']!r}, max={p['max']!r}, "
            f"step={p['step']!r}, continuous_update=False)")


def params_to_interact(code: str) -> str:
    """
    Turn a cell with `# @param` lines into an ipywidgets `interact` demo for
    notebooks. Leading `# @title` / `# @markdown` lines stay on top so Colab
    still shows the cell as a form. Cells without params are returned as is.
    """
    params = parse_params(code)
    if not params:
        return code
    lines = code.replace("\r\n", "\n").split("\n")
    head = []
    while lines and FORM_LINE_RE.match(lines[0]):
        head.append(lines.pop(0))
    body = [line for line in lines if not is_param_line(line)]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    body = [f"    {line}" if line.strip() else "" for line in body] or ["    pass"]
    controls = ", ".join(f"{p['name']}={_widget(p)}" for p in params)
    names = ", ".join(p["name"] for p in params)
    return "\n".join([
        *head,
        "import ipywidgets as widgets",
        "",
        "",
        f"@widgets.interact({controls})",
        f"def _demo({names}):",
        *body,
    ])


def rewrite_notebook_params(nb: dict) -> int:
    """Apply params_to_interact to every code cell in place. Returns the count."""
    count = 0
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else source
        new = params_to_interact(text)
        if new != text:
            cell["source"] = new.splitlines(keepends=True)
            count += 1
    return count


# --- pre-render (CI) ----------------------------------------------------------------
#
# `nma-kit render-scrolly` runs every scrolly page with a
# kernelspec headless and writes its outputs to
# _build/scrolly/<relDir>/<stem>.json = {cell_key: {stdout, images, error}}.
# js/src/scrolly/plugin.mjs embeds them so readers see real figures before
# starting Python.

from nma_kit.config import DEFAULT_TUTORIALS_DIR as TUTORIALS_DIR  # noqa: E402
RENDER_DIR = "_build/scrolly"
RENDER_TIMEOUT = 300


def render_path(rel_dir: str, stem: str):
    from pathlib import Path
    return Path(RENDER_DIR, *([rel_dir] if rel_dir else []), f"{stem}.json")


def _source_cells(text: str) -> dict:
    """cell_key -> 1-based page line of the code cell's opening fence."""
    return {cell_key("\n".join(b.body_lines)): b.start + 1
            for b in find_blocks(text, ()) if b.kind in ("code-cell", "exercise") and not b.nested}


def _outputs(cell: dict) -> dict:
    stdout, images = "", []
    for out in cell.get("outputs", []):
        kind = out.get("output_type")
        if kind == "stream" and out.get("name") == "stdout":
            stdout += out.get("text", "")
        elif kind in ("display_data", "execute_result"):
            data = out.get("data", {})
            if "image/png" in data:
                images.append(data["image/png"].replace("\n", ""))
            elif kind == "execute_result" and "text/plain" in data:
                stdout += data["text/plain"].rstrip("\n") + "\n"
    return {"stdout": stdout, "images": images, "error": None}


def execution_notebook(page, rel_dir: str, repo: str = "org/repo") -> dict:
    """
    The page's instructor notebook, ready to run: flattened, solutions filled
    in, `# @param` cells left as plain assignments (so they run with their
    defaults), and exercise cells removed (the `# Solution` cell after each
    one defines the same names).
    """
    import json
    import tempfile
    from pathlib import Path

    from nma_kit import convert as convert_to_notebooks
    from nma_kit import solutions as nma_solutions

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "nb.ipynb"
        result = convert_to_notebooks.run_jupytext(page, out)
        if result.returncode != 0:
            raise RuntimeError(f"jupytext failed:\n{result.stderr}")
        nb = json.loads(out.read_text(encoding="utf-8"))
    _, instructor, _ = nma_solutions.split_notebook(nb, page.stem, rel_dir, repo)
    cells = []
    for cell in instructor["cells"]:
        if cell.get("cell_type") != "code":
            continue
        source = nma_solutions.text_of_cell(cell)
        if any(nma_solutions.EXERCISE_RE.match(line) for line in source.splitlines()):
            continue
        cells.append({**cell, "source": source, "outputs": [], "execution_count": None})
    return {**instructor, "cells": cells}


def render_page(page, rel_dir: str) -> tuple[dict | None, str | None]:
    """Run one page. Returns (render data, None) or (None, error message)."""
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    text = page.read_text(encoding="utf-8")
    lines_by_key = _source_cells(text)
    nb = nbformat.from_dict(execution_notebook(page, rel_dir))
    client = NotebookClient(nb, timeout=RENDER_TIMEOUT, kernel_name="python3",
                            resources={"metadata": {"path": str(page.parent)}})
    try:
        client.execute()
    except CellExecutionError as exc:
        for cell in nb.cells:
            errors = [o for o in cell.get("outputs", []) if o.get("output_type") == "error"]
            if errors:
                key = cell_key(cell.source)
                where = f"{page.as_posix()}:{lines_by_key.get(key, '?')}"
                if key not in lines_by_key:
                    where += f" (generated cell starting {cell.source.splitlines()[0]!r})"
                return None, f"{where}: {errors[0]['ename']}: {errors[0]['evalue']}"
        return None, f"{page.as_posix()}: {exc}"

    data = {}
    for cell in nb.cells:
        key = cell_key(cell.source)
        if key in lines_by_key:
            data[key] = _outputs(cell)
    return data, None


def render_all(root: str = TUTORIALS_DIR) -> int:
    """Render every scrolly page with a kernelspec under `root`. Returns an exit code."""
    import json
    from pathlib import Path

    from nma_kit import convert as convert_to_notebooks

    failed = False
    for page in sorted(Path(root).rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        if not (is_scrolly(text) and convert_to_notebooks.has_kernelspec(page)):
            continue
        rel = page.relative_to(root)
        rel_dir = rel.parent.as_posix() if rel.parent != Path(".") else ""
        print(f"Rendering {page}")
        data, error = render_page(page, rel_dir)
        if error:
            print(f"  ERROR {error}", file=sys.stderr)
            failed = True
            continue
        out = render_path(rel_dir, page.stem)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data), encoding="utf-8")
        print(f"  Wrote {out} ({len(data)} cell(s))")
    return 1 if failed else 0
