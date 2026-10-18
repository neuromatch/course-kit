"""`nma-kit`: the course kit's command line. Run it from the course root.

  nma-kit check                  validate content and myst.yml
  nma-kit notebooks [--dry-run]  generate student/instructor notebooks and solution files
  nma-kit render-scrolly         pre-render scrolly page outputs into _build/scrolly/
  nma-kit prepare-site           add badges + fallback cells to the .md pages and pin the
                                 kit URL in myst.yml (CI only, never commit the result)
  nma-kit publish-notebooks      push notebooks/ to the notebooks branch

Exit codes: 0 ok, 1 content problems, 2 usage or configuration errors.
"""

import argparse
import os
import sys
from pathlib import Path

from nma_kit import __version__
from nma_kit import convert, scrolly
from nma_kit.config import MYST_CONFIG, MissingConfig, read_settings
from nma_kit.pin import pin_kit_url
from nma_kit.publish import PublishError, publish_notebooks


class UsageError(Exception):
    pass


def _validate(check_injected: bool) -> bool:
    errors = convert.validate_content(check_injected=check_injected)
    if errors:
        print("Content rule violations:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
    return not errors


def _settings():
    settings = read_settings()
    try:
        convert.require_github_repo(settings)
    except ValueError as exc:
        raise UsageError(str(exc)) from exc
    return settings


def cmd_check(args) -> int:
    read_settings()
    if not _validate(check_injected=True):
        return 1
    print("No content problems found.")
    return 0


def cmd_notebooks(args) -> int:
    settings = _settings()
    if not _validate(check_injected=True):
        return 1
    count = convert.process_tutorials(settings, args.dry_run, prepare_site=False)
    print(f"Done. Processed {count} file(s).")
    return 0


def cmd_render_scrolly(args) -> int:
    return scrolly.render_all(read_settings().tutorials_dir)


def cmd_prepare_site(args) -> int:
    settings = _settings()
    if not _validate(check_injected=False):
        return 1
    count = convert.process_tutorials(settings, args.dry_run, prepare_site=True)
    if not args.dry_run:
        text = MYST_CONFIG.read_text(encoding="utf-8")
        pinned = pin_kit_url(text, args.kit_version)
        if pinned != text:
            MYST_CONFIG.write_text(pinned, encoding="utf-8")
            print(f"Pinned course kit URLs in {MYST_CONFIG} to {args.kit_version}")
    print(f"Done. Prepared {count} page(s).")
    return 0


def cmd_publish_notebooks(args) -> int:
    settings = read_settings()
    src = Path("notebooks")
    if not src.is_dir():
        raise UsageError("notebooks/ not found: run `nma-kit notebooks` first")
    message = args.message or "chore: regenerate notebooks" + (
        f" from {os.environ['GITHUB_SHA'][:12]}" if os.environ.get("GITHUB_SHA") else "")
    pushed = publish_notebooks(src, settings.notebooks_branch, args.remote, message)
    print(f"Pushed notebooks to {settings.notebooks_branch}." if pushed else "No notebook changes to push.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nma-kit", description="Neuromatch course kit")
    parser.add_argument("--version", action="version", version=f"nma-kit {__version__}")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="validate content and myst.yml").set_defaults(func=cmd_check)

    p = sub.add_parser("notebooks", help="generate notebooks and solution files")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_notebooks)

    sub.add_parser("render-scrolly", help="pre-render scrolly pages").set_defaults(func=cmd_render_scrolly)

    p = sub.add_parser("prepare-site", help="prepare the .md pages for `myst build` (CI only)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--kit-version", default=__version__,
                   help="version to pin course-kit URLs in myst.yml to (default: this CLI's)")
    p.set_defaults(func=cmd_prepare_site)

    p = sub.add_parser("publish-notebooks", help="push notebooks/ to the notebooks branch")
    p.add_argument("--remote", default="origin")
    p.add_argument("--message", default=None)
    p.set_defaults(func=cmd_publish_notebooks)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_usage(sys.stderr)
        return 2
    try:
        return args.func(args)
    except (MissingConfig, UsageError) as exc:
        print(f"nma-kit: {exc}", file=sys.stderr)
        return 2
    except PublishError as exc:
        print(f"nma-kit: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
