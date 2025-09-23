#!/bin/bash
# Smoke test script for audio transcription on macOS
# Tests the end-to-end transcription pipeline using jfk.mp3

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

# Function to check prerequisites
check_prerequisites() {
    print_status "info" "Checking prerequisites..."

    # Check if on macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_status "error" "This test requires macOS"
        exit 1
    fi

    # Check macOS version
    macos_version=$(sw_vers -productVersion | cut -d. -f1)
    if [ "$macos_version" -lt 26 ]; then
        print_status "error" "macOS 26.0+ required (current: $(sw_vers -productVersion))"
        exit 1
    fi
    print_status "success" "macOS version: $(sw_vers -productVersion)"

    # Check if Swift helper exists
    HELPER_PATH="src/clipdrop/bin/clipdrop-transcribe-clipboard"
    if [ ! -f "$HELPER_PATH" ]; then
        print_status "error" "Swift helper not found at $HELPER_PATH"
        print_status "info" "Build it with: cd swift/TranscribeClipboard && swift build"
        exit 1
    fi
    print_status "success" "Swift helper found"

    # Check if test audio exists
    if [ ! -f "$TEST_AUDIO" ]; then
        print_status "error" "Test audio file not found: $TEST_AUDIO"
        exit 1
    fi
    print_status "success" "Test audio found: $TEST_AUDIO"

    # Check if clipdrop is installed
    if ! command -v clipdrop &> /dev/null; then
        print_status "error" "clipdrop not installed"
        print_status "info" "Install with: pip install -e ."
        exit 1
    fi
    print_status "success" "clipdrop command available"
}

# Function to copy audio to clipboard
copy_to_clipboard() {
    print_status "info" "Copying $TEST_AUDIO to clipboard..."

    # Use AppleScript to copy file to clipboard (simulates Finder copy)
    osascript -e "set the clipboard to (POSIX file \"$(pwd)/$TEST_AUDIO\")" 2>/dev/null

    if [ $? -eq 0 ]; then
        print_status "success" "Audio copied to clipboard"
    else
        print_status "error" "Failed to copy audio to clipboard"
        exit 1
    fi
}

# Function to test transcription
test_transcription() {
    local format=$1
    local output_file="$OUTPUT_DIR/transcript_test.$format"

    print_status "info" "Testing transcription to .$format..."

    # Remove old output if exists
    rm -f "$output_file"

    # Run transcription
    if clipdrop "$output_file" --transcribe 2>/dev/null; then
        # Check if file was created
        if [ -f "$output_file" ]; then
            # Check if file is non-empty
            file_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
            if [ "$file_size" -gt 0 ]; then
                # Format file size for display
                if [ "$file_size" -gt 1024 ]; then
                    size_display="$((file_size / 1024)) KB"
                else
                    size_display="$file_size bytes"
                fi
                print_status "success" "Transcribed to $format: $output_file ($size_display)"

                # Show first few lines of output
                echo "  First few lines:"
                head -n 3 "$output_file" | sed 's/^/    /'
                return 0
            else
                print_status "error" "Output file is empty: $output_file"
                return 1
            fi
        else
            print_status "error" "Output file not created: $output_file"
            return 1
        fi
    else
        print_status "error" "Transcription command failed"
        return 1
    fi
}

# Function to clean up
cleanup() {
    if [ "$1" != "--keep" ]; then
        print_status "info" "Cleaning up test outputs..."
        rm -rf "$OUTPUT_DIR"
        print_status "success" "Cleanup complete"
    else
        print_status "info" "Test outputs kept in $OUTPUT_DIR/"
    fi
}

# Main test execution
main() {
    echo "========================================="
    echo "ClipDrop Audio Transcription Smoke Test"
    echo "========================================="
    echo

    # Check for help flag
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        echo "Usage: $0 [--keep]"
        echo
        echo "Options:"
        echo "  --keep    Keep test output files after completion"
        echo "  --help    Show this help message"
        echo
        echo "This script tests audio transcription using $TEST_AUDIO"
        exit 0
    fi

    # Run checks
    check_prerequisites

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    # Copy audio to clipboard
    copy_to_clipboard

    # Test different formats
    echo
    print_status "info" "Running transcription tests..."
    echo

    failed=0

    # Test SRT format
    if ! test_transcription "srt"; then
        failed=$((failed + 1))
    fi
    echo

    # Test TXT format
    if ! test_transcription "txt"; then
        failed=$((failed + 1))
    fi
    echo

    # Test MD format
    if ! test_transcription "md"; then
        failed=$((failed + 1))
    fi
    echo

    # Summary
    echo "========================================="
    if [ $failed -eq 0 ]; then
        print_status "success" "All smoke tests passed!"
        cleanup "$1"
        exit 0
    else
        print_status "error" "$failed test(s) failed"
        print_status "info" "Check $OUTPUT_DIR for details"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"