"""Pytest configuration and fixtures for ClipDrop tests."""

import json
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from unittest.mock import patch
from PIL import Image
import io


@pytest.fixture
def mock_clipboard():
    """Mock clipboard for testing without actual clipboard access."""
    # Clear clipboard cache before and after tests
    import clipdrop.clipboard as cb

    # Save original cache settings
    original_cache = cb._clipboard_cache.copy()

    # Clear cache before test
    cb._clipboard_cache['content'] = None
    cb._clipboard_cache['timestamp'] = 0

    with patch('pyperclip.paste') as mock_paste, \
         patch('pyperclip.copy') as mock_copy:
        clipboard_content = ""

        def paste_side_effect():
            return clipboard_content

        def copy_side_effect(content):
            nonlocal clipboard_content
            clipboard_content = content
            # Also clear cache when setting content
            cb._clipboard_cache['content'] = None
            cb._clipboard_cache['timestamp'] = 0
            return None

        mock_paste.side_effect = paste_side_effect
        mock_copy.side_effect = copy_side_effect

        yield {
            'paste': mock_paste,
            'copy': mock_copy,
            'set_content': lambda content: copy_side_effect(content),
            'get_content': lambda: clipboard_content
        }

    # Restore original cache after test
    cb._clipboard_cache.update(original_cache)


@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    """Create a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_text() -> str:
    """Sample plain text content."""
    return "Hello, this is a test content for ClipDrop!"


@pytest.fixture
def sample_json() -> str:
    """Sample JSON content."""
    data = {
        "name": "ClipDrop Test",
        "version": "1.0.0",
        "features": ["clipboard", "files", "detection"],
        "nested": {
            "key": "value",
            "number": 42
        }
    }
    return json.dumps(data)


@pytest.fixture
def sample_markdown() -> str:
    """Sample Markdown content."""
    return """# Test Document

## Features
- **Bold text** and *italic*
- [Links](https://example.com)
- `Code snippets`

### Code Block
```python
def hello():
    print("Hello, World!")
```

> This is a blockquote

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
"""


@pytest.fixture
def sample_csv() -> str:
    """Sample CSV content."""
    return """Name,Age,City,Country
Alice Johnson,28,New York,USA
Bob Smith,35,London,UK
Charlie Brown,42,Toronto,Canada
Diana Prince,31,Sydney,Australia"""


@pytest.fixture
def sample_unicode() -> str:
    """Sample content with Unicode characters."""
    return "Hello 世界! 🌍 Здравствуй мир! مرحبا بالعالم"


@pytest.fixture
def sample_large_text() -> str:
    """Generate large text content for performance testing."""
    base_text = "This is a line of text for testing large content handling.\n"
    return base_text * 10000  # ~600KB


@pytest.fixture
def mock_rich_console():
    """Mock Rich console for testing output."""
    with patch('clipdrop.files.console') as mock_console:
        yield mock_console


@pytest.fixture
def mock_confirm_prompt():
    """Mock Rich Confirm prompt."""
    with patch('clipdrop.files.Confirm.ask') as mock_confirm:
        yield mock_confirm


@pytest.fixture
def performance_timer():
    """Simple timer for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()
            return self.elapsed

        @property
        def elapsed(self):
            if self.start_time is None:
                return 0
            if self.end_time is None:
                return time.perf_counter() - self.start_time
            return self.end_time - self.start_time

    return Timer()


@pytest.fixture
def sample_files(temp_directory: Path) -> dict:
    """Create sample files in temp directory."""
    files = {}

    # Create text file
    text_file = temp_directory / "sample.txt"
    text_file.write_text("Sample text content")
    files['text'] = text_file

    # Create JSON file
    json_file = temp_directory / "data.json"
    json_file.write_text('{"key": "value"}')
    files['json'] = json_file

    # Create Markdown file
    md_file = temp_directory / "readme.md"
    md_file.write_text("# Sample Markdown")
    files['markdown'] = md_file

    # Create CSV file
    csv_file = temp_directory / "data.csv"
    csv_file.write_text("col1,col2\nval1,val2")
    files['csv'] = csv_file

    return files


@pytest.fixture
def clean_imports():
    """Clean up imports to ensure isolated testing."""
    import sys
    modules_to_remove = [
        mod for mod in sys.modules
        if mod.startswith('clipdrop')
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]
    yield
    # Cleanup after test if needed


# Image-related fixtures
@pytest.fixture
def sample_image():
    """Create a sample PIL Image for testing."""
    img = Image.new('RGB', (100, 100), color='red')
    return img


@pytest.fixture
def sample_image_with_transparency():
    """Create a sample PIL Image with transparency."""
    img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
    return img


@pytest.fixture
def mock_image_clipboard():
    """Mock image clipboard for testing."""
    # Clear image cache before and after tests
    import clipdrop.clipboard as cb

    # Save original cache settings
    original_cache = cb._image_cache.copy() if hasattr(cb, '_image_cache') else {}

    # Clear cache before test
    if hasattr(cb, '_image_cache'):
        cb._image_cache['image'] = None
        cb._image_cache['timestamp'] = 0

    with patch('PIL.ImageGrab.grabclipboard') as mock_grab:
        # Use a container to hold the image so we can modify it
        clipboard_state = {'image': None}

        def grab_side_effect():
            return clipboard_state['image']

        def set_image(img):
            clipboard_state['image'] = img
            # Also clear the cache to ensure fresh read
            if hasattr(cb, '_image_cache'):
                cb._image_cache['image'] = None
                cb._image_cache['timestamp'] = 0

        mock_grab.side_effect = grab_side_effect

        yield {
            'grab': mock_grab,
            'set_image': set_image,
            'get_image': lambda: clipboard_state['image']
        }

    # Restore original cache after test
    if hasattr(cb, '_image_cache'):
        cb._image_cache.update(original_cache)


@pytest.fixture
def sample_image_bytes():
    """Get bytes representation of a sample image."""
    img = Image.new('RGB', (50, 50), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.fixture
def various_format_images():
    """Create images that would be saved in different formats."""
    return {
        'rgb': Image.new('RGB', (100, 100), color='red'),
        'rgba': Image.new('RGBA', (100, 100), color=(0, 255, 0, 128)),
        'grayscale': Image.new('L', (100, 100), color=128),
        'palette': Image.new('P', (100, 100))
    }