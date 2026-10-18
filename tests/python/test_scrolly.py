import json
from pathlib import Path

import pytest

from nma_kit import scrolly as nma_scrolly
from nma_kit.scrolly import cell_key, find_markers, is_scrolly, parse_params, validate

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "scrolly"

FRONT = "---\ntitle: T\nlayout: scrolly\nkernelspec:\n  name: python3\n  display_name: Python 3\n---\n"
PLAIN_FRONT = "---\ntitle: T\nkernelspec:\n  name: python3\n  display_name: Python 3\n---\n"

PAGE = FRONT + """
Intro before the first step.

:::{step} hero
:kicker: neuromatch academy
:::
# Title

:::{step}
:section: One
:kicker: Exercise 1
:::
### Heading

:::{stage}
:style: list
1. one
2. two
:::

```{code-cell} python
a = 1  # @param [1, 2]
print(a)
```

:::{step}
:::
More prose.
"""


# --- fixtures shared with tests/js/scrolly.test.mjs -------------------------

@pytest.mark.parametrize("case", json.loads((FIXTURES / "cell_keys.json").read_text()),
                         ids=lambda c: c["name"])
def test_cell_key_fixture(case):
    assert nma_scrolly.canonical_code(case["code"]) == case["canonical"]
    assert cell_key(case["code"]) == case["key"]


@pytest.mark.parametrize("case", json.loads((FIXTURES / "params.json").read_text()),
                         ids=lambda c: c["name"])
def test_parse_params_fixture(case):
    if "error" in case:
        with pytest.raises(ValueError, match=case["error"]):
            parse_params(case["code"])
    else:
        assert parse_params(case["code"]) == case["params"]


def test_int_values_stay_ints():
    (p,) = parse_params('n = 3  # @param {type:"slider", min:1, max:10}')
    assert all(isinstance(p[k], int) for k in ("value", "min", "max", "step"))


# --- detection ----------------------------------------------------------------

def test_is_scrolly():
    assert is_scrolly(FRONT)
    assert is_scrolly("---\nlayout: 'scrolly'  # comment\n---\n")
    assert not is_scrolly(PLAIN_FRONT)
    assert not is_scrolly("layout: scrolly\n")          # not in frontmatter
    assert not is_scrolly("---\nsite:\n  layout: scrolly\n---\n")  # nested key


def test_find_markers():
    markers = find_markers(PAGE)
    assert [(m.kind, m.arg) for m in markers] == [("step", "hero"), ("step", ""), ("stage", ""), ("step", "")]
    assert markers[0].options == {"kicker": "neuromatch academy"}
    assert markers[2].body_lines == ["1. one", "2. two"]


def test_markers_in_example_fences_are_text():
    text = FRONT + "\n:::{step}\n:::\n\n````markdown\n:::{step} nonsense\n:bad: 1\n:::\n````\n"
    assert [m.kind for m in find_markers(text)] == ["step"]
    assert validate(text) == []


# --- validation ---------------------------------------------------------------

def test_valid_page():
    assert validate(PAGE) == []


def test_non_scrolly_page_without_markers_is_ignored():
    assert validate(PLAIN_FRONT + "\n```{code-cell} python\na = 1  # @param {bad}\n```\n") == []


def test_markers_need_layout_scrolly():
    errors = validate(PLAIN_FRONT + "\n:::{step}\n:::\n")
    assert len(errors) == 1 and "layout: scrolly" in errors[0] and errors[0].startswith("line 8:")


def test_scrolly_page_needs_a_step():
    errors = validate(FRONT + "\nJust prose.\n")
    assert len(errors) == 1 and "no {step}" in errors[0]


def test_step_rules():
    errors = validate(FRONT + "\n:::{step} big\n:color: red\nbody text\n:::\n")
    assert any("hero" in e for e in errors)
    assert any(":color:" in e for e in errors)
    assert any("no body" in e for e in errors)


def test_marker_must_be_top_level():
    errors = validate(FRONT + "\n:::{step}\n:::\n\n::::{note}\n:::{step}\n:::\n::::\n")
    assert len(errors) == 1 and "top level" in errors[0]


def test_unclosed_marker():
    errors = validate(FRONT + "\n:::{step}\n:::\n\n:::{stage}\ntext\n")
    assert any("never closed" in e for e in errors)


def test_stage_rules():
    before = validate(FRONT + "\n:::{stage}\nx\n:::\n\n:::{step}\n:::\n")
    assert any("before the first {step}" in e for e in before)
    twice = validate(FRONT + "\n:::{step}\n:::\n:::{stage}\nx\n:::\n:::{stage}\ny\n:::\n")
    assert len(twice) == 1 and "more than one {stage}" in twice[0]
    opts = validate(FRONT + "\n:::{step}\n:::\n:::{stage} arg\n:style: grid\n:size: 2\nx\n:::\n")
    assert any("takes no argument" in e for e in opts)
    assert any(":style:" in e for e in opts)
    assert any(":size:" in e for e in opts)


def test_bad_param_reported_with_page_line():
    text = FRONT + "\n:::{step}\n:::\n\n```{code-cell} python\nx = 1\na = 1  # @param {type:\"string\"}\n```\n"
    errors = validate(text)
    assert len(errors) == 1
    assert errors[0].startswith("line 14:") and "# @param" in errors[0]


def test_param_errors_inside_exercise_cells_too():
    text = FRONT + "\n:::{step}\n:::\n\n```{code-cell} python\na = 1  # @param [3]\nraise NotImplementedError\n```\n"
    assert any("# @param" in e for e in validate(text))


# --- Task 2: notebooks ----------------------------------------------------------

from nma_kit.scrolly import flatten_for_notebook, params_to_interact, rewrite_notebook_params


def test_flatten_removes_markers_and_unwraps_stage():
    flat = flatten_for_notebook(PAGE)
    assert "{step}" not in flat and "{stage}" not in flat
    assert ":section:" not in flat and ":style:" not in flat
    assert "*neuromatch academy*\n\n# Title" in flat
    assert "*Exercise 1*\n\n### Heading" in flat
    assert "\n1. one\n2. two\n" in flat
    assert "More prose." in flat
    # code cells and frontmatter are untouched
    assert "```{code-cell} python\na = 1  # @param [1, 2]\nprint(a)\n```" in flat
    assert flat.startswith(FRONT)


def test_flatten_leaves_other_pages_and_examples_alone():
    plain = PLAIN_FRONT + "\n:::{note}\nx\n:::\n"
    assert flatten_for_notebook(plain) == plain
    example = FRONT + "\n:::{step}\n:::\n\n````markdown\n:::{step}\n:kicker: K\n:::\n````\n"
    assert "````markdown\n:::{step}\n:kicker: K\n:::\n````" in flatten_for_notebook(example)


DEMO = '''# @title Demo
# @markdown Move the sliders.
a = -0.5   # @param {type:"slider", min:-2.5, max:1.5, step:0.25}
n = 3      # @param {type:"slider", min:1, max:10}
option = 'x'  # @param ['x', 'y']
calls.append((a, n, option))'''


def test_params_to_interact_shape():
    code = params_to_interact(DEMO)
    assert code.startswith("# @title Demo\n# @markdown Move the sliders.\nimport ipywidgets as widgets\n")
    assert "a=widgets.FloatSlider(value=-0.5, min=-2.5, max=1.5, step=0.25" in code
    assert "n=widgets.IntSlider(value=3, min=1, max=10, step=1" in code
    assert "option=widgets.Dropdown(options=['x', 'y'], value='x')" in code
    assert "def _demo(a, n, option):\n    calls.append((a, n, option))" in code
    assert "@param" not in code


def test_params_to_interact_runs_with_defaults():
    calls = []
    exec(params_to_interact(DEMO), {"calls": calls})
    assert calls == [(-0.5, 3, "x")]


def test_params_to_interact_without_params_is_unchanged():
    assert params_to_interact("x = 1\nprint(x)") == "x = 1\nprint(x)"


def test_params_to_interact_empty_body():
    code = params_to_interact("a = 1  # @param [1, 2]")
    assert code.rstrip().endswith("def _demo(a):\n    pass")


def test_rewrite_notebook_params():
    nb = {"cells": [
        {"cell_type": "markdown", "source": ["a = 1  # @param [1, 2]"]},
        {"cell_type": "code", "source": ["a = 1  # @param [1, 2]\n", "print(a)"], "metadata": {}},
        {"cell_type": "code", "source": "print(2)", "metadata": {}},
    ]}
    assert rewrite_notebook_params(nb) == 1
    assert nb["cells"][0]["source"] == ["a = 1  # @param [1, 2]"]
    assert "widgets.interact" in "".join(nb["cells"][1]["source"])
    assert nb["cells"][2]["source"] == "print(2)"


# --- Task 3: pre-render -------------------------------------------------------------

RENDER_PAGE = FRONT + '''
```{code-cell} python
:tags: [remove-cell]
import matplotlib.pyplot as plt
from pathlib import Path
here = Path.cwd().name
```

:::{step}
:::
Prose.

```{code-cell} python
print("hello from", here)
```

```{code-cell} python
:tags: [remove-input]
plt.plot([0, 1], [1, 0])
plt.show()
```

```{code-cell} python
def f(x):
    raise NotImplementedError("Student exercise")
```

::::{nma-solution}
```python
def f(x):
    return 2 * x
```
::::

```{code-cell} python
k = 3  # @param [1, 3]
print(f(k))
6 * 7
```
'''


def _render_tree(tmp_path, page_text):
    page = tmp_path / "tutorials" / "Day" / "T.md"
    page.parent.mkdir(parents=True)
    page.write_text(page_text)
    return page


def test_render_page_writes_outputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _render_tree(tmp_path, RENDER_PAGE)
    assert nma_scrolly.render_all() == 0
    data = json.loads((tmp_path / "_build" / "scrolly" / "Day" / "T.json").read_text())

    hello = data[cell_key('print("hello from", here)')]
    assert hello == {"stdout": "hello from Day\n", "images": [], "error": None}  # cwd = page dir
    plot = data[cell_key("plt.plot([0, 1], [1, 0])\nplt.show()")]
    assert len(plot["images"]) == 1 and plot["images"][0].startswith("iVBOR")  # base64 PNG
    demo = data[cell_key("k = 3  # @param [1, 3]\nprint(f(k))\n6 * 7")]
    assert demo["stdout"] == "6\n42\n"  # solution used, param default, last expression
    exercise = 'def f(x):\n    raise NotImplementedError("Student exercise")'
    assert cell_key(exercise) not in data


def test_render_failure_names_page_and_line(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _render_tree(tmp_path, FRONT + "\n:::{step}\n:::\n\n```{code-cell} python\nx = 1\n```\n\n```{code-cell} python\n1 / 0\n```\n")
    assert nma_scrolly.render_all() == 1
    err = capsys.readouterr().err
    assert "tutorials/Day/T.md:16:" in err and "ZeroDivisionError" in err


def test_render_skips_non_scrolly_pages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _render_tree(tmp_path, PLAIN_FRONT + "\n```{code-cell} python\n1 / 0\n```\n")
    assert nma_scrolly.render_all() == 0
    assert not (tmp_path / "_build" / "scrolly").exists()


# --- the real scrolly pages ---------------------------------------------------------

KIT = Path(__file__).resolve().parents[2]
DOC_PAGE = FIXTURES / "doc_page.md"  # copy of the template's scrolly how-to page
EXAMPLE_PAGE = KIT / "example-course" / "tutorials" / "W2D1_Examples" / "W2D1_Tutorial2.md"


@pytest.mark.parametrize("page", [DOC_PAGE, EXAMPLE_PAGE], ids=lambda p: p.stem)
def test_real_scrolly_pages_are_valid(page):
    text = page.read_text()
    assert is_scrolly(text)
    assert validate(text) == []


def test_doc_page_examples_are_literal():
    # The how-to page shows {step}/{stage}/{code-cell} syntax inside ````markdown
    # fences. Only its real markers may be found, and flattening must keep the
    # examples intact.
    text = DOC_PAGE.read_text()
    real_steps = [m for m in find_markers(text) if m.kind == nma_scrolly.STEP]
    assert len(real_steps) == 19      # the page's own steps, none from the examples
    assert text.count(":::{step}") > 19  # ...although the examples contain more
    flat = flatten_for_notebook(text)
    assert "````markdown\n---\ntitle: \"Tutorial 2: My topic\"\nlayout: scrolly" in flat
    assert ":::{step} hero\n:::\n# My topic" in flat  # example kept verbatim

