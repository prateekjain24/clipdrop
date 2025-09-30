"""Smart format detection for clipboard content."""

import json
import platform
import re
from pathlib import Path


SINGLE_PASS_LIMIT_REASON = "Content too long for single-pass summarization"


def is_summarizable_content(content: str, detected_format: str) -> tuple[bool, str]:
    """Determine whether clipboard content is appropriate for on-device summarization."""

    if not content.strip():
        return False, "Content is empty"

    normalized_format = detected_format.lower() if detected_format else ""

    # Skip formats that are unlikely to benefit from prose summarization.
    if normalized_format in {"json", "csv", "yaml", "code"}:
        return False, f"Format '{detected_format}' not suitable for summarization"

    word_count = len(content.split())
    if word_count < 50:
        return False, "Content too short for meaningful summarization"

    if word_count > 3_000:
        return False, SINGLE_PASS_LIMIT_REASON

    # Heuristic filter to avoid passing obvious code snippets.
    lowered = content.lower()
    code_keywords = (
        "def ",
        " class ",
        "function ",
        "fn ",
        "#!/",
        "import ",
        "const ",
        " var ",
        "public ",
        "private ",
    )
    code_hits = sum(lowered.count(keyword) for keyword in code_keywords)
    fenced_code = "```" in content or "</code>" in lowered
    indented_code = any(
        line.startswith(("    ", "\t")) and any(sym in line for sym in ("(", ")", "=", ":"))
        for line in content.splitlines()
    )
    structural_tokens = any(token in content for token in ("{", "};", "=>", "#include"))

    if fenced_code or code_hits >= 3 or (
        code_hits >= 2 and (indented_code or structural_tokens)
    ):
        return False, "Content appears to be code"

    if normalized_format in {"md", "markdown", "txt", "text", "html"}:
        return True, ""

    printable = sum(char.isprintable() for char in content)
    printable_ratio = printable / len(content)
    if printable_ratio >= 0.8:
        return True, ""

    # Future: fall back to multi-stage chunking for very long but primarily textual content.
    return False, "Content not suitable for summarization"


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


def detect_format(content: str, has_image: bool = False) -> str:
    """
    Detect the most likely format of the content.

    Args:
        content: String content to analyze
        has_image: Whether image content is also present

    Returns:
        File extension without dot: 'json', 'md', 'csv', 'pdf', or 'txt'
    """
    # Mixed content (text + image) suggests PDF
    if content and has_image:
        return 'pdf'

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


def add_extension(filename: str, content: str, has_image: bool = False) -> str:
    """
    Add appropriate extension to filename if it doesn't have one.

    Args:
        filename: Original filename (with or without extension)
        content: Content to be saved (used for format detection)
        has_image: Whether image content is also present

    Returns:
        Filename with appropriate extension
    """
    path = Path(filename)

    # If file already has an extension, keep it
    if path.suffix:
        return filename

    # Detect format and add extension
    detected_format = detect_format(content, has_image)
    return f"{filename}.{detected_format}"


def detect_audio_clipboard() -> bool:
    """
    Check if clipboard contains audio file or data.

    This is a lightweight check - actual audio detection happens in Swift helper.

    Returns:
        True if on macOS and Swift helper is available, False otherwise
    """
    if platform.system() != "Darwin":
        return False

    # Check if Swift helper exists
    try:
        from clipdrop.macos_ai import helper_path
        return helper_path() is not None
    except ImportError:
        return False


def suggest_filename(content: str, has_image: bool = False, has_audio: bool = False) -> str:
    """
    Suggest a filename based on content type.

    Args:
        content: Content to analyze
        has_image: Whether image content is also present
        has_audio: Whether audio content is detected

    Returns:
        Suggested filename with extension
    """
    # Audio takes precedence
    if has_audio:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"transcript_{timestamp}.srt"

    format_type = detect_format(content, has_image)

    # Generate contextual default names
    if format_type == 'pdf':
        return 'document.pdf'
    elif format_type == 'json':
        return 'data.json'
    elif format_type == 'csv':
        return 'data.csv'
    elif format_type == 'md':
        return 'notes.md'
    else:
        return 'clipboard.txt'
