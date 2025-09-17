"""Image operations module for ClipDrop."""

from pathlib import Path
from typing import Union, Optional, Dict, Any, Tuple
from PIL import Image

from clipdrop.exceptions import (
    ImageSaveError,
    ImageFormatError,
    InvalidFilenameError
)


# Supported image formats
SUPPORTED_FORMATS = {
    '.png': 'PNG',
    '.jpg': 'JPEG',
    '.jpeg': 'JPEG',
    '.gif': 'GIF',
    '.bmp': 'BMP',
    '.tiff': 'TIFF',
    '.tif': 'TIFF',
    '.webp': 'WEBP',
    '.ico': 'ICO'
}

# Default save options for different formats
FORMAT_OPTIONS = {
    'PNG': {'optimize': True, 'compress_level': 9},
    'JPEG': {'quality': 95, 'optimize': True, 'progressive': True},
    'GIF': {'optimize': True},
    'BMP': {},
    'TIFF': {'compression': 'tiff_lzw'},
    'WEBP': {'quality': 90, 'method': 6},
    'ICO': {}
}


def detect_format_from_extension(path: Union[Path, str]) -> Optional[str]:
    """
    Detect image format from file extension.

    Args:
        path: File path with extension

    Returns:
        Format string (e.g., 'PNG', 'JPEG') or None if unknown
    """
    if not isinstance(path, Path):
        path = Path(path)

    suffix = path.suffix.lower()
    return SUPPORTED_FORMATS.get(suffix)


def is_image_extension(filename: str) -> bool:
    """
    Check if filename has an image extension.

    Args:
        filename: Filename to check

    Returns:
        True if has image extension, False otherwise
    """
    path = Path(filename)
    return path.suffix.lower() in SUPPORTED_FORMATS


def optimize_image(image: Image.Image, format: str) -> Dict[str, Any]:
    """
    Get optimized save options for the given format.

    Args:
        image: PIL Image to optimize
        format: Target format (e.g., 'PNG', 'JPEG')

    Returns:
        Dictionary of save options
    """
    options = FORMAT_OPTIONS.get(format, {}).copy()

    # Special handling for certain cases
    if format == 'JPEG' and image.mode in ('RGBA', 'LA', 'P'):
        # Convert RGBA to RGB for JPEG (doesn't support transparency)
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        return options, rgb_image

    if format == 'GIF' and image.mode != 'P':
        # Convert to palette mode for GIF if needed
        if image.mode == 'RGBA':
            # Preserve transparency
            image = image.convert('P', palette=Image.ADAPTIVE, colors=256)
        else:
            image = image.convert('P', palette=Image.ADAPTIVE)
        return options, image

    return options, image


def write_image(
    path: Union[Path, str],
    image: Image.Image,
    format: str = None,
    optimize: bool = True,
    force: bool = False
) -> Dict[str, Any]:
    """
    Write image to file with optimization.

    Args:
        path: Path where image should be saved
        image: PIL Image object to save
        format: Image format (auto-detected if None)
        optimize: Whether to optimize the image
        force: Whether to overwrite existing files

    Returns:
        Dictionary with save info (path, format, size, dimensions)

    Raises:
        ImageSaveError: If image cannot be saved
        ImageFormatError: If format is unsupported
    """
    if not isinstance(path, Path):
        path = Path(path)

    # Detect format from extension if not provided
    if format is None:
        format = detect_format_from_extension(path)
        if format is None:
            # Default to PNG if no extension
            format = 'PNG'
            if not path.suffix:
                path = path.with_suffix('.png')

    # Validate format
    if format not in FORMAT_OPTIONS:
        raise ImageFormatError(format)

    # Check if file exists
    if path.exists() and not force:
        from clipdrop.files import confirm_overwrite
        if not confirm_overwrite(path):
            raise ImageSaveError(str(path), "User cancelled overwrite")

    try:
        # Get optimization options
        save_options, processed_image = optimize_image(image, format) if optimize else ({}, image)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save the image
        processed_image.save(path, format=format, **save_options)

        # Get file info
        file_size = path.stat().st_size
        return {
            'path': str(path),
            'format': format,
            'width': image.width,
            'height': image.height,
            'dimensions': f"{image.width}x{image.height}",
            'file_size': file_size,
            'file_size_human': format_file_size(file_size),
            'mode': image.mode
        }

    except Exception as e:
        raise ImageSaveError(str(path), str(e))


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable form.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            if unit == 'B':
                return f"{size_bytes} {unit}"
            else:
                return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_image_metadata(image_path: Union[Path, str]) -> Dict[str, Any]:
    """
    Get metadata from an image file.

    Args:
        image_path: Path to image file

    Returns:
        Dictionary with image metadata

    Raises:
        ImageSaveError: If image cannot be read
    """
    if not isinstance(image_path, Path):
        image_path = Path(image_path)

    if not image_path.exists():
        raise ImageSaveError(str(image_path), "File not found")

    try:
        with Image.open(image_path) as img:
            file_size = image_path.stat().st_size
            return {
                'path': str(image_path),
                'width': img.width,
                'height': img.height,
                'dimensions': f"{img.width}x{img.height}",
                'format': img.format,
                'mode': img.mode,
                'file_size': file_size,
                'file_size_human': format_file_size(file_size),
                'has_transparency': img.mode in ('RGBA', 'LA', 'P'),
                'info': img.info  # Additional metadata (EXIF, etc.)
            }
    except Exception as e:
        raise ImageSaveError(str(image_path), f"Cannot read image: {e}")


def suggest_image_filename(image: Image.Image = None) -> str:
    """
    Suggest a filename for an image based on its properties.

    Args:
        image: Optional PIL Image object

    Returns:
        Suggested filename with extension
    """
    if image and image.format:
        # Use the image's original format
        ext = next((k for k, v in SUPPORTED_FORMATS.items() if v == image.format), '.png')
        return f"clipboard_image{ext}"

    return "clipboard_image.png"


def add_image_extension(filename: str, image: Image.Image = None) -> str:
    """
    Add appropriate image extension to filename if missing.

    Args:
        filename: Original filename
        image: Optional PIL Image to detect format from

    Returns:
        Filename with appropriate extension
    """
    path = Path(filename)

    # If already has an image extension, keep it
    if path.suffix.lower() in SUPPORTED_FORMATS:
        return filename

    # If image has format info, use it
    if image and image.format:
        ext = next((k for k, v in SUPPORTED_FORMATS.items() if v == image.format), '.png')
        return f"{filename}{ext}"

    # Default to PNG
    return f"{filename}.png"