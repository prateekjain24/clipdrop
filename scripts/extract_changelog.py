#!/usr/bin/env python3
"""Print the CHANGELOG.md section body for a given version.

Used by the release workflow to turn the tag's changelog entry into the
GitHub Release body.

Usage:
    python scripts/extract_changelog.py 2.4.0 > release-notes.md

Exits 2 if the version heading is absent, so a release with no changelog
entry fails loudly instead of shipping empty notes.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def extract(version: str) -> str:
    lines = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()

    heading = f"## [{version}]"
    body: list[str] = []
    in_section = False

    for line in lines:
        if line.startswith(heading):
            in_section = True
            continue
        if in_section:
            # Stop at the next version heading or the link-reference block
            if line.startswith("## ") or (line.startswith("[") and "]: http" in line):
                break
            body.append(line)

    if not in_section:
        print(
            f"CHANGELOG.md has no '{heading}' heading — add the entry before releasing.",
            file=sys.stderr,
        )
        sys.exit(2)

    return "\n".join(body).strip() + "\n"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip())
    sys.stdout.write(extract(sys.argv[1]))


if __name__ == "__main__":
    main()
