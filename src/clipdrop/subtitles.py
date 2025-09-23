"""Subtitle rendering functions for transcription segments."""

from __future__ import annotations


def _fmt_ts(sec: float) -> str:
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm).

    Args:
        sec: Time in seconds

    Returns:
        Formatted timestamp string like "00:01:30,123"
    """
    ms = int(round(sec * 1000))
    h, r = divmod(ms, 3600_000)
    m, r = divmod(r, 60_000)
    s, ms = divmod(r, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(segs: list[dict]) -> str:
    """Convert transcription segments to SRT subtitle format.

    Args:
        segs: List of segment dicts with 'start', 'end', and 'text' keys

    Returns:
        SRT formatted string with proper numbering and timestamps
    """
    out = []
    for i, s in enumerate(segs, 1):
        start = _fmt_ts(float(s["start"]))
        end = _fmt_ts(float(s["end"]))
        text = (s["text"] or "").strip()
        if not text:
            continue
        out += [str(i), f"{start} --> {end}", text, ""]
    return "\n".join(out).rstrip() + "\n"


def to_txt(segs: list[dict]) -> str:
    """Convert transcription segments to plain text format.

    Args:
        segs: List of segment dicts with 'text' key

    Returns:
        Plain text with segments separated by newlines
    """
    return "\n".join(
        (s["text"] or "").strip()
        for s in segs
        if (s["text"] or "").strip()
    ) + "\n"


def to_md(segs: list[dict]) -> str:
    """Convert transcription segments to Markdown format with timestamps.

    Args:
        segs: List of segment dicts with 'start', 'end', and 'text' keys

    Returns:
        Markdown formatted string with timestamp headings
    """
    lines = []
    for s in segs:
        text = (s["text"] or "").strip()
        if not text:
            continue
        # Format timestamps without milliseconds for cleaner markdown
        start = _fmt_ts(float(s["start"]))[:-4]  # hh:mm:ss
        end = _fmt_ts(float(s["end"]))[:-4]
        lines += [f"### {start}–{end}", "", text, ""]
    return "\n".join(lines).rstrip() + "\n"