"""finalize-site: the robots.txt, sitemap and noindex header of a built site."""

import pytest

from nma_kit.cli import main
from nma_kit.site import finalize_site

STUDENT_ROBOTS = "User-agent: *\nAllow: /\n"
INSTRUCTOR_ROBOTS = "User-agent: *\nDisallow: /\n"
NOINDEX = "/*\n  X-Robots-Tag: noindex, nofollow\n"


def built(tmp_path):
    html = tmp_path / "_build" / "html"
    html.mkdir(parents=True)
    (html / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: http://localhost:3000/sitemap.xml\n")
    (html / "sitemap.xml").write_text("<urlset>http://localhost:3000</urlset>")
    (html / "sitemap_style.xsl").write_text("<xsl/>")
    return html


def test_student_site_gets_a_real_robots_txt_and_no_sitemap(tmp_path):
    html = built(tmp_path)
    finalize_site(html, "student")
    assert (html / "robots.txt").read_text() == STUDENT_ROBOTS
    assert not (html / "sitemap.xml").exists() and not (html / "sitemap_style.xsl").exists()
    assert not (html / "_headers").exists()


def test_instructor_site_disallows_crawlers_and_sets_noindex(tmp_path):
    html = built(tmp_path)
    finalize_site(html, "instructor")
    assert (html / "robots.txt").read_text() == INSTRUCTOR_ROBOTS
    assert (html / "_headers").read_text() == NOINDEX
    assert not (html / "sitemap.xml").exists()


def test_an_existing_headers_file_keeps_its_lines_and_gets_the_block_once(tmp_path):
    html = built(tmp_path)
    (html / "_headers").write_text("/assets/*\n  Cache-Control: max-age=60\n")
    finalize_site(html, "instructor")
    finalize_site(html, "instructor")
    text = (html / "_headers").read_text()
    assert text.startswith("/assets/*\n  Cache-Control: max-age=60\n")
    assert text.count("X-Robots-Tag") == 1


def test_running_twice_changes_nothing(tmp_path):
    html = built(tmp_path)
    finalize_site(html, "instructor")
    first = {p.name: p.read_text() for p in html.iterdir()}
    assert finalize_site(html, "instructor") == ["robots.txt"]
    assert {p.name: p.read_text() for p in html.iterdir()} == first


def test_a_folder_without_robots_or_sitemap_works(tmp_path):
    html = tmp_path / "html"
    html.mkdir()
    finalize_site(html, "student")
    assert (html / "robots.txt").read_text() == STUDENT_ROBOTS


def test_it_reports_what_it_wrote_and_deleted(tmp_path):
    html = built(tmp_path)
    assert finalize_site(html, "instructor") == ["sitemap.xml", "sitemap_style.xsl", "robots.txt", "_headers"]


def course(tmp_path, monkeypatch, audience=None):
    (tmp_path / "myst.yml").write_text("project:\n  github: https://github.com/o/r\n")
    monkeypatch.chdir(tmp_path)
    if audience is None:
        monkeypatch.delenv("NMA_AUDIENCE", raising=False)
    else:
        monkeypatch.setenv("NMA_AUDIENCE", audience)


def test_cli_uses_the_audience_from_the_environment(tmp_path, monkeypatch):
    course(tmp_path, monkeypatch, "instructor")
    html = built(tmp_path)
    assert main(["finalize-site"]) == 0
    assert (html / "robots.txt").read_text() == INSTRUCTOR_ROBOTS


def test_cli_defaults_to_student(tmp_path, monkeypatch):
    course(tmp_path, monkeypatch)
    html = built(tmp_path)
    assert main(["finalize-site"]) == 0
    assert (html / "robots.txt").read_text() == STUDENT_ROBOTS


def test_cli_accepts_another_folder(tmp_path, monkeypatch):
    course(tmp_path, monkeypatch)
    other = tmp_path / "out"
    other.mkdir()
    assert main(["finalize-site", "--dir", "out"]) == 0
    assert (other / "robots.txt").exists()


@pytest.mark.parametrize("setup", ["missing", "bad-audience"])
def test_cli_exit_2(tmp_path, monkeypatch, capsys, setup):
    course(tmp_path, monkeypatch, "Instructor" if setup == "bad-audience" else None)
    if setup == "bad-audience":
        built(tmp_path)
    assert main(["finalize-site"]) == 2
    err = capsys.readouterr().err
    assert ("_build/html" in err) if setup == "missing" else ("student, instructor" in err)
