"""
Course settings, read from the course's myst.yml.

Kit settings live in the top-level `nma:` block, as `section: {key: value}`
with string values. js/src/shared/config.mjs reads the same block with a
YAML parser too; both sides are tested against fixtures/config/settings.json.

New settings (all optional, defaults are the template's conventions):

    nma:
      paths:
        tutorials: tutorials        # where the course's .md pages live
      notebooks:
        branch: notebooks-branch    # where generated notebooks are published
"""

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import yaml

DEFAULT_TUTORIALS_DIR = "tutorials"
DEFAULT_NOTEBOOKS_BRANCH = "notebooks-branch"
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
    github_repo: str | None
    tutorials_dir: str = DEFAULT_TUTORIALS_DIR
    notebooks_branch: str = DEFAULT_NOTEBOOKS_BRANCH
    nma: dict = field(default_factory=dict)


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


def load_settings(myst_text: str) -> Settings:
    data = _yaml(myst_text)
    nma = read_nma_block(myst_text)
    return Settings(
        github_repo=_github_repo(data),
        tutorials_dir=_setting(nma, "paths", "tutorials", DEFAULT_TUTORIALS_DIR).strip("/"),
        notebooks_branch=_setting(nma, "notebooks", "branch", DEFAULT_NOTEBOOKS_BRANCH),
        nma=nma,
    )


def read_settings(path: Path = MYST_CONFIG) -> Settings:
    path = Path(path)
    if not path.is_file():
        raise MissingConfig(path)
    return load_settings(path.read_text(encoding="utf-8"))


def page_location(settings: Settings, page: str | Path) -> tuple[str, str] | None:
    """(rel_dir, stem) of a page path relative to the course root, or None if
    it is outside the tutorials dir. 'tutorials/W1/T1.md' -> ('W1', 'T1')."""
    path = PurePosixPath(Path(page).as_posix())
    try:
        rel = path.relative_to(settings.tutorials_dir)
    except ValueError:
        return None
    rel_dir = rel.parent.as_posix()
    return ("" if rel_dir == "." else rel_dir), rel.stem
