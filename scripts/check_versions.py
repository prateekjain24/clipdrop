#!/usr/bin/env python3
"""Check that all version declarations agree.

Compares:
- pyproject.toml  [project] version
- src/clipdrop/__init__.py  __version__
- CHANGELOG.md  first released heading (## [X.Y.Z] - YYYY-MM-DD)

Usage:
    python scripts/check_versions.py [EXPECTED_VERSION]

EXPECTED_VERSION (optional) is typically the release tag with the leading
"v" stripped; when given, all three sources must also match it.

Exits 0 when everything agrees, 1 with a summary table otherwise.
"""

import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CHANGELOG_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}", re.M)
INIT_VERSION = re.compile(r'^__version__ = "([^"]+)"', re.M)


def read_pyproject_version() -> str:
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def read_init_version() -> str:
    text = (REPO_ROOT / "src" / "clipdrop" / "__init__.py").read_text(encoding="utf-8")
    match = INIT_VERSION.search(text)
    if not match:
        sys.exit("No __version__ assignment found in src/clipdrop/__init__.py")
    return match.group(1)


def read_changelog_version() -> str:
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = CHANGELOG_HEADING.search(text)
    if not match:
        sys.exit("No '## [X.Y.Z] - YYYY-MM-DD' heading found in CHANGELOG.md")
    return match.group(1)


def main() -> int:
    expected = sys.argv[1] if len(sys.argv) > 1 else None

    versions = {
        "pyproject.toml": read_pyproject_version(),
        "src/clipdrop/__init__.py": read_init_version(),
        "CHANGELOG.md (top entry)": read_changelog_version(),
    }
    if expected:
        versions["expected (tag)"] = expected

    if len(set(versions.values())) == 1:
        print(f"Version check OK: {next(iter(versions.values()))}")
        return 0

    print("Version mismatch:", file=sys.stderr)
    for source, version in versions.items():
        print(f"  {source:<28} {version}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
