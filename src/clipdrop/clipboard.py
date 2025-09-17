"""Clipboard operations module for ClipDrop."""

import time
import re
from typing import Optional, Dict, Any, Tuple
import pyperclip

try:
    from PIL import Image, ImageGrab
except ImportError:
    Image = None
    ImageGrab = None

from clipdrop.exceptions import (
    ClipboardEmptyError,
    ClipboardAccessError,
    ContentTooLargeError,
    ImageClipboardError
)

# Cache for clipboard content to avoid repeated access
_clipboard_cache: Dict[str, Any] = {
    'content': None,
    'timestamp': 0,
    'cache_duration': 0.1  # Cache for 100ms
}

# Maximum content size (100MB)
MAX_CONTENT_SIZE = 100 * 1024 * 1024


def get_text() -> Optional[str]:
    """
    Get text content from the clipboard.

    Returns:
        Text content from clipboard or None if empty/error

    Raises:
        ContentTooLargeError: If content exceeds size limit
    """
    try:
        # Check cache first
        current_time = time.time()
        if (_clipboard_cache['content'] is not None and
            current_time - _clipboard_cache['timestamp'] < _clipboard_cache['cache_duration']):
            return _clipboard_cache['content']

        content = pyperclip.paste()

        # Check size limit
        if content and len(content.encode('utf-8')) > MAX_CONTENT_SIZE:
            raise ContentTooLargeError(
                len(content.encode('utf-8')),
                MAX_CONTENT_SIZE
            )

        # Update cache
        _clipboard_cache['content'] = content if content else None
        _clipboard_cache['timestamp'] = current_time

        # pyperclip returns empty string for empty clipboard
        return content if content else None
    except ContentTooLargeError:
        raise
    except Exception as e:
        # Handle any clipboard access errors
        return None


def get_clipboard_text() -> str:
    """
    Get text content from clipboard (alias for consistency).

    Returns:
        Text content from clipboard

    Raises:
        ClipboardEmptyError: If clipboard is empty
        ClipboardAccessError: If clipboard cannot be accessed
    """
    try:
        content = get_text()
        if content is None:
            raise ClipboardEmptyError()
        return content
    except ContentTooLargeError:
        raise
    except Exception as e:
        if isinstance(e, ClipboardEmptyError):
            raise
        raise ClipboardAccessError(original_error=e)


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


def get_clipboard_stats() -> Dict[str, Any]:
    """
    Get statistics about clipboard content.

    Returns:
        Dictionary with content statistics:
        - size_bytes: Size in bytes
        - size_human: Human-readable size
        - lines: Number of lines
        - words: Number of words
        - chars: Number of characters
        - is_empty: Whether clipboard is empty
    """
    content = get_text()

    if content is None:
        return {
            'size_bytes': 0,
            'size_human': '0 B',
            'lines': 0,
            'words': 0,
            'chars': 0,
            'is_empty': True
        }

    size_bytes = len(content.encode('utf-8'))

    # Calculate human-readable size
    size_human = f"{size_bytes} B"
    for unit in ['KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            break
        size_bytes_display = size_bytes / 1024.0
        if size_bytes_display < 1024.0:
            size_human = f"{size_bytes_display:.1f} {unit}"
            break

    return {
        'size_bytes': size_bytes,
        'size_human': size_human,
        'lines': content.count('\n') + 1 if content else 0,
        'words': len(content.split()) if content else 0,
        'chars': len(content),
        'is_empty': False
    }


def is_clipboard_binary() -> bool:
    """
    Check if clipboard content might be binary data.

    Returns:
        True if content appears to be binary, False otherwise
    """
    content = get_text()
    if content is None:
        return False

    # Check for null bytes or high proportion of non-printable characters
    if '\x00' in content:
        return True

    # Check for non-printable characters (excluding common whitespace)
    non_printable_count = 0
    sample_size = min(1000, len(content))  # Check first 1000 chars

    for char in content[:sample_size]:
        if not (char.isprintable() or char in '\n\r\t'):
            non_printable_count += 1

    # If more than 10% non-printable, likely binary
    return non_printable_count > sample_size * 0.1


def wait_for_change(timeout: float = 10.0, poll_interval: float = 0.1) -> Optional[str]:
    """
    Wait for clipboard content to change.

    Args:
        timeout: Maximum time to wait in seconds
        poll_interval: How often to check clipboard in seconds

    Returns:
        New clipboard content or None if timeout

    Raises:
        ClipboardAccessError: If clipboard cannot be accessed
    """
    try:
        # Get initial content
        initial_content = get_text()
        start_time = time.time()

        while time.time() - start_time < timeout:
            time.sleep(poll_interval)

            # Clear cache to force fresh read
            _clipboard_cache['content'] = None
            _clipboard_cache['timestamp'] = 0

            current_content = get_text()

            if current_content != initial_content:
                return current_content

        return None  # Timeout
    except Exception as e:
        raise ClipboardAccessError("Error monitoring clipboard", original_error=e)


def clear_clipboard() -> None:
    """
    Clear clipboard content.

    Raises:
        ClipboardAccessError: If clipboard cannot be cleared
    """
    try:
        pyperclip.copy("")
        # Clear cache
        _clipboard_cache['content'] = None
        _clipboard_cache['timestamp'] = 0
    except Exception as e:
        raise ClipboardAccessError("Cannot clear clipboard", original_error=e)


def copy_to_clipboard(content: str) -> None:
    """
    Copy content to clipboard.

    Args:
        content: Text to copy to clipboard

    Raises:
        ClipboardAccessError: If content cannot be copied
        ContentTooLargeError: If content exceeds size limit
    """
    if len(content.encode('utf-8')) > MAX_CONTENT_SIZE:
        raise ContentTooLargeError(
            len(content.encode('utf-8')),
            MAX_CONTENT_SIZE
        )

    try:
        pyperclip.copy(content)
        # Update cache
        _clipboard_cache['content'] = content
        _clipboard_cache['timestamp'] = time.time()
    except Exception as e:
        raise ClipboardAccessError("Cannot copy to clipboard", original_error=e)


# Image clipboard operations
_image_cache: Dict[str, Any] = {
    'image': None,
    'timestamp': 0,
    'cache_duration': 0.2  # Cache for 200ms
}


def has_image() -> bool:
    """
    Check if clipboard contains an image.

    Returns:
        True if clipboard has an image, False otherwise
    """
    if ImageGrab is None:
        return False

    try:
        # Check cache first
        current_time = time.time()
        if (_image_cache['image'] is not None and
            current_time - _image_cache['timestamp'] < _image_cache['cache_duration']):
            return True

        # Try to grab image from clipboard
        img = ImageGrab.grabclipboard()
        if img is not None:
            # Cache the image
            _image_cache['image'] = img
            _image_cache['timestamp'] = current_time
            return True
        return False
    except Exception:
        return False


def get_image() -> Optional['Image.Image']:
    """
    Get image from clipboard.

    Returns:
        PIL Image object or None if no image

    Raises:
        ImageClipboardError: If there's an error accessing the image
    """
    if ImageGrab is None:
        raise ImageClipboardError("Pillow is not installed")

    try:
        # Check cache first
        current_time = time.time()
        if (_image_cache['image'] is not None and
            current_time - _image_cache['timestamp'] < _image_cache['cache_duration']):
            return _image_cache['image']

        # Get fresh image from clipboard
        img = ImageGrab.grabclipboard()

        if img is not None:
            # Cache the image
            _image_cache['image'] = img
            _image_cache['timestamp'] = current_time

        return img
    except Exception as e:
        raise ImageClipboardError("Failed to get image from clipboard", original_error=e)


def get_image_info() -> Optional[Dict[str, Any]]:
    """
    Get information about the image in clipboard.

    Returns:
        Dictionary with image info (width, height, mode, format) or None
    """
    img = get_image()
    if img is None:
        return None

    return {
        'width': img.width,
        'height': img.height,
        'mode': img.mode,  # RGB, RGBA, etc.
        'format': img.format,  # PNG, JPEG, etc. (may be None)
        'size_pixels': img.width * img.height,
        'has_transparency': img.mode in ('RGBA', 'LA', 'P')
    }


def get_content_type() -> str:
    """
    Determine what type of content is in the clipboard.

    Returns:
        'image', 'text', 'both', or 'none'
    """
    has_img = has_image()
    has_txt = has_content()

    if has_img and has_txt:
        return 'both'
    elif has_img:
        return 'image'
    elif has_txt:
        return 'text'
    else:
        return 'none'


def has_both_content() -> bool:
    """
    Check if clipboard has both text and image content.

    Returns:
        True if both types exist, False otherwise
    """
    return has_image() and has_content()


def clear_image_cache() -> None:
    """Clear the image cache."""
    _image_cache['image'] = None
    _image_cache['timestamp'] = 0