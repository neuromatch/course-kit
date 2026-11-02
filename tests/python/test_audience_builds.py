"""The example course as built for each audience (tests/scripts/build-example.sh with
NMA_BUILD_INSTRUCTOR=1): student site in _build/html, instructor site in _build/html-instructor.

Skipped unless those builds exist. They read the built files, not a browser: the page content
is in each page's JSON, so no kernel has to boot.

Not asserted: that the student pages hold no solution *code*. Browser pages carry a hidden
run-all fallback cell that runs the reference solution (nma_kit.solutions), so the code is in
the student page data already. What differs is the inline box and the link."""

import os
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
COURSE = Path(os.environ.get("NMA_BUILT_COURSE", KIT / "tests" / "example-course"))
STUDENT = COURSE / "_build" / "html"
INSTRUCTOR = COURSE / "_build" / "html-instructor"
PAGE = "w2d1-tutorial1"  # tutorials/W2D1_Examples/W2D1_Tutorial1.md has a solution, explanations and a note
NOTE = "Ask for predictions before running the cell"
EXPLANATION = "The more general lesson is that, for each system"
STUDENT_ROBOTS = "User-agent: *\nAllow: /\n"
INSTRUCTOR_ROBOTS = "User-agent: *\nDisallow: /\n"

needs_student = pytest.mark.skipif(not (STUDENT / "robots.txt").exists(), reason="no student build of the example course")
needs_instructor = pytest.mark.skipif(not INSTRUCTOR.exists(), reason="no instructor build (NMA_BUILD_INSTRUCTOR=1)")


def page_text(site: Path) -> str:
    """Everything the build wrote for the page: its HTML and its JSON."""
    files = [p for p in site.rglob("*") if PAGE in p.as_posix() and p.suffix in (".html", ".json")]
    assert files, f"no output for {PAGE} under {site}"
    return "\n".join(p.read_text(encoding="utf-8") for p in files)


def all_html(site: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in site.rglob("*.html"))


@needs_instructor
def test_instructor_site_shows_notes_and_inline_answers():
    text = page_text(INSTRUCTOR)
    assert NOTE in text
    assert EXPLANATION in text
    assert "nma-solution-inline" in text
    assert "Click for solution" not in text and "Click for explanation" not in text


@needs_instructor
def test_instructor_badges_open_the_instructor_notebook():
    text = page_text(INSTRUCTOR)
    assert "notebooks/tutorials/W2D1_Examples/instructor/W2D1_Tutorial1.ipynb" in text
    assert "notebooks/tutorials/W2D1_Examples/W2D1_Tutorial1.ipynb" not in text


@needs_instructor
def test_instructor_site_is_kept_out_of_search_engines():
    assert (INSTRUCTOR / "robots.txt").read_text() == INSTRUCTOR_ROBOTS
    assert "X-Robots-Tag: noindex" in (INSTRUCTOR / "_headers").read_text()
    assert not (INSTRUCTOR / "sitemap.xml").exists()


@needs_instructor
def test_instructor_pages_have_no_canonical_or_og_url():
    html = all_html(INSTRUCTOR)
    assert 'rel="canonical"' not in html
    assert 'property="og:url"' not in html


@needs_student
def test_student_site_has_no_notes_and_keeps_the_links():
    text = page_text(STUDENT)
    assert NOTE not in text
    assert EXPLANATION not in text
    assert "nma-solution-inline" not in text
    assert "Click for solution" in text


@needs_student
def test_student_badges_open_the_student_notebook():
    text = page_text(STUDENT)
    assert "notebooks/tutorials/W2D1_Examples/W2D1_Tutorial1.ipynb" in text
    assert "/instructor/W2D1_Tutorial1.ipynb" not in text


@needs_student
def test_student_site_has_a_real_robots_txt_and_no_sitemap():
    assert (STUDENT / "robots.txt").read_text() == STUDENT_ROBOTS
    assert not (STUDENT / "sitemap.xml").exists() and not (STUDENT / "sitemap_style.xsl").exists()
    assert not (STUDENT / "_headers").exists()
