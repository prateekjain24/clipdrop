# ClipDrop

[![PyPI version](https://badge.fury.io/py/clipdrop.svg)](https://badge.fury.io/py/clipdrop)
[![Python](https://img.shields.io/pypi/pyversions/clipdrop.svg)](https://pypi.org/project/clipdrop/)
[![Downloads](https://img.shields.io/pypi/dm/clipdrop.svg)](https://pypistats.org/packages/clipdrop)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub issues](https://img.shields.io/github/issues/prateekjain24/clipdrop)](https://github.com/prateekjain24/clipdrop/issues)

Save clipboard content to files with one command. ClipDrop automatically detects formats (JSON, Markdown, CSV), suggests appropriate extensions, prevents accidental overwrites, and provides rich visual feedback.

## 📋 Problem We're Solving

**The Pain:** macOS users face a cumbersome 6-step workflow to save clipboard content:
1. Copy content to clipboard
2. Open text editor or image application
3. Paste content
4. Navigate to save location
5. Choose file name and format
6. Click save

**Our Solution:** Transform those 6 steps into **1 simple command** → `clipdrop filename`

This workflow interruption is especially painful for:
- **Developers** saving code snippets, API responses, or terminal outputs
- **Product Managers** capturing screenshots and meeting notes
- **Content Creators** storing drafts, research clips, and visual content
- **Students** organizing research notes and screenshots

## Features

- **Audio Transcription**: On-device audio transcription using Apple Intelligence (macOS 26.0+) 🎵
  - Auto-detects audio in clipboard - just run `clipdrop`
  - Real-time progress feedback with segment count
  - Supports SRT, TXT, and MD output formats
  - Multi-language support with `--lang` option
- **YouTube Transcripts**: Download video transcripts in multiple formats (SRT, VTT, TXT, MD) 🎥
- **Web Content Support**: Save content from web pages with embedded images 🌐
- **PDF Creation**: Save mixed content (text + images) as PDF to preserve context 📄
- **HTML Clipboard Parsing**: Automatically extracts text and images from web copies
- **Image Support**: Save images from clipboard (PNG, JPG, GIF, BMP, WebP) 📷
- **Smart Format Detection**: Automatically detects JSON, Markdown, CSV, PDF, HTML, and image formats
- **Extension Auto-Suggestion**: No extension? ClipDrop suggests the right one
- **Content Priority**: Intelligently handles mixed content (HTML → PDF, text + image → PDF)
- **Safe by Default**: Interactive overwrite protection (bypass with `--force`)
- **Paranoid Mode**: Optional pre-save secret scan with prompt, redact, block, and warn workflows
- **Preview Mode**: See content before saving (text with syntax highlighting, images with dimensions)
- **Rich CLI**: Beautiful, informative output with colors and icons
- **Performance**: Caches clipboard content for speed (<200ms operations)
- **Image Optimization**: Automatic compression for PNG/JPEG formats
- **Large File Support**: Handles files up to 100MB with size warnings
- **Unicode Support**: Full international character support
- **Multi-language Support**: YouTube transcripts in 150+ languages with auto-detection

## 📦 Installation

### Quick Install
```bash
# Basic installation
pip install clipdrop

# With YouTube transcript support
pip install clipdrop[youtube]
```

### Alternative Installation Methods
```bash
# Using uv (fast Python package manager)
uv add clipdrop

# Using pipx (for isolated environments)
pipx install clipdrop
```

### From Source
```bash
# Clone the repository
git clone https://github.com/prateekjain24/clipdrop.git
cd clipdrop

# Install with uv
uv pip install -e .

# Or with pip
pip install -e .
```

## Usage

### Basic Usage
```bash
# Save clipboard to file (auto-detects format)
clipdrop notes              # → notes.txt (text only)
clipdrop screenshot         # → screenshot.png (image only)
clipdrop document           # → document.pdf (mixed content auto-detected)
clipdrop data               # → data.json (if JSON detected)
clipdrop readme             # → readme.md (if Markdown detected)

# Audio transcription (macOS 26.0+)
clipdrop                    # → transcript_20240323_143022.srt (auto-detects audio)
clipdrop meeting.srt        # → meeting.srt (if audio in clipboard)
clipdrop notes.txt          # → notes.txt (transcribed as plain text)

# Specify extension explicitly
clipdrop report.pdf         # Save any content as PDF
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
clipdrop screenshot.png -P

# Paranoid pre-save secret checks
clipdrop notes.txt -p                     # prompt on findings
clipdrop secrets.json --paranoid=redact   # redact matches then save
clipdrop secrets.txt --paranoid=block     # block if secrets found
clipdrop log.txt --paranoid=warn          # warn but save as-is
clipdrop env.txt -p --yes                 # auto-save in non-TTY contexts
clipdrop env.txt --paranoid=prompt --yes  # explicit prompt mode with auto-yes

# Force text mode when both image and text are in clipboard
clipdrop notes.txt --text

# Transcribe audio from clipboard (macOS 26.0+)
clipdrop --transcribe                    # Auto-generate: transcript_YYYYMMDD_HHMMSS.srt
clipdrop --transcribe meeting.txt        # Save as plain text
clipdrop -tr notes.md --lang en-US       # Specify language and format

# Download YouTube video transcripts
clipdrop --youtube                        # Download from clipboard URL (defaults to English)
clipdrop --youtube --lang es             # Download Spanish captions
clipdrop --youtube transcript.srt        # Save as SRT format
clipdrop -yt meeting.txt                 # Short flag, save as plain text
clipdrop --youtube --chapters notes.md   # Include chapter markers in markdown

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

#### Save web article with images
```bash
# Copy article from Medium, Wikipedia, etc., then:
clipdrop article
# 📄 HTML with images detected. Creating PDF: article.pdf
# ✅ Created PDF from HTML (2048 chars, 5 images, 245.3 KB) at article.pdf
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
clipdrop document         # Auto-creates PDF with both (NEW!)
clipdrop content.png      # Save image only
clipdrop content --text   # Forces text mode
```

#### Create PDFs from clipboard
```bash
# Mixed content (text + image) → PDF automatically
clipdrop notes            # Has both? → notes.pdf

# Explicitly create PDF from any content
clipdrop report.pdf       # Always creates PDF

# PDF preserves content order (WYCWYG - What You Copy is What You Get)
# • Text with code → formatted in PDF
# • Screenshots → embedded in PDF
# • Mixed notes → structured document
```

#### Transcribe audio from clipboard (macOS 26.0+)
```bash
# Copy audio file to clipboard, then:
clipdrop                         # Auto-detects and transcribes
# 🎵 Audio detected in clipboard
# ⏳ Transcribing audio...
# 📝 Processing segments: 42
# ✅ Saved 2.1 KB to transcript_20240323_143022.srt

# Explicit transcription with custom filename
clipdrop meeting.srt            # Transcribe to SRT format
clipdrop notes.txt              # Transcribe to plain text
clipdrop summary.md             # Transcribe to Markdown

# Specify language for better accuracy
clipdrop --lang en-US           # American English
clipdrop --lang es-ES           # Spanish (Spain)
clipdrop --lang fr-FR           # French (France)

# Use --transcribe flag when auto-detection fails
clipdrop --transcribe           # Force transcription mode
clipdrop -tr meeting.txt        # Short flag variant
```

#### Download YouTube transcripts
```bash
# Copy YouTube URL to clipboard, then:
clipdrop --youtube
# 🎥 Found YouTube video: dQw4w9WgXcQ
# 📺 Title: Example Video Title
# ✓ Selected: English
# ✅ Transcript saved to 'Example Video Title.srt'

# Specify language (supports 150+ languages)
clipdrop --youtube --lang fr            # French
clipdrop --youtube --lang es            # Spanish
clipdrop --youtube --lang ja            # Japanese

# Different output formats
clipdrop --youtube video.txt            # Plain text
clipdrop --youtube video.srt            # SRT subtitles
clipdrop --youtube video.vtt            # WebVTT format
clipdrop --youtube video.md             # Markdown with timestamps

# Advanced options
clipdrop --youtube --chapters video.md  # Include chapter markers
clipdrop --youtube --lang en-US         # Specific language variant
```

## 🎙️ On-device Transcription (macOS)

ClipDrop leverages Apple Intelligence for fast, private audio transcription directly on your Mac. Your audio never leaves your device.

### Requirements

- **macOS 26.0+** with Apple Intelligence enabled
- **Supported formats**: `.m4a`, `.mp3`, `.wav`, `.aiff`, `.caf`
- **Languages**: 50+ languages supported (auto-detected or specify with `--lang`)

### How to Use

1. **Copy an audio file** to clipboard (select in Finder, press ⌘C)
2. **Run ClipDrop** - it auto-detects audio and transcribes

```bash
# Auto-detect and transcribe
clipdrop                        # Creates: transcript_YYYYMMDD_HHMMSS.srt

# Custom filename and format
clipdrop meeting.srt            # SRT with timestamps
clipdrop notes.txt              # Plain text only
clipdrop summary.md             # Markdown with time headers

# Specify language for accuracy
clipdrop --lang en-US meeting.srt   # US English
clipdrop --lang es-ES acta.txt      # Spanish
clipdrop --lang ja-JP memo.md       # Japanese

# Force transcription mode if auto-detection fails
clipdrop --transcribe           # Uses -tr short flag
```

### Output Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| SRT | `.srt` | Standard subtitle format with timestamps |
| Plain Text | `.txt` | Just the transcribed text |
| Markdown | `.md` | Text with timestamp headers |

### Performance

- **Speed**: ~5 seconds for 1-minute audio
- **Accuracy**: High accuracy using Apple's latest models
- **Privacy**: 100% on-device, no internet required

### Not on macOS?

This feature requires macOS 26.0+ with Apple Intelligence. For other platforms:

- **Linux/Windows users**: Consider cloud-based alternatives like:
  - OpenAI Whisper API
  - Google Cloud Speech-to-Text
  - Azure Speech Services

- **Older macOS**: Upgrade to macOS 26.0 or use online transcription services

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "No audio in clipboard" | Copy audio file using Finder (⌘C) |
| "Platform not supported" | Requires macOS 26.0+ |
| "No speech detected" | Check audio has speech content |
| "Helper not found" | Reinstall: `pip install --force-reinstall clipdrop` |

See [Exit Codes](#-exit-codes) for automation and scripting.

## 🚪 Exit Codes

The audio transcription feature uses standardized exit codes for better automation and debugging:

| Code | Name | Description |
|------|------|-------------|
| 0 | SUCCESS | Transcription completed successfully |
| 1 | NO_AUDIO | No audio file found in clipboard |
| 2 | PLATFORM_ERROR | Not on macOS or version < 26.0 |
| 3 | NO_SPEECH | Audio found but no speech detected |
| 4 | TRANSCRIPTION_ERROR | General transcription failure |

### Using Exit Codes in Scripts

```bash
# Check for specific errors
clipdrop transcript.srt -tr
case $? in
  0) echo "Success!" ;;
  1) echo "No audio in clipboard" ;;
  2) echo "Wrong platform/version" ;;
  3) echo "No speech in audio" ;;
  4) echo "Transcription failed" ;;
esac

# Or simply check success/failure
if clipdrop -tr; then
  echo "Transcription successful"
else
  echo "Transcription failed with code: $?"
fi
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
│   ├── pdf.py             # PDF creation (NEW)
│   └── exceptions.py      # Custom exceptions
├── tests/                 # Comprehensive test suite (124 tests)
│   ├── test_clipboard.py  # 27 tests
│   ├── test_files.py      # 37 tests
│   ├── test_images.py     # 25 tests
│   └── test_pdf.py        # 35 tests (NEW)
├── pyproject.toml         # Modern Python packaging
└── README.md              # This file
```

## 📝 Requirements

- **Python**: 3.10, 3.11, 3.12, or 3.13
- **OS**: macOS 10.15+ (general features)
  - macOS 26.0+ required for on-device audio transcription using Apple Intelligence
- **Dependencies**:
  - typer[all] >= 0.17.4
  - rich >= 14.1.0
  - pyperclip >= 1.9.0
  - Pillow >= 11.3.0
  - reportlab >= 4.0.0

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.



## Issues

Found a bug or have a feature request? Please open an issue on [GitHub Issues](https://github.com/prateekjain24/clipdrop/issues).

---

**Current Version**: 0.50 | **Status**: Available on PyPI 

NOT RELATED to https://clipdrop.co/
