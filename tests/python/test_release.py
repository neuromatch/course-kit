"""The kit ships as one version: every place that states it must agree, and
the release-please config must bump all of them."""

import json
import re
from pathlib import Path

import nma_kit

KIT = Path(__file__).resolve().parents[2]
WORKFLOWS = KIT / ".github" / "workflows"
REUSABLE = ["course-check.yml", "course-publish.yml", "course-preview.yml"]
MARKER = "x-release-please-version"


def stated_versions() -> dict:
    versions = {
        "js/package.json": json.loads((KIT / "js" / "package.json").read_text())["version"],
        "js/package-lock.json": json.loads((KIT / "js" / "package-lock.json").read_text())["version"],
        "js/package-lock.json (root package)": json.loads((KIT / "js" / "package-lock.json").read_text())["packages"][""]["version"],
        "python/pyproject.toml": re.search(r'^version = "([^"]+)"', (KIT / "python" / "pyproject.toml").read_text(), re.M).group(1),
        "nma_kit.__version__": nma_kit.__version__,
        ".release-please-manifest.json": json.loads((KIT / ".release-please-manifest.json").read_text())["."],
    }
    return versions


def test_one_version_everywhere():
    versions = stated_versions()
    assert len(set(versions.values())) == 1, versions


def test_starts_on_0x():
    assert nma_kit.__version__.startswith("0.")


def test_release_please_bumps_every_file():
    config = json.loads((KIT / "release-please-config.json").read_text())
    package = config["packages"]["."]
    assert config.get("bump-minor-pre-major") is True
    assert config.get("bump-patch-for-minor-pre-major") is True
    paths = {f["path"] if isinstance(f, dict) else f for f in package["extra-files"]}
    expected = {"js/package.json", "js/package-lock.json", "python/pyproject.toml", "python/src/nma_kit/__init__.py"}
    assert expected <= paths, expected - paths


def test_generic_files_carry_the_marker():
    path = KIT / "python" / "src" / "nma_kit" / "__init__.py"
    line = next(ln for ln in path.read_text().splitlines() if re.search(r"\d+\.\d+\.\d+", ln) and "VERSION" in ln.upper())
    assert MARKER in line, path


def test_workflows_get_the_kit_version_from_the_manifest():
    """The reusable workflows carry no version of their own: the setup action reads
    .release-please-manifest.json from the workflow's own commit."""
    for name in REUSABLE:
        text = (WORKFLOWS / name).read_text()
        assert "KIT_VERSION" not in text and MARKER not in text, name
        assert ".release-please-manifest.json" in text, f"{name} must fetch the manifest for the setup action"
    action = (KIT / ".github" / "actions" / "setup-course" / "action.yml").read_text()
    assert ".release-please-manifest.json" in action


def test_course_template_calls_the_v0_1_line():
    text = (KIT / "templates" / "course.yml").read_text()
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert uses and all(u.startswith("neuromatch/course-kit/.github/workflows/") and u.endswith("@v0.1") for u in uses), uses
