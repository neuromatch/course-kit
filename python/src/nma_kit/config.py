"""
Course settings, read from the course's myst.yml.

Kit settings live in the top-level `nma:` block, as `section: {key: value}`
with string values. js/src/shared/config.mjs reads the same block with a
YAML parser too; both sides are tested against tests/fixtures/config/settings.json.

Settings read here. `nma.content` is required: it names the folders whose pages the
kit processes (there are no defaults). The rest are optional; the defaults are the
course template's conventions. The feedback and scrolly sections are read by
nma_kit.feedback and the plugin (`nma.scrolly.pyodide_url`):

    nma:
      content:                      # content roots: folders (inside the course) holding pages
        - tutorials                 # shorthand: name = path
        - {name: guide, path: docs/guide}   # name = first folder under notebooks/
      notebooks:
        branch: notebooks-branch    # where generated notebooks are published
                                    # (the env var NMA_NOTEBOOKS_BRANCH overrides it: PR previews)
      assets:
        data: data                  # folder (in each day folder) for data files
        image: image                # folder (in each day folder) for images
        slides: slides              # folder (in each day folder) for slide PDFs

Environment: `NMA_NOTEBOOKS_BRANCH` (see above) and `NMA_AUDIENCE` (`student`, the
default, or `instructor`: which site this build is; there is no myst.yml key).
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import NamedTuple

import yaml

from nma_kit.constants import (
    AUDIENCE_ENV,
    DEFAULT_AUDIENCE,
    DEFAULT_DATA_DIR,
    DEFAULT_IMAGE_DIR,
    DEFAULT_NOTEBOOKS_BRANCH,
    DEFAULT_SLIDES_DIR,
    NOTEBOOKS_BRANCH_ENV,
    RESERVED_CONTENT_DIRS,
)

NOTEBOOKS_DIR = "notebooks"
MYST_CONFIG = Path("myst.yml")

GITHUB_RE = re.compile(r"github\.com/([^\s'\"]+?)/?$")


class MissingConfig(Exception):
    """The course's myst.yml does not exist."""

    def __init__(self, path: Path):
        super().__init__(f"{path} not found: run nma-kit from the course root (the folder with myst.yml)")
        self.path = path


@dataclass(frozen=True)
class Settings:
    """Course settings read from `myst.yml` (the `project.github` repo and the `nma:` block), with defaults filled in.

    JS twin: `loadSettings` in js/src/shared/config.mjs, tested with tests/fixtures/config/settings.json."""
    github_repo: str | None
    content_roots: tuple[tuple[str, str], ...] = ()   # (name, folder) of each content root, from nma.content
    notebooks_branch: str = DEFAULT_NOTEBOOKS_BRANCH
    nma: dict = field(default_factory=dict)
    assets_data_dir: str = DEFAULT_DATA_DIR
    assets_image_dir: str = DEFAULT_IMAGE_DIR
    assets_slides_dir: str = DEFAULT_SLIDES_DIR
    audience: str = DEFAULT_AUDIENCE   # `student` or `instructor` (env NMA_AUDIENCE; `check` rejects others)


def _yaml(text: str) -> dict:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def read_nma_block(text: str) -> dict:
    """The top-level `nma:` block of myst.yml ({} if absent or not a mapping)."""
    block = _yaml(text).get("nma")
    return block if isinstance(block, dict) else {}


NAME_RE = re.compile(r"[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*")


def content_path_problem(path: str) -> str | None:
    """Why `path` cannot be a content root folder (None if it can): it must be a folder strictly inside the course.
    JS twin: `contentPathProblem` in js/src/shared/config.mjs."""
    if not path:
        return "is empty"
    if path.startswith("/") or re.match(r"[A-Za-z]:", path):
        return "must be relative to the course root"
    parts = path.split("/")
    if "." in parts or ".." in parts:
        return "must be a folder inside the course (no '.' or '..')"
    if parts[0].startswith(".") or parts[0] in RESERVED_CONTENT_DIRS:
        return f"cannot be under {parts[0]}/ (the kit or the build owns it)"
    return None


def _content_entry(item) -> tuple[str, str] | None:
    """(name, path) of one `nma.content` entry (a path string or {name, path}), or None if malformed."""
    if isinstance(item, str):
        path, name = item, None
    elif isinstance(item, dict):
        path, name = item.get("path"), item.get("name")
    else:
        return None
    if not isinstance(path, str) or (name is not None and not isinstance(name, str)):
        return None
    path = re.sub(r"^(\./)+|/+$", "", path.strip())
    name = (name or path).strip().strip("/")
    return name, path


def content_roots_from(nma: dict) -> tuple[tuple[str, str], ...]:
    """The valid `nma.content` entries as (name, path). Malformed ones are skipped here; `content_errors` reports them.
    JS twin: `contentRoots` in js/src/shared/config.mjs, tested with tests/fixtures/config/content.json."""
    raw = nma.get("content")
    entries = (_content_entry(i) for i in raw) if isinstance(raw, list) else ()
    return tuple(
        (name, path) for name, path in filter(None, entries)
        if content_path_problem(path) is None and NAME_RE.fullmatch(name)
    )


def content_errors(nma: dict) -> list[str]:
    """Problems with the `nma.content` setting, for `nma-kit check`."""
    example = "nma:\n  content:\n    - tutorials\n    - projects"
    paths = nma.get("paths")
    legacy = [k for k in ("tutorials", "projects") if isinstance(paths, dict) and k in paths]
    errors = [
        f"nma.paths.{k} is no longer read: declare the folder in nma.content instead "
        f"(`content: [{paths[k]}]`; add `name: {k}` to keep the notebook URLs `notebooks/{k}/...`)"
        for k in legacy
    ]
    raw = nma.get("content")
    if raw is None or raw == []:
        if not legacy:
            errors.append(f"nma.content is required: list the folders that hold your pages, for example\n{example}")
        return errors
    if not isinstance(raw, list):
        return errors + [f"nma.content must be a list of folders, for example\n{example}"]
    seen: list[tuple[str, str]] = []
    for item in raw:
        entry = _content_entry(item)
        if entry is None:
            errors.append(f"nma.content entry {item!r} must be a folder or {{name, path}} with string values")
            continue
        name, path = entry
        problem = content_path_problem(path)
        if problem:
            errors.append(f"nma.content path {path!r} {problem}")
            continue
        if not NAME_RE.fullmatch(name):
            errors.append(f"nma.content name {name!r} may only use letters, digits, '-', '_' and '/'")
            continue
        for other_name, other_path in seen:
            if name == other_name:
                errors.append(f"nma.content name {name!r} is used twice")
            if path == other_path or path.startswith(other_path + "/") or other_path.startswith(path + "/"):
                errors.append(f"nma.content folders {other_path!r} and {path!r} overlap: a page must belong to one root")
        seen.append((name, path))
    return errors


def _github_repo(data: dict) -> str | None:
    project = data.get("project")
    url = project.get("github") if isinstance(project, dict) else None
    match = GITHUB_RE.search(url.strip()) if isinstance(url, str) else None
    return match.group(1) if match else None


def _setting(nma: dict, section: str, key: str, default: str) -> str:
    value = (nma.get(section) or {}).get(key) if isinstance(nma.get(section), dict) else None
    return value if isinstance(value, str) and value.strip() else default


def _notebooks_branch(nma: dict, env: Mapping[str, str]) -> str:
    """NMA_NOTEBOOKS_BRANCH (set by PR previews) wins over nma.notebooks.branch."""
    override = env.get(NOTEBOOKS_BRANCH_ENV, "").strip()
    return override or _setting(nma, "notebooks", "branch", DEFAULT_NOTEBOOKS_BRANCH)


def _audience(env: Mapping[str, str]) -> str:
    """NMA_AUDIENCE trimmed; blank or unset means the default (student). Unknown values are kept: `check` reports them."""
    return env.get(AUDIENCE_ENV, "").strip() or DEFAULT_AUDIENCE


def load_settings(myst_text: str, env: Mapping[str, str] | None = None) -> Settings:
    """Build `Settings` from the text of `myst.yml`. `env` (default `os.environ`) supplies `NMA_NOTEBOOKS_BRANCH` and `NMA_AUDIENCE`."""
    env = os.environ if env is None else env
    data = _yaml(myst_text)
    nma = read_nma_block(myst_text)
    return Settings(
        github_repo=_github_repo(data),
        content_roots=content_roots_from(nma),
        notebooks_branch=_notebooks_branch(nma, env),
        assets_data_dir=_setting(nma, "assets", "data", DEFAULT_DATA_DIR).strip("/"),
        assets_image_dir=_setting(nma, "assets", "image", DEFAULT_IMAGE_DIR).strip("/"),
        assets_slides_dir=_setting(nma, "assets", "slides", DEFAULT_SLIDES_DIR).strip("/"),
        nma=nma,
        audience=_audience(env),
    )


def read_settings(path: Path = MYST_CONFIG) -> Settings:
    """Read `myst.yml` (from the current directory by default). Raises `MissingConfig` if the file is absent."""
    path = Path(path)
    if not path.is_file():
        raise MissingConfig(path)
    return load_settings(path.read_text(encoding="utf-8"))


class PageLocation(NamedTuple):
    """Where a page lives: its content root, the folder under that root, and the file stem."""
    root: str      # content root name (from nma.content)
    rel_dir: str   # folder under the content root ('' at the top)
    stem: str

    @property
    def notebook_dir(self) -> str:
        """Folder under notebooks/ holding the page's generated files."""
        return f"{self.root}/{self.rel_dir}" if self.rel_dir else self.root


def notebook_rel_path(settings: Settings, location: PageLocation) -> str:
    """Path (from the course root) of the notebook a page's badges open.

    The instructor audience gets the generated instructor notebook (solutions filled in):
    'notebooks/tutorials/W1/instructor/T1.ipynb'; students get 'notebooks/tutorials/W1/T1.ipynb'.
    JS twin: `notebookPath` in js/src/shared/paths.mjs."""
    folder = f"{NOTEBOOKS_DIR}/{location.notebook_dir}"
    if settings.audience == "instructor":
        folder += "/instructor"
    return f"{folder}/{location.stem}.ipynb"


def page_location(settings: Settings, page: str | Path) -> PageLocation | None:
    """Where a page (path relative to the course root) lives, or None if it is
    outside every content root. With root `tutorials`, 'tutorials/W1/T1.md' -> PageLocation('tutorials', 'W1', 'T1').
    (`content_errors` rejects nested roots; if they slip through, the deepest wins.)"""
    path = PurePosixPath(Path(page).as_posix())
    for name, directory in sorted(settings.content_roots, key=lambda r: -len(r[1])):
        try:
            rel = path.relative_to(directory)
        except ValueError:
            continue
        rel_dir = rel.parent.as_posix()
        return PageLocation(name, "" if rel_dir == "." else rel_dir, rel.stem)
    return None
