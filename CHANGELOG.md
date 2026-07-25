# Changelog

All notable changes to ClipDrop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.3.0] - 2026-07-25

### Added
- **YouTube blocking resilience** — `--youtube` now survives YouTube's
  anti-bot measures much more often:
  - `--cookies-from-browser BROWSER` authenticates requests with your
    browser's cookies (chrome, firefox, safari, edge, brave), the reliable
    fix for "Sign in to confirm you're not a bot" blocks
  - Env overrides: `CLIPDROP_YT_COOKIES_FROM_BROWSER`, `CLIPDROP_YT_COOKIES`
    (cookies file), `CLIPDROP_YT_PLAYER_CLIENT` (pin a yt-dlp player client)
  - Bot-check and HTTP 429 failures are detected and reported with targeted
    fixes instead of a generic error; rate limits retry with exponential
    backoff; bot checks automatically retry once via the `mweb` player client
  - Warns when the installed `yt-dlp` release is over 60 days old — the most
    common cause of sudden YouTube breakage

### Changed
- Raised the `clipdrop[youtube]` extra's minimum `yt-dlp` to 2026.7.4 so
  upgrades pull in current YouTube extractor fixes
- YouTube metadata and caption listing now share a single cached `yt-dlp`
  call (one network round-trip instead of two per video), reducing exposure
  to YouTube's bot checks and rate limits; caption metadata is cached for
  7 days in `~/.cache/clipdrop/youtube/<id>/metadata.json`
- Caption extraction no longer fails when YouTube blocks only the media
  formats (`--ignore-no-formats-error`)

### Fixed
- An HTTP 429 during subtitle download was previously misreported as
  "No captions available" — it now surfaces as a rate-limit error with
  retry guidance

## [2.2.0] - 2026-07-25

### Added
- **Plain text copy (`--plain`/`-P`)** — convert clipboard Markdown to clean
  plain text and copy it back: syntax stripped, structure kept (bullets,
  paragraph breaks, verbatim code blocks, link URLs in parentheses, tables as
  tab-separated rows). Paste AI output naturally into email, LinkedIn, or chat
- **Markdown copy (`--md`/`-M`)** — convert the clipboard's rich text (HTML)
  flavor to GFM Markdown and copy it back. Turn anything copied from a web
  page, Google Docs, or Confluence into clean Markdown for LLMs and notes
- Both compose with `--preview`, secret scanning (`-s`/`--scan-mode`), and an
  optional filename (`.txt`/`.md` defaults); `--rich`/`--plain`/`--md` are
  mutually exclusive
- **Clipboard history** — local, secret-aware clip history for the terminal:
  - `--history-daemon` polls the clipboard and stores each text clip in
    `~/.clipdrop/history.jsonl` (owner-only permissions, 50-entry cap,
    oversized clips skipped, adjacent duplicates deduped)
  - **Clips containing secrets are never persisted** — every clip runs
    through the paranoid scanner before touching disk
  - `--history` browses recent clips; `--last N` restores the Nth most
    recent to the clipboard (or saves it with format detection when a
    filename is given); `--pick` is an interactive picker;
    `--history-clear` wipes the store
  - History operations are mutually exclusive with the format bridge,
    `--audio`, and `--youtube`

## [2.1.0] - 2026-07-22

### Added
- **Rich text copy (`--rich`/`-r`)** — convert clipboard Markdown to rich text
  (HTML) and copy it back to the clipboard, so pasting into Confluence, Google
  Docs, Gmail, or Slack produces formatted headings, lists, tables, links, and
  code blocks instead of raw Markdown syntax
  - Sets both pasteboard flavors: rendered HTML plus the original Markdown as
    the plain-text fallback (plain-text targets and "Paste and Match Style"
    still get your source)
  - Renders with markdown-it-py (CommonMark + GFM tables/strikethrough) and
    scrubs the output for editor-safe pasting: spans unwrapped, style/class
    attributes stripped, code fence languages mapped to Confluence's
    recognized set (`js` → `javascript`, `yml` → `yaml`, …)
  - Composes with `--preview` (inspect the HTML before copying), secret
    scanning (`-s`/`--scan-mode`, runs on the Markdown source), and an
    optional filename to also save the HTML (`clipdrop -r page` → `page.html`)

## [2.0.0] - 2026-06-06

### 🔒 Security & Correctness Hardening

This is a major release focused on security, privacy, and maintainability. The
one behavior change below is why it's a major version.

### ⚠️ Breaking
- **Remote image fetching in HTML→PDF is now opt-in.** Saving HTML-with-images
  no longer silently fetches remote `http(s)` images by default. Pass
  `--fetch-remote-images` to restore the old behavior. Embedded `data:` images
  are always included. This closes an SSRF/privacy hole where rendering copied
  HTML could make the tool reach arbitrary URLs.

### Fixed (security)
- **SSRF guard** - remote image fetches now resolve the host and block
  private/loopback/link-local/reserved/multicast targets (incl.
  `169.254.169.254`); `http(s)` only
- **Decompression-bomb protection** - untrusted (base64/remote) images are
  opened through a guarded path that promotes Pillow's `DecompressionBombWarning`
  to an error and bounds input size
- **Packaging** - the wheel now force-includes all five Swift helpers
  (`transcribe`, `summarize`, `ocr`, `suggest-name`, `transform`); previously
  only the transcribe helper was explicitly listed
- **Exception handling** - `files.write_text` now raises the typed
  `PathTraversalError` (re-exported from `files`), so the corresponding handler
  in `main` resolves instead of collapsing into an `AttributeError`

### Changed (hygiene)
- `hashlib.sha1(..., usedforsecurity=False)` in the secret-mask stub
- Replaced assert-based control flow in the transcribe helpers (which is
  stripped under `python -O`) with explicit checks

### Internal
- **`main()` decomposed** into focused, independently testable stages
  (`_try_html_mixed_to_pdf`, `_apply_ocr`, `_apply_transform`,
  `_resolve_auto_name`) - no behavior change, also fixing a latent
  loop-variable shadowing bug in the inline HTML→PDF path
- Added `test_security.py` (SSRF / decompression-bomb / path-traversal coverage);
  bandit High/Medium = 0, ruff clean

---

## [1.10.0] - 2026-06-06

### ✨ Clipboard Transforms — Writing Tools for the Terminal

Reshape copied text on the way to a file, entirely on-device.

### Added
- **`--rewrite <style>`** - restyle text (formal / concise / friendly / ...) via the on-device model
- **`--prompt "<instruction>"`** - apply any freeform instruction to the text
- **`--to-table`** - turn messy text into a table via guided generation (`@Generable { headers, rows }`); rendered to Markdown, or CSV when the filename ends in `.csv`
- All three compose with existing flags - transforms run after content/OCR is resolved and before naming/summarizing, so `--ocr`, `--auto-name`, and `--summarize` all stack with them
- New Swift helper `clipdrop-transform` (JSON in/out, universal arm64+x86_64)

### Technical
- `macos_ai`: `TransformNotAvailableError`, `get_transform_helper_path()`, `transform_content()` (JSON protocol, length guard, error mapping)
- `main`: `render_markdown_table()` / `render_csv_table()` and mutual-exclusion handling across the verbs
- 19 new Python tests (transform_content, table rendering, per-verb CLI, mutual exclusion, no-text, unavailable)

### Notes
- Translate was intentionally deferred: the Translation framework's `TranslationSession` is SwiftUI-bound and can't be cleanly driven from a headless helper

---

## [1.9.0] - 2026-06-06

### ✨ AI-Suggested Filenames

### Added
- **`--auto-name` flag** - derive a descriptive filename from clipboard content using the on-device model (guided generation)
  - The model proposes a short Title-Case title, which is slugified into a filesystem-safe name
  - The positional filename becomes optional; a provided extension is honored, otherwise format detection picks it
  - Composes with other flags, e.g. `clipdrop --ocr --auto-name` to name a screenshot from its recognized text
  - Falls back to a heuristic content slug when Apple Intelligence is unavailable, so it degrades gracefully
  - New Swift helper `clipdrop-suggest-name` (`@Generable SuggestedName { title }`, universal arm64+x86_64)

### Technical
- `macos_ai.suggest_filename()` invokes the helper and returns the title (or `None`)
- `files.slugify()` produces a lowercase/hyphenated, word- and length-capped slug
- 16 new Python tests (slugify, suggest_filename, generate_auto_filename, CLI behavior)

---

## [1.8.0] - 2026-06-06

### ✨ On-Device Image OCR

### Added
- **`--ocr` flag** - extract text from a clipboard image using Apple's Vision framework (`VNRecognizeTextRequest`), fully on-device
  - Recognized text is routed through the normal text-save pipeline, so it composes with `--summarize`, `--scan`, `--preview`, and append
  - Optional language hints supported by the underlying helper
  - New Swift helper `clipdrop-ocr` (universal arm64+x86_64, macOS 13+)

### Technical
- `macos_ai`: `get_ocr_helper_path()` + `ocr_image()` (writes a temp PNG, invokes the helper, returns text; raises `OCRNotAvailableError` off-macOS or when the helper is missing)
- `build_swift.sh` builds the new helper; the binary ships in the wheel via hatch's VCS file inclusion
- 10 new Python tests covering helper invocation, language hint, no-text/error paths, temp cleanup, and CLI behavior

---

## [1.7.0] - 2026-06-06

### ✨ Guided Generation for On-Device Summaries

### Changed
- **Summarizer now uses Foundation Models guided generation** - the on-device model is constrained to a typed `StructuredSummary` (`overall`, `keyTakeaways`, `actionItems`, `questions`) via `@Generable`/`@Guide`, instead of being asked to format free-form Markdown
  - Structure is now guaranteed by the schema; the model never sees a format spec
  - Single-pass and final chunk aggregation generate structured output; chunk-level and intermediate aggregation remain string-based
  - Dropped brittle placeholder-string detection on the structured paths; the local fallback summary still covers model-unavailable/generation errors

### Technical
- Saved-file Markdown output is byte-identical (rendered via the shared `buildStructuredSummary`)
- Helper JSON contract (`{success, summary, warnings, stage_results}`) unchanged, so the Python glue and tests are unaffected
- Rebuilt the `clipdrop-summarize` universal helper binary (macOS 26 + Xcode 26.5, Swift 6.3.2)

---

## [1.6.6] - 2025-10-01

### 🚀 Long-Form Content Summarization

### Fixed
- **Hierarchical summarization for long transcripts** - Now handles audio/YouTube transcripts of any length
  - Automatically processes content in stages when >8 chunks detected
  - Reduced individual chunk size (8000→5000 chars) to stay within model limits
  - Intermediate aggregation in batches of 5 prevents context window overflow
  - Successfully tested with 73-minute transcripts (~118K characters, 23 chunks)
- **Improved fallback handling** - Chunks exceeding model limits now use local summarization instead of failing

### Technical
- Swift helper now performs multi-level aggregation for documents with >8 chunks
- Added `intermediate_aggregation` stage to processing pipeline
- Chunk size calculation in Python optimized for Foundation Model context limits
- Better error recovery during chunk processing

---

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

[Unreleased]: https://github.com/prateekjain24/clipdrop/compare/v2.3.0...HEAD
[2.3.0]: https://github.com/prateekjain24/clipdrop/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/prateekjain24/clipdrop/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/prateekjain24/clipdrop/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/prateekjain24/clipdrop/compare/v1.10.0...v2.0.0
[1.10.0]: https://github.com/prateekjain24/clipdrop/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/prateekjain24/clipdrop/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/prateekjain24/clipdrop/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/prateekjain24/clipdrop/releases/tag/v1.7.0
