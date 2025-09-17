"""Clipboard operations module for ClipDrop."""

from typing import Optional
import pyperclip


def get_text() -> Optional[str]:
    """
    Get text content from the clipboard.

    Returns:
        Text content from clipboard or None if empty/error
    """
    try:
        content = pyperclip.paste()
        # pyperclip returns empty string for empty clipboard
        return content if content else None
    except Exception:
        # Handle any clipboard access errors
        return None


def has_content() -> bool:
    """
    Check if clipboard has any content.

    Returns:
        True if clipboard has content, False otherwise
    """
    content = get_text()
    return content is not None and len(content) > 0


def get_content_type() -> str:
    """
    Determine the type of content in clipboard.

    Returns:
        'text' if text content exists
        'empty' if clipboard is empty
        'unknown' for any other case
    """
    content = get_text()
    if content is None:
        return 'empty'
    elif len(content) > 0:
        return 'text'
    else:
        return 'empty'


def get_content_preview(max_chars: int = 100) -> Optional[str]:
    """
    Get a preview of clipboard content.

    Args:
        max_chars: Maximum number of characters to return

    Returns:
        Preview string or None if no content
    """
    content = get_text()
    if content is None:
        return None

    if len(content) <= max_chars:
        return content

    # Add ellipsis for truncated content
    return content[:max_chars] + "..."