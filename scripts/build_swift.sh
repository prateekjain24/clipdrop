#!/usr/bin/env bash
set -euo pipefail

SWIFT_DIR="swift/TranscribeClipboard"
OUT="src/clipdrop/bin"
BINARY="clipdrop-transcribe-clipboard"

mkdir -p "$OUT"
pushd "$SWIFT_DIR" >/dev/null

swift build -c release --arch arm64
swift build -c release --arch x86_64

lipo -create \
  .build/arm64-apple-macosx/release/$BINARY \
  .build/x86_64-apple-macosx/release/$BINARY \
  -output "../../$OUT/$BINARY"

chmod +x "../../$OUT/$BINARY"
popd >/dev/null
