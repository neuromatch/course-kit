import re

import pytest

from nma_kit import branding
from nma_kit.cli import main
from nma_kit.config import load_settings

MYST = "version: 1\nproject:\n  github: https://github.com/org/repo\n"


def settings(nma_block: str = ""):
    return load_settings(MYST + nma_block)


def test_packaged_assets_exist():
    for name in ("site.css", "logo.svg", "logo-dark.svg", "favicon.png", "fonts/OFL.txt"):
        assert (branding.ASSETS / name).is_file(), name
    for _, _, name in branding.FONTS:
        assert (branding.ASSETS / "fonts" / name).is_file(), name


def test_favicon_is_small():
    assert (branding.ASSETS / "favicon.png").stat().st_size < 50_000


def test_css_embeds_fonts_and_makes_no_external_requests():
    css = branding.build_css(settings())
    assert css.count("@font-face") == len(branding.FONTS)
    assert css.count("data:font/woff2;base64,") == len(branding.FONTS)
    assert branding.FONT_PLACEHOLDER not in css
    assert "googleapis" not in css
    assert not re.search(r"@import|url\(\s*['\"]?https?:", css)


def test_css_keeps_the_toolbar_rule_courses_used_to_carry():
    assert ".myst-jp-nb-toolbar { display: none !important; }" in branding.build_css(settings())


def test_no_brand_block_means_no_overrides():
    assert branding.brand_overrides({}) == ""
    assert "Course colours" not in branding.build_css(settings())


def test_brand_overrides_follow_the_primary_colour():
    css = branding.brand_overrides({"brand": {"primary": "#ff0000"}})
    assert "--nma-brand-primary: #FF0000;" in css
    assert "--nma-brand-primary-hover: #BF0000;" in css   # 25% darker
    assert "--nma-brand-primary-light: #FF5959;" in css   # 35% lighter


def test_explicit_hover_and_light_win_over_derived():
    css = branding.brand_overrides({"brand": {"primary": "#112233", "primary_hover": "#000000",
                                              "primary_light": "#FFFFFF", "accent": "#abcdef"}})
    assert "--nma-brand-primary-hover: #000000;" in css
    assert "--nma-brand-primary-light: #FFFFFF;" in css
    assert "--nma-brand-accent: #ABCDEF;" in css


def test_overrides_come_after_the_base_so_they_win():
    css = branding.build_css(settings('nma:\n  brand:\n    primary: "#ff0000"\n'))
    assert css.index("--nma-brand-primary: #008CBF") < css.index("--nma-brand-primary: #FF0000")


def test_secondary_only_does_not_touch_primary():
    css = branding.brand_overrides({"brand": {"secondary": "#123456"}})
    assert "--nma-brand-secondary: #123456;" in css and "primary" not in css


@pytest.mark.parametrize("brand, message", [
    ({"primary": "red"}, "must be a colour"),
    ({"primary": "#fff"}, "must be a colour"),
    ({"primry": "#ffffff"}, "not a known colour"),
])
def test_brand_errors(brand, message):
    errors = branding.brand_errors({"brand": brand})
    assert len(errors) == 1 and message in errors[0]


def test_unknown_style_setting_is_an_error():
    assert "nma.style.css" in branding.brand_errors({"style": {"css": "x.css"}})[0]


def test_extra_css_is_appended_last(tmp_path):
    (tmp_path / "extra.css").write_text("h1 { color: hotpink; }\n")
    css = branding.build_css(settings("nma:\n  style:\n    extra: extra.css\n"), tmp_path)
    assert css.rstrip().endswith("h1 { color: hotpink; }")
    assert css.index("toolbar") < css.index("hotpink")


def test_missing_extra_css_is_an_error(tmp_path):
    with pytest.raises(branding.BrandingError, match=r"extra\.css not found"):
        branding.build_css(settings("nma:\n  style:\n    extra: extra.css\n"), tmp_path)


def test_sync_writes_the_files_the_course_references(tmp_path):
    written = branding.sync_assets(settings(), tmp_path)
    names = {p.name for p in written}
    assert names == {"site.css", "logo.svg", "logo-dark.svg", "favicon.png"}
    assert all(p.parent == tmp_path / "_nma" for p in written)
    assert (tmp_path / "_nma" / ".gitignore").read_text().splitlines()[-1] == "*"


def test_sync_is_repeatable(tmp_path):
    first = branding.sync_assets(settings(), tmp_path)[0].read_text()
    assert branding.sync_assets(settings(), tmp_path)[0].read_text() == first


def test_bad_settings_write_nothing(tmp_path):
    with pytest.raises(branding.BrandingError):
        branding.sync_assets(settings('nma:\n  brand:\n    primary: "red"\n'), tmp_path)
    assert not (tmp_path / "_nma").exists()


# --- through the CLI --------------------------------------------------------

def course(tmp_path, nma_block=""):
    (tmp_path / "myst.yml").write_text(MYST + nma_block)
    (tmp_path / "tutorials").mkdir()
    return tmp_path


def test_cli_sync_assets(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(course(tmp_path))
    assert main(["sync-assets"]) == 0
    assert (tmp_path / "_nma" / "site.css").is_file()
    assert "_nma/site.css" in capsys.readouterr().out


def test_cli_sync_assets_reports_bad_settings(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(course(tmp_path, 'nma:\n  brand:\n    primary: "red"\n'))
    assert main(["sync-assets"]) == 2
    assert "nma.brand.primary" in capsys.readouterr().err
    assert not (tmp_path / "_nma").exists()


def test_cli_check_rejects_bad_brand(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(course(tmp_path, 'nma:\n  brand:\n    primary: "red"\n'))
    assert main(["check"]) == 1
    assert "nma.brand.primary" in capsys.readouterr().err


def test_cli_check_accepts_good_brand(tmp_path, monkeypatch):
    monkeypatch.chdir(course(tmp_path, 'nma:\n  brand:\n    primary: "#112233"\n'))
    assert main(["check"]) == 0


def test_prepare_site_syncs_assets_but_dry_run_does_not(tmp_path, monkeypatch):
    monkeypatch.chdir(course(tmp_path))
    assert main(["prepare-site", "--dry-run"]) == 0
    assert not (tmp_path / "_nma").exists()
    assert main(["prepare-site"]) == 0
    assert (tmp_path / "_nma" / "site.css").is_file()
