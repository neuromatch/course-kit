import json
from pathlib import Path

import pytest
import yaml

from nma_kit import feedback as nma_feedback
from nma_kit.feedback import (
    FeedbackConfig,
    config_errors,
    expand_notebook,
    find_directives,
    legacy_cell_errors,
    load_config,
    page_prefix,
    read_nma_block,
    validate,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "nma_config"
EXAMPLE_COURSE = Path(__file__).resolve().parents[2] / "example-course"
CONFIG = FeedbackConfig("https://example.org/klab", "neuromatch_cn", "y1x3mpx5")

PAGE = """---
title: T
feedback_prefix: W2D2_T1
---

Intro

:::{nma-feedback} Linear_Dynamical_Systems_Video
:::

Outro
"""


# --- config -----------------------------------------------------------------

@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("*.yml")), ids=lambda p: p.stem)
def test_simple_reader_matches_yaml_and_expected(fixture):
    text = fixture.read_text()
    expected = json.loads(fixture.with_suffix(".json").read_text())
    assert read_nma_block(text) == expected
    assert (yaml.safe_load(text).get("nma") or {}) == expected
    assert config_errors(text) == []


def test_real_myst_yml_has_feedback_config():
    text = (EXAMPLE_COURSE / "myst.yml").read_text()
    assert config_errors(text) == []
    config = load_config(text)
    assert config is not None and config.url.startswith("https://")


def test_load_config():
    text = (FIXTURES / "basic.yml").read_text()
    assert load_config(text) == CONFIG
    assert load_config((FIXTURES / "absent.yml").read_text()) is None


@pytest.mark.parametrize("block, message", [
    ("nma:\n  feedback:\n    url: u\n    project: p\n", "missing user_key"),
    ("nma:\n  feedback:\n    url: u\n    project: p\n    user_key: ''\n", "missing user_key"),
    ("nma:\n  feedback:\n    url: u\n    project: p\n    user_key: 12345\n", "string values"),
    ("nma: [1]\n", "string values"),
])
def test_config_errors(block, message):
    errors = config_errors("version: 1\n" + block)
    assert any(message in e for e in errors), errors


@pytest.mark.parametrize("block", [
    "nma:\n  feedback: {url: u, project: p, user_key: k}\n",
    "nma:\n  feedback:\n    url: &u u\n    project: *u\n    user_key: k\n",
])
def test_yaml_forms_with_string_values_are_accepted(block):
    # Both sides parse the block with a YAML library, so any YAML spelling of
    # string values is fine.
    assert config_errors("version: 1\n" + block) == []


def test_config_errors_ignore_missing_block():
    assert config_errors("version: 1\n") == []


# --- prefix -----------------------------------------------------------------

def test_prefix_from_frontmatter():
    assert page_prefix(PAGE, "W2D1_Tutorial1") == "W2D2_T1"


@pytest.mark.parametrize("stem, prefix", [
    ("W2D1_Tutorial1", "W2D1_T1"),
    ("W10D3_Tutorial12", "W10D3_T12"),
    ("W1D2_Bonus", "W1D2_Bonus"),
])
def test_prefix_default_from_filename(stem, prefix):
    assert page_prefix("---\ntitle: T\n---\nbody\n", stem) == prefix
    assert page_prefix("no frontmatter\n", stem) == prefix


# --- parsing and validation -------------------------------------------------

def test_find_directive():
    [d] = find_directives(PAGE)
    assert d.arg == "Linear_Dynamical_Systems_Video"
    assert (d.start, d.end) == (7, 8)


def test_examples_in_code_fences_are_ignored():
    text = "````markdown\n:::{nma-feedback} Example\n:::\n````\n"
    assert find_directives(text) == []
    assert validate(text) == []


def test_valid_page_has_no_errors():
    assert validate(PAGE) == []


@pytest.mark.parametrize("text, message", [
    (":::{nma-feedback}\n:::\n", "line 1: {nma-feedback} needs a section name"),
    (":::{nma-feedback} Has spaces\n:::\n", "letters, digits and underscores"),
    (":::{nma-feedback} A\n:prefix: X\n:::\n", "takes no options"),
    (":::{nma-feedback} A\nsome text\n:::\n", "takes no body"),
    (":::{nma-feedback} A\n", "never closed"),
    ("::::{note}\n:::{nma-feedback} A\n:::\n::::\n", "top level"),
    (":::{nma-feedback} A\n:::\n\n:::{nma-feedback} A\n:::\n", "line 4: {nma-feedback} section A is used twice"),
    ("---\nfeedback_prefix: bad prefix\n---\n:::{nma-feedback} A\n:::\n", "feedback_prefix"),
])
def test_validation_errors(text, message):
    errors = validate(text)
    assert any(message in e for e in errors), errors


@pytest.mark.parametrize("code", [
    '# @title Submit your feedback\ncontent_review(f"{feedback_prefix}_X")',
    "from vibecheck import DatatopsContentReviewContainer",
    "import vibecheck",
    "# @title Import feedback gadget\nx = 1",
])
def test_legacy_feedback_cells_rejected(code):
    text = f"Intro\n\n```{{code-cell}} python\n:tags: [hide-input]\n{code}\n```\n"
    [error] = legacy_cell_errors(text)
    assert error.startswith("line 3:") and "{nma-feedback}" in error


def test_legacy_examples_in_fences_allowed():
    text = '````markdown\n```{code-cell} python\ncontent_review("X")\n```\n````\n'
    assert legacy_cell_errors(text) == []


# --- notebook expansion -----------------------------------------------------

def md(text, cell_id="c1"):
    return {"cell_type": "markdown", "id": cell_id, "metadata": {}, "source": text}


def code(text, cell_id="k1"):
    return {"cell_type": "code", "id": cell_id, "metadata": {}, "outputs": [],
            "execution_count": None, "source": text}


def src(cell):
    return "".join(cell["source"])


def test_expand_notebook():
    nb = {"cells": [
        code("import numpy as np", "k0"),
        md("Before\n\n:::{nma-feedback} Video_1\n:::\n\nAfter\n\n:::{nma-feedback} Exercise_1\n:::\n"),
    ]}
    assert expand_notebook(nb, "W2D2_T1", CONFIG) == 2
    cells = nb["cells"]
    assert [c["cell_type"] for c in cells] == ["code", "code", "markdown", "code", "markdown", "code"]

    gadget = cells[0]
    assert src(gadget).startswith("# @title Import feedback gadget\n")
    assert "%pip install -q vibecheck datatops" in src(gadget)
    assert "emscripten" not in src(gadget)
    assert "'url': 'https://example.org/klab'" in src(gadget)
    assert "'name': 'neuromatch_cn'" in src(gadget)
    assert "'user_key': 'y1x3mpx5'" in src(gadget)
    assert "feedback_prefix = 'W2D2_T1'" in src(gadget)
    assert gadget["metadata"] == {"cellView": "form", "tags": ["hide-input"]}

    assert src(cells[1]) == "import numpy as np"
    assert src(cells[2]) == "Before"
    assert src(cells[3]) == '# @title Submit your feedback\ncontent_review(f"{feedback_prefix}_Video_1")'
    assert cells[3]["metadata"] == {"cellView": "form", "tags": ["hide-input"]}
    assert src(cells[4]) == "After"
    assert src(cells[5]).endswith('content_review(f"{feedback_prefix}_Exercise_1")')
    assert len({c["id"] for c in cells}) == len(cells)


def test_gadget_cell_compiles():
    nb = {"cells": [md(":::{nma-feedback} A\n:::\n")]}
    expand_notebook(nb, "P", CONFIG)
    gadget = src(nb["cells"][0]).replace("%pip", "# %pip")
    compile(gadget, "gadget", "exec")


def test_expand_notebook_without_directives_is_noop():
    nb = {"cells": [md("Just text"), code("x = 1")]}
    before = json.dumps(nb)
    assert expand_notebook(nb, "P", CONFIG) == 0
    assert json.dumps(nb) == before


def test_module_documents_sync_with_plugin():
    assert "js/src/feedback/plugin.mjs" in nma_feedback.__doc__
