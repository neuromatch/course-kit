import json
from pathlib import Path

import pytest

from nma_kit.cells import runtime_of, validate

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "cells"


@pytest.mark.parametrize(
    "case", json.loads((FIXTURES / "runtime.json").read_text()), ids=lambda c: c["name"]
)
def test_runtime_of(case):
    assert runtime_of(case["text"]) == case["runtime"]


def test_validate_accepts_browser_and_colab():
    assert validate("---\nruntime: colab\nkernelspec:\n  name: python3\n---\n") == []
    assert validate("---\ntitle: T\n---\n") == []


def test_validate_rejects_unknown_runtime():
    assert validate("---\nruntime: gpu\n---\n") == ["runtime: 'gpu' must be one of browser, colab"]


def test_validate_rejects_colab_scrolly():
    errors = validate("---\nlayout: scrolly\nruntime: colab\n---\n")
    assert errors == ["runtime: colab can't be combined with layout: scrolly"]
