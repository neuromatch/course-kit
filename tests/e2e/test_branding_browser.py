"""Browser checks for the kit's site branding (_nma/site.css via `nma-kit sync-assets`).

They use the `runtime: colab` tutorial: it has no kernel to boot, so a page load
takes about a second (pages with editable cells take over a minute in CI).
"""

import pytest

pytest.importorskip("playwright")

# Deterministic checks: a failure is not cold-cache flakiness, so don't rerun it.
pytestmark = pytest.mark.flaky(reruns=0)

PAGE = "/tutorials/w2d1-examples/w2d1-tutorial3/"
GOOGLE_FONTS = ("fonts.googleapis.com", "fonts.gstatic.com")


def in_main_frame(request):
    """Third-party iframes (the YouTube players) bring their own fonts: not the site's."""
    try:
        return request.frame.parent_frame is None
    except Exception:  # service worker and worker requests have no frame
        return True


def load(page, base_url):
    """Open the page; return the font requests the site itself made as (url, referer, type)."""
    fonts = []

    def record(request):
        if any(host in request.url for host in GOOGLE_FONTS) and in_main_frame(request):
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

    assert not [f for f in fonts if "rubik" in f[0].lower()], fonts


def test_site_makes_no_google_font_requests(page, base_url):
    """Neither the kit's stylesheet nor the theme asks Google for fonts. (Embedded
    YouTube players do, from inside their iframes; those are not counted.) The
    Referer shows which stylesheet asked, if this ever fails."""
    fonts = load(page, base_url)
    assert not fonts, "\n".join(f"{kind}: {url}\n    asked by {referer}" for url, referer, kind in sorted(set(fonts)))


def test_favicon_and_logo_come_from_the_kit(page, base_url):
    page.goto(base_url + PAGE)
    page.wait_for_load_state("networkidle")
    assert page.locator("link[rel~='icon']").count() >= 1
    assert page.locator("header img, nav img").count() >= 1
