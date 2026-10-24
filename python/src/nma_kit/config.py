"""
Course settings, read from the course's myst.yml.

Kit settings live in the top-level `nma:` block, as `section: {key: value}`
with string values. js/src/shared/config.mjs reads the same block with a
YAML parser too; both sides are tested against tests/fixtures/config/settings.json.

Settings read here (all optional; the defaults are the course template's
conventions). The feedback and scrolly sections are read by nma_kit.feedback
and the plugin (`nma.scrolly.pyodide_url`):

    nma:
      paths:
        tutorials: tutorials        # where the course's tutorial .md pages live
        projects: projects          # where the course's project .md pages live
      notebooks:
        branch: notebooks-branch    # where generated notebooks are published
                                    # (the env var NMA_NOTEBOOKS_BRANCH overrides it: PR previews)
      assets:
        data: data                  # folder (in each day folder) for data files
        image: image                # folder (in each day folder) for images
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import NamedTuple
from pathlib import Path, PurePosixPath

import yaml

DEFAULT_TUTORIALS_DIR = "tutorials"
DEFAULT_PROJECTS_DIR = "projects"
DEFAULT_NOTEBOOKS_BRANCH = "notebooks-branch"
NOTEBOOKS_BRANCH_ENV = "NMA_NOTEBOOKS_BRANCH"  # overrides the branch (PR previews)
DEFAULT_DATA_DIR = "data"
DEFAULT_IMAGE_DIR = "image"
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
    tutorials_dir: str = DEFAULT_TUTORIALS_DIR
    notebooks_branch: str = DEFAULT_NOTEBOOKS_BRANCH
    nma: dict = field(default_factory=dict)
    assets_data_dir: str = DEFAULT_DATA_DIR
    assets_image_dir: str = DEFAULT_IMAGE_DIR
    projects_dir: str = DEFAULT_PROJECTS_DIR

    @property
    def content_roots(self) -> tuple[tuple[str, str], ...]:
        """(name, directory) of each place pages live. The name is fixed (it is
        the first folder under notebooks/); the directory is configurable."""
        return (("tutorials", self.tutorials_dir), ("projects", self.projects_dir))


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


def load_settings(myst_text: str, env: Mapping[str, str] | None = None) -> Settings:
    """Build `Settings` from the text of `myst.yml`. `env` (default `os.environ`) supplies the `NMA_NOTEBOOKS_BRANCH` override."""
    env = os.environ if env is None else env
    data = _yaml(myst_text)
    nma = read_nma_block(myst_text)
    return Settings(
        github_repo=_github_repo(data),
        tutorials_dir=_setting(nma, "paths", "tutorials", DEFAULT_TUTORIALS_DIR).strip("/"),
        notebooks_branch=_notebooks_branch(nma, env),
        assets_data_dir=_setting(nma, "assets", "data", DEFAULT_DATA_DIR).strip("/"),
        assets_image_dir=_setting(nma, "assets", "image", DEFAULT_IMAGE_DIR).strip("/"),
        nma=nma,
        projects_dir=_setting(nma, "paths", "projects", DEFAULT_PROJECTS_DIR).strip("/"),
    )


def read_settings(path: Path = MYST_CONFIG) -> Settings:
    """Read `myst.yml` (from the current directory by default). Raises `MissingConfig` if the file is absent."""
    path = Path(path)
    if not path.is_file():
        raise MissingConfig(path)
    return load_settings(path.read_text(encoding="utf-8"))


class PageLocation(NamedTuple):
    """Where a page lives: its content root, the folder under that root, and the file stem."""
    root: str      # content root name: 'tutorials' or 'projects'
    rel_dir: str   # folder under the content root ('' at the top)
    stem: str

    @property
    def notebook_dir(self) -> str:
        """Folder under notebooks/ holding the page's generated files."""
        return f"{self.root}/{self.rel_dir}" if self.rel_dir else self.root


def page_location(settings: Settings, page: str | Path) -> PageLocation | None:
    """Where a page (path relative to the course root) lives, or None if it is
    outside every content root. 'tutorials/W1/T1.md' -> PageLocation('tutorials', 'W1', 'T1').
    The deepest matching root wins."""
    path = PurePosixPath(Path(page).as_posix())
    for name, directory in sorted(settings.content_roots, key=lambda r: -len(r[1])):
        try:
            rel = path.relative_to(directory)
        except ValueError:
            continue
        rel_dir = rel.parent.as_posix()
        return PageLocation(name, "" if rel_dir == "." else rel_dir, rel.stem)
    return None
