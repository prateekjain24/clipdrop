from __future__ import annotations

import json
import platform
import subprocess
from importlib.resources import files
from typing import Any, Callable, Generator, Optional


# Custom exception classes for better error handling
class TranscriptionNotAvailableError(Exception):
    """Base exception for transcription availability issues."""
    pass


class UnsupportedPlatformError(TranscriptionNotAvailableError):
    """Raised when running on non-macOS platform."""
    pass


class UnsupportedMacOSVersionError(TranscriptionNotAvailableError):
    """Raised when macOS version is too old."""
    pass


class HelperNotFoundError(TranscriptionNotAvailableError):
    """Raised when helper binary is missing."""
    pass


def get_macos_version() -> Optional[tuple[int, int]]:
    """Get macOS version as (major, minor) tuple, or None if not macOS."""
    if platform.system() != "Darwin":
        return None
    try:
        version = platform.mac_ver()[0]
        parts = version.split('.')
        if len(parts) >= 2:
            return (int(parts[0]), int(parts[1]))
    except:
        pass
    return None


def helper_path() -> str:
    """
    Return the filesystem path to the Swift transcription helper.

    Raises:
        UnsupportedPlatformError: If not on macOS
        UnsupportedMacOSVersionError: If macOS version < 26.0
        HelperNotFoundError: If helper binary is missing
    """
    # Check platform
    if platform.system() != "Darwin":
        raise UnsupportedPlatformError(
            "On-device transcription is only available on macOS. "
            f"Current platform: {platform.system()}"
        )

    # Check macOS version
    version = get_macos_version()
    if version and version[0] < 26:
        raise UnsupportedMacOSVersionError(
            f"On-device transcription requires macOS 26.0 or later. "
            f"Current version: {version[0]}.{version[1]}"
        )

    # Check helper exists
    helper = files("clipdrop").joinpath("bin/clipdrop-transcribe-clipboard")
    if not helper.exists():
        raise HelperNotFoundError(
            "Transcription helper not found. Please reinstall clipdrop with: "
            "pip install --force-reinstall clipdrop"
        )

    return str(helper)


def transcribe_from_clipboard(lang: str | None = None) -> list[dict[str, Any]]:
    """Invoke the Swift helper and parse JSONL transcription segments from stdout."""
    exe = helper_path()  # Now raises specific exceptions

    args = [exe]
    if lang:
        args.extend(["--lang", lang])

    proc = subprocess.Popen(  # noqa: S603, S607 - controlled arguments
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    segments: list[dict[str, Any]] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        segments.append(json.loads(line))

    code = proc.wait()
    if code != 0:
        err = proc.stderr.read().strip() if proc.stderr else ""
        raise RuntimeError(err or f"helper exit {code}")

    return segments


def transcribe_from_clipboard_stream(
    lang: str | None = None,
    progress_callback: Optional[Callable[[dict[str, Any], int], None]] = None
) -> Generator[dict[str, Any], None, None]:
    """
    Stream transcription segments from clipboard audio with optional progress callback.

    Args:
        lang: Optional language code (e.g., 'en-US')
        progress_callback: Optional callback function(segment, segment_number)

    Yields:
        Transcription segment dictionaries with 'start', 'end', and 'text' keys

    Raises:
        TranscriptionNotAvailableError: If helper is not available
        RuntimeError: If transcription fails
    """
    exe = helper_path()  # Now raises specific exceptions

    args = [exe]
    if lang:
        args.extend(["--lang", lang])

    proc = subprocess.Popen(  # noqa: S603, S607 - controlled arguments
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered for real-time streaming
    )

    segment_count = 0
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            try:
                segment = json.loads(line)
                segment_count += 1

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(segment, segment_count)

                yield segment
            except json.JSONDecodeError:
                # Skip invalid JSON lines (e.g., status messages)
                continue

        # Check for errors after stream ends
        code = proc.wait()
        if code != 0:
            err = proc.stderr.read().strip() if proc.stderr else ""
            raise RuntimeError(err or f"helper exit {code}")

    finally:
        # Ensure process is terminated if interrupted
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)


def check_audio_in_clipboard() -> bool:
    """
    Quick check if clipboard likely contains audio.

    This runs the Swift helper in a check mode to see if audio is available.

    Returns:
        True if audio is detected in clipboard, False otherwise
    """
    try:
        exe = helper_path()
    except TranscriptionNotAvailableError:
        # Silently return False for any availability issue
        return False

    try:
        # Run helper with a quick check (it will exit early if no audio)
        # The helper exits with code 1 if no audio found
        result = subprocess.run(
            [exe, "--check-only"],  # Add check-only flag to Swift helper
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return False
