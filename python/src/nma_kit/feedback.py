"""
Per-section feedback: the {nma-feedback} directive.

Syntax (top level of a page only):

    ---
    feedback_prefix: W2D2_T1     # optional, default from the filename: W2D1_Tutorial1 -> W2D1_T1
    ---

    :::{nma-feedback} Linear_Dynamical_Systems_Video
    :::

The section id sent to datatops is `{prefix}_{name}`. The datatops settings
live in myst.yml:

    nma:
      feedback:
        url: https://...
        project: neuromatch_cn
        user_key: ...

One source becomes:
  - site: a pure-JS widget (js/src/feedback/plugin.mjs + js/src/feedback/assets/widget.mjs) that
    posts to datatops from the browser, with no kernel
  - notebooks: the standard NMA "Submit your feedback" cells, plus one
    "Import feedback gadget" cell that pip-installs vibecheck

The `nma:` block is read with a YAML parser on both sides (read_nma_block in
nma_kit.config, readNmaConfig in js/src/shared/config.mjs). config_errors()
still requires plain `section: {key: "string"}` entries, so the plugin never
sees numbers, lists or nested mappings.
"""

import re
from dataclasses import dataclass

import yaml

from nma_kit.config import read_nma_block  # noqa: F401  (re-exported)
from nma_kit.solutions import find_blocks

KIND = "nma-feedback"
NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
DEFAULT_PREFIX_RE = re.compile(r"^(W\d+D\d+)_Tutorial(\d+)$")
CONFIG_KEYS = ("url", "project", "user_key")
HIDDEN = {"cellView": "form", "tags": ["hide-input"]}


# --- config -----------------------------------------------------------------

@dataclass(frozen=True)
class FeedbackConfig:
    url: str
    project: str
    user_key: str


FORMAT_ERROR = (
    "myst.yml: the `nma:` block must be `section:` mappings of `key: value` with string values "
    "(no numbers, booleans, lists or deeper nesting). Quote values that look like numbers."
)


def _plain_block(raw) -> bool:
    """True if `raw` is {section: {key: str}} (sections may not be empty)."""
    return isinstance(raw, dict) and all(
        isinstance(section, dict) and section
        and all(isinstance(k, str) and isinstance(v, str) for k, v in section.items())
        for section in raw.values())


def config_errors(text: str) -> list[str]:
    """Problems with the `nma:` block in myst.yml. A missing block is fine."""
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return [f"myst.yml is not valid YAML: {exc}"]
    raw = data.get("nma") if isinstance(data, dict) else None
    if raw is None:
        return []
    if not _plain_block(raw):
        return [FORMAT_ERROR]
    feedback = raw.get("feedback")
    if feedback is None:
        return []
    return [f"myst.yml: nma.feedback is missing {key} (or it is empty)"
            for key in CONFIG_KEYS if not feedback.get(key)]


def load_config(text: str) -> FeedbackConfig | None:
    """The feedback settings from myst.yml, or None if absent or incomplete."""
    feedback = read_nma_block(text).get("feedback") or {}
    if not all(feedback.get(key) for key in CONFIG_KEYS):
        return None
    return FeedbackConfig(*(feedback[key] for key in CONFIG_KEYS))


# --- pages ------------------------------------------------------------------

def _frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    try:
        data = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def default_prefix(stem: str) -> str:
    match = DEFAULT_PREFIX_RE.match(stem)
    return f"{match.group(1)}_T{match.group(2)}" if match else stem


def page_prefix(text: str, stem: str) -> str:
    """`feedback_prefix` from the frontmatter, else derived from the filename."""
    prefix = _frontmatter(text).get("feedback_prefix")
    return str(prefix) if prefix is not None else default_prefix(stem)


def find_directives(text: str) -> list:
    """Top-level {nma-feedback} blocks (see nma_solutions.Block)."""
    return [b for b in find_blocks(text, (KIND,)) if b.kind == KIND and not b.nested]


def validate(text: str) -> list[str]:
    """Human-readable errors for the page, each prefixed with its line."""
    errors = []
    prefix = _frontmatter(text).get("feedback_prefix")
    if prefix is not None and not NAME_RE.match(str(prefix)):
        errors.append(
            f"feedback_prefix in the frontmatter must use only letters, digits and "
            f"underscores (got {prefix!r})"
        )
    seen = set()
    for b in find_blocks(text, (KIND,)):
        if b.kind != KIND:
            continue
        where = f"line {b.start + 1}: {{{KIND}}}"
        if b.nested:
            errors.append(f"{where} must be at the top level of the page, not inside another directive")
            continue
        if b.end == -1:
            errors.append(f"{where} is never closed")
            continue
        if not b.arg:
            errors.append(f"{where} needs a section name, e.g. {{{KIND}}} Linear_Dynamical_Systems_Video")
        elif not NAME_RE.match(b.arg):
            errors.append(f"{where} section name must use only letters, digits and underscores (got {b.arg!r})")
        elif b.arg in seen:
            errors.append(f"{where} section {b.arg} is used twice on this page")
        seen.add(b.arg)
        if b.options:
            errors.append(f"{where} takes no options")
        if any(line.strip() for line in b.body_lines):
            errors.append(f"{where} takes no body")
    return errors


LEGACY_RES = [
    re.compile(r"\bcontent_review\("),
    re.compile(r"^\s*(from|import)\s+vibecheck\b"),
    re.compile(r"^\s*#\s*@title\s+Import feedback gadget"),
]


def legacy_cell_errors(text: str) -> list[str]:
    """Errors for hand-written vibecheck feedback code cells."""
    errors = []
    for b in find_blocks(text):
        if b.kind not in ("code-cell", "exercise"):
            continue
        if any(r.search(line) for r in LEGACY_RES for line in b.body_lines):
            errors.append(
                f"line {b.start + 1}: hand-written feedback cell (vibecheck / content_review). "
                f"Replace it with a {{{KIND}}} directive; the notebook cells are generated"
            )
    return errors


# --- notebooks --------------------------------------------------------------

def gadget_cell_source(prefix: str, config: FeedbackConfig) -> str:
    return f'''\
# @title Import feedback gadget
%pip install -q vibecheck datatops

from vibecheck import DatatopsContentReviewContainer
def content_review(notebook_section: str):
    return DatatopsContentReviewContainer(
        "",  # No text prompt
        notebook_section,
        {{
            'url': {config.url!r},
            'name': {config.project!r},
            'user_key': {config.user_key!r},
        }},
    ).render()


feedback_prefix = {prefix!r}'''


def feedback_cell_source(name: str) -> str:
    return f'# @title Submit your feedback\ncontent_review(f"{{feedback_prefix}}_{name}")'


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _code(source: str, cell_id: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "id": cell_id,
            "metadata": {**HIDDEN, "tags": list(HIDDEN["tags"])}, "outputs": [],
            "source": _lines(source)}


def _markdown(text: str, cell_id: str) -> list[dict]:
    text = text.strip("\n")
    if not text.strip():
        return []
    return [{"cell_type": "markdown", "id": cell_id, "metadata": {}, "source": _lines(text)}]


def expand_notebook(nb: dict, prefix: str, config: FeedbackConfig) -> int:
    """
    Replace {nma-feedback} directives in markdown cells with feedback code
    cells, and add the gadget cell at the top if there were any. In place.
    Returns the number of directives expanded. Assumes validate() passed.
    """
    new_cells, count = [], 0
    for cell in nb["cells"]:
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else source
        directives = find_directives(text) if cell.get("cell_type") == "markdown" else []
        if not directives:
            new_cells.append(cell)
            continue
        lines = text.splitlines(keepends=True)
        base = cell.get("id", "cell")[:50]
        cursor = 0
        for n, d in enumerate(directives):
            new_cells += _markdown("".join(lines[cursor:d.start]), f"{base}-fm{n}")
            new_cells.append(_code(feedback_cell_source(d.arg), f"{base}-fb{n}"))
            cursor = d.end + 1
        new_cells += _markdown("".join(lines[cursor:]), f"{base}-fm{len(directives)}")
        count += len(directives)
    if count:
        new_cells.insert(0, _code(gadget_cell_source(prefix, config), "nma-feedback-gadget"))
        nb["cells"] = new_cells
    return count
