"""
Exercise solutions and explanations: {nma-solution} / {nma-explanation}.

Syntax (top level of a page only):

    ```{code-cell} python
    def f(x):
      raise NotImplementedError("Student exercise: ...")
    ```

    ::::{nma-solution}
    ```python
    def f(x):
      return 2 * x
    ```
    ::::

    :::{nma-explanation}
    Markdown text, math allowed.
    :::

An {nma-solution} belongs to the exercise code cell directly above it.

One source becomes:
  - student notebook: "Click for solution/explanation" link cells
  - instructor notebook: the solution as a code cell, the explanation as markdown
  - solution files, written to notebooks/<day>/solutions/ on notebooks-branch
  - a hidden setup cell for the site that runs the reference solution when
    an unfinished exercise is executed, so "Run all" doesn't stop

The website renders the directives with js/src/solutions/plugin.mjs. The file naming and
URL rules here and in that file must stay in sync.
"""

import re
from dataclasses import dataclass, field
from string import Template

FENCE_RE = re.compile(r"^(`{3,}|~{3,}|:{3,})(.*)$")
DIRECTIVE_RE = re.compile(r"^\{([\w-]+)\}\s*(.*?)\s*$")
OPTION_RE = re.compile(r"^:([A-Za-z][\w-]*):\s*(.*?)\s*$")

SOLUTION = "nma-solution"
EXPLANATION = "nma-explanation"
KINDS = (SOLUTION, EXPLANATION)

# Directives whose body is code, not Markdown, so fences inside them are text.
LITERAL_DIRECTIVES = {"code-cell", "code", "code-block"}

# An exercise cell has an uncommented `raise NotImplementedError` line. The
# site fallback uses the same rule to decide whether a cell is still unfinished.
EXERCISE_RE = re.compile(r"^\s*raise NotImplementedError\b")
TO_REMOVE_RE = re.compile(r"^\s*#\s*to_remove\b")


@dataclass
class Block:
    kind: str           # "nma-solution", "nma-explanation", "exercise" or "code-cell"
    start: int          # 0-based line of the opening fence
    end: int = -1       # 0-based line of the closing fence; -1 if unclosed
    nested: bool = False
    arg: str = ""
    options: dict = field(default_factory=dict)
    body_lines: list = field(default_factory=list)


def _split_options(lines: list[str]) -> tuple[dict, list[str]]:
    """Split leading `:key: value` lines (or a `---` YAML block) off a body."""
    options, i = {}, 0
    if lines and lines[0].strip() == "---":
        close = next((j for j in range(1, len(lines)) if lines[j].strip() == "---"), None)
        if close is not None:
            return {}, lines[close + 1:]
    while i < len(lines):
        match = OPTION_RE.match(lines[i])
        if not match:
            break
        options[match.group(1)] = match.group(2)
        i += 1
    return options, lines[i:]


def find_blocks(text: str, kinds: tuple = KINDS) -> list[Block]:
    """
    Return the `kinds` directives (default: solution/explanation) and the code
    cells in `text`.

    The scanner keeps a stack of open fences. Fences whose content is code
    (plain ``` blocks, {code-cell}) are opaque. Anything inside them is text,
    so syntax examples on documentation pages are ignored. Directive fences are
    containers, so blocks inside them are found and marked `nested`.
    """
    lines = text.splitlines()
    blocks, stack = [], []   # stack items: [char, length, literal, block|None]

    def close_block(block, end):
        block.end = end
        stop = end if end != -1 else len(lines)
        body = lines[block.start + 1:stop]
        block.options, block.body_lines = _split_options(body)
        if block.kind == "code-cell" and any(EXERCISE_RE.match(l) for l in block.body_lines):
            block.kind = "exercise"

    for i, line in enumerate(lines):
        match = FENCE_RE.match(line)
        if not match:
            continue
        marker, info = match.group(1), match.group(2).strip()
        char, length = marker[0], len(marker)
        top = stack[-1] if stack else None

        if top and not info and char == top[0] and length >= top[1]:
            stack.pop()
            if top[3] is not None:
                close_block(top[3], i)
            continue
        if top and top[2]:
            continue  # inside a code fence: just text

        directive = DIRECTIVE_RE.match(info) if char == ":" or info.startswith("{") else None
        name = directive.group(1) if directive else None
        literal = char != ":" and (name is None or name in LITERAL_DIRECTIVES)
        block = None
        if name in kinds or name == "code-cell":
            block = Block("code-cell" if name == "code-cell" else name, i,
                          nested=bool(stack), arg=directive.group(2))
            blocks.append(block)
        stack.append([char, length, literal, block])

    for item in stack:
        if item[3] is not None:
            close_block(item[3], -1)
    return blocks


def _previous_content_line(lines: list[str], index: int) -> int:
    """Index of the last non-blank line before `index`, or -1."""
    i = index - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    return i


def _next_content_line(lines: list[str], index: int) -> int:
    """Index of the first non-blank line after `index`, or -1."""
    i = index + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    return i if i < len(lines) else -1


def solution_code(block: Block) -> str | None:
    """The code inside a solution's single ```python fence, or None if malformed."""
    body = list(block.body_lines)
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    if len(body) < 2:
        return None
    opening, closing = FENCE_RE.match(body[0]), FENCE_RE.match(body[-1])
    if not (opening and closing) or opening.group(1)[0] == ":":
        return None
    if opening.group(2).strip() != "python" or closing.group(2).strip():
        return None
    if closing.group(1)[0] != opening.group(1)[0] or len(closing.group(1)) < len(opening.group(1)):
        return None
    code = "\n".join(body[1:-1]).strip("\n")
    return code if code.strip() else None


def explanation_text(block: Block) -> str:
    return "\n".join(block.body_lines).strip("\n")


def validate(text: str) -> list[str]:
    """Return human-readable errors for the page, each prefixed with its line."""
    lines = text.splitlines()
    blocks = find_blocks(text)
    errors = []
    exercise_ends = {b.end: b for b in blocks if b.kind == "exercise" and not b.nested and b.end != -1}
    solution_starts = {b.start for b in blocks if b.kind == SOLUTION and not b.nested}

    for b in blocks:
        where = f"line {b.start + 1}:"
        if b.kind in ("code-cell", "exercise"):
            if any(TO_REMOVE_RE.match(l) for l in b.body_lines):
                errors.append(
                    f"{where} code cell has a `# to_remove` marker. Move the solution into "
                    f"an {{nma-solution}} or the explanation into an {{nma-explanation}} directive"
                )
            if b.kind == "exercise" and not b.nested and b.end != -1:
                if _next_content_line(lines, b.end) not in solution_starts:
                    errors.append(
                        f"{where} exercise code cell (raises NotImplementedError) has no "
                        f"{{nma-solution}} directly after it"
                    )
            continue

        name = f"{{{b.kind}}}"
        if b.nested:
            errors.append(f"{where} {name} must be at the top level of the page, not inside another directive")
            continue
        if b.end == -1:
            errors.append(f"{where} {name} is never closed")
            continue
        if b.arg:
            errors.append(f"{where} {name} takes no argument (got {b.arg!r})")
        for option in sorted(b.options):
            errors.append(f"{where} {name} has unknown option :{option}: (it takes none)")
        if b.kind == SOLUTION:
            if solution_code(b) is None:
                errors.append(f"{where} {name} body must be a single ```python fence with the solution code")
            if _previous_content_line(lines, b.start) not in exercise_ends:
                errors.append(
                    f"{where} {name} must come directly after an exercise code cell "
                    f"(one that raises NotImplementedError)"
                )
        elif not explanation_text(b).strip():
            errors.append(f"{where} {name} is empty")
    return errors


# File naming. Keep in sync with js/src/solutions/plugin.mjs.
FILE_PATTERNS = {SOLUTION: "{stem}_Solution_{n}.py", EXPLANATION: "{stem}_Explanation_{n}.md"}
NOTEBOOKS_BRANCH = "notebooks-branch"  # default; courses override with nma.notebooks.branch


def solution_filename(stem: str, kind: str, n: int) -> str:
    return FILE_PATTERNS[kind].format(stem=stem, n=n)


def solution_url(repo: str, rel_dir: str, filename: str, branch: str = NOTEBOOKS_BRANCH) -> str:
    """GitHub URL of a solution file. rel_dir is the page's folder under the tutorials dir."""
    path = "/".join(p for p in ("notebooks", rel_dir, "solutions", filename) if p)
    return f"https://github.com/{repo}/blob/{branch}/{path}"


@dataclass
class Item:
    kind: str       # SOLUTION or EXPLANATION
    n: int          # 1-based position among directives of the same kind
    filename: str
    content: str    # solution code or explanation Markdown, newline-terminated


def items_from_blocks(blocks: list[Block], stem: str, counters: dict | None = None) -> list[Item]:
    """Number top-level directives. Pass `counters` to continue numbering across calls."""
    counters = {} if counters is None else counters
    items = []
    for b in blocks:
        if b.kind not in KINDS or b.nested:
            continue
        counters[b.kind] = counters.get(b.kind, 0) + 1
        n = counters[b.kind]
        content = solution_code(b) if b.kind == SOLUTION else explanation_text(b)
        items.append(Item(b.kind, n, solution_filename(stem, b.kind, n), (content or "") + "\n"))
    return items


def extract(text: str, stem: str) -> list[Item]:
    """The page's solutions and explanations, in order. Assumes validate() passed."""
    return items_from_blocks(find_blocks(text), stem)


def exercise_pairs(text: str) -> list[tuple[str, str]]:
    """(exercise source, solution code) for each exercise. Assumes validate() passed."""
    blocks = [b for b in find_blocks(text) if not b.nested]
    pairs = []
    for ex, sol in zip(blocks, blocks[1:]):
        if ex.kind == "exercise" and sol.kind == SOLUTION:
            exercise = "\n".join(ex.body_lines).strip("\n")
            pairs.append((exercise, solution_code(sol) or ""))
    return pairs


LINK_LABELS = {SOLUTION: "Click for solution", EXPLANATION: "Click for explanation"}


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _markdown(text: str, cell_id: str) -> dict:
    return {"cell_type": "markdown", "id": cell_id, "metadata": {}, "source": _lines(text)}


def _student_cell(item: Item, url: str, cell_id: str) -> dict:
    return _markdown(f"[*{LINK_LABELS[item.kind]}*]({url})", cell_id)


def _instructor_cell(item: Item, cell_id: str) -> dict:
    body = item.content.rstrip("\n")
    if item.kind == EXPLANATION:
        return _markdown(f"**Explanation**\n\n{body}", cell_id)
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": [],
        "source": _lines(f"# Solution\n{body}"),
    }


def split_notebook(nb: dict, stem: str, rel_dir: str, repo: str,
                   branch: str = NOTEBOOKS_BRANCH) -> tuple[dict, dict, dict]:
    """
    Build the student and instructor versions of a jupytext-generated notebook.

    Markdown cells are split around top-level {nma-solution}/{nma-explanation}
    directives. Returns (student_nb, instructor_nb, files), where files maps
    solution filenames to their content. The input notebook is not modified.
    Assumes validate() passed on the source page.
    """
    student, instructor, files = [], [], {}
    counters = {}
    for cell in nb["cells"]:
        text = text_of_cell(cell)
        blocks = find_blocks(text) if cell.get("cell_type") == "markdown" else []
        directive_blocks = [b for b in blocks if b.kind in KINDS and not b.nested]
        if not directive_blocks:
            student.append(cell)
            instructor.append(cell)
            continue

        items = items_from_blocks(directive_blocks, stem, counters)
        lines = text.splitlines(keepends=True)
        base = cell.get("id", "cell")[:50]
        cursor = 0
        for k, (block, item) in enumerate(zip(directive_blocks, items)):
            prose = "".join(lines[cursor:block.start]).strip("\n")
            if prose.strip():
                fragment = _markdown(prose, f"{base}-m{k}")
                student.append(fragment)
                instructor.append(fragment)
            url = solution_url(repo, rel_dir, item.filename, branch)
            student.append(_student_cell(item, url, f"{base}-s{k}"))
            instructor.append(_instructor_cell(item, f"{base}-i{k}"))
            files[item.filename] = item.content
            cursor = block.end + 1
        prose = "".join(lines[cursor:]).strip("\n")
        if prose.strip():
            fragment = _markdown(prose, f"{base}-m{len(directive_blocks)}")
            student.append(fragment)
            instructor.append(fragment)

    return {**nb, "cells": student}, {**nb, "cells": instructor}, files


def text_of_cell(cell: dict) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else source


FALLBACK_SENTINEL = "# nma-exercise-fallback (generated, do not edit)"
FALLBACK_NOTE = "Exercise not completed yet, so the reference solution was run."

# Runs inside the reader's kernel (Pyodide on the site). It must be
# self-contained and leave no names behind. The transformer runs more than
# once per cell (pyodide-kernel also uses it to detect imports), so it must
# not have side effects: the note is printed by the code it returns.
FALLBACK_TEMPLATE = '''\
$sentinel
# Runs the reference solution when an unfinished exercise is executed,
# so "Run all" doesn't stop at the first exercise.
def _nma_install_fallback(exercises):
    import difflib
    import re
    from IPython import get_ipython

    shell = get_ipython()
    if shell is None:
        return
    unfinished = re.compile(r"^[ \\t]*raise NotImplementedError", re.MULTILINE)

    def nma_exercise_fallback(lines):
        source = "".join(lines)
        if (not unfinished.search(source)
                or "nma-exercise-fallback" in source
                or "$no_fallback" in source):
            return lines
        best, best_score = None, $threshold
        for exercise, solution in exercises:
            if source.strip() == exercise.strip():
                best = solution
                break
            score = difflib.SequenceMatcher(None, source, exercise).ratio()
            if score >= best_score:
                best, best_score = solution, score
        if best is None:
            return lines
        return [$note_line] + (best + "\\n").splitlines(keepends=True)

    transformers = shell.input_transformers_post
    transformers[:] = [t for t in transformers
                       if getattr(t, "__name__", "") != "nma_exercise_fallback"]
    transformers.append(nma_exercise_fallback)


_nma_install_fallback($exercises)
del _nma_install_fallback'''

FUZZY_THRESHOLD = 0.6
# A cell containing this marker is never replaced by the fallback: the editable
# panels append it to the cell the student explicitly runs.
NO_FALLBACK_MARKER = "nma-no-fallback"  # keep in sync with js/src/cells/src/model.mjs


def fallback_cell_source(pairs: list[tuple[str, str]]) -> str:
    exercises = "[\n" + "".join(f"    ({e!r}, {s!r}),\n" for e, s in pairs) + "]"
    return Template(FALLBACK_TEMPLATE).substitute(
        sentinel=FALLBACK_SENTINEL,
        no_fallback=NO_FALLBACK_MARKER,
        threshold=FUZZY_THRESHOLD,
        note_line=repr(f"print({FALLBACK_NOTE!r})\n"),
        exercises=exercises,
    )


def fallback_md_block(pairs: list[tuple[str, str]]) -> str:
    """The fallback as a hidden MyST code cell, for injecting into a page."""
    return f"```{{code-cell}} python\n:tags: [remove-cell]\n{fallback_cell_source(pairs)}\n```"
