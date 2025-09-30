# ClipDrop Usage Guide

## Quick Start

```bash
# Basic usage - auto-detects format
clipdrop notes              # → notes.txt
clipdrop screenshot         # → screenshot.png (if image in clipboard)
clipdrop data               # → data.json (if JSON detected)

# With extension specified
clipdrop report.pdf         # Create PDF with clipboard content
clipdrop log.txt            # Save as text file
```

## Complete Flag Reference

### Core Options

| Flag | Short | Description | Example |
|------|-------|-------------|---------|
| `--preview` | `-p` | Preview content before saving | `clipdrop notes.txt -p` |
| `--force` | `-f` | Skip overwrite confirmation | `clipdrop data.json -f` |
| `--append` | `-a` | Append to existing file | `clipdrop journal.md -a` |
| `--yes` | `-y` | Auto-accept all prompts | `clipdrop secure.txt --scan -y` |

### Input Sources

| Flag | Short | Description | Example |
|------|-------|-------------|---------|
| `--youtube` | `-yt` | Download YouTube transcript from URL | `clipdrop -yt transcript.srt` |
| `--audio` | - | Force audio transcription mode | `clipdrop --audio meeting.txt` |

### Content Filters

| Flag | Description | Example |
|------|-------------|---------|
| `--text-only` | Save only text, ignore images | `clipdrop notes.txt --text-only` |
| `--image-only` | Save only image, ignore text | `clipdrop pic.png --image-only` |

### Security

| Flag | Short | Description | Example |
|------|-------|-------------|---------|
| `--scan` | `-s` | Scan for secrets (interactive) | `clipdrop config.env -s` |
| `--scan-mode` | - | Set scan behavior: prompt\|redact\|block\|warn | `clipdrop keys.txt --scan-mode redact` |

### Additional Options

| Flag | Description | Example |
|------|-------------|---------|
| `--lang CODE` | Language for transcripts | `clipdrop -yt --lang es` |
| `--chapters` | Include YouTube chapter markers | `clipdrop -yt video.md --chapters` |
| `--summarize` | `-S` | Generate structured summary at top (macOS 26.0+) | `clipdrop notes.md --summarize` |
| `--version` | Show version | `clipdrop --version` |
| `--help` | Show help | `clipdrop --help` |

## Common Workflows

### 1. Daily Journal/Notes
Build up a daily journal by appending entries throughout the day:
```bash
# Morning thoughts
clipdrop journal.md -a

# Afternoon notes (appends with separator)
clipdrop journal.md -a

# Evening reflection
clipdrop journal.md -a
```

### 2. Code Snippet Collection
Collect code snippets from various sources:
```bash
# Start a new collection
clipdrop snippets.py

# Add more snippets throughout the day
clipdrop snippets.py -a
clipdrop snippets.py -a
```

### 3. Screenshot Management
Save screenshots with proper naming:
```bash
# Basic screenshot
clipdrop screenshot.png

# Preview before saving
clipdrop mockup.png -p

# Force overwrite existing
clipdrop final-design.png -f
```

### 4. YouTube Research
Download video transcripts for research:
```bash
# Copy YouTube URL to clipboard, then:
clipdrop -yt                          # Auto-names from video title
clipdrop -yt lecture.md --lang en     # Markdown with timestamps
clipdrop -yt subtitles.srt --lang es  # Spanish subtitles
clipdrop -yt research.txt --summarize # Transcript + summary
clipdrop -yt tutorial.md --chapters   # Include chapter markers
```

### 5. Audio Transcription (macOS 26.0+)
Transcribe audio files using Apple Intelligence:
```bash
# Copy audio file to clipboard, then:
clipdrop                               # Auto-detects audio → transcript_[timestamp].srt
clipdrop meeting.txt --summarize      # Plain text + summary
clipdrop interview.md --summarize     # Markdown + summary

# Force audio mode if not detected
clipdrop --audio notes.txt
```

### 6. Secure Content Handling
Handle sensitive content with secret scanning:
```bash
# Interactive prompt on findings
clipdrop config.env -s

# Auto-redact secrets
clipdrop api-keys.txt --scan-mode redact

# Block if secrets found
clipdrop credentials.json --scan-mode block

# Just warn but save anyway
clipdrop notes.txt --scan-mode warn
```

### 7. Mixed Content to PDF
When you have both text and images in clipboard:
```bash
# Auto-detect mixed content
clipdrop report              # → report.pdf (preserves both)

# Force PDF creation
clipdrop summary.pdf

# Extract only text or image
clipdrop content.txt --text-only
clipdrop content.png --image-only
```

### 8. Automation & Scripting
Use in scripts without prompts:
```bash
# Force overwrite without confirmation
clipdrop output.txt -f

# Accept all security prompts
clipdrop data.json --scan -y

### 9. AI Summaries (macOS 26.0+)
Generate a quick recap of long clipboard text:
```bash
# Save and summarize in one step
clipdrop article.md --summarize

# Works with existing files too
clipdrop notes.txt --summarize

# Summaries are skipped for short or non-text content
clipdrop changelog.txt --summarize
```

# Combine flags for full automation
clipdrop log.txt -a -f -y
```

## Smart Format Detection

ClipDrop automatically detects and suggests appropriate extensions:

| Content Type | Detection | Suggested Extension |
|--------------|-----------|-------------------|
| JSON | `{` or `[` at start | `.json` |
| Markdown | Headers, lists, links | `.md` |
| CSV | Comma-separated values | `.csv` |
| HTML | HTML tags | `.html` |
| YAML | YAML structure | `.yaml` |
| Python | Python syntax | `.py` |
| JavaScript | JS syntax | `.js` |
| Plain text | Default | `.txt` |

## Image Formats

Supported image formats with automatic detection:

- **PNG** - Lossless, supports transparency
- **JPEG/JPG** - Lossy compression, no transparency
- **GIF** - Animation support
- **BMP** - Uncompressed bitmap
- **WebP** - Modern format, good compression

## Tips & Tricks

### 1. Quick Preview
Always preview before saving important content:
```bash
clipdrop important.txt -p
```

### 2. Building Logs
Use append mode with `.log` extension for timestamped entries:
```bash
clipdrop app.log -a  # Adds timestamp automatically
```

### 3. Markdown Separation
When appending to markdown files, ClipDrop adds `---` separators:
```bash
clipdrop notes.md -a  # Adds --- between sections
```

### 4. Format Conversion
Change format by specifying different extension:
```bash
# Clipboard has JSON, save as YAML
clipdrop config.yaml

# Clipboard has Markdown, save as TXT
clipdrop plain.txt
```

### 5. Quick Audio Check
If audio transcription isn't working:
```bash
clipdrop --audio  # Forces audio mode
```

### 6. YouTube Language Codes
Common language codes for YouTube transcripts:
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `pt` - Portuguese
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese

### 7. Mixed Clipboard Priority
When both text and image are in clipboard:
1. No flag → PDF (preserves both)
2. `--text-only` → Text file
3. `--image-only` → Image file
4. File extension → Determines format

## Error Messages & Solutions

| Error | Solution |
|-------|----------|
| "No content in clipboard" | Copy something first |
| "Cannot append to PDF files" | Append only works with text files |
| "Cannot use both --text-only and --image-only" | Choose one filter |
| "Platform not supported" | Audio transcription needs macOS 26.0+ |
| "No audio found in clipboard" | Copy audio file from Finder |
| "File exists" | Use `-f` to overwrite or `-a` to append |

## Platform Requirements

- **General features**: macOS 10.15+
- **Audio transcription**: macOS 26.0+ with Apple Intelligence
- **YouTube transcripts**: Requires `pip install clipdrop[youtube]`

## Examples by Use Case

### For Developers
```bash
# Save code snippets
clipdrop snippet.py -a

# Save API responses
clipdrop response.json

# Save configuration
clipdrop .env --scan-mode redact
```

### For Writers
```bash
# Build articles
clipdrop article.md -a

# Save research
clipdrop research.txt -a

# Download video transcripts
clipdrop -yt reference.md
```

### For Designers
```bash
# Save screenshots
clipdrop mockup.png -p

# Save with specific format
clipdrop design.jpg

# Preview dimensions
clipdrop layout.png -p
```

### For Students
```bash
# Lecture notes
clipdrop lecture-notes.md -a

# YouTube lectures
clipdrop -yt lecture.txt

# Research compilation
clipdrop research.md -a
```

## Advanced Usage

### Combining Flags
```bash
# Append with preview
clipdrop notes.txt -a -p

# Force overwrite with scan
clipdrop config.json -f -s

# YouTube with specific language and chapters
clipdrop -yt --lang fr --chapters video.md
```

### Shell Aliases
Add to your `.zshrc` or `.bashrc`:
```bash
alias cda='clipdrop -a'           # Quick append
alias cdp='clipdrop -p'           # Preview first
alias cdy='clipdrop -yt'          # YouTube mode
alias cds='clipdrop -s'           # With scanning
```

### Integration with Other Tools
```bash
# Pipe to clipdrop
echo "Hello" | pbcopy && clipdrop note.txt

# Use with screenshot tools
screencapture -c && clipdrop screenshot.png

# Combine with curl
curl api.example.com | pbcopy && clipdrop response.json
```

---

For more information, visit: https://github.com/prateekjain24/clipdrop
