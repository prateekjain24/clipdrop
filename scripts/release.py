#!/usr/bin/env python3
"""One-command release preparation.

Usage:
    python scripts/release.py 2.4.0 [--dry-run]

What it does:
1. Validates the version (SemVer, greater than current, tag vX.Y.Z absent)
2. Bumps pyproject.toml and src/clipdrop/__init__.py
3. Rolls CHANGELOG.md: [Unreleased] -> [X.Y.Z] - <today>, re-seeds an empty
   [Unreleased] section, and maintains the compare links at the bottom
4. Self-verifies with the same checks CI runs

It edits files only — the git steps are printed for you to run after
reviewing the diff, because the release tag belongs on the merge commit
on main, which doesn't exist yet when this script runs.
"""

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/prateekjain24/clipdrop"

SEMVER = re.compile(r"\d+\.\d+\.\d+")
UNRELEASED_HEADING = "## [Unreleased]"


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def current_version() -> str:
    import tomllib

    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def validate(version: str, previous: str) -> None:
    if not SEMVER.fullmatch(version):
        fail(f"'{version}' is not X.Y.Z semantic versioning")

    def parts(v: str) -> tuple:
        return tuple(int(p) for p in v.split("."))

    if parts(version) <= parts(previous):
        fail(f"{version} must be greater than the current version {previous}")

    tags = subprocess.run(
        ["git", "tag", "-l", f"v{version}"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.strip()
    if tags:
        fail(f"tag v{version} already exists")

    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.strip()
    if dirty:
        print("warning: working tree is not clean — the release diff will "
              "mix with your uncommitted changes", file=sys.stderr)


def bump_pyproject(version: str, previous: str, dry_run: bool) -> None:
    path = REPO_ROOT / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(
        rf'^version = "{re.escape(previous)}"$',
        f'version = "{version}"',
        text, count=1, flags=re.M,
    )
    if count != 1:
        fail(f'could not find version = "{previous}" in pyproject.toml')
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")


def bump_init(version: str, previous: str, dry_run: bool) -> None:
    path = REPO_ROOT / "src" / "clipdrop" / "__init__.py"
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(
        rf'^__version__ = "{re.escape(previous)}"$',
        f'__version__ = "{version}"',
        text, count=1, flags=re.M,
    )
    if count != 1:
        fail(f'could not find __version__ = "{previous}" in src/clipdrop/__init__.py')
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")


def roll_changelog(version: str, previous: str, dry_run: bool) -> None:
    path = REPO_ROOT / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")

    if UNRELEASED_HEADING not in text:
        fail("CHANGELOG.md has no '## [Unreleased]' section")

    # The Unreleased section must actually describe something
    unreleased_body = text.split(UNRELEASED_HEADING, 1)[1]
    unreleased_body = unreleased_body.split("\n## ", 1)[0]
    if not any(line.strip().startswith(("-", "###")) for line in unreleased_body.splitlines()):
        fail("the [Unreleased] section is empty — describe the release in "
             "CHANGELOG.md before running this script")

    today = date.today().isoformat()
    text = text.replace(
        UNRELEASED_HEADING,
        f"{UNRELEASED_HEADING}\n\n## [{version}] - {today}",
        1,
    )

    # Maintain the link references at the bottom
    unreleased_ref = re.compile(r"^\[Unreleased\]: \S+$", re.M)
    new_refs = (
        f"[Unreleased]: {REPO_URL}/compare/v{version}...HEAD\n"
        f"[{version}]: {REPO_URL}/compare/v{previous}...v{version}"
    )
    if unreleased_ref.search(text):
        text = unreleased_ref.sub(new_refs, text, count=1)
    else:
        text = text.rstrip("\n") + "\n\n" + new_refs + "\n"

    if not dry_run:
        path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a clipdrop release")
    parser.add_argument("version", help="new version, e.g. 2.4.0")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and report without editing files")
    args = parser.parse_args()

    version = args.version
    previous = current_version()

    validate(version, previous)
    bump_pyproject(version, previous, args.dry_run)
    bump_init(version, previous, args.dry_run)
    roll_changelog(version, previous, args.dry_run)

    if args.dry_run:
        print(f"Dry run OK: {previous} -> {version} (no files changed)")
        return

    # Self-verify with the same checks CI runs
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_versions.py"), version],
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        fail("self-verification failed — inspect the diff before committing")

    print(f"""
Release {version} prepared. Review the diff, then:

    git add -A
    git commit -m "chore(release): {version}"
    git push origin HEAD          # open a PR, let CI pass, merge it

After the PR merges, tag the merge commit on main:

    git switch main && git pull
    git tag -a v{version} -m "clipdrop {version}"
    git push origin v{version}

The Release workflow takes it from there (verify -> build -> GitHub
Release with this CHANGELOG section -> PyPI).""")


if __name__ == "__main__":
    main()
