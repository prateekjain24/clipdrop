"""File operations module for ClipDrop."""

import json
from pathlib import Path
from typing import Union
import typer
from rich.console import Console
from rich.prompt import Confirm

console = Console()


def check_exists(path: Path) -> bool:
    """
    Check if a file exists at the given path.

    Args:
        path: Path to check

    Returns:
        True if file exists, False otherwise
    """
    return path.exists() and path.is_file()


def ensure_parent_dir(path: Path) -> None:
    """
    Ensure parent directory exists, creating it if necessary.

    Args:
        path: Path whose parent directory should exist

    Raises:
        PermissionError: If directory cannot be created
    """
    parent = path.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(f"Cannot create directory {parent}: {e}")


def confirm_overwrite(path: Path) -> bool:
    """
    Interactive prompt to confirm file overwrite.

    Args:
        path: Path of file that would be overwritten

    Returns:
        True if user confirms, False otherwise
    """
    return Confirm.ask(
        f"[yellow]⚠️  File '{path}' already exists. Overwrite?[/yellow]",
        default=False
    )


def get_file_size(content: str) -> str:
    """
    Get human-readable file size for content.

    Args:
        content: String content to measure

    Returns:
        Human-readable size string (e.g., "1.2 KB")
    """
    size_bytes = len(content.encode('utf-8'))

    for unit in ['B', 'KB', 'MB']:
        if size_bytes < 1024.0:
            if unit == 'B':
                return f"{size_bytes} {unit}"
            else:
                return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.1f} GB"


def write_text(path: Union[Path, str], content: str, force: bool = False) -> None:
    """
    Write text content to a file.

    Args:
        path: Path where file should be written (Path object or string)
        content: Text content to write
        force: If True, overwrite without asking

    Raises:
        typer.Abort: If user cancels overwrite
        PermissionError: If file cannot be written
        ValueError: If content is empty
    """
    if not content:
        raise ValueError("Cannot write empty content")

    # Convert string path to Path object if needed
    if not isinstance(path, Path):
        path = Path(path)

    # Make path absolute to avoid confusion
    path = path.resolve()

    # Check for dangerous paths
    if ".." in str(path):
        raise ValueError("Path traversal not allowed")

    # Ensure parent directory exists
    ensure_parent_dir(path)

    # Handle overwrite confirmation
    if check_exists(path) and not force:
        if not confirm_overwrite(path):
            console.print("[yellow]Operation cancelled.[/yellow]")
            raise typer.Abort()

    # Write the file
    try:
        # Handle JSON specially for pretty printing
        if path.suffix.lower() == '.json':
            try:
                # Try to parse and pretty-print JSON
                json_data = json.loads(content)
                content = json.dumps(json_data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                # If it's not valid JSON, write as-is
                pass

        path.write_text(content, encoding='utf-8')

    except PermissionError as e:
        raise PermissionError(f"Cannot write to {path}: {e}")
    except Exception as e:
        raise Exception(f"Failed to write file: {e}")


def validate_filename(filename: str) -> bool:
    """
    Validate that filename is safe to use.

    Args:
        filename: Filename to validate

    Returns:
        True if valid, False otherwise
    """
    # Check for invalid characters
    invalid_chars = ['/', '\\', '\0', ':', '*', '?', '"', '<', '>', '|']
    if any(char in filename for char in invalid_chars):
        return False

    # Check for path traversal
    if '..' in filename:
        return False

    # Check for hidden files (optional, could allow these)
    # if filename.startswith('.'):
    #     return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Replace invalid characters with underscore
    invalid_chars = ['/', '\\', '\0', ':', '*', '?', '"', '<', '>', '|']
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')

    # Remove path traversal attempts
    sanitized = sanitized.replace('..', '_')

    # Ensure it's not empty after sanitization
    if not sanitized or sanitized.strip() == '':
        sanitized = 'clipboard_content'

    return sanitized