import json
from pathlib import Path

import pytest

from nma_kit.assets import (
    parse_data_directive,
    find_data_directives,
    validate_data_directives,
    asset_url,
    scan_code_references,
    undeclared_reference_errors,
)

FIXTURE = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "assets" / "directives.json").read_text()
)


@pytest.mark.parametrize("case", FIXTURE["parse"], ids=[c["name"] for c in FIXTURE["parse"]])
def test_parse_matches_fixture(case):
    assert parse_data_directive(case["text"]) == case["paths"]


def test_parse_collects_paths():
    text = ":::{nma-data}\ndata/a.npz\nimage/b.png\n:::\n"
    assert parse_data_directive(text) == ["data/a.npz", "image/b.png"]


def test_parse_dedupes_across_blocks_in_order():
    text = ":::{nma-data}\ndata/a.npz\n:::\n\n:::{nma-data}\ndata/a.npz\ndata/c.npz\n:::\n"
    assert parse_data_directive(text) == ["data/a.npz", "data/c.npz"]


def test_fenced_example_is_ignored():
    text = "````markdown\n:::{nma-data}\ndata/a.npz\n:::\n````\n"
    assert parse_data_directive(text) == []


def test_find_directive_positions():
    text = "intro\n\n:::{nma-data}\ndata/a.npz\n:::\n\noutro\n"
    [d] = find_data_directives(text)
    assert d.paths == ["data/a.npz"]
    assert (d.start, d.end) == (2, 4)


def test_validate_rejects_unknown_prefix_and_escape():
    text = ":::{nma-data}\nfoo/a.npz\n../x.npz\n:::\n"
    errs = validate_data_directives(text, "data", "image")
    assert len(errs) == 2


def test_validate_rejects_absolute_path():
    errs = validate_data_directives(":::{nma-data}\n/etc/passwd\n:::\n", "data", "image")
    assert len(errs) == 1


def test_validate_rejects_unclosed():
    errs = validate_data_directives(":::{nma-data}\ndata/a.npz\n", "data", "image")
    assert any("closed" in e for e in errs)


def test_validate_rejects_inline_arg():
    errs = validate_data_directives(":::{nma-data} oops\ndata/a.npz\n:::\n", "data", "image")
    assert any("argument" in e or "arg" in e for e in errs)


def test_validate_rejects_empty_body():
    errs = validate_data_directives(":::{nma-data}\n:::\n", "data", "image")
    assert any("empty" in e or "no files" in e for e in errs)


def test_validate_passes_custom_dirs():
    text = ":::{nma-data}\nassets/a.npz\npics/b.png\n:::\n"
    assert validate_data_directives(text, "assets", "pics") == []


@pytest.mark.parametrize("case", FIXTURE["asset_url"], ids=lambda c: c["path"])
def test_asset_url_matches_fixture(case):
    assert asset_url(case["repo"], case["branch"], case["day"], case["path"]) == case["url"]


def test_asset_url_joins_day():
    assert asset_url("org/repo", "nb", "W1D1", "data/a.npz") == \
        "https://raw.githubusercontent.com/org/repo/nb/notebooks/W1D1/data/a.npz"


@pytest.mark.parametrize("case", FIXTURE["scan"], ids=[c["name"] for c in FIXTURE["scan"]])
def test_scan_matches_fixture(case):
    assert scan_code_references(case["code"], case["data_dir"], case["image_dir"]) == case["refs"]


def test_undeclared_reference_is_error():
    md = '---\nkernelspec: {}\n---\n```{code-cell}\nnp.load("data/a.npz")\n```\n'
    assert undeclared_reference_errors(md, "data", "image")


def test_declared_reference_is_ok():
    md = (
        '---\nkernelspec: {}\n---\n'
        ':::{nma-data}\ndata/a.npz\n:::\n\n'
        '```{code-cell}\nnp.load("data/a.npz")\n```\n'
    )
    assert undeclared_reference_errors(md, "data", "image") == []


def test_reference_in_fenced_example_not_flagged():
    md = '---\nkernelspec: {}\n---\n````markdown\n```{code-cell}\nnp.load("data/a.npz")\n```\n````\n'
    assert undeclared_reference_errors(md, "data", "image") == []
