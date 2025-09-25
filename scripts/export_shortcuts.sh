#!/usr/bin/env bash
set -euo pipefail

if ! command -v shortcuts >/dev/null 2>&1; then
  echo "shortcuts CLI not found. Install the macOS 26 Command Line Tools." >&2
  exit 1
fi

if ! shortcuts --help | grep -qE "\\bexport\\b"; then
  cat >&2 <<'MSG'
This build of the Shortcuts CLI does not expose the `shortcuts export` subcommand.
Update to macOS 26 with the latest Shortcuts app, then rerun.
In the meantime, open Shortcuts ▸ right-click each ClipDrop shortcut ▸ Share ▸ Export File…
MSG
  exit 2
fi

DEST_DIR=${1:-shortcuts}
VERSION=${VERSION:-v1}
mkdir -p "$DEST_DIR"

SHORTCUTS=(
  "ClipDrop Summarize Clipboard::clipdrop-summarize-clipboard"
  "ClipDrop Actions Decisions::clipdrop-actions-decisions"
  "ClipDrop Delta Summarizer::clipdrop-delta-summarizer"
  "ClipDrop Daily Digest::clipdrop-daily-digest"
)

rc=0
for entry in "${SHORTCUTS[@]}"; do
  name="${entry%%::*}"
  slug="${entry##*::}"
  outfile="${DEST_DIR}/${slug}-${VERSION}.shortcut"
  echo "Exporting '$name' → $outfile"
  if ! shortcuts export "$name" --output "$outfile" 2>export.err; then
    rc=$?
    if grep -q "Couldn’t communicate with a helper application" export.err; then
      echo "Grant Terminal automation access: open Shortcuts once, rerun, and approve the prompt." >&2
    else
      cat export.err >&2
    fi
    rm -f export.err
    continue
  fi
  rm -f export.err
  if [[ ! -s "$outfile" ]]; then
    echo "Warning: $outfile is empty. Check that the shortcut exists and export succeeded." >&2
  fi
done

exit $rc
