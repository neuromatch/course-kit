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

    :::{nma-slides} Tutorial slides
    :osf: <osf id>
    :path: slides/<file>.pdf
    :::

`{nma-slides}` takes an optional title and one or both backends: `:osf:` (an
OSF file id) and `:path:` (a PDF in the day folder's slides folder, published
with the notebooks). With both, readers get one tab per backend.
"""

import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

from nma_kit.constants import DEFAULT_SLIDES_DIR

ANY_FENCE_RE = re.compile(r"^(`{3,}|~{3,}|:{3,})(.*)$")
DIRECTIVE_RE = re.compile(r"^\{(nma-video|nma-slides)\}\s*(.*?)\s*$")
OPTION_RE = re.compile(r"^:([A-Za-z][\w-]*):\s*(.*?)\s*$")


@dataclass
class MediaDirective:
    """One `{nma-video}` or `{nma-slides}` directive found in a page (see `find_directives`)."""
    kind: str                 # "nma-video" or "nma-slides"
    arg: str                  # video or slides title
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
    "nma-slides": {"osf", "path"},
}
DEFAULT_SLIDES_TITLE = "Tutorial slides"
# (option name, tab label), in display order. JS twin: SLIDE_SOURCES in media/plugin.mjs.
SLIDE_SOURCES = [("osf", "OSF"), ("path", "PDF")]

# Colab shows cell output in a sandboxed frame, where Chromium refuses to draw a
# bare PDF ("This page has been blocked by Chromium"), so an iframe on the PDF
# stays blank. The Colab cell shows the PDF with PDF.js instead: its viewer
# component (scrolling, zoom, page navigation) plus a small toolbar, loaded from
# jsDelivr (a host Colab can reach; jsDelivr allows the cross-origin reads
# PDF.js needs for the PDF, its worker and its fonts).
PDFJS_VERSION = "4.10.38"
PDFJS_URL = f"https://cdn.jsdelivr.net/npm/pdfjs-dist@{PDFJS_VERSION}/"

# __ID__ and __URL__ are filled in by the cell at run time, __LIB__ when the cell is written.
# The page's own <script> is classic (so it runs in Colab's HTML output); PDF.js is an ES module,
# loaded with import(). The viewer module reads `window.pdfjsLib`, so that is set first. The
# worker is fetched and started from a blob: URL, because a browser won't start a worker from
# another origin. Keep this free of backslashes and triple quotes: it sits in a Python string twice.
PDF_VIEWER_HTML = """\
<link rel="stylesheet" href="__LIB__web/pdf_viewer.css">
<div id="__ID__" style="width:854px;max-width:100%;height:480px;display:flex;flex-direction:column;border:1px solid #ccc;box-sizing:border-box;background:#eee;font:14px sans-serif">
  <div data-bar style="display:flex;gap:6px;align-items:center;padding:4px 6px;background:#f8f8f8;border-bottom:1px solid #ccc">
    <button data-act="out" title="Zoom out">-</button>
    <button data-act="in" title="Zoom in">+</button>
    <button data-act="fit" title="Fit the whole slide">Fit</button>
    <button data-act="width" title="Fit the width">Width</button>
    <span style="flex:1"></span>
    <button data-act="prev" title="Previous slide">&lt;</button>
    <span data-page style="min-width:4em;text-align:center">Loading...</span>
    <button data-act="next" title="Next slide">&gt;</button>
  </div>
  <div style="position:relative;flex:1;min-height:0">
    <div data-container style="position:absolute;inset:0;overflow:auto"><div class="pdfViewer"></div></div>
  </div>
</div>
<script>
(async () => {
  const root = document.getElementById("__ID__");
  const url = __URL__;
  const lib = "__LIB__";
  try {
    const pdfjs = await import(lib + "build/pdf.min.mjs");
    window.pdfjsLib = pdfjs;
    const viewerLib = await import(lib + "web/pdf_viewer.mjs");
    const worker = await (await fetch(lib + "build/pdf.worker.min.mjs")).text();
    pdfjs.GlobalWorkerOptions.workerSrc = URL.createObjectURL(new Blob([worker], {type: "text/javascript"}));

    const container = root.querySelector("[data-container]");
    const label = root.querySelector("[data-page]");
    const eventBus = new viewerLib.EventBus();
    const linkService = new viewerLib.PDFLinkService({eventBus});
    const viewer = new viewerLib.PDFViewer({container, viewer: container.firstElementChild, eventBus, linkService});
    linkService.setViewer(viewer);

    let mode = "page-fit";
    const show = (value) => { mode = value; viewer.currentScaleValue = value; };
    const zoom = (factor) => { mode = null; viewer.currentScale = viewer.currentScale * factor; };
    eventBus.on("pagesinit", () => {
      show("page-fit");
      label.textContent = "1 / " + viewer.pagesCount;
    });
    eventBus.on("pagechanging", (event) => {
      label.textContent = event.pageNumber + " / " + viewer.pagesCount;
    });
    root.querySelector("[data-bar]").addEventListener("click", (event) => {
      const button = event.target.closest("button");
      const actions = {
        out: () => zoom(1 / 1.25),
        in: () => zoom(1.25),
        fit: () => show("page-fit"),
        width: () => show("page-width"),
        prev: () => viewer.previousPage(),
        next: () => viewer.nextPage(),
      };
      if (button && actions[button.dataset.act]) actions[button.dataset.act]();
    });
    new ResizeObserver(() => { if (mode) viewer.currentScaleValue = mode; }).observe(root);

    const pdf = await pdfjs.getDocument({
      url,
      cMapUrl: lib + "cmaps/",
      cMapPacked: true,
      standardFontDataUrl: lib + "standard_fonts/",
    }).promise;
    viewer.setDocument(pdf);
    linkService.setDocument(pdf, null);
  } catch (error) {
    console.error(error);
    root.textContent = "Could not show the slides here. ";
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.textContent = "Open the PDF in a new tab";
    root.appendChild(link);
  }
})();
</script>"""


def osf_slides_embed_url(osf_id: str) -> str:
    """The OSF renderer URL that shows an OSF slide deck in an iframe."""
    return f"https://mfr.ca-1.osf.io/render?url=https://osf.io/{osf_id}/?direct%26mode=render%26action=download%26mode=render"


def slide_cdn_url(repo: str, branch: str, day: str, path: str) -> str:
    """URL (jsDelivr's GitHub mirror) of a slide PDF published on the notebooks branch.

    raw.githubusercontent.com can't be used: it sends X-Frame-Options: deny, so a
    browser refuses to show it in an iframe. `day` is the page's folder under
    notebooks/ ('' at the top). JS twin: slideUrl in media/plugin.mjs.
    """
    tail = "/".join(part.strip("/") for part in ("notebooks", day, path) if part.strip("/"))
    return f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{tail}"


def _slide_path_errors(path: str, slides_dir: str, where: str) -> list[str]:
    parts = path.split("/")
    if path.startswith("/") or ".." in parts:
        return [f"{where} :path: {path!r} must stay inside the day folder"]
    if parts[0] != slides_dir or len(parts) < 2:
        return [f"{where} :path: {path!r} must start with {slides_dir}/"]
    if not path.lower().endswith(".pdf"):
        return [f"{where} :path: {path!r} must be a .pdf file"]
    return []


def validate_directive(d: MediaDirective, slides_dir: str = DEFAULT_SLIDES_DIR) -> list[str]:
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
    else:
        if not any(d.options.get(name) for name, _ in SLIDE_SOURCES):
            errors.append(f"{where} needs at least one of :osf:, :path:")
        if d.options.get("path"):
            errors += _slide_path_errors(d.options["path"], slides_dir, where)
    return errors


def slide_paths(text: str) -> list[str]:
    """The `:path:` values of every well-formed-looking `{nma-slides}` on a page, in order, without duplicates."""
    paths = [d.options["path"] for d in find_directives(text)
             if d.kind == "nma-slides" and d.options.get("path")]
    return list(dict.fromkeys(paths))


def _inside_day_folder(path: str) -> bool:
    return bool(path) and not path.startswith("/") and ".." not in path.split("/")


def missing_slide_errors(text: str, day_dir: Path) -> list[str]:
    """Errors for `:path:` files that do not exist under the page's day folder."""
    errors = []
    for d in find_directives(text):
        path = d.options.get("path") if d.kind == "nma-slides" else None
        if path and _inside_day_folder(path) and not (Path(day_dir) / path).is_file():
            errors.append(f"line {d.start + 1}: {{nma-slides}} uses {path!r}, but {day_dir}/{path} does not exist")
    return errors


def copy_slide_files(text: str, src_day: Path, dest_day: Path) -> int:
    """Copy the existing `:path:` slide files into the notebooks tree. Returns how many."""
    count = 0
    for path in slide_paths(text):
        source = Path(src_day) / path
        if not _inside_day_folder(path) or not source.is_file():
            continue
        target = Path(dest_day) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        count += 1
    return count



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
import json, sys, uuid
from IPython.display import HTML, IFrame, display
from ipywidgets import widgets

# Colab shows cell output in a sandboxed frame, where a browser can't draw a bare
# PDF. There the PDF is drawn with PDF.js; elsewhere it is embedded as is.
IN_COLAB = "google.colab" in sys.modules

PDF_VIEWER = r"""$viewer"""


def show_pdf(url):
  box = "nma-slides-" + uuid.uuid4().hex[:12]
  display(HTML(PDF_VIEWER.replace("__ID__", box).replace("__URL__", json.dumps(url))))


# (label, embed url, download url, the embed url is a bare PDF)
slides = $slides

tab_contents = []
for label, src, download, is_pdf in slides:
  out = widgets.Output()
  with out:
    print(f"If you want to download the slides: {download}")
    if is_pdf and IN_COLAB:
      show_pdf(src)
    else:
      display(IFrame(src=src, width=854, height=480))
  tab_contents.append(out)
if len(tab_contents) == 1:
  display(tab_contents[0])
else:
  tabs = widgets.Tab()
  tabs.children = tab_contents
  for i, (label, _, _, _) in enumerate(slides):
    tabs.set_title(i, label)
  display(tabs)''')

NO_SLIDES_TEMPLATE = Template('''\
# @title $title
print("The slides are available on the course website.")''')


def video_cell_source(d: MediaDirective) -> str:
    """Notebook code that shows the video(s) of a `{nma-video}` directive, one tab per source."""
    video_ids = [(label, d.options[name]) for name, label in VIDEO_SOURCES if d.options.get(name)]
    return VIDEO_TEMPLATE.substitute(title=d.arg, video_ids=repr(video_ids))


def slides_cell_source(d: MediaDirective, path_url: Callable[[str], str] | None = None) -> str:
    """Notebook code that shows the slides of a `{nma-slides}` directive.

    `path_url` maps a `:path:` file to its published URL. Without it (the course
    has no GitHub repo) the `:path:` source is left out.
    """
    title = d.arg or DEFAULT_SLIDES_TITLE
    slides = []
    if d.options.get("osf"):
        osf_id = d.options["osf"]
        slides.append(("OSF", osf_slides_embed_url(osf_id), f"https://osf.io/download/{osf_id}/", False))
    if d.options.get("path") and path_url:
        url = path_url(d.options["path"])
        slides.append(("PDF", url, url, True))
    if not slides:
        return NO_SLIDES_TEMPLATE.substitute(title=title)
    viewer = PDF_VIEWER_HTML.replace("__LIB__", PDFJS_URL)
    return SLIDES_TEMPLATE.substitute(title=title, slides=repr(slides), viewer=viewer)


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def make_code_cell(d: MediaDirective, cell_id: str,
                   path_url: Callable[[str], str] | None = None) -> dict:
    """A hidden notebook code cell replacing a media directive."""
    source = video_cell_source(d) if d.kind == "nma-video" else slides_cell_source(d, path_url)
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


def expand_markdown_cell(cell: dict, path_url: Callable[[str], str] | None = None) -> list[dict]:
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
        out.append(make_code_cell(d, f"{base}-{d.kind}{n}", path_url))
        cursor = d.end + 1
    out += _markdown_fragment(lines[cursor:], f"{base}-md{len(directives)}")
    return out


def expand_notebook(nb: dict, path_url: Callable[[str], str] | None = None) -> int:
    """Replace media directives in markdown cells with code cells, in place.

    Returns the number of directives expanded. Assumes validate_directive
    passed, so every directive is closed.
    """
    new_cells, count = [], 0
    for cell in nb["cells"]:
        if cell.get("cell_type") != "markdown":
            new_cells.append(cell)
            continue
        expanded = expand_markdown_cell(cell, path_url)
        count += sum(1 for c in expanded if c["cell_type"] == "code")
        new_cells += expanded
    nb["cells"] = new_cells
    return count
