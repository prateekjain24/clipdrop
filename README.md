# ClipDrop

Save clipboard content to files with one command. ClipDrop automatically detects formats (JSON, Markdown, CSV), suggests appropriate extensions, prevents accidental overwrites, and provides rich visual feedback.

## Features

- **Smart Format Detection**: Automatically detects JSON, Markdown, and CSV content
- **Extension Auto-Suggestion**: No extension? ClipDrop suggests the right one
- **Safe by Default**: Interactive overwrite protection (bypass with `--force`)
- **Preview Mode**: See content before saving with syntax highlighting
- **Rich CLI**: Beautiful, informative output with colors and icons
- **Performance**: Caches clipboard content for speed (<200ms operations)
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
clipdrop notes              # → notes.txt
clipdrop data               # → data.json (if JSON detected)
clipdrop readme             # → readme.md (if Markdown detected)

# Specify extension explicitly
clipdrop report.pdf
clipdrop config.yaml
```

### Options
```bash
# Force overwrite without confirmation
clipdrop notes.txt --force
clipdrop notes.txt -f

# Preview content before saving (with syntax highlighting)
clipdrop data.json --preview
clipdrop data.json -p

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

### Completed Features (Sprint 1 & 2) ✅
- Project setup with uv package manager
- CLI skeleton with Typer
- Clipboard text reading with caching
- File writing with atomic operations
- Extension detection for common formats
- Overwrite protection
- Rich success/error messages
- JSON, Markdown, CSV format detection
- Path validation and sanitization
- Comprehensive test suite (64+ tests)
- Preview mode with syntax highlighting

### Enhanced Features 🌟
- Custom exception hierarchy for better error handling
- Advanced clipboard operations (stats, monitoring, binary detection)
- Enhanced file operations (atomic writes, backups, compression)
- Performance optimizations with content caching

### Upcoming Features (Sprint 3) 🔄
- Image clipboard support (PNG, JPG)
- Content priority logic (image vs text)
- Force text mode flag

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
│   ├── clipboard.py       # Clipboard operations
│   ├── files.py           # File operations
│   ├── detect.py          # Format detection
│   └── exceptions.py      # Custom exceptions
├── tests/                 # Comprehensive test suite
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

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📚 Documentation

- [Product Requirements](requirement.md) - Original PRD
- [Implementation Plan](IMP.md) - Detailed implementation status
- [API Documentation](https://github.com/prateekjain24/clipdrop/wiki) - Coming soon

## Issues

Found a bug or have a feature request? Please open an issue on [GitHub Issues](https://github.com/prateekjain24/clipdrop/issues).

---

**Current Version**: 0.1.0 | **Status**: Active Development | **Sprint**: 2/4 Complete
