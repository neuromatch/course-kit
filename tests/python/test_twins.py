"""The Python/JS twin registry (tests/twins.json) matches the code.

Logic that exists in both languages must behave the same. The registry lists
every pair; this test keeps it honest: each symbol exists, is named by a test
on its side, and each fixture exists. Declare unavoidable gaps in the entry's
"gap" list rather than leaving them silent.
"""

import json
import re
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
REGISTRY = json.loads((KIT / "tests" / "twins.json").read_text(encoding="utf-8"))["twins"]
TESTS = {
    "py": "\n".join(p.read_text(encoding="utf-8") for p in (KIT / "tests" / "python").glob("test_*.py")),
    "js": "\n".join(p.read_text(encoding="utf-8") for p in (KIT / "tests" / "js").glob("*.test.mjs")),
}


def _defined(side: str, ref: str) -> bool:
    path, name = ref.split("::")
    text = (KIT / path).read_text(encoding="utf-8")
    n = re.escape(name)
    if side == "py":
        pattern = rf"^\s*(def|class) {n}\b|^{n}\s*(:[^=\n]+)?="
    else:
        pattern = rf"^(export )?(async )?(function|const) {n}\b"
    return re.search(pattern, text, re.M) is not None


@pytest.mark.parametrize("entry", REGISTRY, ids=lambda e: e["what"])
def test_twin_is_registered_correctly(entry):
    for side in ("js", "py"):
        assert _defined(side, entry[side]), f"{entry[side]} not found: renamed or removed? update tests/twins.json"
        name = entry[side].split("::")[1]
        if side not in entry.get("gap", []):
            assert name in TESTS[side], f"no {side} test mentions {name}: add one, or list {side!r} under 'gap'"
    if entry.get("fixture"):
        assert (KIT / "tests" / "fixtures" / entry["fixture"]).exists(), entry["fixture"]


def test_registry_names_are_unique():
    refs = [e[s] for e in REGISTRY for s in ("js", "py")]
    assert len(refs) == len(set(refs))
