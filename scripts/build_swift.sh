#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd -P)"
OUT_DIR="$ROOT_DIR/src/clipdrop/bin"

declare -a HELPERS=(
  "clipdrop-transcribe-clipboard:swift/TranscribeClipboard"
  "clipdrop-summarize:swift/ClipdropSummarize"
)

mkdir -p "$OUT_DIR"

for entry in "${HELPERS[@]}"; do
  IFS=":" read -r binary rel_dir <<<"$entry"
  swift_dir="$ROOT_DIR/$rel_dir"

  pushd "$swift_dir" >/dev/null

  swift build -c release --arch arm64
  swift build -c release --arch x86_64

  lipo -create \
    .build/arm64-apple-macosx/release/$binary \
    .build/x86_64-apple-macosx/release/$binary \
    -output "$OUT_DIR/$binary"

  chmod +x "$OUT_DIR/$binary"

  popd >/dev/null
done
