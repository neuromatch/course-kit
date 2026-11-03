import json
from pathlib import Path

import pytest

from nma_kit.config import (
    MissingConfig,
    Settings,
    content_errors,
    content_path_problem,
    content_roots_from,
    load_settings,
    notebook_rel_path,
    page_location,
    read_nma_block,
    read_settings,
)
from nma_kit.convert import make_badge_html
from nma_kit.feedback import FORMAT_ERROR, config_errors
from nma_kit.solutions import solution_url

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CASES = json.loads((FIXTURES / "config" / "settings.json").read_text())["cases"]
CONTENT_CASES = json.loads((FIXTURES / "config" / "content.json").read_text())["cases"]


def test_defaults_without_nma_block():
    s = load_settings("project:\n  github: https://github.com/o/r\n")
    assert s.content_roots == ()   # no defaults: the course declares its content
    assert s.notebooks_branch == "notebooks-branch"
    assert s.github_repo == "o/r"


def test_content_and_notebooks_branch():
    s = load_settings("nma:\n  content: [content]\n  notebooks:\n    branch: nb\n")
    assert (s.content_roots, s.notebooks_branch) == ((("content", "content"),), "nb")
    assert s.github_repo is None


@pytest.mark.parametrize("case", CONTENT_CASES, ids=lambda c: c["name"])
def test_shared_content_cases(case):
    import yaml

    nma = yaml.safe_load(case["nma"])
    assert [list(r) for r in content_roots_from(nma)] == case["roots"]
    assert load_settings(f"nma: {case['nma']}\n").content_roots == tuple(tuple(r) for r in case["roots"])


def test_content_path_problem():
    assert content_path_problem("docs/guide") is None
    assert "inside the course" in content_path_problem("..")
    assert "relative" in content_path_problem("/x")
    assert "owns it" in content_path_problem("notebooks/x")
    assert content_path_problem("") == "is empty"


def errors_for(nma_yaml: str) -> list[str]:
    return content_errors(read_nma_block(f"nma:\n{nma_yaml}"))


def test_content_is_required():
    assert "nma.content is required" in content_errors({})[0]
    assert "nma.content is required" in errors_for("  content: []\n")[0]
    assert "must be a list" in errors_for("  content: tutorials\n")[0]


def test_content_errors_name_each_problem():
    assert errors_for("  content: [tutorials, {name: guide, path: docs/guide}]\n") == []
    assert any("'..'" in e for e in errors_for("  content: ['..']\n"))
    assert any("'.'" in e for e in errors_for("  content: ['.']\n"))
    assert any("name 'a b'" in e for e in errors_for("  content: [{name: a b, path: x}]\n"))
    assert any("must be a folder or" in e for e in errors_for("  content: [3]\n"))


def test_content_errors_reject_duplicate_names_and_nested_folders():
    assert any("used twice" in e for e in errors_for("  content: [{name: a, path: x}, {name: a, path: y}]\n"))
    assert any("overlap" in e for e in errors_for("  content: [a, a/b]\n"))
    assert any("overlap" in e for e in errors_for("  content: [a/b, a]\n"))
    assert errors_for("  content: [a, ab]\n") == []   # a sibling that shares a prefix is not nested


def test_old_paths_keys_say_what_to_write_instead():
    errors = errors_for("  paths:\n    tutorials: content\n")
    assert len(errors) == 1 and "nma.paths.tutorials" in errors[0] and "nma.content" in errors[0]
    assert "name: tutorials" in errors[0]


def test_asset_dirs_default_and_custom():
    d = load_settings("project:\n  github: https://github.com/o/r\n")
    assert (d.assets_data_dir, d.assets_image_dir) == ("data", "images")
    c = load_settings("nma:\n  assets:\n    data: files\n    image: pics/\n")
    assert (c.assets_data_dir, c.assets_image_dir) == ("files", "pics")


def test_slides_dir_default_and_custom():
    assert load_settings("").assets_slides_dir == "slides"
    assert load_settings("nma:\n  assets:\n    slides: decks/\n").assets_slides_dir == "decks"


def test_nma_block_is_exposed():
    s = load_settings("nma:\n  feedback:\n    url: https://x\n")
    assert s.nma == {"feedback": {"url": "https://x"}}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_shared_fixture_cases(case):
    s = load_settings(case["myst"], env=case.get("env", {}))
    location = page_location(s, case["page"])
    expect = case["expect"]
    assert s.audience == (expect or {}).get("audience", "student")
    if expect is None:
        assert location is None
        return
    assert (location.root, location.rel_dir, location.stem) == (expect["root"], expect["relDir"], expect["stem"])
    assert location.notebook_dir == expect["notebookDir"]
    assert notebook_rel_path(s, location) == expect["notebook"]
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
    (tmp_path / "myst.yml").write_text("nma:\n  content: [content]\n")
    assert read_settings(tmp_path / "myst.yml") == Settings(None, (("content", "content"),), "notebooks-branch",
                                                            {"content": ["content"]})


def test_audience_defaults_to_student_and_follows_the_env():
    assert load_settings("").audience == "student"
    assert load_settings("", env={"NMA_AUDIENCE": "instructor"}).audience == "instructor"
    assert load_settings("", env={"NMA_AUDIENCE": " instructor "}).audience == "instructor"
    assert load_settings("", env={"NMA_AUDIENCE": ""}).audience == "student"


def _course(tmp_path, monkeypatch, audience):
    (tmp_path / "myst.yml").write_text("project:\n  github: https://github.com/o/r\nnma:\n  content: [tutorials]\n")
    (tmp_path / "tutorials").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NMA_AUDIENCE", audience)


def test_unknown_audience_is_a_check_error(tmp_path, monkeypatch):
    from nma_kit.convert import validate_content

    _course(tmp_path, monkeypatch, "Instructor")
    errors = validate_content()
    assert any("student, instructor" in e and "'Instructor'" in e for e in errors), errors


@pytest.mark.parametrize("audience", ["student", "instructor", " "])
def test_valid_audiences_add_no_error(tmp_path, monkeypatch, audience):
    from nma_kit.convert import validate_content

    _course(tmp_path, monkeypatch, audience)
    assert not [e for e in validate_content() if "NMA_AUDIENCE" in e]
