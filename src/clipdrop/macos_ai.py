from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Callable, Generator, Optional

from .chunking import DEFAULT_MAX_CHUNK_CHARS, ChunkedSummarizationRequest, build_chunked_request


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


class SummarizationNotAvailableError(Exception):
    """Raised when the summarization helper cannot be used."""
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
    except (ValueError, IndexError, AttributeError):
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


def get_swift_helper_path(helper_name: str) -> Path:
    """Return path to a packaged Swift helper binary for macOS 26.0+."""

    if platform.system() != "Darwin":
        raise SummarizationNotAvailableError(
            "On-device summarization is only available on macOS. "
            f"Current platform: {platform.system()}"
        )

    version = get_macos_version()
    if version and version[0] < 26:
        raise SummarizationNotAvailableError(
            "On-device summarization requires macOS 26.0 or later."
        )

    helper_path = files("clipdrop").joinpath(f"bin/{helper_name}")
    if not helper_path.exists():
        raise SummarizationNotAvailableError(
            f"{helper_name} helper not found. Please rebuild with scripts/build_swift.sh."
        )

    return helper_path


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
        # Map exit codes to specific error messages
        if code == 1:
            raise RuntimeError("No audio file found in clipboard")
        elif code == 2:
            raise RuntimeError("Platform not supported - requires macOS 26.0+")
        elif code == 3:
            raise RuntimeError("No speech detected in audio")
        elif code == 4:
            raise RuntimeError(err or "Transcription failed")
        else:
            raise RuntimeError(err or f"Helper exited with code {code}")

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
            # Map exit codes to specific error messages
            if code == 1:
                raise RuntimeError("No audio file found in clipboard")
            elif code == 2:
                raise RuntimeError("Platform not supported - requires macOS 26.0+")
            elif code == 3:
                raise RuntimeError("No speech detected in audio")
            elif code == 4:
                raise RuntimeError(err or "Transcription failed")
            else:
                raise RuntimeError(err or f"Helper exited with code {code}")

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


def _run_summarizer(helper: Path, payload: str, timeout: int) -> "SummaryResult":
    """Execute summarization helper and normalize the response."""

    try:
        process = subprocess.run(  # noqa: S603, S607 - controlled args
            [str(helper)],
            input=payload,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return SummaryResult(success=False, error="Summarization timed out", retryable=True)
    except FileNotFoundError:
        return SummaryResult(success=False, error="Summarization helper not found")
    except subprocess.SubprocessError as exc:
        return SummaryResult(success=False, error=f"Summarization failed: {exc}")

    return _parse_summarizer_process(process)


def _parse_summarizer_process(process: subprocess.CompletedProcess[str]) -> "SummaryResult":
    stdout = (process.stdout or "").strip()
    stderr = (process.stderr or "").strip()

    def _normalize_payload(data: Any) -> Any:
        if isinstance(data, dict):
            for camel_key, snake_key in (
                ("stageResults", "stage_results"),
                ("elapsedMs", "elapsed_ms"),
            ):
                if camel_key in data and snake_key not in data:
                    data[snake_key] = data[camel_key]
        return data

    if process.returncode != 0:
        error_payload = stdout or stderr
        if error_payload:
            try:
                data = _normalize_payload(json.loads(error_payload))
            except json.JSONDecodeError:
                return SummaryResult(
                    success=False,
                    error=f"Summarization failed: {error_payload}",
                )
            return SummaryResult(
                success=False,
                error=data.get("error") or "Summarization failed",
                retryable=data.get("retryable"),
                stage=data.get("stage"),
                warnings=data.get("warnings"),
                stage_results=data.get("stage_results"),
            )
        return SummaryResult(success=False, error="Summarization failed")

    if not stdout:
        return SummaryResult(success=False, error="Summarization returned no data")

    try:
        data = _normalize_payload(json.loads(stdout))
    except json.JSONDecodeError:
        return SummaryResult(success=False, error="Failed to parse summarization result")

    if data.get("success"):
        return SummaryResult(
            success=True,
            summary=(data.get("summary") or "").strip(),
            warnings=data.get("warnings"),
            stage_results=data.get("stage_results"),
        )

    return SummaryResult(
        success=False,
        error=data.get("error", "Summarization failed"),
        retryable=data.get("retryable"),
        stage=data.get("stage"),
        warnings=data.get("warnings"),
        stage_results=data.get("stage_results"),
    )


def summarize_content(content: str, timeout: int = 30) -> SummaryResult:
    """Summarize text using the on-device Apple Intelligence helper."""

    stripped = content.strip()
    if len(stripped) < 200:
        return SummaryResult(
            success=False,
            error="Content too short for summarization (minimum 200 characters)"
        )

    if len(content) > 15_000:
        return SummaryResult(
            success=False,
            error="Content too long for summarization (maximum ~15,000 characters)"
        )

    try:
        helper = get_swift_helper_path("clipdrop-summarize")
    except SummarizationNotAvailableError as exc:
        return SummaryResult(success=False, error=str(exc))

    return _run_summarizer(helper, content, timeout)


def summarize_content_with_chunking(
    content: str,
    *,
    content_format: str = "plaintext",
    language: str = "en-US",
    instructions: Optional[str] = None,
    timeout: int = 45,
    origin: str = "clipdrop-cli",
    retry_attempt: int = 0,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    metadata: Optional[dict[str, Any]] = None,
) -> SummaryResult:
    """Summarize long-form text via the chunked helper protocol."""

    stripped = content.strip()
    if len(stripped) < 200:
        return SummaryResult(
            success=False,
            error="Content too short for summarization (minimum 200 characters)",
        )

    request: ChunkedSummarizationRequest = build_chunked_request(
        content=stripped,
        content_format=content_format,
        origin=origin,
        language=language,
        instructions=instructions,
        max_chunk_chars=max_chunk_chars,
        retry_attempt=retry_attempt,
        metadata=metadata,
    )

    if not request.chunks:
        return SummaryResult(success=False, error="No content available for summarization")

    try:
        helper = get_swift_helper_path("clipdrop-summarize")
    except SummarizationNotAvailableError as exc:
        return SummaryResult(success=False, error=str(exc))

    payload = request.to_json()
    result = _run_summarizer(helper, payload, timeout)

    # Attach total chunk count for debugging in stage results if missing
    if result.stage_results is None:
        result.stage_results = [
            {
                "stage": "chunk_summaries",
                "status": "pending" if not result.success else "ok",
                "processed": len(request.chunks),
            }
        ]

    return result


@dataclass(slots=True)
class SummaryResult:
    success: bool
    summary: Optional[str] = None
    error: Optional[str] = None
    retryable: Optional[bool] = None
    stage: Optional[str] = None
    warnings: Optional[list[str]] = None
    stage_results: Optional[list[dict[str, Any]]] = None
