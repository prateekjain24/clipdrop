# Changelog

All notable changes to ClipDrop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.5] - 2025-10-01

### ✨ Structured Summaries Everywhere

### Added
- Markdown summaries now include `**Overall**`, `### Key Takeaways`, `### Action Items`, and `### Questions`
- Summaries appear at the top of saved files, with transcript separated by `---`
- `--summarize` now works for YouTube transcripts and audio transcription output
- Local fallback summaries keep working even if Apple Intelligence returns placeholder text

### Changed
- Swift helper prompts generate richer insights and auto-detect placeholder responses
- CLI summary flow consolidated with consistent progress messages and better warnings
- Token budget increased to 500 response tokens to capture more detail

---

## [1.6.0] - 2025-09-30

## [1.5.3] - 2025-09-23

### 🐛 Bug Fixes

### Fixed
- Audio transcription duration display now uses hh:mm:ss format
- Fixed duration tracking to show actual audio length, not accumulated segments

---

## [1.5.2] - 2025-09-23

### 🐛 Bug Fixes

### Fixed
- Help text formatting with proper line breaks and indentation
- Rich markup rendering in CLI help output

---

## [1.5.1] - 2025-09-23

### 🐛 Bug Fixes

### Fixed
- Variable reference errors from flag simplification
- Test suite compatibility with new flag syntax
- YouTube E2E test with updated video URL
- All 280 tests now passing

---

## [1.5] - 2025-09-23

### ✨ Enhanced UX & Append Mode

### Added
- **Append mode (`-a/--append`)** - Build files over time without overwriting
  - Smart separators based on file type (markdown gets `---`, logs get timestamps)
  - Perfect for journals, notes, and log files
- **Simplified flags for better UX**
  - `--preview` now uses `-p` (lowercase, standard)
  - `--scan/-s` replaces paranoid mode (clearer name)
  - `--text-only` and `--image-only` for explicit control
  - `--audio` replaces `--transcribe` (simpler)
  - `-y` for `--yes` (standard convention)
- **Comprehensive documentation**
  - New `usage.md` with complete examples
  - Redesigned README with product focus
  - Clear workflows and use cases

### Changed
- Removed `--educational` flag (now default for PDFs)
- Audio auto-detection works even with filename provided
- Better error messages and conflict detection

### Fixed
- Audio transcription auto-detection with filenames
- Flag naming conflicts and inconsistencies

---

## [1.0] - 2025-09-23

### 🎵 Audio Transcription & Production Ready

### Added
- **On-device audio transcription** (macOS 26.0+)
  - Uses Apple Intelligence for fast, private transcription
  - Auto-detects audio in clipboard
  - Real-time progress feedback
  - Outputs to SRT, TXT, or Markdown
  - Multi-language support with locale fallback
- **Production-ready release**
  - Pre-built Swift binary for compatibility
  - Standardized exit codes
  - GitHub Actions CI/CD pipeline
  - Comprehensive test coverage

### Technical
- Swift helper binary using SpeechTranscriber API
- Universal binary (arm64 + x86_64)
- Robust platform detection and error handling

---

## [0.50] - 2025-09-22

### 🎥 Major Feature Release - YouTube Transcript Support

### Added
- **YouTube video transcript download feature**
  - Support for downloading transcripts from any YouTube video
  - 150+ language support with auto-generated and manual captions
  - Multiple output formats: VTT, SRT, TXT, and Markdown
  - Smart language selection (defaults to English when not specified)
  - Chapter marker integration in transcripts
  - Comprehensive caching system (~/.cache/clipdrop/youtube/)
- **CLI enhancements for YouTube**
  - New `--youtube` / `-yt` flag to enable YouTube mode
  - New `--lang` flag for language selection (e.g., `--lang es` for Spanish)
  - New `--chapters` flag to include chapter markers in output
  - Auto-generates filename from video title when not specified
- **Robust YouTube functionality**
  - URL validation and video ID extraction
  - yt-dlp integration for reliable caption download
  - VTT parsing with support for various formats
  - Format conversion between VTT, SRT, TXT, and Markdown
  - Handles videos with 150+ auto-generated language tracks
- **Comprehensive test coverage**
  - 66 unit tests for YouTube functionality
  - 6 CLI integration tests
  - 6 end-to-end tests with real YouTube videos
  - Test coverage for all conversion formats

### Changed
- Default language selection now prefers English when `--lang` not specified
- Filename becomes optional when using `--youtube` flag (auto-generated from video title)

### Technical
- Added `youtube.py` module with complete YouTube operations
- New optional dependency: `yt-dlp` (install with `pip install clipdrop[youtube]`)
- Smart caching for video info (7 days) and VTT files (permanent)
- Handles yt-dlp output format variations (including NA prefix)

### Use Cases
- Download lecture transcripts for study notes
- Extract meeting recordings from YouTube
- Create subtitles for video projects
- Archive video content as text
- Translate content by downloading different language tracks

---

## [0.45] - 2025-01-18

### Added
- Paranoid mode secret scanning with `-p` interactive prompt and `--paranoid` modes (`prompt`, `redact`, `block`, `warn`)
- Binary skip notice for paranoid scans when saving images
- CLI `--yes` flag for non-interactive paranoid prompts
- Automated masking/redaction helpers and comprehensive scanner test suite

### Changed
- Preview short flag is now `-P` (long form `--preview` unchanged)
- Updated documentation and examples to highlight paranoid workflows

---

## [0.4.2] - 2025-01-17

### 📚 Enhanced HTML to PDF Conversion for Educational Content

### Added
- **Advanced HTML structure preservation**
  - New `parse_html_content_enhanced()` function for better parsing
  - Preserves tables, lists (ordered/unordered), blockquotes
  - Detects and styles special content (callouts, highlights)
  - Maintains code blocks with proper formatting
  - Hierarchical heading preservation (H1-H6)
- **Educational content optimizations**
  - Callout boxes with yellow background for important notes
  - Justified text option for improved readability
  - Enhanced table formatting with grid lines and alternating rows
  - Blockquote styling with italic text
  - Better visual hierarchy for cognitive load management
- **New CLI options**
  - `--educational/--no-educational` flag for formatting control
  - Educational mode enabled by default for better formatting
- **Comprehensive test coverage**
  - Added `test_enhanced_html.py` with 20+ tests
  - Tests for all HTML elements and edge cases
  - Integration tests for complete workflow

### Improved
- Automatic fallback to standard parsing if enhanced parsing fails
- Better content type detection in preview mode
- Enhanced spacing and typography in PDFs
- Improved handling of nested HTML structures
- Better support for educational and technical documentation

### Technical
- Added `create_pdf_from_enhanced_html()` in pdf.py
- Enhanced main.py integration with automatic format detection
- No new dependencies required - uses existing libraries
- Maintains backward compatibility

---

## [0.4.1] - 2025-01-17

### Bug Fixes & Minor Improvements
- Fixed HTML parsing edge cases
- Improved error handling in PDF generation
- Better memory management for large documents

---

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
