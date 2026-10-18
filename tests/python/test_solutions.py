from nma_kit.solutions import find_blocks

EXERCISE = '''```{code-cell} python
def f(x):
  raise NotImplementedError("Student exercise: implement f")
  return ...
```'''

SOLUTION = '''::::{nma-solution}
```python
def f(x):
  return 2 * x
```
::::'''

EXPLANATION = ''':::{nma-explanation}
For $a<0$ the solution **decays**.
:::'''

PAGE = f"""# Title

{EXERCISE}

{SOLUTION}

Some prose.

```{{code-cell}} python
:tags: [hide-input]
plot()
```

{EXPLANATION}
"""


def kinds(text):
    return [b.kind for b in find_blocks(text)]


# --- Task 1: scanning -------------------------------------------------------

def test_finds_blocks_in_order():
    assert kinds(PAGE) == ["exercise", "nma-solution", "code-cell", "nma-explanation"]


def test_block_positions_and_body():
    ex, sol, cell, expl = find_blocks(PAGE)
    assert (ex.start, ex.end) == (2, 6)
    assert (sol.start, sol.end) == (8, 13)
    assert sol.body_lines == ["```python", "def f(x):", "  return 2 * x", "```"]
    assert expl.body_lines == ["For $a<0$ the solution **decays**."]
    assert cell.options == {"tags": "[hide-input]"}
    assert cell.body_lines == ["plot()"]
    assert not any(b.nested for b in (ex, sol, cell, expl))


def test_ignores_blocks_inside_literal_example_fence():
    text = f"`````markdown\n{EXERCISE}\n\n{SOLUTION}\n`````\n"
    assert kinds(text) == []


def test_flags_blocks_nested_in_directive():
    text = f":::::{{note}}\n{SOLUTION}\n:::::\n"
    [sol] = find_blocks(text)
    assert sol.kind == "nma-solution" and sol.nested


def test_same_length_colon_nesting_is_detected():
    text = ":::{dropdown} Answer\n:::{nma-explanation}\nText\n:::\n:::\n"
    [expl] = find_blocks(text)
    assert expl.nested
    assert expl.body_lines == ["Text"]


def test_backtick_directive_form():
    text = "````{nma-solution}\n```python\nx = 1\n```\n````\n"
    [sol] = find_blocks(text)
    assert sol.kind == "nma-solution"
    assert sol.body_lines == ["```python", "x = 1", "```"]


def test_unclosed_block_has_end_minus_one():
    [sol] = find_blocks(":::{nma-explanation}\ntext\n")
    assert sol.end == -1


def test_arg_and_options_are_parsed():
    [expl] = find_blocks(":::{nma-explanation} extra\n:label: x\nText\n:::\n")
    assert expl.arg == "extra"
    assert expl.options == {"label": "x"}
    assert expl.body_lines == ["Text"]


def test_code_cell_inside_code_cell_body_is_not_a_block():
    text = "```{code-cell} python\ns = '''\n:::{nma-solution}\n'''\n```\n"
    assert kinds(text) == ["code-cell"]


# --- Task 2: validation -----------------------------------------------------

from nma_kit.solutions import validate


def test_valid_page_has_no_errors():
    assert validate(PAGE) == []


def test_page_without_exercises_is_valid():
    assert validate("# Hi\n\n```{code-cell} python\nx = 1\n```\n") == []


def test_to_remove_marker_is_error():
    text = "```{code-cell} python\n:tags: [hide-input]\n# to_remove solution\nx = 1\n```\n"
    [err] = validate(text)
    assert err.startswith("line 1:") and "# to_remove" in err


def test_to_remove_inside_example_fence_is_fine():
    text = "````markdown\n```{code-cell} python\n# to_remove solution\n```\n````\n"
    assert validate(text) == []


def test_nested_solution_is_error():
    text = f"{EXERCISE}\n\n{SOLUTION}\n\n:::::{{note}}\n{SOLUTION}\n:::::\n"
    errors = validate(text)
    assert len(errors) == 1 and "top level" in errors[0]


def test_unclosed_is_error():
    errors = validate(":::{nma-explanation}\ntext\n")
    assert any("never closed" in e for e in errors)


def test_argument_and_options_are_errors():
    errors = validate(":::{nma-explanation} extra\n:label: x\nText\n:::\n")
    assert any("argument" in e for e in errors)
    assert any(":label:" in e for e in errors)


def test_solution_body_must_be_one_python_fence():
    bad_bodies = [
        "x = 1",                          # no fence
        "```\nx = 1\n```",                # no language
        "```r\nx <- 1\n```",              # wrong language
        "```python\n```",                 # empty code
        "```python\nx = 1\n```\nmore",    # stray text
    ]
    for body in bad_bodies:
        text = f"{EXERCISE}\n\n::::{{nma-solution}}\n{body}\n::::\n"
        errors = validate(text)
        assert any("single ```python fence" in e for e in errors), body


def test_empty_explanation_is_error():
    errors = validate(":::{nma-explanation}\n\n:::\n")
    assert any("empty" in e for e in errors)


def test_solution_without_exercise_is_error():
    errors = validate(f"Prose\n\n{SOLUTION}\n")
    assert any("directly after an exercise" in e for e in errors)


def test_prose_between_exercise_and_solution_is_error():
    errors = validate(f"{EXERCISE}\n\nProse\n\n{SOLUTION}\n")
    assert any("directly after an exercise" in e for e in errors)
    assert any("no {nma-solution}" in e for e in errors)


def test_exercise_without_solution_is_error():
    [err] = validate(f"{EXERCISE}\n\nProse\n")
    assert err.startswith("line 1:") and "no {nma-solution}" in err


# --- Task 3: naming, urls, extraction ---------------------------------------

from nma_kit.solutions import EXPLANATION as EXPL_KIND
from nma_kit.solutions import SOLUTION as SOL_KIND
from nma_kit.solutions import exercise_pairs, extract, solution_filename, solution_url


def test_solution_filename():
    assert solution_filename("W2D1_Tutorial1", SOL_KIND, 1) == "W2D1_Tutorial1_Solution_1.py"
    assert solution_filename("W2D1_Tutorial1", EXPL_KIND, 3) == "W2D1_Tutorial1_Explanation_3.md"


def test_solution_url():
    assert solution_url("org/repo", "W2D1_Examples", "T_Solution_1.py") == (
        "https://github.com/org/repo/blob/notebooks-branch/notebooks/"
        "W2D1_Examples/solutions/T_Solution_1.py"
    )


def test_extract_numbers_each_kind_separately():
    text = f"{PAGE}\n{EXERCISE}\n\n{SOLUTION}\n"
    items = extract(text, "T")
    assert [(i.kind, i.n, i.filename) for i in items] == [
        (SOL_KIND, 1, "T_Solution_1.py"),
        (EXPL_KIND, 1, "T_Explanation_1.md"),
        (SOL_KIND, 2, "T_Solution_2.py"),
    ]
    assert items[0].content == "def f(x):\n  return 2 * x\n"
    assert items[1].content == "For $a<0$ the solution **decays**.\n"


def test_exercise_pairs():
    [(exercise, solution)] = exercise_pairs(PAGE)
    assert exercise.startswith("def f(x):\n  raise NotImplementedError")
    assert exercise.endswith("return ...")
    assert solution == "def f(x):\n  return 2 * x"


def test_exercise_pairs_strip_cell_options():
    text = f"```{{code-cell}} python\n:tags: []\nraise NotImplementedError\n```\n\n{SOLUTION}\n"
    [(exercise, _)] = exercise_pairs(text)
    assert exercise == "raise NotImplementedError"


# --- Task 4: notebook splitting ---------------------------------------------

from nma_kit.solutions import split_notebook


def md(source, cell_id="m"):
    return {"cell_type": "markdown", "id": cell_id, "metadata": {}, "source": source}


def code(source, cell_id="c"):
    return {"cell_type": "code", "id": cell_id, "metadata": {}, "execution_count": None,
            "outputs": [], "source": source}


def notebook(*cells):
    return {"cells": list(cells), "metadata": {}, "nbformat": 4, "nbformat_minor": 5}


def text_of(cell):
    src = cell["source"]
    return "".join(src) if isinstance(src, list) else src


NB = notebook(
    md("# T", "a"),
    code('def f(x):\n  raise NotImplementedError("x")', "b"),
    md(f"{SOLUTION}\n\nProse after.\n\n{EXPLANATION}", "c"),
    code("plot()", "d"),
    md(f"{SOLUTION}", "e"),
)
URL = "https://github.com/org/repo/blob/notebooks-branch/notebooks/Day/solutions/"


def test_student_notebook_has_links_and_no_solution_code():
    student, _, _ = split_notebook(NB, "T", "Day", "org/repo")
    texts = [(c["cell_type"], text_of(c)) for c in student["cells"]]
    assert texts == [
        ("markdown", "# T"),
        ("code", 'def f(x):\n  raise NotImplementedError("x")'),
        ("markdown", f"[*Click for solution*]({URL}T_Solution_1.py)"),
        ("markdown", "Prose after."),
        ("markdown", f"[*Click for explanation*]({URL}T_Explanation_1.md)"),
        ("code", "plot()"),
        ("markdown", f"[*Click for solution*]({URL}T_Solution_2.py)"),
    ]
    assert "return 2 * x" not in str(student)
    assert "decays" not in str(student)


def test_instructor_notebook_has_solutions_and_explanations():
    _, instructor, _ = split_notebook(NB, "T", "Day", "org/repo")
    cells = instructor["cells"]
    assert [c["cell_type"] for c in cells] == [
        "markdown", "code", "code", "markdown", "markdown", "code", "code"]
    assert text_of(cells[2]) == "# Solution\ndef f(x):\n  return 2 * x"
    assert cells[2]["metadata"] == {}
    assert "to_remove" not in str(instructor)
    assert cells[2]["outputs"] == [] and cells[2]["execution_count"] is None
    assert text_of(cells[4]) == "**Explanation**\n\nFor $a<0$ the solution **decays**."


def test_files_are_returned():
    _, _, files = split_notebook(NB, "T", "Day", "org/repo")
    assert files == {
        "T_Solution_1.py": "def f(x):\n  return 2 * x\n",
        "T_Explanation_1.md": "For $a<0$ the solution **decays**.\n",
        "T_Solution_2.py": "def f(x):\n  return 2 * x\n",
    }


def test_cell_ids_are_unique():
    student, instructor, _ = split_notebook(NB, "T", "Day", "org/repo")
    for nb in (student, instructor):
        ids = [c["id"] for c in nb["cells"]]
        assert len(ids) == len(set(ids))


def test_notebook_without_directives_is_unchanged():
    nb = notebook(md("# T", "a"), code("x = 1", "b"))
    student, instructor, files = split_notebook(nb, "T", "Day", "org/repo")
    assert student == nb and instructor == nb and files == {}


def test_input_notebook_is_not_mutated():
    before = str(NB)
    split_notebook(NB, "T", "Day", "org/repo")
    assert str(NB) == before


# --- Task 5: run-all fallback -----------------------------------------------

import pytest
from IPython.core.interactiveshell import InteractiveShell

from nma_kit.solutions import FALLBACK_NOTE, NO_FALLBACK_MARKER, fallback_cell_source, fallback_md_block

EX_SRC = 'def f(x):\n  raise NotImplementedError("Student exercise: implement f")\n  return ...\n\nresult = f(3)'
SOL_SRC = "def f(x):\n  return 2 * x\n\nresult = f(3)"


@pytest.fixture
def shell():
    ip = InteractiveShell.instance()
    saved = list(ip.input_transformers_post)
    ip.user_ns.pop("result", None)
    yield ip
    ip.input_transformers_post[:] = saved


def test_unfinished_exercise_runs_solution(shell, capsys):
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC)]))
    result = shell.run_cell(EX_SRC)
    assert result.success
    assert shell.user_ns["result"] == 6
    assert FALLBACK_NOTE in capsys.readouterr().out


def test_edited_but_unfinished_exercise_still_falls_back(shell):
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC)]))
    edited = EX_SRC.replace("  return ...", "  y = x  # started\n  return ...")
    assert shell.run_cell(edited).success
    assert shell.user_ns["result"] == 6


def test_finished_exercise_runs_student_code(shell, capsys):
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC)]))
    shell.run_cell("def f(x):\n  return 10 * x\n\nresult = f(3)")
    assert shell.user_ns["result"] == 30
    assert FALLBACK_NOTE not in capsys.readouterr().out


def test_unrelated_raise_is_left_alone(shell):
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC)]))
    result = shell.run_cell("class Base:\n  def go(self):\n    raise NotImplementedError\nBase().go()")
    assert isinstance(result.error_in_exec, NotImplementedError)


def test_picks_the_matching_exercise(shell):
    other_ex = 'def g(a, b):\n  raise NotImplementedError("Student exercise: g")\n\nresult = g(1, 2)'
    other_sol = "def g(a, b):\n  return a + b\n\nresult = g(1, 2)"
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC), (other_ex, other_sol)]))
    shell.run_cell(other_ex)
    assert shell.user_ns["result"] == 3


def test_rerunning_setup_keeps_one_transformer(shell):
    before = len(shell.input_transformers_post)
    source = fallback_cell_source([(EX_SRC, SOL_SRC)])
    assert shell.run_cell(source).success
    assert shell.run_cell(source).success
    assert len(shell.input_transformers_post) == before + 1


def test_setup_leaves_no_names_behind(shell):
    names = set(shell.user_ns)
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC)]))
    assert set(shell.user_ns) - names <= {"_", "__", "___"} | {k for k in shell.user_ns if k.startswith("_i")}


def test_md_block_is_a_hidden_code_cell():
    block = fallback_md_block([(EX_SRC, SOL_SRC)])
    lines = block.splitlines()
    assert lines[0] == "```{code-cell} python"
    assert lines[1] == ":tags: [remove-cell]"
    assert lines[2].startswith("# nma-exercise-fallback")
    assert lines[-1] == "```"
    assert "\n```\n" not in block[:-4]


def test_commented_out_raise_counts_as_finished(shell):
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC)]))
    shell.run_cell(EX_SRC.replace("  raise", "  # raise").replace("return ...", "return 5 * x"))
    assert shell.user_ns["result"] == 15


def test_injected_fallback_cell_is_not_an_exercise():
    text = fallback_md_block([(EX_SRC, SOL_SRC)]) + "\n"
    assert [b.kind for b in find_blocks(text)] == ["code-cell"]
    assert validate(text) == []


def test_commented_out_raise_is_not_an_exercise():
    text = "```{code-cell} python\ndef f():\n  # raise NotImplementedError\n  return 1\n```\n"
    assert [b.kind for b in find_blocks(text)] == ["code-cell"]


def test_marked_exercise_is_not_replaced(shell, capsys):
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC)]))
    result = shell.run_cell(EX_SRC + f"\n# {NO_FALLBACK_MARKER}\n")
    assert isinstance(result.error_in_exec, NotImplementedError)
    assert FALLBACK_NOTE not in capsys.readouterr().out


def test_marker_keeps_traceback_line_numbers(shell):
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC)]))
    result = shell.run_cell(EX_SRC + f"\n# {NO_FALLBACK_MARKER}\n")
    tb, lines = result.error_in_exec.__traceback__, {}
    while tb:
        lines[tb.tb_frame.f_code.co_name] = tb.tb_lineno
        tb = tb.tb_next
    assert lines["f"] == 2  # the raise line in f


def test_unfinished_exercise_without_marker_still_falls_back(shell):
    shell.run_cell(fallback_cell_source([(EX_SRC, SOL_SRC)]))
    assert shell.run_cell(EX_SRC).success and shell.user_ns["result"] == 6
