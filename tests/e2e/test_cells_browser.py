import os
import re
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import expect  # noqa: E402

from nma_kit import solutions as nma_solutions  # noqa: E402
from nma_kit.solutions import FALLBACK_NOTE  # noqa: E402

# The course whose built site is under test (its .md sources are read to
# count cells). Default: the kit's example course. The template sets
# NMA_E2E_COURSE to its own root.
ROOT = Path(os.environ.get("NMA_E2E_COURSE") or Path(__file__).resolve().parents[2] / "example-course")
TUTORIAL1 = "/tutorials/w2d1-examples/w2d1-tutorial1/"
TUTORIAL1_MD = (ROOT / "tutorials/W2D1_Examples/W2D1_Tutorial1.md").read_text()
DONE = re.compile(r"^\[\s*\d*\] (✓|✗)")


def visible_cell_count(md: str) -> int:
    """Code cells that aren't tagged remove-cell."""
    count = 0
    for m in re.finditer(r"^```\{code-cell\}[^\n]*\n((?::[^\n]*\n)*)", md, re.M):
        if "remove-cell" not in m.group(1):
            count += 1
    return count


def open_page(page, base_url, path):
    page.goto(base_url + path)
    page.wait_for_load_state("networkidle")
    page.wait_for_selector(".myst-anywidget.nma-cell")
    page.wait_for_timeout(2000)  # let hydration settle


def panels(page):
    # anywidget's shadow-root container carries the same class as its host, so
    # restrict the match to the light DOM (one host per cell).
    return page.locator("css:light=.nma-cell")


def panel_with(page, snippet):
    host = panels(page)
    for i in range(host.count()):
        text = host.nth(i).locator(".cm-content").text_content() or ""
        if snippet in text:
            return host.nth(i)
    raise AssertionError(f"no panel contains {snippet!r}")


def status(panel):
    return panel.locator(".status")


def out_text(panel):
    return panel.locator(".nma-cell-out").inner_text()


def run(panel):
    panel.locator("button.run").click()
    expect(status(panel)).to_have_text(DONE, timeout=120_000)


def test_one_panel_per_visible_cell(page, base_url):
    open_page(page, base_url, TUTORIAL1)
    assert panels(page).count() == visible_cell_count(TUTORIAL1_MD)
    for i in range(panels(page).count()):
        panel = panels(page).nth(i)
        assert panel.locator(".nma-cell-out").count() == 1
        if panel.locator(".cm-editor").count() != 1:
            assert panel.locator(".cell").get_attribute("data-mode") == "output"


def test_run_last_cell_runs_earlier_cells(page, base_url):
    open_page(page, base_url, TUTORIAL1)
    last = panels(page).last
    run(last)
    expect(status(last)).to_contain_text("✓")
    first_exercise = panel_with(page, "def integrate_exponential")
    assert FALLBACK_NOTE in out_text(first_exercise)


def test_student_solution_runs(page, base_url):
    open_page(page, base_url, TUTORIAL1)
    exercise = panel_with(page, "def integrate_exponential")
    solution = nma_solutions.exercise_pairs(TUTORIAL1_MD)[0][1]
    exercise.locator(".cm-content").click()
    page.keyboard.press("Control+A")
    page.keyboard.insert_text(solution)
    run(exercise)
    expect(status(exercise)).to_contain_text("✓")
    assert FALLBACK_NOTE not in out_text(exercise)


def test_unfinished_exercise_shows_error(page, base_url):
    open_page(page, base_url, TUTORIAL1)
    exercise = panel_with(page, "def integrate_exponential")
    run(exercise)
    expect(status(exercise)).to_contain_text("✗ NotImplementedError")
    text = out_text(exercise)
    assert "NotImplementedError" in text
    assert FALLBACK_NOTE not in text


def test_interact_slider_updates_plot(page, base_url):
    open_page(page, base_url, TUTORIAL1)
    plot = panel_with(page, "def plot_euler_integration(a, dt)")
    run(plot)
    out = plot.locator(".nma-cell-out")
    expect(out.locator(".widget-slider").first).to_be_visible()
    img = out.locator("img").first
    expect(img).to_be_visible()
    before = img.get_attribute("src")
    out.locator(".noUi-handle, .ui-slider-handle, input[type=range]").first.focus()
    for _ in range(3):
        page.keyboard.press("ArrowRight")
    page.wait_for_function(
        "([sel, before]) => { const i = document.querySelector(sel); return i && i.src !== before; }",
        arg=[".nma-cell-out img", before],
        timeout=10_000,
    )


def go_next(page, expected):
    page.locator("a.myst-footer-link").last.click()
    page.wait_for_function(f"location.pathname.includes({expected!r})")
    page.wait_for_timeout(1500)  # W1D1 Tutorial 2 has no code, so don't wait for panels here


def test_navigation_and_back(page, base_url):
    open_page(page, base_url, "/tutorials/w1d1-gettingstarted/w1d1-tutorial1/")
    run(panels(page).first)
    go_next(page, "w1d1-tutorial2")
    go_next(page, "w1d1-tutorial3")
    page.wait_for_selector(".myst-anywidget.nma-cell")
    run(panels(page).first)
    page.go_back()
    page.wait_for_function("location.pathname.includes('w1d1-tutorial2')")
    page.go_back()
    page.wait_for_function("location.pathname.includes('w1d1-tutorial1')")
    page.wait_for_selector(".myst-anywidget.nma-cell")
    page.wait_for_timeout(1500)
    run(panels(page).first)


def test_colab_page(page, base_url):
    page.goto(base_url + "/tutorials/w2d1-examples/w2d1-tutorial3/")
    page.wait_for_load_state("networkidle")
    banner = page.locator(".nma-colab-banner, .admonition-important").first
    expect(banner).to_contain_text("Do this tutorial in Colab")
    assert page.locator(".myst-anywidget.nma-cell").count() == 0
    expect(page.locator(".myst-jp-nb-toolbar-power")).not_to_be_visible()


def test_edit_marks_output_stale(page, base_url):
    open_page(page, base_url, TUTORIAL1)
    panel = panel_with(page, "import numpy")
    run(panel)
    out = panel.locator(".nma-cell-out")
    panel.locator(".cm-content").click()
    page.keyboard.type("x")
    expect(out).to_have_class(re.compile("is-stale"))
    panel.locator("button.reset").click()
    expect(out).not_to_have_class(re.compile("is-stale"))


def test_restart(page, base_url):
    open_page(page, base_url, TUTORIAL1)
    last = panels(page).last
    run(last)
    last.locator("button.restart").click()
    expect(status(last)).to_have_text("", timeout=120_000)  # restart takes a few seconds
    run(last)
    expect(status(last)).to_contain_text("✓")
    assert FALLBACK_NOTE in out_text(panel_with(page, "def integrate_exponential"))
