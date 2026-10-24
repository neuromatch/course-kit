"""Site branding: the kit's stylesheet, logos, favicon and fonts.

`nma-kit sync-assets` (also run by `prepare-site`) writes them to `_nma/` in
the course. The course's myst.yml points MyST at the files:

    site:
      options:
        style: _nma/site.css
        logo: _nma/logo.svg
        logo_dark: _nma/logo-dark.svg
        favicon: _nma/favicon.png

and may adjust them in the `nma:` block:

    nma:
      brand:                       # all optional, "#RRGGBB"
        primary: "#008CBF"         # links, accents, buttons
        primary_hover: "#006B8F"   # default: primary, darkened
        primary_light: "#35B4DC"   # accent on dark backgrounds, default: primary, lightened
        secondary: "#45429C"       # header surface, tips
        accent: "#FA7A7A"          # exercise cells
      style:
        extra: _static/extra.css   # the course's own CSS, appended after the kit's

`_nma/site.css` is the kit stylesheet (Rubik embedded as data URIs, so no
request leaves the site), then the brand overrides, then the course's CSS:
MyST accepts a single `style` file. The folder gets its own .gitignore, so
courses never commit it.
"""

import base64
import re
import shutil
from pathlib import Path

from nma_kit.config import Settings

ASSETS = Path(__file__).parent / "assets"
OUT_DIR = Path("_nma")

BRAND_KEYS = ("primary", "primary_hover", "primary_light", "secondary", "accent")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# (weight, style, file) of the embedded Rubik faces
FONTS = (
    ("400", "normal", "Rubik-400-normal.woff2"),
    ("400", "italic", "Rubik-400-italic.woff2"),
    ("500", "normal", "Rubik-500-normal.woff2"),
    ("700", "normal", "Rubik-700-normal.woff2"),
)
FONT_PLACEHOLDER = "/*FONTS*/"

# kit asset -> file in _nma/ (the names courses use in myst.yml)
COPIED = {"logo.svg": "logo.svg", "logo-dark.svg": "logo-dark.svg", "favicon.png": "favicon.png"}


class BrandingError(Exception):
    """A problem with the `nma.brand` / `nma.style` settings."""


def _section(nma: dict, name: str) -> dict:
    section = nma.get(name)
    return section if isinstance(section, dict) else {}


def brand_errors(nma: dict) -> list[str]:
    """Problems with `nma.brand` and `nma.style.extra` (the extra file's existence
    is checked at sync time, relative to the course root)."""
    errors = []
    brand = _section(nma, "brand")
    for key, value in brand.items():
        if key not in BRAND_KEYS:
            errors.append(f"myst.yml: nma.brand.{key} is not a known colour "
                          f"(one of {', '.join(BRAND_KEYS)})")
        elif not isinstance(value, str) or not HEX_RE.match(value):
            errors.append(f"myst.yml: nma.brand.{key} must be a colour like \"#008CBF\", got {value!r}")
    for key in _section(nma, "style"):
        if key != "extra":
            errors.append(f"myst.yml: nma.style.{key} is not a known setting (only `extra`)")
    return errors


def _mix(color: str, other: tuple[int, int, int], share: float) -> str:
    """`color` with `share` (0..1) of `other` mixed in, as #RRGGBB."""
    rgb = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(c * (1 - share) + o * share) for c, o in zip(rgb, other, strict=True)]
    return "#" + "".join(f"{v:02X}" for v in mixed)


def brand_overrides(nma: dict) -> str:
    """A `:root { ... }` block for the colours the course set, or ''.

    Setting only `primary` also derives `primary_hover` (25% darker) and
    `primary_light` (35% lighter), because those two follow the primary
    colour unless the course says otherwise.
    """
    brand = {k: v.upper() for k, v in _section(nma, "brand").items() if k in BRAND_KEYS}
    if "primary" in brand:
        brand.setdefault("primary_hover", _mix(brand["primary"], (0, 0, 0), 0.25))
        brand.setdefault("primary_light", _mix(brand["primary"], (255, 255, 255), 0.35))
    if not brand:
        return ""
    lines = [f"  --nma-brand-{key.replace('_', '-')}: {brand[key]};" for key in BRAND_KEYS if key in brand]
    return "/* Course colours (nma.brand in myst.yml) */\n:root {\n" + "\n".join(lines) + "\n}\n"


def font_face_css() -> str:
    """`@font-face` rules for the bundled Rubik font, with the files embedded as base64 data URIs (so the stylesheet makes no font requests)."""
    rules = []
    for weight, style, name in FONTS:
        data = base64.b64encode((ASSETS / "fonts" / name).read_bytes()).decode("ascii")
        rules.append(
            "@font-face {\n"
            "  font-family: 'Rubik';\n"
            f"  font-style: {style};\n"
            f"  font-weight: {weight};\n"
            "  font-display: swap;\n"
            f"  src: url(data:font/woff2;base64,{data}) format('woff2');\n"
            "}"
        )
    return "\n".join(rules)


def extra_css_path(settings: Settings) -> Path | None:
    """The course's `nma.style.extra` CSS file (relative to the course root), or None if unset."""
    extra = _section(settings.nma, "style").get("extra")
    return Path(extra) if isinstance(extra, str) and extra.strip() else None


def build_css(settings: Settings, root: Path = Path(".")) -> str:
    """The complete site stylesheet for a course."""
    base = (ASSETS / "site.css").read_text(encoding="utf-8")
    if FONT_PLACEHOLDER not in base:
        raise BrandingError("kit stylesheet has no font placeholder (broken install?)")
    parts = [base.replace(FONT_PLACEHOLDER, font_face_css())]
    overrides = brand_overrides(settings.nma)
    if overrides:
        parts.append(overrides)
    extra = extra_css_path(settings)
    if extra is not None:
        path = root / extra
        if not path.is_file():
            raise BrandingError(f"nma.style.extra: {extra.as_posix()} not found (relative to the course root)")
        parts.append(f"/* Course CSS ({extra.as_posix()}) */\n" + path.read_text(encoding="utf-8"))
    return "\n".join(part.rstrip("\n") + "\n" for part in parts)


def sync_assets(settings: Settings, root: Path = Path(".")) -> list[Path]:
    """Write the branding files to `<root>/_nma/`. Returns the files written."""
    errors = brand_errors(settings.nma)
    if errors:
        raise BrandingError("; ".join(errors))
    css = build_css(settings, root)  # before touching the disk, so a bad setting leaves it alone
    out = root / OUT_DIR
    out.mkdir(exist_ok=True)
    (out / ".gitignore").write_text("# written by `nma-kit sync-assets`\n*\n", encoding="utf-8")
    written = []
    (out / "site.css").write_text(css, encoding="utf-8")
    written.append(out / "site.css")
    for source, name in COPIED.items():
        shutil.copyfile(ASSETS / source, out / name)
        written.append(out / name)
    return written
