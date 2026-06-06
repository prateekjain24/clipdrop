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


class OCRNotAvailableError(Exception):
    """Raised when the OCR helper cannot be used."""
    pass


class TransformNotAvailableError(Exception):
    """Raised when the transform helper cannot be used."""
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


def get_ocr_helper_path() -> Path:
    """Return path to the packaged Vision OCR helper binary.

    Raises:
        OCRNotAvailableError: If not on macOS or the helper is missing.
    """
    if platform.system() != "Darwin":
        raise OCRNotAvailableError(
            "On-device OCR is only available on macOS. "
            f"Current platform: {platform.system()}"
        )

    helper = files("clipdrop").joinpath("bin/clipdrop-ocr")
    if not helper.exists():
        raise OCRNotAvailableError(
            "clipdrop-ocr helper not found. Please rebuild with scripts/build_swift.sh."
        )

    return Path(str(helper))


def ocr_image(image: Any, lang: Optional[str] = None, timeout: int = 30) -> str:
    """Run on-device OCR on a PIL image and return the recognized text.

    Args:
        image: A PIL ``Image.Image`` to recognize text from.
        lang: Optional comma-separated BCP-47 language hints (e.g. ``en-US``).
        timeout: Seconds to wait for the helper before giving up.

    Returns:
        The recognized text, or an empty string if no text was detected.

    Raises:
        OCRNotAvailableError: If the helper is unavailable (e.g. not macOS).
        RuntimeError: If the helper fails unexpectedly.
    """
    helper = get_ocr_helper_path()  # raises OCRNotAvailableError

    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        image.save(tmp_path, format="PNG")

        args = [str(helper), str(tmp_path)]
        if lang:
            args.extend(["--lang", lang])

        try:
            proc = subprocess.run(  # noqa: S603 - controlled arguments
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("OCR timed out")

        if proc.returncode == 1:
            # Helper ran fine but found no text.
            return ""
        if proc.returncode != 0:
            message = (proc.stderr or "").strip() or f"OCR helper exited with code {proc.returncode}"
            raise RuntimeError(message)

        return (proc.stdout or "").strip()
    finally:
        tmp_path.unlink(missing_ok=True)


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
    if proc.stdout is None:
        raise RuntimeError("Failed to capture transcription helper output")
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
        if proc.stdout is None:
            raise RuntimeError("Failed to capture transcription helper output")
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


TRANSFORM_MAX_CHARS = 10_000


def get_transform_helper_path() -> Path:
    """Return path to the packaged transform helper binary.

    Raises:
        TransformNotAvailableError: If not on macOS 26+ or the helper is missing.
    """
    try:
        return get_swift_helper_path("clipdrop-transform")
    except SummarizationNotAvailableError as exc:
        raise TransformNotAvailableError(str(exc)) from exc


def transform_content(
    content: str,
    operation: str,
    *,
    style: Optional[str] = None,
    instruction: Optional[str] = None,
    language: Optional[str] = None,
    timeout: int = 45,
) -> dict[str, Any]:
    """Apply an on-device transformation to ``content``.

    Args:
        content: The text to transform.
        operation: One of ``"rewrite"``, ``"prompt"``, or ``"table"``.
        style: Target style for ``rewrite`` (e.g. ``"formal"``).
        instruction: Freeform instruction for ``prompt``.
        language: Optional BCP-47 language hint.
        timeout: Seconds to wait for the helper.

    Returns:
        The parsed helper payload, e.g. ``{"success": True, "result": "..."}``
        or ``{"success": True, "table": {"headers": [...], "rows": [[...]]}}``.

    Raises:
        TransformNotAvailableError: If the helper is unavailable (e.g. not macOS).
        RuntimeError: If the transform fails.
    """
    stripped = content.strip()
    if not stripped:
        raise RuntimeError("No content to transform")
    if len(stripped) > TRANSFORM_MAX_CHARS:
        raise RuntimeError(
            f"Content too long to transform (max ~{TRANSFORM_MAX_CHARS:,} characters)"
        )

    helper = get_transform_helper_path()  # raises TransformNotAvailableError

    payload: dict[str, Any] = {"operation": operation, "content": stripped}
    if style:
        payload["style"] = style
    if instruction:
        payload["instruction"] = instruction
    if language:
        payload["language"] = language

    try:
        process = subprocess.run(  # noqa: S603 - controlled args
            [str(helper)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Transform timed out")
    except (subprocess.SubprocessError, OSError) as exc:
        raise RuntimeError(f"Transform failed: {exc}")

    stdout = (process.stdout or "").strip()
    if not stdout:
        raise RuntimeError((process.stderr or "").strip() or "Transform produced no output")

    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError("Failed to parse transform result")

    if not data.get("success"):
        raise RuntimeError(data.get("error") or "Transform failed")

    return data


def suggest_filename(content: str, timeout: int = 15) -> Optional[str]:
    """Ask the on-device model for a short descriptive title for ``content``.

    Returns the suggested title (the caller slugifies it), or ``None`` if the
    helper is unavailable or fails — callers should fall back to a heuristic.
    """
    stripped = content.strip()
    if not stripped:
        return None

    try:
        helper = get_swift_helper_path("clipdrop-suggest-name")
    except SummarizationNotAvailableError:
        return None

    try:
        process = subprocess.run(  # noqa: S603 - controlled args
            [str(helper)],
            input=stripped,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except (subprocess.SubprocessError, OSError):
        return None

    stdout = (process.stdout or "").strip()
    if not stdout:
        return None

    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return None

    if data.get("success") and data.get("title"):
        return str(data["title"]).strip() or None
    return None


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
