# ClipDrop

Save clipboard content to files with one command. ClipDrop automatically detects formats (JSON, Markdown, CSV), suggests appropriate extensions, prevents accidental overwrites, and provides rich visual feedback.

## Features

- **Image Support**: Save images from clipboard (PNG, JPG, GIF, BMP, WebP) 📷
- **Smart Format Detection**: Automatically detects JSON, Markdown, CSV, and image formats
- **Extension Auto-Suggestion**: No extension? ClipDrop suggests the right one
- **Content Priority**: Intelligently handles mixed content (image + text)
- **Safe by Default**: Interactive overwrite protection (bypass with `--force`)
- **Preview Mode**: See content before saving (text with syntax highlighting, images with dimensions)
- **Rich CLI**: Beautiful, informative output with colors and icons
- **Performance**: Caches clipboard content for speed (<200ms operations)
- **Image Optimization**: Automatic compression for PNG/JPEG formats
- **Large File Support**: Handles files up to 100MB with size warnings
- **Unicode Support**: Full international character support

## 📦 Installation

### Using uv (Recommended)
```bash
# Install from PyPI (when released)
uv add clipdrop

# Install from local checkout
uv pip install -e .
```

### Using pip
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### Basic Usage
```bash
# Save clipboard to file (auto-detects format)
clipdrop notes              # → notes.txt (text)
clipdrop screenshot         # → screenshot.png (image)
clipdrop data               # → data.json (if JSON detected)
clipdrop readme             # → readme.md (if Markdown detected)

# Specify extension explicitly
clipdrop photo.jpg          # Save as JPEG
clipdrop diagram.png        # Save as PNG
clipdrop config.yaml        # Save as YAML
```

### Options
```bash
# Force overwrite without confirmation
clipdrop notes.txt --force
clipdrop notes.txt -f

# Preview content before saving (with syntax highlighting for text, dimensions for images)
clipdrop data.json --preview
clipdrop screenshot.png -p

# Force text mode when both image and text are in clipboard
clipdrop notes.txt --text
clipdrop notes.txt -t

# Show version
clipdrop --version

# Get help
clipdrop --help
```

### Examples

#### Save copied text
```bash
# Copy some text, then:
clipdrop notes
# ✅ Saved 156 B to notes.txt
```

#### Auto-detect JSON and pretty-print
```bash
# Copy JSON data, then:
clipdrop config
# 📝 Auto-detected format. Saving as: config.json
# ✅ Saved 2.3 KB to config.json
```

#### Preview with syntax highlighting
```bash
clipdrop script.py --preview
# Shows colored preview with line numbers
# Save this content? [Y/n]:
```

#### Save copied image
```bash
# Copy an image (screenshot, etc.), then:
clipdrop screenshot
# 📷 Auto-detected image format. Saving as: screenshot.png
# ✅ Saved image (1920x1080, 245.3 KB) to screenshot.png
```

#### Handle mixed content
```bash
# When both image and text are in clipboard:
clipdrop content          # Saves image by default
clipdrop content --text   # Forces text mode
```

## 🔧 Development

### Setup Development Environment
```bash
# Clone the repository
git clone https://github.com/prateekjain24/clipdrop.git
cd clipdrop

# Install with dev dependencies
uv pip install -e .[dev]
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov --cov-report=term-missing

# Run specific test file
pytest tests/test_clipboard.py
```

### Code Quality
```bash
# Format code
black src tests

# Lint code
ruff check .

# Type checking (if using mypy)
mypy src
```

## Project Status

### Completed Features (Sprints 1-3) ✅
- Project setup with uv package manager
- CLI skeleton with Typer
- Clipboard text and image reading with caching
- File writing with atomic operations
- Extension detection for text and image formats
- Overwrite protection
- Rich success/error messages
- JSON, Markdown, CSV format detection
- Path validation and sanitization
- **Image clipboard support** (PNG, JPG, GIF, BMP, WebP)
- **Content priority logic** (image > text, with --text override)
- **Image optimization** with format-specific compression
- Comprehensive test suite (89 tests)
- Preview mode with syntax highlighting (text) and dimensions (images)

### Enhanced Features 🌟
- Custom exception hierarchy for better error handling
- Advanced clipboard operations (stats, monitoring, binary detection, images)
- Enhanced file operations (atomic writes, backups, compression)
- Image format conversion (RGBA→RGB for JPEG)
- Performance optimizations with content caching
- Smart format detection for images and text

### Future Roadmap (Sprint 4) 🚧
- PyPI package release
- Performance profiling for large files
- Cross-platform support (Windows, Linux)
- Configuration file support

## 🏗️ Architecture

```
clipdrop/
├── src/clipdrop/
│   ├── __init__.py         # Version management
│   ├── main.py            # CLI entry point
│   ├── clipboard.py       # Clipboard operations (text + images)
│   ├── files.py           # File operations
│   ├── images.py          # Image-specific operations
│   ├── detect.py          # Format detection
│   └── exceptions.py      # Custom exceptions
├── tests/                 # Comprehensive test suite (89 tests)
│   ├── test_clipboard.py  # 27 tests
│   ├── test_files.py      # 37 tests
│   └── test_images.py     # 25 tests
├── pyproject.toml         # Modern Python packaging
└── README.md              # This file
```

## 📝 Requirements

- **Python**: 3.10, 3.11, 3.12, or 3.13
- **OS**: macOS 10.15+ (initial target)
- **Dependencies**:
  - typer[all] >= 0.17.4
  - rich >= 14.1.0
  - pyperclip >= 1.9.0
  - Pillow >= 11.3.0

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.



## Issues

Found a bug or have a feature request? Please open an issue on [GitHub Issues](https://github.com/prateekjain24/clipdrop/issues).

---

**Current Version**: 0.1.0 | **Status**: Active Development 
