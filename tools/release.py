#!/usr/bin/env python

"""Automate MNELAB release process.

Run from the repository root:

  # turn the current dev checkout into a release checkout (and update the lock)
  uv run tools/release.py prepare 1.6.0

  # after the release: bump to the next dev version and reopen the CHANGELOG
  uv run tools/release.py bump 1.7.0

`prepare` and `bump` run `uv lock` at the end. Both leave the resulting changes
uncommitted so they can be reviewed before commit.
"""

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
# files that reference the released version in the installer download URLs
URL_FILES = [ROOT / "README.md", ROOT / "docs" / "quickstart" / "index.md"]

VERSION_RE = re.compile(r"^version = \"[^\"]*\"$", re.MULTILINE)


def set_version(version):
    """Set the `version` field in pyproject.toml."""
    text = PYPROJECT.read_text(encoding="utf-8")
    text, n = VERSION_RE.subn(f'version = "{version}"', text, count=1)
    if n != 1:
        sys.exit("Could not find a unique version field in pyproject.toml.")
    PYPROJECT.write_text(text, encoding="utf-8")


def update_urls(version):
    """Point the installer download links to `version`."""
    for path in URL_FILES:
        text = path.read_text(encoding="utf-8")
        # e.g. releases/download/v1.6.0/MNELAB-1.6.0.dmg
        text = re.sub(
            r"releases/download/v\d+\.\d+\.\d+/MNELAB-\d+\.\d+\.\d+\.(dmg|exe)",
            rf"releases/download/v{version}/MNELAB-{version}.\1",
            text,
        )
        # e.g. link text "MNELAB 1.6.0 (macOS)"
        text = re.sub(
            r"MNELAB \d+\.\d+\.\d+ \((macOS|Windows)\)",
            rf"MNELAB {version} (\1)",
            text,
        )
        path.write_text(text, encoding="utf-8")


def uv_lock():
    """Update uv.lock to reflect the new version."""
    subprocess.run(["uv", "lock"], cwd=ROOT, check=True)


def prepare(version):
    """Turn the current dev checkout into a release checkout for `version`."""
    set_version(version)
    update_urls(version)
    text = CHANGELOG.read_text(encoding="utf-8")
    text, n = re.subn(
        r"^## \[UNRELEASED\].*$",
        f"## [{version}] · {date.today().isoformat()}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        sys.exit("Could not find an [UNRELEASED] heading in CHANGELOG.md.")
    CHANGELOG.write_text(text, encoding="utf-8")
    uv_lock()


def bump(next_version):
    """Set the version to `next_version.dev0` and open a fresh CHANGELOG section."""
    set_version(f"{next_version}.dev0")
    text = CHANGELOG.read_text(encoding="utf-8")
    if not text.startswith("## ["):
        sys.exit("CHANGELOG.md does not start with a version heading.")
    CHANGELOG.write_text("## [UNRELEASED] · YYYY-MM-DD\n\n" + text, encoding="utf-8")
    uv_lock()


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare", help="prepare the release version")
    p.add_argument("version")

    p = sub.add_parser("bump", help="bump to the next development version")
    p.add_argument("version")

    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.version)
    elif args.command == "bump":
        bump(args.version)


if __name__ == "__main__":
    main()
