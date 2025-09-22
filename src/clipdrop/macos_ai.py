from __future__ import annotations

import json
import platform
import subprocess
from importlib.resources import files
from typing import Any


def helper_path() -> str | None:
    """Return the filesystem path to the Swift transcription helper, or None off macOS."""
    if platform.system() != "Darwin":
        return None

    helper = files("clipdrop").joinpath("bin/clipdrop-transcribe-clipboard")
    return str(helper) if helper.exists() else None


def transcribe_from_clipboard(lang: str | None = None) -> list[dict[str, Any]]:
    """Invoke the Swift helper and parse JSONL transcription segments from stdout."""
    exe = helper_path()
    if exe is None:
        raise RuntimeError("On-device transcription is only available on macOS 26.0+.")

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
