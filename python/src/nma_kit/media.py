"""
Parse {nma-video} / {nma-slides} directives in MyST Markdown and expand them
into NMA-style code cells for generated notebooks.

The website renders the same directives with js/src/media/plugin.mjs. The URL
templates here and in that file must stay in sync.

Syntax (top level of a page only, not nested inside other directives/fences):

    :::{nma-video} Video 1: Title
    :youtube: <id>
    :bilibili: <BV id>
    :osf: <id>
    :::

    :::{nma-slides} <osf id>
    :title: Tutorial slides
    :::
"""

import re
from dataclasses import dataclass, field
from string import Template

ANY_FENCE_RE = re.compile(r"^(`{3,}|~{3,}|:{3,})(.*)$")
DIRECTIVE_RE = re.compile(r"^\{(nma-video|nma-slides)\}\s*(.*?)\s*$")
OPTION_RE = re.compile(r"^:([A-Za-z][\w-]*):\s*(.*?)\s*$")


@dataclass
class MediaDirective:
    kind: str                 # "nma-video" or "nma-slides"
    arg: str                  # video title, or OSF id for slides
    options: dict             # option name -> value
    start: int                # 0-based line index of the opening fence
    end: int = -1             # 0-based line index of the closing fence; -1 if unclosed
    body: list = field(default_factory=list)  # unexpected non-option lines


def find_directives(text: str) -> list[MediaDirective]:
    """
    Return the top-level media directives in `text`, in order.

    Anything inside another fence (```, ~~~ or :::) is skipped. That keeps
    syntax examples on documentation pages from being treated as real
    directives.
    """
    found = []
    open_fence = None   # (char, length) of a non-media fence we're inside
    current = None      # directive being read
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
            option = OPTION_RE.match(line)
            if option and not current.body:
                current.options[option.group(1)] = option.group(2)
            elif line.strip():
                current.body.append(line)
            continue

        if not match:
            continue
        marker, info = match.group(1), match.group(2).strip()
        if open_fence is None:
            directive = DIRECTIVE_RE.match(info)
            if directive:
                current = MediaDirective(directive.group(1), directive.group(2), {}, i)
                current_fence = (marker[0], len(marker))
            else:
                open_fence = (marker[0], len(marker))
        elif marker[0] == open_fence[0] and len(marker) >= open_fence[1] and not info:
            open_fence = None

    if current is not None:
        found.append(current)  # unclosed; validate_directive reports it
    return found


# (option name, label used in NMA's video_ids), in display order
VIDEO_SOURCES = [("youtube", "Youtube"), ("bilibili", "Bilibili"), ("osf", "Osf")]
ALLOWED_OPTIONS = {
    "nma-video": {name for name, _ in VIDEO_SOURCES},
    "nma-slides": {"title"},
}
DEFAULT_SLIDES_TITLE = "Tutorial slides"


def validate_directive(d: MediaDirective) -> list[str]:
    """Return human-readable errors for one directive, each prefixed with its line."""
    where = f"line {d.start + 1}: {{{d.kind}}}"
    errors = []
    if d.end == -1:
        errors.append(f"{where} is never closed")
    for name in sorted(set(d.options) - ALLOWED_OPTIONS[d.kind]):
        allowed = ", ".join(f":{o}:" for o in sorted(ALLOWED_OPTIONS[d.kind]))
        errors.append(f"{where} has unknown option :{name}: (allowed: {allowed})")
    if d.body:
        errors.append(f"{where} takes no body content, only options")
    if d.kind == "nma-video":
        if not d.arg:
            errors.append(f"{where} needs a title argument, e.g. {{nma-video}} Video 1: Intro")
        if not any(d.options.get(name) for name, _ in VIDEO_SOURCES):
            errors.append(f"{where} needs at least one of :youtube:, :bilibili:, :osf:")
    elif not d.arg:
        errors.append(f"{where} needs an OSF id argument, e.g. {{nma-slides}} snv4m")
    return errors


# Reproduces the standard NMA video cell. string.Template ($name) is used so
# the f-string braces inside the cell need no escaping.
VIDEO_TEMPLATE = Template('''\
# @title $title
from ipywidgets import widgets
from IPython.display import YouTubeVideo
from IPython.display import IFrame
from IPython.display import display


class PlayVideo(IFrame):
  def __init__(self, id, source, page=1, width=400, height=300, **kwargs):
    self.id = id
    if source == 'Bilibili':
      src = f'https://player.bilibili.com/player.html?bvid={id}&page={page}'
    elif source == 'Osf':
      src = f'https://mfr.ca-1.osf.io/render?url=https://osf.io/download/{id}/?direct%26mode=render'
    super(PlayVideo, self).__init__(src, width, height, **kwargs)


def display_videos(video_ids, W=400, H=300, fs=1):
  tab_contents = []
  for i, video_id in enumerate(video_ids):
    out = widgets.Output()
    with out:
      if video_ids[i][0] == 'Youtube':
        video = YouTubeVideo(id=video_ids[i][1], width=W,
                             height=H, fs=fs, rel=0)
        print(f'Video available at https://youtube.com/watch?v={video.id}')
      else:
        video = PlayVideo(id=video_ids[i][1], source=video_ids[i][0], width=W,
                          height=H, fs=fs, autoplay=False)
        if video_ids[i][0] == 'Bilibili':
          print(f'Video available at https://www.bilibili.com/video/{video.id}')
        elif video_ids[i][0] == 'Osf':
          print(f'Video available at https://osf.io/{video.id}')
      display(video)
    tab_contents.append(out)
  return tab_contents


video_ids = $video_ids
tab_contents = display_videos(video_ids, W=854, H=480)
tabs = widgets.Tab()
tabs.children = tab_contents
for i in range(len(tab_contents)):
  tabs.set_title(i, video_ids[i][0])
display(tabs)''')

SLIDES_TEMPLATE = Template('''\
# @title $title
from IPython.display import IFrame
link_id = "$link_id"
print(f"If you want to download the slides: https://osf.io/download/{link_id}/")
IFrame(src=f"https://mfr.ca-1.osf.io/render?url=https://osf.io/{link_id}/?direct%26mode=render%26action=download%26mode=render", width=854, height=480)''')


def video_cell_source(d: MediaDirective) -> str:
    video_ids = [(label, d.options[name]) for name, label in VIDEO_SOURCES if d.options.get(name)]
    return VIDEO_TEMPLATE.substitute(title=d.arg, video_ids=repr(video_ids))


def slides_cell_source(d: MediaDirective) -> str:
    title = d.options.get("title") or DEFAULT_SLIDES_TITLE
    return SLIDES_TEMPLATE.substitute(title=title, link_id=d.arg)


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def make_code_cell(d: MediaDirective, cell_id: str) -> dict:
    source = video_cell_source(d) if d.kind == "nma-video" else slides_cell_source(d)
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {"cellView": "form", "tags": ["hide-input"]},
        "outputs": [],
        "source": _lines(source),
    }


def _markdown_fragment(lines: list[str], cell_id: str) -> list[dict]:
    text = "".join(lines).strip("\n")
    if not text.strip():
        return []
    return [{"cell_type": "markdown", "id": cell_id, "metadata": {}, "source": _lines(text)}]


def expand_markdown_cell(cell: dict) -> list[dict]:
    """Split a markdown cell around its media directives. Returns replacement cells."""
    source = cell["source"]
    text = "".join(source) if isinstance(source, list) else source
    directives = find_directives(text)
    if not directives:
        return [cell]

    lines = text.splitlines(keepends=True)
    base = cell.get("id", "cell")[:50]
    out, cursor = [], 0
    for n, d in enumerate(directives):
        out += _markdown_fragment(lines[cursor:d.start], f"{base}-md{n}")
        out.append(make_code_cell(d, f"{base}-{d.kind}{n}"))
        cursor = d.end + 1
    out += _markdown_fragment(lines[cursor:], f"{base}-md{len(directives)}")
    return out


def expand_notebook(nb: dict) -> int:
    """Replace media directives in markdown cells with code cells, in place.

    Returns the number of directives expanded. Assumes validate_directive
    passed, so every directive is closed.
    """
    new_cells, count = [], 0
    for cell in nb["cells"]:
        if cell.get("cell_type") != "markdown":
            new_cells.append(cell)
            continue
        expanded = expand_markdown_cell(cell)
        count += sum(1 for c in expanded if c["cell_type"] == "code")
        new_cells += expanded
    nb["cells"] = new_cells
    return count
