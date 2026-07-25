"""Guard against version drift between pyproject.toml, the package, and the CHANGELOG."""

import re
import tomllib
from pathlib import Path

from clipdrop import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def _changelog_top_version() -> str:
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}", text, re.M)
    assert match, "CHANGELOG.md has no '## [X.Y.Z] - YYYY-MM-DD' heading"
    return match.group(1)


def test_package_version_matches_pyproject():
    assert __version__ == _pyproject_version()


def test_changelog_top_entry_matches_pyproject():
    assert _changelog_top_version() == _pyproject_version()


def test_changelog_has_unreleased_section():
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in text, (
        "CHANGELOG.md needs an '## [Unreleased]' section — scripts/release.py "
        "rolls it into the next release heading"
    )
