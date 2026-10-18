import json
from pathlib import Path

import pytest

from nma_kit.config import MissingConfig, Settings, load_settings, page_location, read_settings
from nma_kit.convert import make_badge_html
from nma_kit.feedback import FORMAT_ERROR, config_errors
from nma_kit.solutions import solution_url

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
CASES = json.loads((FIXTURES / "config" / "settings.json").read_text())["cases"]


def test_defaults_without_nma_block():
    s = load_settings("project:\n  github: https://github.com/o/r\n")
    assert s.tutorials_dir == "tutorials"
    assert s.notebooks_branch == "notebooks-branch"
    assert s.github_repo == "o/r"


def test_custom_paths():
    s = load_settings("nma:\n  paths:\n    tutorials: content\n  notebooks:\n    branch: nb\n")
    assert (s.tutorials_dir, s.notebooks_branch) == ("content", "nb")
    assert s.github_repo is None


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
    rel_dir, stem = location
    assert (rel_dir, stem) == (expect["relDir"], expect["stem"])
    html = make_badge_html(expect["notebook"], s.github_repo, s.notebooks_branch)
    assert f'href="{expect["colab"]}"' in html
    assert f'href="{expect["kaggle"]}"' in html
    assert solution_url(s.github_repo, rel_dir, f"{stem}_Solution_1.py", s.notebooks_branch) == expect["solution1"]


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
