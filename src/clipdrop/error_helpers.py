"""User-friendly error messages and helpers for ClipDrop."""

from typing import Optional, List, Dict, Any
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


# Error message templates with suggestions
ERROR_MESSAGES = {
    'empty_clipboard': {
        'icon': '📋',
        'message': 'Nothing to save!',
        'details': 'Your clipboard is empty.',
        'suggestions': [
            'Copy some text with Cmd+C (Mac) or Ctrl+C',
            'Take a screenshot with Cmd+Shift+4 (Mac)',
            'Copy an image from any application'
        ]
    },
    'permission_denied': {
        'icon': '🔒',
        'message': "Can't write to this location",
        'details': 'Permission denied or directory is protected.',
        'suggestions': [
            'Try saving to your Desktop or Documents folder',
            'Use current directory: clipdrop ./filename',
            'Check folder permissions with: ls -la',
            'Try with sudo (admin) if necessary'
        ]
    },
    'file_exists': {
        'icon': '📁',
        'message': 'File already exists',
        'details': 'A file with this name already exists.',
        'suggestions': [
            'Use --force or -f to overwrite',
            'Choose a different filename',
            'Add a number: filename2.txt'
        ]
    },
    'invalid_path': {
        'icon': '📍',
        'message': 'Invalid file path',
        'details': 'The path contains invalid characters or is malformed.',
        'suggestions': [
            'Remove special characters from filename',
            'Use only letters, numbers, dash, and underscore',
            'Try a simpler path: clipdrop simple.txt'
        ]
    },
    'no_image_support': {
        'icon': '🖼️',
        'message': 'Image support unavailable',
        'details': 'Pillow library is not installed or configured.',
        'suggestions': [
            'Install Pillow: pip install Pillow',
            'Try reinstalling: pip install --upgrade Pillow',
            'Use --text flag to save text content instead'
        ]
    },
    'format_unknown': {
        'icon': '❓',
        'message': 'Unknown format',
        'details': 'Could not determine the file format.',
        'suggestions': [
            'Specify extension explicitly: filename.txt',
            'Supported: .txt, .json, .md, .csv, .png, .jpg',
            'Check clipboard content with --preview'
        ]
    },
    'content_too_large': {
        'icon': '📦',
        'message': 'Content too large',
        'details': 'The clipboard content exceeds the size limit.',
        'suggestions': [
            'Try saving to a compressed format',
            'Split content into multiple files',
            'Increase system memory if needed'
        ]
    },
    'clipboard_access_error': {
        'icon': '⚠️',
        'message': 'Cannot access clipboard',
        'details': 'Failed to read from system clipboard.',
        'suggestions': [
            'Check clipboard permissions in System Preferences',
            'Try copying content again',
            'Restart the application',
            'On macOS: Check Security & Privacy settings'
        ]
    }
}


def get_error_message(error_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get formatted error message with suggestions.

    Args:
        error_type: Type of error from ERROR_MESSAGES
        context: Optional context dictionary with additional info

    Returns:
        Error message dictionary
    """
    message = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES['format_unknown'])

    # Add context-specific information
    if context:
        if 'filename' in context:
            message = message.copy()
            message['details'] = f"{message['details']} (File: {context['filename']})"
        if 'size' in context:
            message = message.copy()
            message['details'] = f"{message['details']} (Size: {context['size']})"

    return message


def display_error(error_type: str, context: Optional[Dict[str, Any]] = None,
                  show_suggestions: bool = True) -> None:
    """
    Display a formatted error message with suggestions.

    Args:
        error_type: Type of error from ERROR_MESSAGES
        context: Optional context dictionary
        show_suggestions: Whether to show suggestions
    """
    error_info = get_error_message(error_type, context)

    # Main error message
    console.print(f"\n{error_info['icon']} [bold red]{error_info['message']}[/bold red]")
    console.print(f"[yellow]{error_info['details']}[/yellow]\n")

    # Show suggestions
    if show_suggestions and 'suggestions' in error_info:
        console.print("[bold cyan]💡 Try these solutions:[/bold cyan]")
        for i, suggestion in enumerate(error_info['suggestions'], 1):
            console.print(f"  {i}. {suggestion}")
        console.print()


def suggest_similar_files(attempted_path: str, directory: Path = Path('.')) -> List[str]:
    """
    Suggest similar existing files based on attempted filename.

    Args:
        attempted_path: The path user tried to use
        directory: Directory to search in

    Returns:
        List of similar filenames
    """
    attempted_name = Path(attempted_path).name.lower()
    suggestions = []

    try:
        for file in directory.iterdir():
            if file.is_file():
                similarity = calculate_similarity(attempted_name, file.name.lower())
                if similarity > 0.5:  # More than 50% similar
                    suggestions.append(file.name)
    except Exception:
        pass

    return suggestions[:3]  # Return top 3 suggestions


def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate simple similarity between two strings.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity score between 0 and 1
    """
    if not str1 or not str2:
        return 0.0

    # Simple character overlap similarity
    set1 = set(str1)
    set2 = set(str2)

    if not set1 or not set2:
        return 0.0

    intersection = set1.intersection(set2)
    union = set1.union(set2)

    return len(intersection) / len(union)


def format_permission_error(path: Path, operation: str = "write") -> str:
    """
    Format a permission error with helpful context.

    Args:
        path: Path that caused the error
        operation: Operation that failed

    Returns:
        Formatted error message
    """
    parent = path.parent

    # Check various permission scenarios
    if not parent.exists():
        return f"Directory '{parent}' does not exist. Create it first or choose another location."
    elif not parent.is_dir():
        return f"'{parent}' is not a directory. Choose a valid directory."
    elif path.exists() and not path.is_file():
        return f"'{path}' exists but is not a file. Choose a different name."
    else:
        return f"Permission denied to {operation} '{path}'. Try another location or check permissions."


def show_success_message(filepath: Path, content_type: str, size: str,
                         additional_info: Optional[Dict[str, Any]] = None) -> None:
    """
    Display a formatted success message.

    Args:
        filepath: Path where file was saved
        content_type: Type of content (text, image, json, etc.)
        size: Human-readable file size
        additional_info: Optional additional information
    """
    icon_map = {
        'text': '📝',
        'image': '📷',
        'json': '📊',
        'markdown': '📄',
        'csv': '📈',
        'code': '💻'
    }

    icon = icon_map.get(content_type, '✅')

    message = f"{icon} [bold green]Success![/bold green] "

    if content_type == 'image' and additional_info:
        dims = additional_info.get('dimensions', 'unknown')
        message += f"Saved image ({dims}, {size}) to {filepath}"
    else:
        message += f"Saved {size} to {filepath}"

    console.print(message)

    # Show additional info if provided
    if additional_info:
        if 'format_detected' in additional_info:
            console.print(f"  [dim]Format: {additional_info['format_detected']}[/dim]")
        if 'optimized' in additional_info and additional_info['optimized']:
            console.print("  [dim]✨ Optimized for smaller file size[/dim]")


def show_clipboard_status() -> None:
    """Display current clipboard status in a formatted table."""
    from clipdrop import clipboard

    table = Table(title="📋 Clipboard Status", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    content_type = clipboard.get_content_type()

    # Content type
    type_emoji = {
        'text': '📝 Text',
        'image': '🖼️ Image',
        'both': '📝🖼️ Text + Image',
        'none': '❌ Empty'
    }
    table.add_row("Content", type_emoji.get(content_type, 'Unknown'))

    # Add specific info based on content
    if content_type in ('text', 'both'):
        try:
            text = clipboard.get_text()
            if text:
                table.add_row("Text Size", f"{len(text)} characters")
                # Detect format
                from clipdrop import detect
                format_type = detect.detect_format(text)
                table.add_row("Detected Format", format_type.upper())
        except Exception:
            pass

    if content_type in ('image', 'both'):
        try:
            info = clipboard.get_image_info()
            if info:
                table.add_row("Image Size", f"{info['width']}x{info['height']} pixels")
                if info.get('mode'):
                    table.add_row("Color Mode", info['mode'])
        except Exception:
            pass

    console.print(table)