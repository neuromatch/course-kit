from pathlib import Path

from nma_kit.convert import add_badge_cell, prepare_site_md
from nma_kit.solutions import FALLBACK_SENTINEL

PAGE = """---
title: T
kernelspec:
  name: python3
  display_name: Python 3
---

# Title

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
"""


def prepare(path, times=1):
    for _ in range(times):
        prepare_site_md(path, "notebooks/D/T.ipynb", "org/repo", dry_run=False)
    return path.read_text()


def test_prepare_site_adds_badges_and_fallback(tmp_path):
    page = tmp_path / "T.md"
    page.write_text(PAGE)
    text = prepare(page)
    body = text.split("---\n", 2)[2]
    assert body.startswith("<a href=\"https://colab.research.google.com/github/org/repo/")
    assert text.count(FALLBACK_SENTINEL) == 1
    assert body.index("colab") < body.index(FALLBACK_SENTINEL) < body.index("# Title")
    assert "return 2 * x" in text.split("# Title")[0]  # solution is in the setup cell


def test_prepare_site_is_idempotent(tmp_path):
    page = tmp_path / "T.md"
    page.write_text(PAGE)
    once = prepare(page)
    assert prepare(page, times=2) == once


def test_prepare_site_without_exercises_adds_only_badges(tmp_path):
    page = tmp_path / "T.md"
    page.write_text(PAGE.split("```{code-cell}")[0])
    text = prepare(page, times=2)
    assert FALLBACK_SENTINEL not in text
    assert text.count("colab-badge.svg") == 1


def test_add_badge_cell_is_idempotent():
    nb = {"cells": [{"cell_type": "markdown", "id": "a", "metadata": {}, "source": ["# T"]}]}
    once = add_badge_cell(nb, "notebooks/D/T.ipynb", "org/repo")
    twice = add_badge_cell(once, "notebooks/D/T.ipynb", "org/repo")
    assert twice == once
    assert len(once["cells"]) == 2 and once["cells"][0]["id"] == "badges"
    assert len(nb["cells"]) == 1


from nma_kit.convert import injected_content_errors


def test_clean_source_has_no_injected_content_errors():
    assert injected_content_errors(PAGE) == []


def test_prepared_source_is_rejected(tmp_path):
    page = tmp_path / "T.md"
    page.write_text(PAGE)
    errors = injected_content_errors(prepare(page))
    assert len(errors) == 2
    assert any("badge" in e for e in errors) and any("fallback" in e for e in errors)


def test_badge_example_inside_code_block_is_fine():
    text = PAGE + '\n```html\n<a href="https://colab.research.google.com/x"><img src="colab-badge.svg"/></a>\n```\n'
    assert injected_content_errors(text) == []


FEEDBACK_PAGE = """---
title: T
feedback_prefix: W9D9_T1
kernelspec:
  name: python3
  display_name: Python 3
---

# Title

```{code-cell} python
x = 1
```

:::{nma-feedback} Some_Video
:::
"""


def test_build_notebooks_expands_feedback(tmp_path, monkeypatch):
    import json

    from nma_kit import feedback as nma_feedback
    from nma_kit.convert import build_notebooks, convert_md_to_notebook

    monkeypatch.chdir(tmp_path)
    page = tmp_path / "tutorials" / "D" / "T.md"
    page.parent.mkdir(parents=True)
    page.write_text(FEEDBACK_PAGE)
    out = tmp_path / "notebooks" / "D" / "T.ipynb"
    config = nma_feedback.FeedbackConfig("https://e.org", "proj", "key")

    convert_md_to_notebook(page.relative_to(tmp_path), out, dry_run=False)
    build_notebooks(page.relative_to(tmp_path), out.relative_to(tmp_path), "org/repo", False, config)

    for path in (out, out.parent / "instructor" / out.name):
        cells = json.loads(path.read_text())["cells"]
        sources = ["".join(c["source"]) for c in cells]
        assert "colab-badge.svg" in sources[0]
        assert sources[1].startswith("# @title Import feedback gadget")
        assert "feedback_prefix = 'W9D9_T1'" in sources[1]
        assert sources[-1] == '# @title Submit your feedback\ncontent_review(f"{feedback_prefix}_Some_Video")'
        assert not any("{nma-feedback}" in s for s in sources)


SCROLLY_PAGE = """---
title: T
layout: scrolly
kernelspec:
  name: python3
  display_name: Python 3
---

:::{step} hero
:kicker: Hello
:::
# Title

:::{step}
:::
Prose.

:::{stage}
- objective
:::

```{code-cell} python
:tags: [hide-input]
a = 1  # @param [1, 2]
print(a)
```

```{code-cell} python
def f():
    raise NotImplementedError("x")
```

::::{nma-solution}
```python
def f():
    return 1
```
::::
"""


def test_build_notebooks_flattens_scrolly_pages(tmp_path, monkeypatch):
    import json

    from nma_kit.convert import build_notebooks, convert_md_to_notebook

    monkeypatch.chdir(tmp_path)
    page = tmp_path / "tutorials" / "D" / "T.md"
    page.parent.mkdir(parents=True)
    page.write_text(SCROLLY_PAGE)
    out = tmp_path / "notebooks" / "D" / "T.ipynb"

    convert_md_to_notebook(page.relative_to(tmp_path), out, dry_run=False)
    build_notebooks(page.relative_to(tmp_path), out.relative_to(tmp_path), "org/repo", False, None)

    assert page.read_text() == SCROLLY_PAGE  # source untouched
    student = json.loads(out.read_text())["cells"]
    text = "\n".join("".join(c["source"]) for c in student)
    assert "{step}" not in text and "{stage}" not in text
    assert "*Hello*" in text and "- objective" in text
    assert "@widgets.interact(a=widgets.Dropdown(options=[1, 2], value=1))" in text
    assert "Click for solution" in text
    instructor = json.loads((out.parent / "instructor" / out.name).read_text())["cells"]
    assert any("".join(c["source"]).startswith("# Solution") for c in instructor)


def test_prepare_site_skips_fallback_on_scrolly_pages(tmp_path):
    page = tmp_path / "T.md"
    page.write_text(SCROLLY_PAGE)
    prepare_site_md(page, "notebooks/D/T.ipynb", "org/repo", dry_run=False)
    text = page.read_text()
    assert "colab-badge.svg" in text
    assert FALLBACK_SENTINEL not in text


def test_validate_content_reports_scrolly_errors(tmp_path, monkeypatch):
    from nma_kit.convert import validate_content

    monkeypatch.chdir(tmp_path)
    (tmp_path / "tutorials").mkdir()
    (tmp_path / "tutorials" / "P.md").write_text("---\ntitle: P\n---\n\n:::{step}\n:::\n")
    errors = validate_content()
    assert len(errors) == 1 and "P.md: line 5:" in errors[0] and "layout: scrolly" in errors[0]


def test_prepare_site_skips_fallback_on_colab_pages(tmp_path):
    page = tmp_path / "T.md"
    page.write_text(PAGE.replace("title: T\n", "title: T\nruntime: colab\n"))
    text = prepare(page)
    assert FALLBACK_SENTINEL not in text
    assert "colab.research.google.com" in text  # badges still added


def test_validate_content_reports_runtime_errors(tmp_path, monkeypatch):
    from nma_kit.convert import validate_content

    monkeypatch.chdir(tmp_path)
    (tmp_path / "tutorials").mkdir()
    (tmp_path / "tutorials" / "P.md").write_text("---\ntitle: P\nruntime: gpu\n---\n")
    assert any("runtime: 'gpu'" in e for e in validate_content())


ASSET_PAGE = """---
title: T
kernelspec:
  name: python3
  display_name: Python 3
---

# Title

![fig](image/pic.png)

:::{nma-data}
data/a.npz
image/pic.png
:::

```{code-cell} python
import numpy as np
arr = np.load("data/a.npz")
```
"""


def _asset_course(tmp_path, monkeypatch, page_text=ASSET_PAGE, files=("data/a.npz", "image/pic.png")):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "myst.yml").write_text("project:\n  github: https://github.com/org/repo\n")
    day = tmp_path / "tutorials" / "D"
    day.mkdir(parents=True)
    (day / "T.md").write_text(page_text)
    for f in files:
        (day / f).parent.mkdir(parents=True, exist_ok=True)
        (day / f).write_bytes(b"bytes:" + f.encode())
    return day


def test_build_notebooks_adds_download_cell_rewrites_images_and_copies_files(tmp_path, monkeypatch):
    import json

    from nma_kit.config import read_settings
    from nma_kit.convert import build_notebooks, convert_md_to_notebook

    day = _asset_course(tmp_path, monkeypatch)
    settings = read_settings()
    page = Path("tutorials/D/T.md")
    out = Path("notebooks/D/T.ipynb")
    convert_md_to_notebook(page, out, dry_run=False)
    build_notebooks(page, out, "org/repo", False, None, settings)

    base = "https://raw.githubusercontent.com/org/repo/notebooks-branch/notebooks/D/"
    for path in (out, out.parent / "instructor" / out.name):
        cells = json.loads(path.read_text())["cells"]
        sources = ["".join(c["source"]) for c in cells]
        assert "colab-badge.svg" in sources[0]
        assert sources[1].startswith("# @title Download course data")
        assert "data/a.npz" in sources[1] and base in sources[1]
        assert cells[1]["metadata"]["tags"] == ["hide-cell"]
        assert f"![fig]({base}image/pic.png)" in "\n".join(sources)
        assert not any("nma-data" in s for s in sources)
    assert (Path("notebooks/D/data/a.npz")).read_bytes() == b"bytes:data/a.npz"
    assert (Path("notebooks/D/image/pic.png")).exists()
    assert not (Path("notebooks/D/instructor/data")).exists()


def test_page_without_assets_is_unaffected(tmp_path, monkeypatch):
    import json

    from nma_kit.config import read_settings
    from nma_kit.convert import build_notebooks, convert_md_to_notebook

    _asset_course(tmp_path, monkeypatch, page_text=PAGE, files=())
    page, out = Path("tutorials/D/T.md"), Path("notebooks/D/T.ipynb")
    convert_md_to_notebook(page, out, dry_run=False)
    build_notebooks(page, out, "org/repo", False, None, read_settings())
    sources = ["".join(c["source"]) for c in json.loads(out.read_text())["cells"]]
    assert not any("Download course data" in s for s in sources)
    assert not (out.parent / "data").exists()


def test_validate_content_reports_asset_problems(tmp_path, monkeypatch):
    from nma_kit.convert import validate_content

    page = ASSET_PAGE.replace("data/a.npz\nimage", "data/a.npz\ndata/gone.npz\nimage")
    _asset_course(tmp_path, monkeypatch, page_text=page)
    errors = validate_content()
    assert any("data/gone.npz" in e and "T.md" in e for e in errors)

    undeclared = ASSET_PAGE.replace('np.load("data/a.npz")', 'np.load("data/other.npz")')
    (tmp_path / "tutorials" / "D" / "T.md").write_text(undeclared)
    assert any("data/other.npz" in e and "no {nma-data}" in e for e in validate_content())


def test_validate_content_accepts_declared_assets(tmp_path, monkeypatch):
    from nma_kit.convert import validate_content

    _asset_course(tmp_path, monkeypatch)
    assert validate_content() == []


def test_committed_download_cell_is_rejected():
    from nma_kit.assets import DOWNLOAD_SENTINEL
    from nma_kit.convert import injected_content_errors

    text = f"---\ntitle: T\n---\n\n```{{code-cell}} python\n{DOWNLOAD_SENTINEL}\nimport os\n```\n"
    assert any("download" in e.lower() for e in injected_content_errors(text))
