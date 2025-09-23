"""File operations module for ClipDrop."""

import json
import gzip
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Union, Optional
import typer
from rich.console import Console
from rich.prompt import Confirm

from clipdrop.exceptions import (
    FilePermissionError,
    FileExistsError as ClipDropFileExistsError,
    EmptyContentError
)

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

    # Check for dangerous paths BEFORE resolving
    if ".." in str(path):
        raise ValueError("Path traversal not allowed")

    # Make path absolute to avoid confusion
    path = path.resolve()

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


def is_image_extension(filename: str) -> bool:
    """
    Check if filename has an image extension.

    Args:
        filename: Filename to check

    Returns:
        True if has image extension, False otherwise
    """
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico'}
    path = Path(filename)
    return path.suffix.lower() in image_extensions


def get_file_size_human(size_bytes: int) -> str:
    """
    Convert file size in bytes to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


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
    # Also handle cases where everything becomes underscores
    if not sanitized or sanitized.strip() == '' or all(c == '_' for c in sanitized):
        sanitized = 'clipboard_content'

    return sanitized


def append_text_to_file(path: Union[Path, str], content: str, separator: Optional[str] = None) -> int:
    """
    Append text content to an existing file or create new if doesn't exist.

    Args:
        path: Path where content should be appended
        content: Text content to append
        separator: Optional separator between existing and new content
                  If None, smart separator is chosen based on file extension

    Returns:
        Number of bytes appended

    Raises:
        ValueError: If content is empty
        PermissionError: If file cannot be written
    """
    if not content:
        raise ValueError("Cannot append empty content")

    # Convert string path to Path object if needed
    if not isinstance(path, Path):
        path = Path(path)

    # Ensure parent directory exists
    ensure_parent_dir(path)

    # Determine smart separator if not provided
    if separator is None:
        ext = path.suffix.lower()
        if ext == '.md':
            separator = "\n\n---\n\n"  # Markdown separator
        elif ext == '.log':
            # Add timestamp for log files
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            separator = f"\n[{timestamp}]\n"
        elif ext in ['.json', '.csv', '.xml']:
            separator = "\n"  # Minimal separator for structured files
        else:
            separator = "\n\n"  # Default double newline

    # Check if file exists
    if path.exists():
        # Read existing content to ensure proper append
        try:
            with open(path, 'r', encoding='utf-8') as f:
                existing_content = f.read()

            # Add separator only if file has content
            if existing_content and not existing_content.endswith('\n'):
                final_content = existing_content + separator + content
            elif existing_content:
                # File ends with newline, adjust separator
                if separator.startswith('\n'):
                    final_content = existing_content + separator[1:] + content
                else:
                    final_content = existing_content + separator + content
            else:
                # Empty file
                final_content = content

        except Exception as e:
            raise PermissionError(f"Cannot read file for appending: {e}")
    else:
        # New file, no separator needed
        final_content = content

    # Write atomically using temp file
    try:
        # Create temp file in same directory as target
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=path.parent,
            delete=False,
            suffix='.tmp'
        ) as tmp_file:
            tmp_file.write(final_content)
            tmp_path = Path(tmp_file.name)

        # Atomic rename
        tmp_path.replace(path)

        # Calculate and return bytes appended (including separator)
        bytes_appended = len(content.encode('utf-8'))
        if path.exists() and separator:
            bytes_appended += len(separator.encode('utf-8'))

        return bytes_appended

    except Exception as e:
        # Clean up temp file on error
        if 'tmp_path' in locals() and tmp_path.exists():
            tmp_path.unlink()
        raise PermissionError(f"Cannot append to file: {e}")


def write_text_file(path: Union[Path, str], content: str, force: bool = False) -> None:
    """
    Write text content to a file (alias for consistency with ticket).

    Args:
        path: Path where file should be written
        content: Text content to write
        force: If True, overwrite without asking

    Raises:
        Same as write_text()
    """
    write_text(path, content, force)


def write_atomic(path: Union[Path, str], content: str, force: bool = False) -> None:
    """
    Atomically write content to a file (write to temp, then rename).

    This ensures the file is either fully written or not written at all,
    preventing partial writes in case of errors.

    Args:
        path: Path where file should be written
        content: Text content to write
        force: If True, overwrite without asking

    Raises:
        Same as write_text(), plus:
        OSError: If atomic rename fails
    """
    if not content:
        raise EmptyContentError()

    if not isinstance(path, Path):
        path = Path(path)

    path = path.resolve()

    # Check overwrite permission first
    if check_exists(path) and not force:
        if not confirm_overwrite(path):
            console.print("[yellow]Operation cancelled.[/yellow]")
            raise typer.Abort()

    # Ensure parent directory exists
    ensure_parent_dir(path)

    # Write to temporary file in same directory (for atomic rename)
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=path.parent,
            delete=False,
            suffix='.tmp'
        ) as temp_file:
            temp_file.write(content)
            temp_file.flush()

        # Atomic rename
        temp_path = Path(temp_file.name)
        temp_path.replace(path)

    except Exception as e:
        # Clean up temp file if it exists
        if temp_file and Path(temp_file.name).exists():
            Path(temp_file.name).unlink()
        raise Exception(f"Atomic write failed: {e}")


def backup_file(path: Union[Path, str]) -> Optional[Path]:
    """
    Create a backup of an existing file.

    Args:
        path: Path of file to backup

    Returns:
        Path of backup file, or None if original doesn't exist

    Raises:
        PermissionError: If backup cannot be created
    """
    if not isinstance(path, Path):
        path = Path(path)

    if not path.exists():
        return None

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.parent / f"{path.stem}.backup.{timestamp}{path.suffix}"

    try:
        shutil.copy2(path, backup_path)
        return backup_path
    except PermissionError as e:
        raise FilePermissionError(backup_path, f"Cannot create backup: {e}")


def get_safe_filename(base_path: Union[Path, str], max_attempts: int = 100) -> Path:
    """
    Generate a unique filename if the original exists.

    Args:
        base_path: Base path for the file
        max_attempts: Maximum number of attempts to find unique name

    Returns:
        Safe path that doesn't exist

    Raises:
        FileExistsError: If cannot find unique filename
    """
    if not isinstance(base_path, Path):
        base_path = Path(base_path)

    if not base_path.exists():
        return base_path

    # Try adding numbers
    for i in range(1, max_attempts + 1):
        new_path = base_path.parent / f"{base_path.stem}_{i}{base_path.suffix}"
        if not new_path.exists():
            return new_path

    raise ClipDropFileExistsError(f"Cannot find unique filename after {max_attempts} attempts")


def write_with_compression(
    path: Union[Path, str],
    content: str,
    compress: bool = False,
    force: bool = False
) -> None:
    """
    Write content to file with optional gzip compression.

    Args:
        path: Path where file should be written
        content: Text content to write
        compress: If True, compress with gzip
        force: If True, overwrite without asking

    Raises:
        Same as write_text()
    """
    if not isinstance(path, Path):
        path = Path(path)

    if compress:
        # Add .gz extension if not present
        if not str(path).endswith('.gz'):
            path = Path(str(path) + '.gz')

        # Check overwrite permission
        if check_exists(path) and not force:
            if not confirm_overwrite(path):
                console.print("[yellow]Operation cancelled.[/yellow]")
                raise typer.Abort()

        # Ensure parent directory exists
        ensure_parent_dir(path)

        # Write compressed
        with gzip.open(path, 'wt', encoding='utf-8') as f:
            f.write(content)
    else:
        # Regular write
        write_text(path, content, force)


def append_to_file(
    path: Union[Path, str],
    content: str,
    create_if_missing: bool = True
) -> None:
    """
    Append content to an existing file.

    Args:
        path: Path of file to append to
        content: Text content to append
        create_if_missing: If True, create file if it doesn't exist

    Raises:
        FileNotFoundError: If file doesn't exist and create_if_missing is False
        PermissionError: If file cannot be written
    """
    if not isinstance(path, Path):
        path = Path(path)

    if not path.exists() and not create_if_missing:
        raise FileNotFoundError(f"File not found: {path}")

    try:
        # Ensure parent directory exists
        ensure_parent_dir(path)

        # Append to file
        with path.open('a', encoding='utf-8') as f:
            f.write(content)
    except PermissionError as e:
        raise FilePermissionError(path, f"Cannot append to file: {e}")


def get_file_metadata(path: Union[Path, str]) -> dict:
    """
    Get metadata about a file.

    Args:
        path: Path of file

    Returns:
        Dictionary with file metadata:
        - exists: Whether file exists
        - size: Size in bytes
        - size_human: Human-readable size
        - modified: Last modified timestamp
        - created: Creation timestamp (if available)
        - is_file: Whether it's a regular file
        - is_dir: Whether it's a directory

    """
    if not isinstance(path, Path):
        path = Path(path)

    if not path.exists():
        return {
            'exists': False,
            'size': 0,
            'size_human': '0 B',
            'modified': None,
            'created': None,
            'is_file': False,
            'is_dir': False
        }

    stat = path.stat()
    size_human = get_file_size("x" * stat.st_size)  # Reuse size formatting

    return {
        'exists': True,
        'size': stat.st_size,
        'size_human': size_human,
        'modified': datetime.fromtimestamp(stat.st_mtime),
        'created': datetime.fromtimestamp(stat.st_ctime) if hasattr(stat, 'st_ctime') else None,
        'is_file': path.is_file(),
        'is_dir': path.is_dir()
    }