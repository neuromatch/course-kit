"""{nma-instructor}: validation and stripping from notebooks (the site side is js/src/instructor)."""

import json

import pytest

from nma_kit import instructor

FRONT = "---\ntitle: T\nkernelspec:\n  name: python3\n  display_name: Python 3\n---\n\n"
NOTE = ":::{nma-instructor}\nSay this first.\n:::\n"


def md(cells):
    return {"cells": [{"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)} for text in cells]}


def sources(nb):
    return ["".join(c["source"]) for c in nb["cells"]]


def test_a_good_note_is_valid():
    assert instructor.validate(FRONT + NOTE) == []


def test_a_note_with_math_a_code_fence_and_a_nested_block_is_valid():
    body = "Math $x^2$.\n\n```python\nprint(1)\n```\n\n::::{note}\nnested\n::::\n"
    assert instructor.validate(FRONT + f":::::{{nma-instructor}}\n{body}:::::\n") == []


@pytest.mark.parametrize(
    "text, message",
    [
        (":::{nma-instructor}\nnever closed\n", "is never closed"),
        (":::{nma-instructor}\n:::\n", "is empty"),
        (":::{nma-instructor} extra\ntext\n:::\n", "takes no argument"),
        (":::{nma-instructor}\n:foo: bar\ntext\n:::\n", "unknown option :foo:"),
        ("::::{note}\n:::{nma-instructor}\ntext\n:::\n::::\n", "top level"),
    ],
)
def test_validate_reports_each_problem_with_its_line(text, message):
    errors = instructor.validate(FRONT + text)
    assert len(errors) == 1 and message in errors[0], errors
    assert errors[0].startswith("line ")


def test_scrolly_pages_reject_notes():
    page = "---\nlayout: scrolly\nkernelspec:\n  name: python3\n---\n\n" + NOTE
    errors = instructor.validate(page)
    assert len(errors) == 1 and "scrolly" in errors[0]


def test_strip_removes_a_cell_that_is_only_a_note():
    nb = md(["# Title\n", NOTE])
    assert instructor.strip_notes(nb) == 1
    assert sources(nb) == ["# Title\n"]


def test_strip_keeps_the_text_around_a_note_in_the_same_cell():
    nb = md(["Before.\n\n" + NOTE + "\nAfter.\n"])
    assert instructor.strip_notes(nb) == 1
    assert sources(nb) == ["Before.\n\nAfter."]


def test_strip_removes_a_note_holding_a_code_example_whole():
    note = ":::::{nma-instructor}\nTry:\n\n```python\n:::\n```\n\n:::{note}\nx\n:::\n:::::\n"
    nb = md(["Keep.\n\n" + note])
    assert instructor.strip_notes(nb) == 1
    assert sources(nb) == ["Keep."]


def test_strip_counts_every_note_and_ignores_pages_without_any():
    assert instructor.strip_notes(md(["plain\n"])) == 0
    nb = md([NOTE, "between\n", NOTE])
    assert instructor.strip_notes(nb) == 2
    assert sources(nb) == ["between\n"]


PAGE = FRONT + "# Title\n\n" + NOTE + "\nMore text.\n"


def test_build_notebooks_strips_notes_from_student_and_instructor_notebooks(tmp_path, monkeypatch):
    from nma_kit.convert import build_notebooks, convert_md_to_notebook

    monkeypatch.chdir(tmp_path)
    page = tmp_path / "tutorials" / "D" / "T.md"
    page.parent.mkdir(parents=True)
    page.write_text(PAGE)
    out = tmp_path / "notebooks" / "tutorials" / "D" / "T.ipynb"
    convert_md_to_notebook(page.relative_to(tmp_path), out, dry_run=False)
    build_notebooks(page.relative_to(tmp_path), out.relative_to(tmp_path), "org/repo", False)
    for path in (out, out.parent / "instructor" / out.name):
        text = "".join("".join(c["source"]) for c in json.loads(path.read_text())["cells"])
        assert "nma-instructor" not in text and "Say this first" not in text
        assert "More text." in text


def test_check_reports_a_bad_note_with_the_page_and_line(tmp_path, monkeypatch):
    from nma_kit.convert import validate_content

    (tmp_path / "myst.yml").write_text("project:\n  github: https://github.com/o/r\n")
    page = tmp_path / "tutorials" / "D" / "T.md"
    page.parent.mkdir(parents=True)
    page.write_text(FRONT + ":::{nma-instructor}\n:::\n")
    monkeypatch.chdir(tmp_path)
    errors = validate_content()
    assert any("T.md" in e and "line 8" in e and "is empty" in e for e in errors), errors
