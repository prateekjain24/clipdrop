"""Paranoid mode secret scanner and gate helpers."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional, Tuple

import typer
from rich.console import Console
from rich.panel import Panel

MAX_SCAN_BYTES = 1_000_000
MAX_FINDINGS = 100


class ParanoidMode(str, Enum):
    """Supported paranoid modes."""

    PROMPT = "prompt"
    REDACT = "redact"
    BLOCK = "block"
    WARN = "warn"


@dataclass(frozen=True)
class Finding:
    """Represents a potential secret finding within scanned text."""

    kind: str
    span: Tuple[int, int]
    value: str
    mask: str


_SIGNATURE_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    (
        "private_key",
        re.compile(
            r"-----BEGIN [^-]+ PRIVATE KEY-----[\s\S]+?-----END [^-]+ PRIVATE KEY-----",
            re.MULTILINE,
        ),
    ),
    (
        "aws_access_key_id",
        re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    (
        "github_pat",
        re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    ),
    (
        "slack_token",
        re.compile(r"\bxox[aboprs]-[A-Za-z0-9-]{10,}\b"),
    ),
    (
        "google_api_key",
        re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    ),
    (
        "sk_token",
        re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    ),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_\-]+=*\.[A-Za-z0-9_\-]+=*\.[A-Za-z0-9_\-+/=]*\b"
        ),
    ),
)


_KEYNAME_PATTERN = re.compile(
    r"(password|secret|token|apikey|authorization|private_key)\s*[:=]\s*[\"']?([A-Za-z0-9_\-/.+]{12,})",
    re.IGNORECASE,
)

_ENTROPY_CANDIDATE_PATTERN = re.compile(r"\b[A-Za-z0-9_/\-+=]{24,}\b")
_HEX_OR_UUID_PATTERN = re.compile(
    r"^(?:[0-9a-fA-F]{32,}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)

_TYPE_PRIORITY = {
    "private_key": 3,
    "aws_access_key_id": 3,
    "github_pat": 3,
    "slack_token": 3,
    "google_api_key": 3,
    "sk_token": 3,
    "jwt": 3,
}

_console = Console(stderr=True)


def mask_value(raw: str) -> str:
    """Return a masked representation while retaining a short identifier."""

    if not raw:
        return "[redacted]"

    prefix = raw[:4]
    suffix = raw[-2:] if len(raw) > 6 else ""
    sha1_stub = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:6]
    ellipsis = "…" if suffix else ""
    return f"{prefix}{ellipsis}{suffix} (sha1: {sha1_stub})"


def _add_finding(
    findings: dict[Tuple[int, int], Finding],
    span: Tuple[int, int],
    kind: str,
    value: str,
) -> None:
    """Add finding with prioritisation rules and capping."""

    start, end = span
    if start == end:
        return

    existing = findings.get(span)
    priority = _TYPE_PRIORITY.get(kind, 1)

    if existing is not None:
        if _TYPE_PRIORITY.get(existing.kind, 1) >= priority:
            return

    findings[span] = Finding(kind=kind, span=span, value=value, mask=mask_value(value))


def _shannon_entropy(sample: str) -> float:
    counts = {}
    for char in sample:
        counts[char] = counts.get(char, 0) + 1
    length = len(sample)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def scan_text(text: str) -> Tuple[List[Finding], bool, bool]:
    """Scan text for potential secrets.

    Returns tuple of findings list, truncated flag, and limit flag.
    """

    if not text:
        return [], False, False

    truncated = False
    if len(text.encode("utf-8")) > MAX_SCAN_BYTES:
        text = text.encode("utf-8")[:MAX_SCAN_BYTES].decode("utf-8", errors="ignore")
        truncated = True

    findings: dict[Tuple[int, int], Finding] = {}

    # Signature regexes
    for kind, pattern in _SIGNATURE_PATTERNS:
        for match in pattern.finditer(text):
            _add_finding(findings, match.span(), kind, match.group(0))
            if len(findings) >= MAX_FINDINGS:
                return sorted(findings.values(), key=lambda f: f.span[0]), truncated, True

    # Key-name heuristic
    for match in _KEYNAME_PATTERN.finditer(text):
        value = match.group(2)
        span = match.span(2)
        keyword = match.group(1).lower()
        kind = f"keyname_{keyword}"
        _add_finding(findings, span, kind, value)
        if len(findings) >= MAX_FINDINGS:
            return sorted(findings.values(), key=lambda f: f.span[0]), truncated, True

    # High-entropy fallback
    for match in _ENTROPY_CANDIDATE_PATTERN.finditer(text):
        candidate = match.group(0)
        if len(candidate) < 20:
            continue
        if _HEX_OR_UUID_PATTERN.match(candidate):
            continue
        entropy = _shannon_entropy(candidate)
        if entropy < 3.5:
            continue
        _add_finding(findings, match.span(), "high_entropy", candidate)
        if len(findings) >= MAX_FINDINGS:
            return sorted(findings.values(), key=lambda f: f.span[0]), truncated, True

    result = sorted(findings.values(), key=lambda f: f.span[0])
    limit_hit = len(result) >= MAX_FINDINGS
    return result, truncated, limit_hit


def redact_text(text: str, findings: Iterable[Finding]) -> str:
    """Replace finding spans with placeholders."""

    if not text:
        return text

    mutable = list(text)
    for finding in sorted(findings, key=lambda f: f.span[0], reverse=True):
        start, end = finding.span
        placeholder = f"[REDACTED:{finding.kind.upper()}]"
        mutable[start:end] = list(placeholder)
    return "".join(mutable)


def _format_summary(findings: List[Finding]) -> List[str]:
    lines = []
    for finding in findings:
        lines.append(f"• {finding.kind} — {finding.mask}")
    return lines


def _print_summary(
    findings: List[Finding],
    truncated: bool,
    limit_hit: bool,
    console: Console,
) -> None:
    if not findings:
        return

    title = f"Possible secrets found ({len(findings)})"
    body_lines = _format_summary(findings)
    if limit_hit:
        body_lines.append("[yellow]Findings capped at 100[/yellow]")
    if truncated:
        body_lines.append("[yellow]Scan truncated at 1 MB[/yellow]")
    console.print(Panel("\n".join(body_lines), title=title, expand=False))


def paranoid_gate(
    text: str,
    mode: ParanoidMode,
    *,
    is_tty: bool,
    auto_yes: bool,
    console: Optional[Console] = None,
) -> Tuple[str, str]:
    """Apply paranoid mode decision to text.

    Returns a tuple of resulting text and action ("save" or "redact").
    Raises SystemExit(17/18) for block/abort scenarios.
    """

    console = console or _console

    findings, truncated, limit_hit = scan_text(text)
    if not findings:
        return text, "save"

    _print_summary(findings, truncated, limit_hit, console)

    if mode == ParanoidMode.WARN:
        return text, "save"

    if mode == ParanoidMode.BLOCK:
        console.print("[red]Blocking save due to detected secrets.[/red]")
        raise typer.Exit(17)

    if mode == ParanoidMode.REDACT:
        redacted = redact_text(text, findings)
        return redacted, "redact"

    # Prompt mode
    if not is_tty and not auto_yes:
        console.print("[red]Non-interactive session: aborting save due to secrets.[/red]")
        raise typer.Exit(17)

    if auto_yes:
        return text, "save"

    choices = {"s": "save", "r": "redact", "a": "abort"}
    while True:
        console.print("[cyan][S]ave  [R]edact  [A]bort[/cyan]", highlight=False)
        try:
            response = console.input("").strip().lower()
        except (EOFError, KeyboardInterrupt):
            response = "a"

        action = choices.get(response)
        if action == "save":
            return text, "save"
        if action == "redact":
            redacted = redact_text(text, findings)
            return redacted, "redact"
        if action == "abort":
            console.print("[yellow]Aborting save at user request.[/yellow]")
            raise typer.Exit(18)

        console.print("[yellow]Please choose S, R, or A.[/yellow]")


def print_binary_skip_notice(mode: ParanoidMode, console: Optional[Console] = None) -> None:
    """Notify user that binary content is not scanned when paranoid mode is active."""

    if mode not in (ParanoidMode.PROMPT, ParanoidMode.WARN):
        return

    (console or _console).print(
        "[yellow]Binary clipboard payload not scanned under paranoid mode.[/yellow]"
    )
