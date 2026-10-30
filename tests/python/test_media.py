import json
import re
from pathlib import Path

import pytest

from nma_kit.media import find_directives

VIDEO_MD = """Intro text

:::{nma-video} Video 1: Linear Dynamical Systems
:youtube: 87z6OR7-DBI
:bilibili: BV1up4y1S7wj
:::

Outro text
"""


def test_find_video_directive():
    [d] = find_directives(VIDEO_MD)
    assert d.kind == "nma-video"
    assert d.arg == "Video 1: Linear Dynamical Systems"
    assert d.options == {"youtube": "87z6OR7-DBI", "bilibili": "BV1up4y1S7wj"}
    assert (d.start, d.end) == (2, 5)
    assert d.body == []


def test_find_backtick_slides_directive():
    [d] = find_directives("```{nma-slides} Day slides\n:osf: snv4m\n:path: slides/day.pdf\n```\n")
    assert d.kind == "nma-slides"
    assert d.arg == "Day slides"
    assert d.options == {"osf": "snv4m", "path": "slides/day.pdf"}


def test_ignores_directive_inside_example_fence():
    text = "````markdown\n:::{nma-video} T\n:youtube: x\n:::\n````\n"
    assert find_directives(text) == []


def test_ignores_directive_nested_in_other_directive():
    text = ":::{note}\n:::{nma-video} T\n:youtube: x\n:::\n:::\n"
    # Only top-level media directives are supported (see validate_content docs)
    assert find_directives(text) == []


def test_unclosed_directive_has_end_minus_one():
    [d] = find_directives(":::{nma-video} T\n:youtube: x\n")
    assert d.end == -1


def test_body_lines_are_captured():
    [d] = find_directives(":::{nma-video} T\n:youtube: x\nstray text\n:::\n")
    assert d.body == ["stray text"]


from nma_kit.media import validate_directive


def _errors(text):
    [d] = find_directives(text)
    return validate_directive(d)


def test_valid_video_has_no_errors():
    assert _errors(VIDEO_MD) == []


def test_video_without_source_is_error():
    [err] = _errors(":::{nma-video} T\n:::\n")
    assert "at least one of :youtube:, :bilibili:, :osf:" in err
    assert err.startswith("line 1: ")


def test_video_without_title_is_error():
    [err] = _errors(":::{nma-video}\n:youtube: x\n:::\n")
    assert "needs a title" in err


def test_unknown_option_is_error():
    [err] = _errors(":::{nma-video} T\n:youtube: x\n:vimeo: y\n:::\n")
    assert "unknown option :vimeo:" in err


def test_unclosed_is_error():
    [err] = _errors(":::{nma-slides} x\n:osf: snv4m\n")
    assert "never closed" in err


def test_body_is_error():
    [err] = _errors(":::{nma-video} T\n:youtube: x\nhello\n:::\n")
    assert "takes no body" in err


from nma_kit.media import (
    copy_slide_files,
    expand_notebook,
    missing_slide_errors,
    osf_slides_embed_url,
    slide_cdn_url,
    slides_cell_source,
    video_cell_source,
)


def test_video_cell_source():
    [d] = find_directives(VIDEO_MD)
    src = video_cell_source(d)
    assert src.startswith("# @title Video 1: Linear Dynamical Systems\n")
    assert "video_ids = [('Youtube', '87z6OR7-DBI'), ('Bilibili', 'BV1up4y1S7wj')]" in src
    assert "tabs = widgets.Tab()" in src
    compile(src, "<cell>", "exec")


def test_video_sources_use_fixed_order():
    [d] = find_directives(":::{nma-video} T\n:osf: o1\n:youtube: y1\n:::\n")
    assert "video_ids = [('Youtube', 'y1'), ('Osf', 'o1')]" in video_cell_source(d)


def test_valid_slides_have_no_errors():
    assert _errors(":::{nma-slides}\n:osf: snv4m\n:::\n") == []
    assert _errors(":::{nma-slides} Day 3\n:path: slides/day3.pdf\n:::\n") == []
    assert _errors(":::{nma-slides}\n:osf: a\n:path: slides/b.pdf\n:::\n") == []


def test_slides_without_source_is_error():
    [err] = _errors(":::{nma-slides} Day 3\n:::\n")
    assert "at least one of :osf:, :path:" in err


def test_slides_old_id_argument_and_title_option_are_errors():
    errors = _errors(":::{nma-slides} snv4m\n:title: T\n:::\n")
    assert any("unknown option :title:" in e for e in errors)


@pytest.mark.parametrize("path", ["/slides/a.pdf", "slides/../a.pdf", "other/a.pdf", "slides/a.pptx", "a.pdf"])
def test_slides_bad_path_is_error(path):
    errors = _errors(f":::{{nma-slides}}\n:path: {path}\n:::\n")
    assert len(errors) == 1
    assert ":path:" in errors[0]


def test_slides_path_uses_configured_folder():
    [d] = find_directives(":::{nma-slides}\n:path: decks/a.pdf\n:::\n")
    assert validate_directive(d, slides_dir="decks") == []
    assert validate_directive(d) != []


def test_slides_cell_source_osf_only():
    [d] = find_directives(":::{nma-slides}\n:osf: snv4m\n:::\n")
    src = slides_cell_source(d)
    assert src.startswith("# @title Tutorial slides\n")
    assert "https://osf.io/download/snv4m/" in src
    assert "mfr.ca-1.osf.io/render?url=https://osf.io/snv4m/" in src
    compile(src, "<cell>", "exec")


def test_slides_cell_source_path_uses_published_url():
    [d] = find_directives(":::{nma-slides} Day 3 slides\n:path: slides/day3.pdf\n:::\n")
    url = "https://cdn.jsdelivr.net/gh/o/r@nb/notebooks/tutorials/D1/slides/day3.pdf"
    src = slides_cell_source(d, path_url=lambda p: url)
    assert src.startswith("# @title Day 3 slides\n")
    assert url in src
    assert "osf.io" not in src
    compile(src, "<cell>", "exec")


def test_slides_cell_source_both_backends_make_tabs():
    [d] = find_directives(":::{nma-slides}\n:osf: snv4m\n:path: slides/a.pdf\n:::\n")
    src = slides_cell_source(d, path_url=lambda p: "https://example.org/" + p)
    assert "widgets.Tab()" in src
    assert "'OSF'" in src and "'PDF'" in src
    compile(src, "<cell>", "exec")


def _run_slides_cell(src, in_colab):
    """Run a slides cell with IPython.display faked; return what it displayed."""
    import sys
    import types

    shown = []
    display_mod = types.ModuleType("IPython.display")
    display_mod.IFrame = lambda src, width, height: ("iframe", src)
    display_mod.HTML = lambda html: ("html", html)
    display_mod.display = shown.append
    widgets_mod = types.ModuleType("ipywidgets")

    class Output:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    widgets_mod.widgets = types.SimpleNamespace(Output=Output, Tab=lambda: types.SimpleNamespace(set_title=lambda i, t: None))
    fakes = {"IPython": types.ModuleType("IPython"), "IPython.display": display_mod, "ipywidgets": widgets_mod}
    saved = {k: sys.modules.get(k) for k in [*fakes, "google.colab"]}
    sys.modules.update(fakes)
    if in_colab:
        sys.modules["google.colab"] = types.ModuleType("google.colab")
    else:
        sys.modules.pop("google.colab", None)
    try:
        exec(compile(src, "<cell>", "exec"), {})
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return shown


def _embeds(shown):
    return [x for x in shown if isinstance(x, tuple)]


def test_slides_pdf_is_a_link_in_colab_and_an_iframe_elsewhere():
    [d] = find_directives(":::{nma-slides}\n:path: slides/a.pdf\n:::\n")
    src = slides_cell_source(d, path_url=lambda p: "https://x/" + p)
    assert _embeds(_run_slides_cell(src, in_colab=False)) == [("iframe", "https://x/slides/a.pdf")]
    [(kind, html)] = _embeds(_run_slides_cell(src, in_colab=True))
    assert kind == "html" and 'href="https://x/slides/a.pdf"' in html


def test_slides_osf_stays_an_iframe_in_colab():
    # The OSF renderer returns an HTML page, which the sandboxed Colab frame can show.
    [d] = find_directives(":::{nma-slides}\n:osf: snv4m\n:::\n")
    [(kind, src)] = _embeds(_run_slides_cell(slides_cell_source(d), in_colab=True))
    assert kind == "iframe" and src == osf_slides_embed_url("snv4m")


def test_slides_cell_without_published_url_skips_path():
    [d] = find_directives(":::{nma-slides}\n:path: slides/a.pdf\n:::\n")
    src = slides_cell_source(d)
    assert "slides/a.pdf" not in src or "course website" in src
    compile(src, "<cell>", "exec")


SLIDE_URLS = json.loads((Path(__file__).parents[1] / "fixtures" / "media" / "slide_urls.json").read_text())


@pytest.mark.parametrize("case", SLIDE_URLS["cdn"], ids=lambda c: f"{c['branch']}-{c['path']}")
def test_slide_cdn_url(case):
    assert slide_cdn_url(case["repo"], case["branch"], case["day"], case["path"]) == case["url"]


@pytest.mark.parametrize("case", SLIDE_URLS["osf"], ids=lambda c: c["id"])
def test_osf_slides_embed_url(case):
    assert osf_slides_embed_url(case["id"]) == case["url"]


def test_expand_notebook_passes_path_url():
    nb = {"cells": [{"cell_type": "markdown", "id": "c", "metadata": {},
                     "source": ":::{nma-slides}\n:path: slides/a.pdf\n:::\n"}]}
    assert expand_notebook(nb, path_url=lambda p: "https://x/" + p) == 1
    assert "https://x/slides/a.pdf" in "".join(nb["cells"][0]["source"])


def test_missing_slide_file_is_error(tmp_path):
    text = ":::{nma-slides}\n:path: slides/a.pdf\n:::\n"
    [err] = missing_slide_errors(text, tmp_path)
    assert "slides/a.pdf" in err and "does not exist" in err
    (tmp_path / "slides").mkdir()
    (tmp_path / "slides" / "a.pdf").write_bytes(b"%PDF")
    assert missing_slide_errors(text, tmp_path) == []


def test_copy_slide_files(tmp_path):
    src, dest = tmp_path / "src", tmp_path / "dest"
    (src / "slides").mkdir(parents=True)
    (src / "slides" / "a.pdf").write_bytes(b"%PDF")
    text = ":::{nma-slides}\n:path: slides/a.pdf\n:::\n:::{nma-slides}\n:path: slides/gone.pdf\n:::\n"
    assert copy_slide_files(text, src, dest) == 1
    assert (dest / "slides" / "a.pdf").read_bytes() == b"%PDF"



CELL_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _md_cell(text, cell_id="abc123"):
    return {"cell_type": "markdown", "id": cell_id, "metadata": {},
            "source": text.splitlines(keepends=True)}


def test_expand_splits_markdown_cell():
    nb = {"cells": [_md_cell(VIDEO_MD)]}
    assert expand_notebook(nb) == 1
    cells = nb["cells"]
    assert [c["cell_type"] for c in cells] == ["markdown", "code", "markdown"]
    assert "".join(cells[0]["source"]) == "Intro text"
    assert "".join(cells[2]["source"]) == "Outro text"
    code = cells[1]
    assert code["metadata"] == {"cellView": "form", "tags": ["hide-input"]}
    assert code["outputs"] == [] and code["execution_count"] is None
    assert "".join(code["source"]).startswith("# @title Video 1")
    ids = [c["id"] for c in cells]
    assert len(set(ids)) == 3 and all(CELL_ID_RE.match(i) for i in ids)


def test_expand_drops_empty_markdown_fragments():
    nb = {"cells": [_md_cell(":::{nma-slides} snv4m\n:::\n")]}
    expand_notebook(nb)
    assert [c["cell_type"] for c in nb["cells"]] == ["code"]


def test_expand_handles_two_directives_in_one_cell():
    text = ":::{nma-slides} s1\n:::\n\nmiddle\n\n:::{nma-video} V\n:youtube: y\n:::\n"
    nb = {"cells": [_md_cell(text)]}
    assert expand_notebook(nb) == 2
    assert [c["cell_type"] for c in nb["cells"]] == ["code", "markdown", "code"]


def test_expand_leaves_other_cells_alone_and_is_idempotent():
    code = {"cell_type": "code", "id": "c1", "metadata": {}, "outputs": [],
            "execution_count": None, "source": ["x = 1"]}
    plain = _md_cell("just text", "m1")
    nb = {"cells": [code, plain]}
    assert expand_notebook(nb) == 0
    assert nb["cells"] == [code, plain]
