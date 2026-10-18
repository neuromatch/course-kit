"""The kit ships as one version: every place that states it must agree, and
the release-please config must bump all of them."""

import json
import re
from pathlib import Path

import yaml

import nma_kit

KIT = Path(__file__).resolve().parents[2]
WORKFLOWS = KIT / ".github" / "workflows"
REUSABLE = ["course-check.yml", "course-publish.yml"]
MARKER = "x-release-please-version"


def stated_versions() -> dict:
    versions = {
        "js/package.json": json.loads((KIT / "js" / "package.json").read_text())["version"],
        "python/pyproject.toml": re.search(r'^version = "([^"]+)"', (KIT / "python" / "pyproject.toml").read_text(), re.M).group(1),
        "nma_kit.__version__": nma_kit.__version__,
        ".release-please-manifest.json": json.loads((KIT / ".release-please-manifest.json").read_text())["."],
    }
    for name in REUSABLE:
        env = yaml.safe_load((WORKFLOWS / name).read_text())["env"]
        versions[name] = env["KIT_VERSION"]
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
    expected = {f".github/workflows/{n}" for n in REUSABLE} | {
        "js/package.json", "python/pyproject.toml", "python/src/nma_kit/__init__.py"}
    assert expected <= paths, expected - paths


def test_generic_files_carry_the_marker():
    for path in [*(WORKFLOWS / n for n in REUSABLE), KIT / "python" / "src" / "nma_kit" / "__init__.py"]:
        line = next(l for l in path.read_text().splitlines() if re.search(r"\d+\.\d+\.\d+", l) and "VERSION" in l.upper())
        assert MARKER in line, path


def test_course_template_calls_the_v0_1_line():
    text = (KIT / "templates" / "course.yml").read_text()
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert uses and all(u.startswith("neuromatch/course-kit/.github/workflows/") and u.endswith("@v0.1") for u in uses), uses
