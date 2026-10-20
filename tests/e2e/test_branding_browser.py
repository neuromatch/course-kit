"""Browser checks for the kit's site branding (_nma/site.css via `nma-kit sync-assets`)."""

import pytest

pytest.importorskip("playwright")

PAGE = "/tutorials/w2d1-examples/w2d1-tutorial1/"


def test_brand_font_and_colours_apply_without_external_requests(page, base_url):
    requests = []
    page.on("request", lambda r: requests.append(r.url))
    page.goto(base_url + PAGE)
    page.wait_for_load_state("networkidle")

    # Rubik comes from the embedded data URI, so it must be loaded and in use.
    assert page.evaluate("document.fonts.ready.then(() => document.fonts.check('1em Rubik'))")
    assert "Rubik" in page.evaluate("getComputedStyle(document.body).fontFamily")

    primary = page.evaluate(
        "getComputedStyle(document.documentElement).getPropertyValue('--nma-brand-primary').trim()")
    assert primary.upper() == "#008CBF"

    assert not [u for u in requests if "fonts.googleapis.com" in u or "fonts.gstatic.com" in u]


def test_favicon_and_logo_come_from_the_kit(page, base_url):
    page.goto(base_url + PAGE)
    page.wait_for_load_state("networkidle")
    assert page.locator("link[rel~='icon']").count() >= 1
    assert page.locator("header img, nav img").count() >= 1
