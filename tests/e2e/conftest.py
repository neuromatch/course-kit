"""Browser smoke tests for editable cells.

Run against a built site:  NMA_E2E_URL=http://localhost:8765 pytest -q tests/e2e
(from course-kit/; NMA_E2E_COURSE=<course root> when testing another course)
Skipped unless NMA_E2E_URL is set.

NMA_E2E_REQUIREJS (optional): path to a local require.js. thebe's widget manager
loads require.js from cdnjs; in sandboxes where cdnjs is blocked, set this to
serve it locally. Service workers are then blocked, because Playwright can't
intercept requests that go through JupyterLite's service worker.
"""

import os

import pytest

pytest.importorskip("playwright")

BASE_URL = os.environ.get("NMA_E2E_URL", "").rstrip("/")
REQUIREJS = os.environ.get("NMA_E2E_REQUIREJS")


def pytest_collection_modifyitems(config, items):
    if BASE_URL:
        return
    skip = pytest.mark.skip(reason="set NMA_E2E_URL to run browser tests")
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def _browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(_browser):
    options = {"ignore_https_errors": True}
    if REQUIREJS:
        options["service_workers"] = "block"
    context = _browser.new_context(**options)
    if REQUIREJS:
        context.route(
            "**/require.min.js",
            lambda route: route.fulfill(path=REQUIREJS, content_type="application/javascript"),
        )
    page = context.new_page()
    page.set_default_timeout(120_000)
    yield page
    context.close()


@pytest.fixture
def base_url():
    return BASE_URL
