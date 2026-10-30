"""The PDF viewer that the Colab slides cell shows (nma_kit.media.PDF_VIEWER_HTML), in a real browser.

It needs no built site, only a browser. PDF.js comes from jsDelivr, as it does in Colab;
set NMA_E2E_PDFJS_DIR to a local `node_modules/pdfjs-dist/build` (version PDFJS_VERSION)
where jsDelivr is blocked. The PDF is served from a made-up address, with the
cross-origin header jsDelivr sends.
"""

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
CORS = {"access-control-allow-origin": "*"}


def viewer_page(url=PDF_URL):
    return "<!doctype html><body>" + (
        PDF_VIEWER_HTML.replace("__LIB__", PDFJS_URL).replace("__ID__", "box").replace("__URL__", f'"{url}"')
    )


@pytest.fixture
def viewer(_browser):
    context = _browser.new_context()
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # Same shape as Colab's output frame: a page on another origin than the PDF and PDF.js.
    page.route("https://notebook.example.test/", lambda r: r.fulfill(body=viewer_page(), content_type="text/html"))
    page.route(PDF_URL, lambda r: r.fulfill(path=str(PDF), content_type="application/pdf", headers=CORS))
    if PDFJS_DIR:
        def local(route):
            name = route.request.url.rsplit("/", 1)[1]
            route.fulfill(path=str(Path(PDFJS_DIR) / name), content_type="text/javascript", headers=CORS)
        page.route(PDFJS_URL + "*", local)
    yield page, errors
    context.close()


def test_every_page_of_the_pdf_is_drawn(viewer):
    page, errors = viewer
    page.goto("https://notebook.example.test/")
    page.wait_for_function("document.querySelectorAll('#box canvas').length === 2", timeout=60000)
    assert page.locator("#box a").count() == 0
    # Pages are drawn, not blank: at least one non-white pixel on each.
    drawn = page.evaluate(
        """() => [...document.querySelectorAll('#box canvas')].map(c => {
            const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
            for (let i = 0; i < d.length; i += 4) if (d[i] < 200) return true;
            return false;
        })"""
    )
    assert drawn == [True, True]
    assert not errors


def test_a_pdf_that_cannot_be_loaded_leaves_a_link(viewer):
    page, _ = viewer
    page.route("https://notebook.example.test/", lambda r: r.fulfill(
        body=viewer_page("https://slides.example.test/missing.pdf"), content_type="text/html"))
    page.route("https://slides.example.test/missing.pdf", lambda r: r.fulfill(status=404, headers=CORS, body="no"))
    page.goto("https://notebook.example.test/")
    link = page.locator("#box a")
    link.wait_for(timeout=60000)
    assert link.get_attribute("href") == "https://slides.example.test/missing.pdf"
