import re
from pathlib import Path

import pytest
import yaml

from nma_kit import __version__, scaffold
from nma_kit.cli import main

REPO = Path(__file__).resolve().parents[2]
ARGS = ["--title", "My Course", "--author", "Ada Lovelace", "--author", "Alan Turing",
        "--github", "https://github.com/org/my-course", "--license", "MIT"]


def init(tmp_path, *extra):
    target = tmp_path / "course"
    code = main(["init", str(target), *ARGS, *extra])
    return code, target


def test_workflow_comes_from_the_repo_template_in_a_checkout(monkeypatch, tmp_path):
    # The package copy exists only in release builds; without it `init` reads templates/course.yml.
    monkeypatch.setattr(scaffold, "TEMPLATES", tmp_path)   # no templates/workflows/ here
    assert scaffold.workflow_template() == REPO / "templates" / "course.yml"


def test_workflow_prefers_the_packaged_copy(monkeypatch, tmp_path):
    copy = tmp_path / "workflows" / "course.yml"
    copy.parent.mkdir()
    copy.write_text("x", encoding="utf-8")
    monkeypatch.setattr(scaffold, "TEMPLATES", tmp_path)
    assert scaffold.workflow_template() == copy


def test_nvmrc_matches_the_kit_node_version():
    node = next(line.split()[1] for line in (REPO / ".tool-versions").read_text().splitlines()
                if line.startswith("nodejs"))
    nvmrc = (scaffold.TEMPLATES / "course" / "dot-nvmrc").read_text().strip()
    assert node.split(".")[0] == nvmrc


def test_writes_the_starter(tmp_path):
    code, target = init(tmp_path)
    assert code == 0
    for name in ("myst.yml", "requirements.txt", ".nvmrc", ".gitignore", "LICENSE", "README.md",
                 ".github/workflows/course.yml", "tutorials/intro.md",
                 "tutorials/W1D1_Example/chapter_intro.md", "tutorials/W1D1_Example/W1D1_Tutorial1.md",
                 "tutorials/W1D1_Example/further_reading.md", "projects/project_intro.md"):
        assert (target / name).is_file(), name


def test_no_placeholders_or_template_names_are_left(tmp_path):
    _, target = init(tmp_path, "--preview")
    for path in target.rglob("*"):
        assert not path.name.endswith(".tmpl") and not path.name.startswith("dot-"), path
        if path.is_file():
            assert not re.search(r"\{\{\w+\}\}", path.read_text(encoding="utf-8")), path


def test_myst_yml(tmp_path):
    _, target = init(tmp_path)
    text = (target / "myst.yml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    minor = ".".join(__version__.split(".")[:2])
    assert data["extend"] == f"https://cdn.jsdelivr.net/npm/@neuromatch/course-kit@{minor}/dist/nma.yml"
    assert data["project"]["title"] == "My Course"
    assert data["project"]["github"] == "https://github.com/org/my-course"
    assert [a["name"] for a in data["project"]["authors"]] == ["Ada Lovelace", "Alan Turing"]
    # The feedback block is a comment, and does not point at the Neuromatch project.
    assert "feedback" not in data.get("nma", {})
    assert "# nma:" in text or "#   feedback:" in text
    assert "neuromatch_cn" not in text and "amazonaws" not in text


def test_title_with_yaml_characters_stays_valid(tmp_path):
    target = tmp_path / "c"
    assert main(["init", str(target), "--title", 'A: "B" #1', "--author", "O'Neil: Jr",
                 "--github", "https://github.com/o/r", "--license", "MIT"]) == 0
    data = yaml.safe_load((target / "myst.yml").read_text(encoding="utf-8"))
    assert data["project"]["title"] == 'A: "B" #1'
    assert data["project"]["authors"][0]["name"] == "O'Neil: Jr"


def test_workflow_without_preview(tmp_path):
    _, target = init(tmp_path)
    text = (target / ".github/workflows/course.yml").read_text()
    jobs = yaml.safe_load(text)["jobs"]
    assert set(jobs) == {"check", "publish"}
    # The preview job is kept as a comment, so enabling it is uncommenting.
    assert "#   preview:" in text or "# preview:" in text
    assert "course-preview.yml" in text


def test_workflow_with_preview(tmp_path):
    _, target = init(tmp_path, "--preview")
    text = (target / ".github/workflows/course.yml").read_text()
    assert set(yaml.safe_load(text)["jobs"]) == {"check", "publish", "preview"}
    assert "does not want previews" not in text and "previews are off" not in text


def test_workflow_pins_the_kit_minor(tmp_path):
    _, target = init(tmp_path)
    minor = ".".join(__version__.split(".")[:2])
    text = (target / ".github/workflows/course.yml").read_text()
    refs = re.findall(r"course-kit/\.github/workflows/[\w-]+\.yml@(\S+)", text)
    assert refs and set(refs) == {f"v{minor}"}


def test_license_is_chosen_and_filled_in(tmp_path):
    _, target = init(tmp_path)
    text = (target / "LICENSE").read_text()
    assert text.startswith("MIT License")
    assert "Ada Lovelace, Alan Turing" in text


@pytest.mark.parametrize("name", sorted(scaffold.LICENSES))
def test_every_license_renders(tmp_path, name):
    target = tmp_path / "c"
    assert main(["init", str(target), *ARGS[:-2], "--license", name]) == 0
    assert (target / "LICENSE").read_text().strip()


def test_readme_checklist_mentions_cloudflare_only_with_preview(tmp_path):
    _, plain = init(tmp_path)
    _, with_preview = init(tmp_path / "p", "--preview")
    assert "Pages" in (plain / "README.md").read_text()
    assert "CLOUDFLARE_API_TOKEN" not in (plain / "README.md").read_text()
    assert "CLOUDFLARE_API_TOKEN" in (with_preview / "README.md").read_text()


def test_the_starter_passes_check_and_builds_notebooks(tmp_path, monkeypatch):
    _, target = init(tmp_path)
    monkeypatch.chdir(target)
    assert main(["check"]) == 0
    assert main(["notebooks"]) == 0
    assert (target / "notebooks/tutorials/W1D1_Example/W1D1_Tutorial1.ipynb").is_file()
    assert (target / "notebooks/tutorials/W1D1_Example/instructor/W1D1_Tutorial1.ipynb").is_file()
    assert list((target / "notebooks/tutorials/W1D1_Example/solutions").glob("*"))


def test_toc_lists_only_files_that_exist(tmp_path):
    _, target = init(tmp_path)
    data = yaml.safe_load((target / "myst.yml").read_text(encoding="utf-8"))

    def files(entries):
        for entry in entries:
            if "file" in entry:
                yield entry["file"]
            yield from files(entry.get("children", []))

    listed = list(files(data["project"]["toc"]))
    assert listed
    for rel in listed:
        assert (target / rel).is_file(), rel


def test_refuses_to_overwrite(tmp_path, capsys):
    _, target = init(tmp_path)
    (target / "myst.yml").write_text("mine", encoding="utf-8")
    assert main(["init", str(target), *ARGS]) == 2
    assert "myst.yml" in capsys.readouterr().err
    assert (target / "myst.yml").read_text(encoding="utf-8") == "mine"


def test_missing_values_without_a_terminal_is_a_usage_error(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", open("/dev/null"))
    assert main(["init", str(tmp_path / "c"), "--author", "A"]) == 2
    assert "--title" in capsys.readouterr().err
    assert not (tmp_path / "c").exists()


def test_prompts_for_missing_values(tmp_path, monkeypatch):
    answers = iter(["Prompted Course", "Grace Hopper", "", "https://github.com/o/r", "MIT"])
    monkeypatch.setattr(scaffold, "is_interactive", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    target = tmp_path / "c"
    assert main(["init", str(target)]) == 0
    data = yaml.safe_load((target / "myst.yml").read_text(encoding="utf-8"))
    assert data["project"]["title"] == "Prompted Course"
    assert data["project"]["authors"] == [{"name": "Grace Hopper"}]


def test_rejects_a_bad_github_url_and_license(tmp_path, capsys):
    assert main(["init", str(tmp_path / "a"), *ARGS[:-4], "--github", "nope", "--license", "MIT"]) == 2
    with pytest.raises(SystemExit) as exc:   # argparse rejects it, with the choices listed
        main(["init", str(tmp_path / "b"), *ARGS[:-1], "WTFPL"])
    assert exc.value.code == 2
    assert not (tmp_path / "a").exists() and not (tmp_path / "b").exists()
