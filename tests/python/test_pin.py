from nma_kit.pin import pin_kit_url

KIT = "https://cdn.jsdelivr.net/npm/@neuromatch/course-kit"


def test_scalar_extend():
    text = f"version: 1\nextend: {KIT}@0.1/dist/nma.yml\nproject:\n  title: T\n"
    assert pin_kit_url(text, "0.1.3") == f"version: 1\nextend: {KIT}@0.1.3/dist/nma.yml\nproject:\n  title: T\n"


def test_list_extend_leaves_other_urls_alone():
    other = "https://example.org/shared@1/config.yml"
    text = f"extend:\n  - {other}\n  - {KIT}@latest/dist/nma.yml\n"
    assert pin_kit_url(text, "0.2.0") == f"extend:\n  - {other}\n  - {KIT}@0.2.0/dist/nma.yml\n"


def test_quoted_extend():
    text = f"extend: '{KIT}@0/dist/nma.yml'\n"
    assert pin_kit_url(text, "0.1.3") == f"extend: '{KIT}@0.1.3/dist/nma.yml'\n"


def test_plugin_url_is_pinned_too():
    text = f"project:\n  plugins:\n    - \"{KIT}@0.1/dist/nma.mjs\"\n"
    assert pin_kit_url(text, "0.1.3") == f"project:\n  plugins:\n    - \"{KIT}@0.1.3/dist/nma.mjs\"\n"


def test_no_kit_url_is_unchanged():
    text = "version: 1\nproject:\n  plugins:\n    - course-kit/js/dist/nma.mjs\n"
    assert pin_kit_url(text, "0.1.3") == text
