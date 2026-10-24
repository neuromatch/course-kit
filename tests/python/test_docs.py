"""Docs stay true to the code: every CLI command is documented and every
relative link in the repo's own markdown files resolves."""

import re
from pathlib import Path

import pytest

from nma_kit.cli import build_parser

KIT = Path(__file__).resolve().parents[2]
DOCS = ["README.md", "CONTRIBUTING.md", "AGENTS.md", "docs/releasing.md", "python/README.md", "js/README.md"]
LINK_RE = re.compile(r"\]\((?!https?:|mailto:|#)([^)#\s]+)")


def _commands() -> list[str]:
    sub = next(a for a in build_parser()._actions if a.dest == "command")
    return sorted(sub.choices)


@pytest.mark.parametrize("command", _commands())
def test_every_command_is_in_the_command_table(command):
    assert f"`nma-kit {command}" in (KIT / "python/README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("doc", DOCS)
def test_relative_links_resolve(doc):
    path = KIT / doc
    for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
        if "://" in target:
            continue
        assert (path.parent / target).exists(), f"{doc}: broken link {target}"
