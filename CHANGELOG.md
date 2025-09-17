# Changelog

All notable changes to ClipDrop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-17

### 🎉 Major Release - Image Support & Polish

### Added
- **Full image clipboard support** - Save screenshots and copied images directly
  - Support for PNG, JPG, GIF, BMP, WebP, TIFF formats
  - Automatic image optimization and compression
  - Smart format conversion (RGBA→RGB for JPEG)
  - Image dimensions in success messages
- **Enhanced user experience**
  - Rich, detailed help documentation with examples
  - Friendly, actionable error messages with solutions
  - Beautiful colored output with emoji indicators
  - Content preview for images showing dimensions
- **Content priority logic**
  - Intelligently handles mixed clipboard content (image + text)
  - `--text` flag to force text mode when both exist
- **Performance optimizations**
  - Content caching for faster operations
  - All operations under 200ms for typical use
  - Memory-efficient handling of large files
- **Developer features**
  - Comprehensive test suite (89 tests)
  - Performance benchmarking suite
  - Custom exception hierarchy
  - Error helper system

### Enhanced
- Help text now includes rich examples and workflows
- Error messages provide specific solutions and tips
- File operations with atomic writes and backups
- Success messages with format detection info
- Preview mode supports both text and images

### Fixed
- Path traversal security improvements
- Better handling of invalid filenames
- Improved clipboard access error handling
- More robust format detection

### Technical
- Added Pillow dependency for image handling
- New modules: `images.py`, `error_helpers.py`
- Performance tests ensuring <200ms operations
- Enhanced clipboard module with image support

## [0.1.0] - 2025-01-16

### Initial Release

### Features
- Save clipboard text to files with one command
- Smart format detection (JSON, Markdown, CSV)
- Automatic extension suggestion
- Overwrite protection with confirmation
- Force mode with `--force` flag
- Preview mode with `--preview` flag
- Rich CLI with colors and formatting
- Path validation and security
- Unicode support
- JSON pretty-printing

### Technical
- Built with Typer CLI framework
- Uses pyperclip for clipboard access
- Rich terminal formatting
- Modern Python packaging with uv
- Support for Python 3.10-3.13
- Comprehensive test coverage

---

## Roadmap

### Future Releases
- [ ] Cross-platform support (Windows, Linux)
- [ ] Configuration file support
- [ ] Multiple clipboard history
- [ ] Cloud storage integration
- [ ] Shell completions
- [ ] Plugin system for custom formats