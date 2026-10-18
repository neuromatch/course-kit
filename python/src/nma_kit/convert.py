"""
Convert MyST Markdown tutorials to Jupyter notebooks and inject Colab/Kaggle badges.

Usage:
    nma-kit notebooks [--dry-run]
    nma-kit prepare-site [--dry-run]

`nma-kit notebooks` (CI: course-publish workflow). For each .md file in the tutorials dir
that has a kernelspec frontmatter:
  1. Convert to .ipynb via jupytext. Scrolly pages (`layout: scrolly`) are
     flattened first: {step} markers removed, {stage} blocks unwrapped, and
     `# @param` cells become widgets.interact demos (nma_kit.scrolly)
  2. Replace {nma-video}/{nma-slides} directives with NMA code cells
     (nma_kit.media)
  3. Replace {nma-feedback} directives with "Submit your feedback" cells and
     add the "Import feedback gadget" cell (nma_kit.feedback)
  4. Split {nma-solution}/{nma-explanation} directives (nma_kit.solutions)
     into a student notebook (link cells) and an instructor notebook (solution
     code cells, explanation markdown), and write the solution files
  5. Inject a Colab + Kaggle badge markdown cell at position 0 of each notebook
  6. Write notebooks/<day>/<tutorial>.ipynb (student),
     notebooks/<day>/instructor/<tutorial>.ipynb and notebooks/<day>/solutions/*
  The .md sources are never modified in this mode.

`nma-kit prepare-site` (CI, right before `myst build`): edit each kernelspec .md file in place,
inserting after the frontmatter:
  - the Colab + Kaggle badge HTML
  - for pages with exercises, a hidden setup cell that runs the reference
    solution when an unfinished exercise is executed, so "Run all" in
    JupyterLite doesn't stop at the first exercise (not on scrolly pages,
    whose own runtime does this)
  Only run it on a throwaway checkout (CI). Never commit the result.

Both modes first validate the content rules and exit non-zero on any violation:
  - No .ipynb files in tutorials/ (all content is authored as MyST .md)
  - Any .md with a {code-cell} directive must declare a kernelspec
  - {nma-video}/{nma-slides} directives must be valid (ids present, known
    options only, closed, no body)
  - {nma-solution}/{nma-explanation} directives must be valid, every exercise
    (code cell raising NotImplementedError) must be directly followed by an
    {nma-solution}, and no `# to_remove` markers may be left in code cells
  - {nma-feedback} directives must be valid, myst.yml must define
    nma.feedback if any page uses them, and no hand-written vibecheck
    feedback cells may be left
  - {step}/{stage} markers and `# @param` lines must be valid
    (nma_kit.scrolly)

The GitHub repo URL is read from myst.yml (project.github) so badge URLs update
automatically when the template is forked.

Both modes are idempotent — safe to re-run.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from nma_kit import cells as nma_cells
from nma_kit.config import (
    DEFAULT_NOTEBOOKS_BRANCH,
    MYST_CONFIG,
    Settings,
    load_settings,
    page_location,
    read_settings,
)
from nma_kit import feedback as nma_feedback
from nma_kit import scrolly as nma_scrolly
from nma_kit import solutions as nma_solutions
from nma_kit.media import expand_notebook, find_directives, validate_directive


NOTEBOOKS_DIR = Path("notebooks")


def require_github_repo(settings: Settings) -> str:
    """'org/repo' from project.github, or ValueError if it is missing."""
    if not settings.github_repo:
        raise ValueError("project.github is not set to a github.com URL in myst.yml")
    return settings.github_repo


def load_github_repo(myst_config: Path) -> str:
    """
    Read project.github from myst.yml and return 'org/repo' string.

    Example: 'https://github.com/neuromatch/course-template' -> 'neuromatch/course-template'
    """
    return require_github_repo(read_settings(myst_config))


def has_kernelspec(md_file: Path) -> bool:
    """Return True if the .md file has a kernelspec key in its YAML frontmatter."""
    content = md_file.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False

    end = content.find("---", 3)
    if end == -1:
        return False

    frontmatter_text = content[3:end]
    try:
        fm = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        return False

    return isinstance(fm, dict) and "kernelspec" in fm


FENCE_RE = re.compile(r"^(`{3,}|~{3,})(.*)$")


def has_code_cells(md_file: Path) -> bool:
    """
    Return True if the .md file contains a top-level {code-cell} directive.

    Code-cells shown as examples inside another fenced block (e.g. a
    ````markdown fence) don't count, so documentation pages can show the
    syntax without being treated as executable.
    """
    open_fence = None  # (char, length) of the fence we're currently inside
    for line in md_file.read_text(encoding="utf-8").splitlines():
        match = FENCE_RE.match(line)
        if not match:
            continue
        marker, info = match.group(1), match.group(2).strip()
        if open_fence is None:
            if info.startswith("{code-cell}"):
                return True
            open_fence = (marker[0], len(marker))
        elif marker[0] == open_fence[0] and len(marker) >= open_fence[1] and not info:
            open_fence = None
    return False


def injected_content_errors(text: str) -> list[str]:
    """
    Errors for build-time content (badges, the run-all fallback cell) that
    --prepare-site adds and that must never be committed to a source file.
    """
    if not text.startswith("---"):
        return []
    fm_end = text.find("---", 3)
    if fm_end == -1:
        return []
    body = text[fm_end + 3:]
    errors = []
    if BADGE_LINE_RE.match(body):
        errors.append("starts with Colab/Kaggle badge HTML, which CI adds at build time")
    if any(b.kind == "code-cell" and not b.nested and b.body_lines[:1] == [nma_solutions.FALLBACK_SENTINEL]
           for b in nma_solutions.find_blocks(body)):
        errors.append("contains the generated run-all fallback cell, which CI adds at build time")
    return [
        f"{e}. Remove it (this usually means `nma-kit prepare-site` output was committed; "
        f"revert with `git checkout -- tutorials/`)" for e in errors
    ]


def validate_content(check_injected: bool = True) -> list[str]:
    """Check the Markdown-only content rules. Returns a list of violations.

    check_injected: also reject build-time content in the sources. Off for
    --prepare-site, which re-runs on its own output.
    """
    errors = []
    config_text = MYST_CONFIG.read_text(encoding="utf-8") if MYST_CONFIG.exists() else ""
    tutorials_dir = Path(load_settings(config_text).tutorials_dir)
    config_problems = nma_feedback.config_errors(config_text)
    errors += config_problems
    has_config = not config_problems and nma_feedback.load_config(config_text) is not None
    for path in sorted(tutorials_dir.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in path.parts:
            continue
        errors.append(
            f"{path}: .ipynb files are not allowed in {tutorials_dir.as_posix()}/. Convert it with "
            f"`jupytext --to md:myst` and commit only the .md."
        )
    for path in sorted(tutorials_dir.rglob("*.md")):
        if has_code_cells(path) and not has_kernelspec(path):
            errors.append(
                f"{path}: contains {{code-cell}} blocks but no `kernelspec` in its "
                f"frontmatter, so it would get no notebook, badges, or JupyterLite button."
            )
        text = path.read_text(encoding="utf-8")
        if check_injected:
            for problem in injected_content_errors(text):
                errors.append(f"{path}: {problem}")
        for directive in find_directives(text):
            for problem in validate_directive(directive):
                errors.append(f"{path}: {problem}")
        for problem in nma_solutions.validate(text):
            errors.append(f"{path}: {problem}")
        for problem in nma_feedback.validate(text) + nma_feedback.legacy_cell_errors(text):
            errors.append(f"{path}: {problem}")
        for problem in nma_scrolly.validate(text):
            errors.append(f"{path}: {problem}")
        for problem in nma_cells.validate(text):
            errors.append(f"{path}: {problem}")
        if not has_config and not config_problems and nma_feedback.find_directives(text):
            errors.append(
                f"{path}: uses {{nma-feedback}} but myst.yml has no complete "
                f"nma.feedback block (url, project, user_key)"
            )
    return errors


def make_badge_html(notebook_rel_path: str, github_repo: str,
                    branch: str = DEFAULT_NOTEBOOKS_BRANCH) -> str:
    """
    Return raw HTML string containing Colab and Kaggle badge links.

    notebook_rel_path: path relative to repo root, e.g.
        'notebooks/W1D2_InteractiveContent/W1D2_Tutorial1.ipynb'
    github_repo: 'org/repo' string, e.g. 'neuromatch/course-template'
    branch: the branch the notebooks are published to (nma.notebooks.branch)
    """
    colab_url = (
        f"https://colab.research.google.com/github/{github_repo}"
        f"/blob/{branch}/{notebook_rel_path}"
    )
    kaggle_url = (
        f"https://kaggle.com/kernels/welcome?src="
        f"https://raw.githubusercontent.com/{github_repo}/{branch}/{notebook_rel_path}"
    )

    return (
        f'<a href="{colab_url}" target="_blank">'
        f'<img src="https://colab.research.google.com/assets/colab-badge.svg" '
        f'alt="Open In Colab"/></a> '
        f'<a href="{kaggle_url}" target="_blank">'
        f'<img src="https://kaggle.com/static/images/open-in-kaggle.svg" '
        f'alt="Open In Kaggle"/></a>'
    )


BADGE_LINE_RE = re.compile(
    r"\A\s*<a href=\"https://colab\.research\.google\.com/[^\n]*?</a>[ \t]*"
    r"<a href=\"https://kaggle\.com/[^\n]*?</a>[ \t]*\n"
)
FALLBACK_BLOCK_RE = re.compile(
    r"\A\s*```\{code-cell\} python\n:tags: \[remove-cell\]\n"
    + re.escape(nma_solutions.FALLBACK_SENTINEL)
    + r"\n.*?\n```[ \t]*\n",
    re.S,
)


def prepare_site_md(
    md_file: Path, notebook_rel_path: str, github_repo: str, dry_run: bool,
    branch: str = DEFAULT_NOTEBOOKS_BRANCH,
) -> None:
    """
    Insert badges (and, for browser pages with exercises, the run-all fallback cell)
    into the .md source after the frontmatter block.

    Idempotent: removes a previously injected badge line and fallback cell first.
    Both are anchored to the start of the body, so examples elsewhere on the
    page (e.g. inside a code block) are never touched.
    """
    print(f"  Preparing site page: {md_file}")
    if dry_run:
        return

    content = md_file.read_text(encoding="utf-8")

    # Split off frontmatter: content starts with ---, find closing ---
    if not content.startswith("---"):
        return  # no frontmatter, skip

    fm_end = content.find("---", 3)
    if fm_end == -1:
        return

    frontmatter = content[: fm_end + 3]  # includes closing ---
    body = content[fm_end + 3:]           # everything after closing ---
    body = BADGE_LINE_RE.sub("", body)
    body = FALLBACK_BLOCK_RE.sub("", body)

    header = [make_badge_html(notebook_rel_path, github_repo, branch)]
    # Scrolly pages don't run in JupyterLite (their runtime substitutes
    # solutions itself, js/src/scrolly/assets/runnable.mjs), and `runtime: colab`
    # pages never run on the site, so neither needs the fallback cell.
    skip = nma_scrolly.is_scrolly(content) or nma_cells.runtime_of(content) == "colab"
    pairs = [] if skip else nma_solutions.exercise_pairs(body)
    if pairs:
        header.append(nma_solutions.fallback_md_block(pairs))
        print(f"    Added run-all fallback for {len(pairs)} exercise(s)")

    # Normalise spacing so repeated runs don't accumulate blank lines
    header_text = "\n\n".join(header)
    new_content = f"{frontmatter}\n{header_text}\n\n{body.lstrip(chr(10))}"
    md_file.write_text(new_content, encoding="utf-8")


def make_badge_cell(notebook_rel_path: str, github_repo: str,
                    branch: str = DEFAULT_NOTEBOOKS_BRANCH) -> dict:
    """
    Return a Jupyter markdown cell containing Colab and Kaggle badge links.

    notebook_rel_path: path relative to repo root, forward-slash separated,
        e.g. 'notebooks/W1D2_InteractiveContent/W1D2_Tutorial1.ipynb'
    github_repo: 'org/repo' string, e.g. 'neuromatch/course-template'
    """
    return {
        "cell_type": "markdown",
        "id": "badges",
        "metadata": {},
        "source": [make_badge_html(notebook_rel_path, github_repo, branch)],
    }


def run_jupytext(md_file: Path, out_path: Path) -> subprocess.CompletedProcess:
    """
    Run jupytext on md_file. Scrolly pages are flattened into a temporary copy
    first (nma_scrolly.flatten_for_notebook); the source is never modified.
    """
    text = md_file.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        source = md_file
        if nma_scrolly.is_scrolly(text):
            source = Path(tmp) / md_file.name
            source.write_text(nma_scrolly.flatten_for_notebook(text), encoding="utf-8")
        return subprocess.run(
            [
                sys.executable, "-m", "jupytext",
                "--from", "md:myst",
                "--to", "notebook",
                "--output", str(out_path),
                str(source),
            ],
            capture_output=True,
            text=True,
        )


def convert_md_to_notebook(md_file: Path, out_path: Path, dry_run: bool) -> None:
    """Convert a MyST .md file to .ipynb using jupytext."""
    print(f"  Converting: {md_file} -> {out_path}")
    if dry_run:
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = run_jupytext(md_file, out_path)
    if result.returncode != 0:
        print(f"  ERROR: jupytext failed for {md_file}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def add_badge_cell(nb: dict, notebook_rel_path: str, github_repo: str,
                   branch: str = DEFAULT_NOTEBOOKS_BRANCH) -> dict:
    """Return nb with a Colab/Kaggle badge cell at position 0. Idempotent."""
    cells = [c for c in nb["cells"] if "colab-badge.svg" not in "".join(c.get("source", []))]
    return {**nb, "cells": [make_badge_cell(notebook_rel_path, github_repo, branch)] + cells}


def write_notebook(nb: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(nb, fh, indent=1, ensure_ascii=False)


def build_notebooks(source_file: Path, out_path: Path, github_repo: str, dry_run: bool,
                    feedback_config: "nma_feedback.FeedbackConfig | None" = None,
                    settings: Settings | None = None) -> None:
    """
    Post-process the jupytext output at out_path: expand media directives,
    split solutions into student/instructor notebooks, write solution files
    and add badges.
    """
    settings = settings or Settings(github_repo)
    rel_dir, _ = page_location(settings, source_file)
    branch = settings.notebooks_branch
    instructor_path = out_path.parent / "instructor" / out_path.name
    solutions_dir = out_path.parent / "solutions"
    if dry_run:
        print(f"  Would write: {instructor_path} and {solutions_dir}/")
        return

    with out_path.open(encoding="utf-8") as fh:
        nb = json.load(fh)

    count = expand_notebook(nb)
    if count:
        print(f"  Expanded {count} video/slides directive(s)")

    if nma_scrolly.is_scrolly(source_file.read_text(encoding="utf-8")):
        count = nma_scrolly.rewrite_notebook_params(nb)
        if count:
            print(f"  Turned {count} # @param cell(s) into widgets.interact")

    if feedback_config is not None:
        prefix = nma_feedback.page_prefix(source_file.read_text(encoding="utf-8"), source_file.stem)
        count = nma_feedback.expand_notebook(nb, prefix, feedback_config)
        if count:
            print(f"  Expanded {count} feedback directive(s) (prefix {prefix})")

    student, instructor, files = nma_solutions.split_notebook(
        nb, source_file.stem, rel_dir, github_repo, branch)
    for name, content in files.items():
        solutions_dir.mkdir(parents=True, exist_ok=True)
        (solutions_dir / name).write_text(content, encoding="utf-8")
    if files:
        print(f"  Wrote {len(files)} solution file(s) to {solutions_dir}/")

    for nb_out, path in ((student, out_path), (instructor, instructor_path)):
        notebook_rel = path.as_posix()
        write_notebook(add_badge_cell(nb_out, notebook_rel, github_repo, branch), path)
        print(f"  Wrote notebook with badges: {path}")


def process_tutorials(settings: Settings, dry_run: bool, prepare_site: bool) -> int:
    """Walk the tutorials dir and process all executable .md pages. Returns count processed."""
    count = 0
    github_repo = require_github_repo(settings)
    feedback_config = nma_feedback.load_config(MYST_CONFIG.read_text(encoding="utf-8"))
    tutorials_dir = Path(settings.tutorials_dir)

    for source_file in sorted(tutorials_dir.rglob("*.md")):
        if not has_kernelspec(source_file):
            continue  # static page — skip

        # Determine output path under notebooks/
        relative_to_tutorials = source_file.relative_to(tutorials_dir)
        out_path = NOTEBOOKS_DIR / relative_to_tutorials.with_suffix(".ipynb")

        if prepare_site:
            prepare_site_md(source_file, out_path.as_posix(), github_repo, dry_run,
                            settings.notebooks_branch)
        else:
            convert_md_to_notebook(source_file, out_path, dry_run)
            build_notebooks(source_file, out_path, github_repo, dry_run, feedback_config, settings)

        count += 1

    return count
