"""`nma-kit init`: write a starter course.

The starter is a folder of real files, `templates/course/`, rendered with plain
`{{name}}` replacement; the license texts are `templates/licenses/`. Two rules
keep the files editable as files and safe to package:

  - `*.tmpl` files are rendered (the suffix is dropped); other files are copied.
  - a leading `dot-` becomes `.` (`dot-gitignore` -> `.gitignore`), so packaging
    tools and git never treat the template as a real dotfile.

The workflow comes from `templates/workflows/course.yml`, a copy of the repo's
`templates/course.yml` (the wheel can't ship files from outside `python/`;
`make sync-templates` refreshes the copy and a test checks it). The preview job
is switched on or off in `render_workflow`.
"""

import datetime
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from nma_kit import __version__

TEMPLATES = Path(__file__).parent / "templates"

DEFAULT_LICENSE = "BSD-3-Clause"
LICENSES = {name: f"{name}.txt" for name in ("BSD-3-Clause", "MIT", "Apache-2.0", "CC-BY-4.0")}

GITHUB_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+$")
PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")
WORKFLOW_PATH = Path(".github/workflows/course.yml")


class ScaffoldError(Exception):
    """A problem with the `init` arguments or the target folder. `main` prints it and exits 2."""


@dataclass
class Options:
    """What `init` needs to know. Missing values are prompted for, or reported when there is no terminal."""
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    github: str | None = None
    license: str | None = None
    preview: bool = False


def is_interactive() -> bool:
    """True when a person can answer prompts."""
    return sys.stdin.isatty()


def kit_minor() -> str:
    """The compatible release line the starter pins to: '0.1' for 0.1.8."""
    return ".".join(__version__.split(".")[:2])


# --- rendering ---------------------------------------------------------------

def render(text: str, values: dict[str, str]) -> str:
    """Replace each `{{name}}` with values[name]. An unknown name is an error (it would ship as literal text)."""
    def replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise ScaffoldError(f"template uses unknown placeholder {{{{{key}}}}}")
        return values[key]
    return PLACEHOLDER_RE.sub(replace, text)


def keep_block(text: str, name: str, keep: bool) -> str:
    """Handle `<!-- name:start -->` ... `<!-- name:end -->` markers: keep the lines between them, or drop them too."""
    pattern = re.compile(rf"^<!-- {name}:start -->\n(.*?)^<!-- {name}:end -->\n", re.S | re.M)
    return pattern.sub(lambda m: m.group(1) if keep else "", text)


def _replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise ScaffoldError(f"the workflow template changed: cannot find {old!r}")
    return text.replace(old, new, 1)


def render_workflow(text: str, preview: bool) -> str:
    """The course workflow for a new course: kit versions pinned to this release line, preview job on or off."""
    minor = kit_minor()
    text = re.sub(r"(course-kit/\.github/workflows/[\w-]+\.yml@v)\d+\.\d+", rf"\g<1>{minor}", text)
    text = re.sub(r"newest \d+\.\d+\.x", f"newest {minor}.x", text)
    text = re.sub(r"(e\.g\. @v)\d+\.\d+\.\d+", rf"\g<1>{minor}.0", text)
    text = _replace_once(text, "# Copy to .github/workflows/course.yml in your course repo.\n", "")
    marker = "  # Needs the CLOUDFLARE_API_TOKEN"
    head, sep, tail = text.partition(marker)
    if not sep:
        raise ScaffoldError("the workflow template changed: cannot find the preview job")
    notes, sep, job = tail.partition("  preview:\n")
    if not sep:
        raise ScaffoldError("the workflow template changed: cannot find the preview job")
    job = "  preview:\n" + job
    if preview:
        return head + marker + _replace_once(
            notes, "Delete\n  # this job if the course does not want previews.", "Delete\n  # this job to turn previews off.") + job
    head = _replace_once(
        head,
        "# Pull requests are checked and get a public preview on Cloudflare Pages (see\n"
        '# the README, "Pull request previews"); pushes to main publish the notebooks\n'
        "# and the site.\n",
        "# Pull requests are checked; pushes to main publish the notebooks and the site.\n"
        "# Pull request previews (Cloudflare Pages) are off: see the commented job at the end.\n")
    note = ("  # Pull request previews are off. To turn them on, remove the leading \"# \" from\n"
            "  # each line below and follow the README's setup checklist (or run\n"
            "  # `nma-kit init --preview` in a fresh folder to compare). The job needs the\n"
            "  # CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID secrets and the\n"
            "  # CLOUDFLARE_PROJECT variable.\n")
    commented = "\n".join(f"# {line}" if line.strip() else "#" for line in job.rstrip("\n").splitlines())
    return head + note + commented + "\n"


# --- inputs ------------------------------------------------------------------

def _ask(prompt: str) -> str:
    return input(prompt).strip()


def complete(options: Options) -> Options:
    """Prompt for what is missing. Without a terminal, name the missing flags instead of hanging."""
    missing = []
    if not options.title:
        missing.append("--title")
    if not options.authors:
        missing.append("--author")
    if not options.github:
        missing.append("--github")
    if missing and not is_interactive():
        raise ScaffoldError(f"missing {', '.join(missing)} (pass them as flags; there is no terminal to ask on)")
    if not options.title:
        options.title = _ask("Course title: ")
    if not options.authors:
        print("Authors, one per line (empty line to finish):")
        while name := _ask("  Author: "):
            options.authors.append(name)
    if not options.github:
        options.github = _ask("GitHub repository URL (https://github.com/<org>/<repo>): ")
    if not options.license and is_interactive():
        options.license = _ask(f"License ({', '.join(LICENSES)}) [{DEFAULT_LICENSE}]: ") or None
    options.license = options.license or DEFAULT_LICENSE
    return options


def validate(options: Options) -> Options:
    """Check the answers; normalise the GitHub URL. Raises ScaffoldError."""
    if not options.title or not options.title.strip():
        raise ScaffoldError("the course title is empty")
    if not options.authors:
        raise ScaffoldError("give at least one author")
    github = (options.github or "").strip().rstrip("/")
    github = github[:-4] if github.endswith(".git") else github
    if not GITHUB_RE.match(github):
        raise ScaffoldError(f"--github must look like https://github.com/<org>/<repo>, got {options.github!r}")
    if options.license not in LICENSES:
        raise ScaffoldError(f"unknown license {options.license!r}; choose one of {', '.join(LICENSES)}")
    options.github = github
    options.title = options.title.strip()
    return options


# --- files -------------------------------------------------------------------

def _quote(value: str) -> str:
    # A JSON string is a valid double-quoted YAML scalar.
    return json.dumps(value, ensure_ascii=False)


def _target_name(rel: Path) -> Path:
    parts = [("." + p[4:] if p.startswith("dot-") else p) for p in rel.parts]
    if parts[-1].endswith(".tmpl"):
        parts[-1] = parts[-1][: -len(".tmpl")]
    return Path(*parts)


def build_files(options: Options, year: int | None = None) -> dict[Path, str]:
    """Every file of the starter as {path relative to the course root: text}."""
    year = year or datetime.date.today().year
    values = {
        "title": options.title,
        "title_yaml": _quote(options.title),
        "authors": "\n".join(f"    - name: {_quote(name)}" for name in options.authors),
        "authors_inline": ", ".join(options.authors),
        "github": options.github,
        "kit_minor": kit_minor(),
        "year": str(year),
    }
    files: dict[Path, str] = {}
    root = TEMPLATES / "course"
    for source in sorted(p for p in root.rglob("*") if p.is_file()):
        text = source.read_text(encoding="utf-8")
        if source.name.endswith(".tmpl"):
            text = keep_block(text, "preview", options.preview)
            text = render(text, values)
        files[_target_name(source.relative_to(root))] = text
    licence = (TEMPLATES / "licenses" / LICENSES[options.license]).read_text(encoding="utf-8")
    files[Path("LICENSE")] = render(licence, values)
    workflow = (TEMPLATES / "workflows" / "course.yml").read_text(encoding="utf-8")
    files[WORKFLOW_PATH] = render_workflow(workflow, options.preview)
    return files


def init(target: Path, options: Options) -> list[Path]:
    """Write the starter into `target`. Refuses to overwrite; writes nothing if anything is wrong."""
    options = validate(complete(options))
    if target.exists() and not target.is_dir():
        raise ScaffoldError(f"{target} exists and is not a folder")
    files = build_files(options)
    clashes = sorted(rel.as_posix() for rel in files if (target / rel).exists())
    if clashes:
        raise ScaffoldError(f"{target} already has: {', '.join(clashes)}. Nothing was written.")
    for rel, text in files.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return sorted(files)
