"""The PDF viewer that the Colab slides cell shows (nma_kit.media.PDF_VIEWER_HTML), in a real browser.

It needs no built site, only a browser. PDF.js comes from jsDelivr, as it does in Colab;
set NMA_E2E_PDFJS_DIR to a local `node_modules/pdfjs-dist` (version PDFJS_VERSION)
where jsDelivr is blocked. The PDF is served from a made-up address, with the
cross-origin header jsDelivr sends.
"""

import mimetypes
import os
from pathlib import Path

import pytest

pytest.importorskip("playwright")

from nma_kit.media import PDF_VIEWER_HTML, PDFJS_URL  # noqa: E402

pytestmark = pytest.mark.flaky(reruns=0)

KIT = Path(__file__).resolve().parents[2]
PDF = KIT / "tests/example-course/tutorials/W2D1_Examples/slides/example_slides.pdf"
PDFJS_DIR = os.environ.get("NMA_E2E_PDFJS_DIR")
PDF_URL = "https://slides.example.test/example_slides.pdf"
PAGE_URL = "https://notebook.example.test/"
CORS = {"access-control-allow-origin": "*"}


def viewer_page(url=PDF_URL):
    return "<!doctype html><body>" + (
        PDF_VIEWER_HTML.replace("__LIB__", PDFJS_URL).replace("__ID__", "box").replace("__URL__", f'"{url}"')
    )


def serve_pdfjs_locally(page):
    def local(route):
        name = route.request.url[len(PDFJS_URL):].split("?")[0]
        path = Path(PDFJS_DIR) / name
        if not path.is_file():
            return route.fulfill(status=404, headers=CORS, body="not found")
        kind = "text/javascript" if name.endswith(".mjs") else mimetypes.guess_type(name)[0] or "application/octet-stream"
        return route.fulfill(path=str(path), content_type=kind, headers=CORS)

    page.route(PDFJS_URL + "**", local)


@pytest.fixture
def viewer(_browser):
    context = _browser.new_context(viewport={"width": 1000, "height": 700})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # Same shape as Colab's output frame: a page on another origin than the PDF and PDF.js.
    page.route(PAGE_URL, lambda r: r.fulfill(body=viewer_page(), content_type="text/html"))
    page.route(PDF_URL, lambda r: r.fulfill(path=str(PDF), content_type="application/pdf", headers=CORS))
    if PDFJS_DIR:
        serve_pdfjs_locally(page)
    yield page, errors
    context.close()


def page_width(page, number):
    return page.evaluate(f"document.querySelector('#box .page[data-page-number=\"{number}\"]').getBoundingClientRect().width")


def drawn(page, number):
    """The slide's canvas has at least one dark pixel (it is drawn, not blank)."""
    return page.evaluate(
        f"""() => {{
            const c = document.querySelector('#box .page[data-page-number="{number}"] canvas');
            if (!c) return false;
            const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
            for (let i = 0; i < d.length; i += 4) if (d[i] < 200) return true;
            return false;
        }}"""
    )


def open_viewer(page):
    page.goto(PAGE_URL)
    page.wait_for_function("document.querySelector('#box [data-page]').textContent === '1 / 2'", timeout=60000)
    page.wait_for_function("document.querySelector('#box canvas')", timeout=60000)


def test_the_first_slide_is_drawn_and_fits_the_box(viewer):
    page, errors = viewer
    open_viewer(page)
    page.wait_for_function("document.querySelector('#box .page[data-page-number=\"1\"] canvas')")
    assert drawn(page, 1)
    box = page.locator("#box [data-container]").bounding_box()
    slide = page.locator("#box .page[data-page-number='1'] .canvasWrapper").bounding_box()  # the page without its border
    # "Fit" shows the whole slide: it is inside the scroll area, not zoomed out to a speck.
    assert slide["height"] <= box["height"] + 1 and slide["width"] <= box["width"] + 1
    assert slide["width"] > box["width"] * 0.5 or slide["height"] > box["height"] * 0.5
    assert not errors


def test_zoom_buttons_change_the_size_and_fit_restores_it(viewer):
    page, _ = viewer
    open_viewer(page)
    fitted = page_width(page, 1)
    page.click("#box [data-act=in]")
    zoomed = page_width(page, 1)
    assert zoomed > fitted * 1.2
    page.click("#box [data-act=out]")
    page.click("#box [data-act=out]")
    assert page_width(page, 1) < zoomed
    page.click("#box [data-act=fit]")
    assert abs(page_width(page, 1) - fitted) < 2


def test_zoomed_in_slides_scroll(viewer):
    page, _ = viewer
    open_viewer(page)
    page.click("#box [data-act=in]")
    page.click("#box [data-act=in]")
    scrollable = page.evaluate(
        "(() => { const c = document.querySelector('#box [data-container]'); return c.scrollHeight > c.clientHeight; })()"
    )
    assert scrollable


def test_next_and_previous_move_between_slides(viewer):
    page, _ = viewer
    open_viewer(page)
    page.click("#box [data-act=next]")
    page.wait_for_function("document.querySelector('#box [data-page]').textContent === '2 / 2'")
    page.wait_for_function("document.querySelector('#box .page[data-page-number=\"2\"] canvas')")
    assert drawn(page, 2)
    page.click("#box [data-act=prev]")
    page.wait_for_function("document.querySelector('#box [data-page]').textContent === '1 / 2'")


def test_a_pdf_that_cannot_be_loaded_leaves_a_link(viewer):
    page, _ = viewer
    page.route(PAGE_URL, lambda r: r.fulfill(
        body=viewer_page("https://slides.example.test/missing.pdf"), content_type="text/html"))
    page.route("https://slides.example.test/missing.pdf", lambda r: r.fulfill(status=404, headers=CORS, body="no"))
    page.goto(PAGE_URL)
    link = page.locator("#box a")
    link.wait_for(timeout=60000)
    assert link.get_attribute("href") == "https://slides.example.test/missing.pdf"
