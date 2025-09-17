"""Smart format detection for clipboard content."""

import json
import re
from pathlib import Path


def is_json(content: str) -> bool:
    """
    Check if content is valid JSON.

    Args:
        content: String to check

    Returns:
        True if valid JSON, False otherwise
    """
    if not content or not content.strip():
        return False

    content = content.strip()
    # Quick check for JSON-like structure
    if not ((content.startswith('{') and content.endswith('}')) or
            (content.startswith('[') and content.endswith(']'))):
        return False

    try:
        json.loads(content)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def is_markdown(content: str) -> bool:
    """
    Check if content appears to be Markdown.

    Args:
        content: String to check

    Returns:
        True if likely Markdown, False otherwise
    """
    if not content:
        return False

    # Markdown patterns to check
    patterns = [
        r'^#{1,6}\s+.*$',          # Headers (# Title, ## Subtitle, etc.)
        r'^\*\*.*\*\*',             # Bold text
        r'^\*.*\*[^*]',             # Italic text
        r'^\[.*\]\(.*\)',           # Links [text](url)
        r'^```[\s\S]*```',          # Code blocks
        r'^\* .*$|^- .*$|^\d+\. .*$',  # Lists
        r'^\|.*\|.*\|',             # Tables
        r'^>\s+.*$',                # Blockquotes
    ]

    # Check if content matches multiple markdown patterns
    matches = 0
    lines = content.split('\n')
    for line in lines[:20]:  # Check first 20 lines for performance
        for pattern in patterns:
            if re.search(pattern, line.strip(), re.MULTILINE):
                matches += 1
                break

    # Consider it markdown if we find at least 2 patterns
    # or if it has headers
    has_headers = bool(re.search(r'^#{1,6}\s+', content, re.MULTILINE))
    return has_headers or matches >= 2


def is_csv(content: str) -> bool:
    """
    Check if content appears to be CSV data.

    Args:
        content: String to check

    Returns:
        True if likely CSV, False otherwise
    """
    if not content:
        return False

    lines = content.strip().split('\n')
    if len(lines) < 2:  # Need at least 2 lines for CSV
        return False

    # Check for consistent delimiter count
    # Try both comma and tab
    for delimiter in [',', '\t']:
        delimiter_counts = []
        for line in lines[:10]:  # Check first 10 lines
            if line.strip():
                delimiter_counts.append(line.count(delimiter))

        # If all non-empty lines have the same number of delimiters > 0
        if delimiter_counts and all(c == delimiter_counts[0] and c > 0
                                   for c in delimiter_counts):
            return True

    return False


def detect_format(content: str) -> str:
    """
    Detect the most likely format of the content.

    Args:
        content: String content to analyze

    Returns:
        File extension without dot: 'json', 'md', 'csv', or 'txt'
    """
    if not content:
        return 'txt'

    # Check in order of specificity
    if is_json(content):
        return 'json'
    elif is_csv(content):
        return 'csv'
    elif is_markdown(content):
        return 'md'
    else:
        return 'txt'


def add_extension(filename: str, content: str) -> str:
    """
    Add appropriate extension to filename if it doesn't have one.

    Args:
        filename: Original filename (with or without extension)
        content: Content to be saved (used for format detection)

    Returns:
        Filename with appropriate extension
    """
    path = Path(filename)

    # If file already has an extension, keep it
    if path.suffix:
        return filename

    # Detect format and add extension
    detected_format = detect_format(content)
    return f"{filename}.{detected_format}"


def suggest_filename(content: str) -> str:
    """
    Suggest a filename based on content type.

    Args:
        content: Content to analyze

    Returns:
        Suggested filename with extension
    """
    format_type = detect_format(content)

    # Generate contextual default names
    if format_type == 'json':
        return 'data.json'
    elif format_type == 'csv':
        return 'data.csv'
    elif format_type == 'md':
        return 'notes.md'
    else:
        return 'clipboard.txt'