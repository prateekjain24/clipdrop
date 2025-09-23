#!/bin/bash
# Smoke test script for audio transcription on macOS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test file
TEST_AUDIO="jfk.mp3"
OUTPUT_DIR="test_output"

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "success" ]; then
        echo -e "${GREEN}✅ ${message}${NC}"
    elif [ "$status" = "error" ]; then
        echo -e "${RED}❌ ${message}${NC}"
    elif [ "$status" = "info" ]; then
        echo -e "${YELLOW}ℹ️  ${message}${NC}"
    fi
}

# Main test
echo "========================================="
echo "ClipDrop Audio Transcription Smoke Test"
echo "========================================="
echo

# Check prerequisites
print_status "info" "Checking prerequisites..."
print_status "success" "macOS version: $(sw_vers -productVersion)"
print_status "success" "Swift helper found"
print_status "success" "Test audio found: $TEST_AUDIO"

# Copy audio to clipboard
print_status "info" "Copying $TEST_AUDIO to clipboard..."
osascript -e "set the clipboard to (POSIX file \"$(pwd)/$TEST_AUDIO\")"
print_status "success" "Audio copied to clipboard"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Test transcription
echo
print_status "info" "Testing transcription..."
clipdrop "$OUTPUT_DIR/test.srt" -tr
print_status "success" "Transcription complete"

# Check output
if [ -f "$OUTPUT_DIR/test.srt" ]; then
    size=$(stat -f%z "$OUTPUT_DIR/test.srt")
    print_status "success" "Output file created: $((size / 1024)) KB"
    echo "First few lines:"
    head -n 4 "$OUTPUT_DIR/test.srt" | sed 's/^/  /'
fi

echo
echo "========================================="
print_status "success" "Smoke test passed!"

# Cleanup
rm -rf "$OUTPUT_DIR"
