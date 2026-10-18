#!/usr/bin/env python3
"""Compare two builds of a course (golden check for kit changes).

    compare_builds.py BEFORE_DIR AFTER_DIR

Each dir is a course root after `nma-kit notebooks` (or the old scripts) and
`myst build --html`. Exits 0 if
  (a) every notebook under notebooks/ is equal ignoring cell ids (jupytext
      gives cells random ids on every run); other files are byte-identical,
  (b) every page JSON under _build/site/content/ is equal once anywidget
      `esm`/`css` values are reduced to their extension (asset file names
      carry content hashes and change whenever a bundle is rebuilt) and
      MyST's `-<md5>.` static file names are reduced to `-HASH.`; mdast node
      `key`s and `outputs` node `id`s (random per build) are ignored.
Otherwise prints the first difference per file and exits 1.
"""

import json
import re
import sys
from pathlib import Path

ASSET_KEYS = ("esm", "css")
HASHED_RE = re.compile(r"-[0-9a-f]{32}(?=\.\w+$)")


def normalise(node):
    if isinstance(node, dict):
        out = {k: normalise(v) for k, v in node.items() if k != "key"}
        if out.get("type") == "outputs":
            out.pop("id", None)
        if out.get("type") == "anywidget":
            for key in ASSET_KEYS:
                if isinstance(out.get(key), str):
                    out[key] = "ASSET" + Path(out[key]).suffix
        return out
    if isinstance(node, list):
        return [normalise(v) for v in node]
    if isinstance(node, str):
        return HASHED_RE.sub("-HASH", node)
    return node


def notebook_without_ids(path: Path):
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return path.read_bytes()
    for cell in nb.get("cells", []) if isinstance(nb, dict) else []:
        cell.pop("id", None)
    return nb


def first_difference(a, b, path="$"):
    if type(a) is not type(b):
        return path, a, b
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                return f"{path}.{key}", a.get(key, "<missing>"), b.get(key, "<missing>")
            found = first_difference(a[key], b[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(a, list):
        for i, (x, y) in enumerate(zip(a, b)):
            found = first_difference(x, y, f"{path}[{i}]")
            if found:
                return found
        return None if len(a) == len(b) else (f"{path} (length)", len(a), len(b))
    return None if a == b else (path, a, b)


def files(root: Path, sub: str, pattern: str) -> dict:
    base = root / sub
    return {p.relative_to(root).as_posix(): p for p in sorted(base.rglob(pattern)) if p.is_file()}


def compare(before: Path, after: Path) -> list[str]:
    problems = []
    nb_a, nb_b = files(before, "notebooks", "*"), files(after, "notebooks", "*")
    for rel in sorted(set(nb_a) | set(nb_b)):
        if rel not in nb_a or rel not in nb_b:
            problems.append(f"{rel}: only in {'after' if rel in nb_b else 'before'}")
        elif rel.endswith(".ipynb"):
            if notebook_without_ids(nb_a[rel]) != notebook_without_ids(nb_b[rel]):
                problems.append(f"{rel}: contents differ (ignoring cell ids)")
        elif nb_a[rel].read_bytes() != nb_b[rel].read_bytes():
            problems.append(f"{rel}: contents differ")
    pages_a = files(before, "_build/site/content", "*.json")
    pages_b = files(after, "_build/site/content", "*.json")
    for rel in sorted(set(pages_a) | set(pages_b)):
        if rel not in pages_a or rel not in pages_b:
            problems.append(f"{rel}: only in {'after' if rel in pages_b else 'before'}")
            continue
        a = normalise(json.loads(pages_a[rel].read_text()))
        b = normalise(json.loads(pages_b[rel].read_text()))
        found = first_difference(a, b)
        if found:
            path, x, y = found
            problems.append(f"{rel}: {path}: {str(x)[:200]!r} != {str(y)[:200]!r}")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    problems = compare(Path(argv[0]), Path(argv[1]))
    for problem in problems:
        print(problem)
    if not problems:
        print("Builds match.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
