"""Custom exceptions for ClipDrop."""


class ClipDropError(Exception):
    """Base exception for all ClipDrop errors."""
    pass


class ClipboardError(ClipDropError):
    """Exception for clipboard-related errors."""
    pass


class ClipboardEmptyError(ClipboardError):
    """Exception raised when clipboard is empty."""
    def __init__(self, message="Clipboard is empty"):
        self.message = message
        super().__init__(self.message)


class ClipboardAccessError(ClipboardError):
    """Exception raised when clipboard cannot be accessed."""
    def __init__(self, message="Cannot access clipboard", original_error=None):
        self.message = message
        self.original_error = original_error
        if original_error:
            message = f"{message}: {str(original_error)}"
        super().__init__(message)


class FileWriteError(ClipDropError):
    """Exception for file writing errors."""
    pass


class FilePermissionError(FileWriteError):
    """Exception raised for file permission issues."""
    def __init__(self, path, message=None):
        self.path = path
        if message is None:
            message = f"Permission denied: Cannot write to {path}"
        super().__init__(message)


class FileExistsError(FileWriteError):
    """Exception raised when file exists and overwrite is not allowed."""
    def __init__(self, path):
        self.path = path
        message = f"File already exists: {path}"
        super().__init__(message)


class ValidationError(ClipDropError):
    """Exception for input validation errors."""
    pass


class InvalidFilenameError(ValidationError):
    """Exception raised for invalid filenames."""
    def __init__(self, filename, reason=None):
        self.filename = filename
        message = f"Invalid filename: {filename}"
        if reason:
            message = f"{message} - {reason}"
        super().__init__(message)


class PathTraversalError(ValidationError):
    """Exception raised for path traversal attempts."""
    def __init__(self, path):
        self.path = path
        message = f"Path traversal not allowed: {path}"
        super().__init__(message)


class ContentError(ClipDropError):
    """Exception for content-related errors."""
    pass


class EmptyContentError(ContentError):
    """Exception raised when content is empty."""
    def __init__(self, message="Cannot process empty content"):
        super().__init__(message)


class ContentTooLargeError(ContentError):
    """Exception raised when content exceeds size limits."""
    def __init__(self, size, max_size):
        self.size = size
        self.max_size = max_size
        message = f"Content too large: {size} bytes (max: {max_size} bytes)"
        super().__init__(message)


class FormatDetectionError(ClipDropError):
    """Exception for format detection failures."""
    def __init__(self, message="Cannot detect content format"):
        super().__init__(message)


# Image-related exceptions
class ImageClipboardError(ClipboardError):
    """Raised when there's an error accessing image from clipboard."""
    def __init__(self, message="Cannot access image from clipboard", original_error=None):
        self.original_error = original_error
        if original_error:
            message = f"{message}: {str(original_error)}"
        super().__init__(message)


class ImageFormatError(ClipDropError):
    """Raised when image format is unsupported or invalid."""
    def __init__(self, format: str = None):
        if format:
            message = f"Unsupported image format: {format}"
        else:
            message = "Invalid or unsupported image format"
        super().__init__(message)


class ImageSaveError(FileWriteError):
    """Raised when image cannot be saved to file."""
    def __init__(self, path: str, reason: str = None):
        self.path = path
        if reason:
            message = f"Cannot save image to {path}: {reason}"
        else:
            message = f"Cannot save image to {path}"
        super().__init__(message)