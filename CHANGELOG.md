# Changelog

All notable changes to ClipDrop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-01-17

### 🌐 HTML Clipboard Support & Web Content

### Added
- **HTML clipboard parsing from web content**
  - Automatically detects HTML content from browser copies
  - Extracts text and embedded images from web pages
  - Downloads external images from URLs
  - Processes base64 embedded images
  - Creates PDFs preserving original content structure
- **Enhanced mixed content detection**
  - Recognizes HTML clipboard format (rich content)
  - Improved content type detection for web copies
  - Better handling of Medium, Wikipedia, and other web articles
- **26 comprehensive tests for HTML parsing**
  - Full coverage of HTML extraction functionality
  - Image download and processing tests
  - Base64 image extraction tests
- **New dependencies for web content**
  - BeautifulSoup4 for HTML parsing
  - Requests for image downloads
  - lxml for efficient HTML processing

### Changed
- Content type detection now prioritizes HTML mixed content
- PDF generation preserves exact content order (WYCWYG)
- Removed automatic title addition to PDFs
- Fixed performance test flakiness

### Fixed
- Mixed content mode now works with web copies
- PDFs no longer add unwanted titles
- Images maintain original position in content
- Performance test timing variations handled

---

## [0.3.0] - 2025-01-17

### 🚀 Major Feature Release - PDF Support

### Added
- **Comprehensive PDF creation support**
  - Mixed content (text + image) automatically creates PDF
  - Preserves content order exactly as copied (WYCWYG principle)
  - Explicit `.pdf` extension forces PDF creation
  - Smart content analysis and chunk detection
  - Code syntax detection and formatting in PDFs
  - Automatic image scaling and RGBA to RGB conversion
- **Enhanced format detection**
  - Auto-detects mixed content → suggests PDF
  - Improved content priority logic (mixed → PDF, image > text)
- **35 new tests** for complete PDF functionality coverage
- **ReportLab integration** for professional PDF generation

### Changed
- Default behavior for mixed content now creates PDF instead of prioritizing image
- Updated help documentation with PDF examples
- Enhanced CLI to seamlessly handle PDF workflow

### Use Cases
- Bug reports with screenshots and error messages
- Documentation with diagrams and explanations
- Meeting notes with whiteboard photos
- Research with mixed media content

### Technical
- Added `pdf.py` module with comprehensive PDF operations
- Updated `detect.py` to recognize PDF format requests
- Enhanced `main.py` for PDF creation workflow
- Total test count: 138 tests (was 103)

---

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