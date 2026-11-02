"""
Teaching notes: {nma-instructor}.

Syntax (top level of a page only):

    :::{nma-instructor}
    Markdown for the instructor: timing, common mistakes, what to say.
    :::

The instructor site (js/src/instructor/plugin.mjs) shows the body in an
"Instructor notes" box. The student site shows nothing, and generated
notebooks, student and instructor, never contain it (`strip_notes`).
"""

import re

from nma_kit import scrolly as nma_scrolly
from nma_kit.solutions import find_blocks

NAME = "nma-instructor"


def _notes(text: str):
    return [b for b in find_blocks(text, (NAME,)) if b.kind == NAME]


def validate(text: str) -> list[str]:
    """Human-readable errors for the page, each prefixed with its line."""
    scrolly = nma_scrolly.is_scrolly(text)
    errors = []
    for note in _notes(text):
        where = f"line {note.start + 1}:"
        name = f"{{{NAME}}}"
        if scrolly:
            errors.append(f"{where} {name} is not supported on pages with `layout: scrolly`")
        elif note.nested:
            errors.append(f"{where} {name} must be at the top level of the page, not inside another directive")
        elif note.end == -1:
            errors.append(f"{where} {name} is never closed")
        elif note.arg:
            errors.append(f"{where} {name} takes no argument (got {note.arg!r})")
        elif note.options:
            errors.append(f"{where} {name} has unknown option :{sorted(note.options)[0]}: (it takes none)")
        elif not "\n".join(note.body_lines).strip():
            errors.append(f"{where} {name} is empty")
    return errors


def strip_notes(nb: dict) -> int:
    """Remove {nma-instructor} directives from markdown cells, dropping cells left empty.

    Returns the number removed. Same behaviour as `assets.strip_data_directives`."""
    new_cells, removed = [], 0
    for cell in nb["cells"]:
        if cell.get("cell_type") != "markdown":
            new_cells.append(cell)
            continue
        source = cell["source"]
        text = "".join(source) if isinstance(source, list) else source
        notes = _notes(text)
        if not notes:
            new_cells.append(cell)
            continue
        lines = text.splitlines(keepends=True)
        drop = {i for n in notes for i in range(n.start, (n.end if n.end != -1 else len(lines) - 1) + 1)}
        kept = "".join(line for i, line in enumerate(lines) if i not in drop)
        kept = re.sub(r"\n{3,}", "\n\n", kept).strip("\n")
        removed += len(notes)
        if kept.strip():
            cell["source"] = kept.splitlines(keepends=True)
            new_cells.append(cell)
    nb["cells"] = new_cells
    return removed
