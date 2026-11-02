"""
Finish a built site (`_build/html`) before it is deployed: `nma-kit finalize-site`.

`myst build --html` writes `robots.txt`, `sitemap.xml` and `sitemap_style.xsl`
from its local theme server, so every URL in them is `http://localhost:3000`.
Nothing can use them. This replaces them:

  - the sitemap files are deleted;
  - `robots.txt` allows crawlers on the student site and disallows all of them
    on the instructor site, which also gets `X-Robots-Tag: noindex, nofollow`
    (a Cloudflare Pages `_headers` file) as a backup.
"""

from pathlib import Path

ROBOTS = {
    "student": "User-agent: *\nAllow: /\n",
    "instructor": "User-agent: *\nDisallow: /\n",
}
SITEMAP_FILES = ("sitemap.xml", "sitemap_style.xsl")
NOINDEX_HEADERS = "/*\n  X-Robots-Tag: noindex, nofollow\n"


def finalize_site(html_dir: Path, audience: str) -> list[str]:
    """Fix up the built site in `html_dir` for `audience` (`student` or `instructor`).

    Returns the names it deleted or wrote, in that order. Safe to run twice."""
    html_dir = Path(html_dir)
    changed = []
    for name in SITEMAP_FILES:
        path = html_dir / name
        if path.exists():
            path.unlink()
            changed.append(name)
    (html_dir / "robots.txt").write_text(ROBOTS[audience], encoding="utf-8")
    changed.append("robots.txt")
    if audience == "instructor":
        headers = html_dir / "_headers"
        existing = headers.read_text(encoding="utf-8") if headers.exists() else ""
        if NOINDEX_HEADERS not in existing:
            if existing:  # keep the course's own rules, a blank line apart
                existing = existing.rstrip("\n") + "\n\n"
            headers.write_text(existing + NOINDEX_HEADERS, encoding="utf-8")
            changed.append("_headers")
    return changed
