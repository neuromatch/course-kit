import json
from pathlib import Path

import pytest

from nma_kit.config import MissingConfig, Settings, load_settings, page_location, read_settings
from nma_kit.convert import make_badge_html
from nma_kit.feedback import FORMAT_ERROR, config_errors
from nma_kit.solutions import solution_url

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CASES = json.loads((FIXTURES / "config" / "settings.json").read_text())["cases"]


def test_defaults_without_nma_block():
    s = load_settings("project:\n  github: https://github.com/o/r\n")
    assert s.tutorials_dir == "tutorials"
    assert s.projects_dir == "projects"
    assert s.content_roots == (("tutorials", "tutorials"), ("projects", "projects"))
    assert s.notebooks_branch == "notebooks-branch"
    assert s.github_repo == "o/r"


def test_custom_paths():
    s = load_settings("nma:\n  paths:\n    tutorials: content\n  notebooks:\n    branch: nb\n")
    assert (s.tutorials_dir, s.notebooks_branch) == ("content", "nb")
    assert s.github_repo is None


def test_asset_dirs_default_and_custom():
    d = load_settings("project:\n  github: https://github.com/o/r\n")
    assert (d.assets_data_dir, d.assets_image_dir) == ("data", "image")
    c = load_settings("nma:\n  assets:\n    data: files\n    image: pics/\n")
    assert (c.assets_data_dir, c.assets_image_dir) == ("files", "pics")


def test_custom_projects_dir():
    s = load_settings("nma:\n  paths:\n    projects: capstone/\n")
    assert s.content_roots == (("tutorials", "tutorials"), ("projects", "capstone"))


def test_nma_block_is_exposed():
    s = load_settings("nma:\n  feedback:\n    url: https://x\n")
    assert s.nma == {"feedback": {"url": "https://x"}}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_shared_fixture_cases(case):
    s = load_settings(case["myst"])
    location = page_location(s, case["page"])
    expect = case["expect"]
    if expect is None:
        assert location is None
        return
    assert (location.root, location.rel_dir, location.stem) == (expect["root"], expect["relDir"], expect["stem"])
    assert location.notebook_dir == expect["notebookDir"]
    html = make_badge_html(expect["notebook"], s.github_repo, s.notebooks_branch)
    assert f'href="{expect["colab"]}"' in html
    assert f'href="{expect["kaggle"]}"' in html
    assert solution_url(s.github_repo, location.notebook_dir, f"{location.stem}_Solution_1.py", s.notebooks_branch) == expect["solution1"]


def test_number_value_rejected():
    assert config_errors("nma:\n  feedback:\n    user_key: 123\n") == [FORMAT_ERROR]


def test_list_value_rejected():
    assert config_errors("nma:\n  feedback:\n    url: [a, b]\n") == [FORMAT_ERROR]


def test_read_settings_missing_file(tmp_path):
    with pytest.raises(MissingConfig) as info:
        read_settings(tmp_path / "myst.yml")
    assert "myst.yml" in str(info.value)


def test_read_settings_reads_file(tmp_path):
    (tmp_path / "myst.yml").write_text("nma:\n  paths:\n    tutorials: content\n")
    assert read_settings(tmp_path / "myst.yml") == Settings(None, "content", "notebooks-branch",
                                                            {"paths": {"tutorials": "content"}})
