"""Browser checks for the kit's site branding (_nma/site.css via `nma-kit sync-assets`)."""

import pytest

pytest.importorskip("playwright")

PAGE = "/tutorials/w2d1-examples/w2d1-tutorial1/"
GOOGLE_FONTS = ("fonts.googleapis.com", "fonts.gstatic.com")


def load(page, base_url):
    """Open the page; return the font requests it made as (url, referer, resource type)."""
    fonts = []

    def record(request):
        if any(host in request.url for host in GOOGLE_FONTS):
            fonts.append((request.url, request.headers.get("referer", "?"), request.resource_type))

    page.on("request", record)
    page.goto(base_url + PAGE)
    page.wait_for_load_state("networkidle")
    return fonts


def test_brand_font_and_colours_apply(page, base_url):
    fonts = load(page, base_url)

    # Rubik comes from the embedded data URI, so it must be loaded and in use.
    assert page.evaluate("document.fonts.ready.then(() => document.fonts.check('1em Rubik'))")
    assert "Rubik" in page.evaluate("getComputedStyle(document.body).fontFamily")

    primary = page.evaluate(
        "getComputedStyle(document.documentElement).getPropertyValue('--nma-brand-primary').trim()")
    assert primary.upper() == "#008CBF"

    # What the kit controls: Rubik is never fetched from Google.
    assert not [f for f in fonts if "rubik" in f[0].lower()], fonts


def test_no_google_font_requests(page, base_url):
    """The kit's stylesheet makes no font requests. Anything reported here comes
    from something else on the page (the theme, thebe, ...): the Referer is the
    stylesheet that asked for it."""
    fonts = load(page, base_url)
    assert not fonts, "\n".join(f"{kind}: {url}\n    asked by {referer}" for url, referer, kind in sorted(set(fonts)))


def test_favicon_and_logo_come_from_the_kit(page, base_url):
    page.goto(base_url + PAGE)
    page.wait_for_load_state("networkidle")
    assert page.locator("link[rel~='icon']").count() >= 1
    assert page.locator("header img, nav img").count() >= 1
