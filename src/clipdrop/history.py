"""Local clipboard history for ClipDrop.

Stores recent text clips in a bounded JSON Lines file so the terminal user
can recover content they copied over. Privacy-first: clips that look like
secrets (per the paranoid scanner) are never persisted, oversized clips are
skipped, and the store is plain local files with owner-only permissions.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

import pyperclip

from clipdrop.paranoid import scan_text

# Overridable in tests
HISTORY_DIR = Path.home() / '.clipdrop'
HISTORY_FILENAME = 'history.jsonl'

HISTORY_MAX_ENTRIES = 50
HISTORY_MAX_ITEM_BYTES = 256 * 1024


@dataclass
class Entry:
    """A single clipboard history entry."""
    ts: str
    text: str


def get_history_file() -> Path:
    """Path to the history store (directory may not exist yet)."""
    return HISTORY_DIR / HISTORY_FILENAME


def _ensure_store() -> Path:
    """Create the history dir/file with owner-only permissions."""
    path = get_history_file()
    path.parent.mkdir(mode=0o700, exist_ok=True)
    # mkdir mode is masked by umask; enforce explicitly
    os.chmod(path.parent, 0o700)
    if not path.exists():
        path.touch(mode=0o600)
    os.chmod(path, 0o600)
    return path


def get_entries() -> List[Entry]:
    """Return history entries, newest first. Corrupt lines are skipped."""
    path = get_history_file()
    if not path.exists():
        return []

    entries = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            entries.append(Entry(ts=str(data['ts']), text=str(data['text'])))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    entries.reverse()
    return entries


def get_entry(n: int) -> Entry:
    """
    Return the Nth most recent entry (1-based).

    Raises:
        IndexError: If n is out of range
    """
    entries = get_entries()
    if n < 1 or n > len(entries):
        raise IndexError(
            f"History has {len(entries)} entries; {n} is out of range"
        )
    return entries[n - 1]


def add_entry(text: str) -> bool:
    """
    Add a clip to history. Returns True if stored, False if skipped.

    Skips: empty/whitespace clips, clips over HISTORY_MAX_ITEM_BYTES,
    duplicates of the most recent entry, and clips containing secrets
    (never persisted).
    """
    if not text or not text.strip():
        return False
    if len(text.encode('utf-8')) > HISTORY_MAX_ITEM_BYTES:
        return False

    findings, _, _ = scan_text(text)
    if findings:
        return False

    entries = get_entries()
    if entries and entries[0].text == text:
        return False

    path = _ensure_store()
    entry = Entry(ts=datetime.now(timezone.utc).isoformat(), text=text)
    newest_first = [entry] + entries
    kept = newest_first[:HISTORY_MAX_ENTRIES]

    lines = [
        json.dumps({'ts': e.ts, 'text': e.text}, ensure_ascii=False)
        for e in reversed(kept)
    ]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    os.chmod(path, 0o600)
    return True


def clear_history() -> None:
    """Remove all stored history."""
    path = get_history_file()
    if path.exists():
        path.unlink()


def format_age(iso_ts: str) -> str:
    """Human-readable age for a history entry timestamp."""
    try:
        then = datetime.fromisoformat(iso_ts)
    except ValueError:
        return '?'
    seconds = max(0, (datetime.now(timezone.utc) - then).total_seconds())
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"


def watch_clipboard(
    poll_interval: float = 1.0,
    max_iterations: Optional[int] = None,
    on_capture: Optional[Callable[[str], None]] = None,
) -> int:
    """
    Poll the clipboard and store each new text clip in history.

    Args:
        poll_interval: Seconds between clipboard checks
        max_iterations: Stop after this many polls (None = run until
            interrupted); mainly for testing
        on_capture: Optional callback invoked with each stored clip

    Returns:
        Number of clips stored
    """
    captured = 0
    last_hash = None
    iterations = 0

    while max_iterations is None or iterations < max_iterations:
        iterations += 1
        try:
            content = pyperclip.paste()
        except Exception:
            content = None

        if content:
            content_hash = hashlib.sha256(
                content.encode('utf-8', errors='replace')
            ).digest()
            if content_hash != last_hash:
                last_hash = content_hash
                if add_entry(content):
                    captured += 1
                    if on_capture is not None:
                        on_capture(content)

        if max_iterations is None or iterations < max_iterations:
            time.sleep(poll_interval)

    return captured
