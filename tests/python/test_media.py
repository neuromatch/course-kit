import re

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
    [d] = find_directives("```{nma-slides} snv4m\n:title: Day slides\n```\n")
    assert d.kind == "nma-slides"
    assert d.arg == "snv4m"
    assert d.options == {"title": "Day slides"}


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


def test_valid_slides_has_no_errors():
    assert _errors(":::{nma-slides} snv4m\n:::\n") == []


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


def test_slides_without_id_is_error():
    [err] = _errors(":::{nma-slides}\n:::\n")
    assert "needs an OSF id" in err


def test_unclosed_is_error():
    [err] = _errors(":::{nma-slides} x\n")
    assert "never closed" in err


def test_body_is_error():
    [err] = _errors(":::{nma-video} T\n:youtube: x\nhello\n:::\n")
    assert "takes no body" in err


from nma_kit.media import slides_cell_source, video_cell_source


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


def test_slides_cell_source_default_title():
    [d] = find_directives(":::{nma-slides} snv4m\n:::\n")
    src = slides_cell_source(d)
    assert src.startswith("# @title Tutorial slides\n")
    assert 'link_id = "snv4m"' in src
    compile(src, "<cell>", "exec")


def test_slides_cell_source_custom_title():
    [d] = find_directives(":::{nma-slides} snv4m\n:title: Day 3 slides\n:::\n")
    assert slides_cell_source(d).startswith("# @title Day 3 slides\n")


from nma_kit.media import expand_notebook

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
