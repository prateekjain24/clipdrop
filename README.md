# ClipDrop - Your Clipboard, Instantly Saved ✨

[![PyPI version](https://badge.fury.io/py/clipdrop.svg)](https://badge.fury.io/py/clipdrop)
[![Downloads](https://img.shields.io/pypi/dm/clipdrop.svg)](https://pypistats.org/packages/clipdrop)
[![Python](https://img.shields.io/pypi/pyversions/clipdrop.svg)](https://pypi.org/project/clipdrop/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Stop the copy-paste-save dance.** One command turns your clipboard into any file.

```bash
pip install clipdrop
```

## 🚀 Get Started in 30 Seconds

**1. Copy anything** - text, code, images, audio
**2. Save it** - `clipdrop myfile`
**3. That's it!** ClipDrop detects the format and saves it perfectly.

```bash
# Just copied some code? Save it:
clipdrop script.py

# Screenshot in clipboard? Save it:
clipdrop design.png

# Building a journal? Append to it:
clipdrop journal.md -a
```

## 💡 Why ClipDrop?

**The Problem:** Saving clipboard content on macOS is tedious:
Copy → Open app → Paste → Navigate → Name → Choose format → Save 😫

**The Solution:** Just `clipdrop filename` and you're done! 🎉

Perfect for:
- 👨‍💻 **Developers** - Save code snippets and API responses instantly
- 📊 **PMs** - Capture screenshots and meeting notes in one command
- ✍️ **Writers** - Build documents by appending content throughout the day
- 🎓 **Students** - Organize research without switching apps

## 🎯 Killer Features

### 1. 🧠 **Smart Format Detection**
ClipDrop knows what you copied and saves it correctly:
```bash
clipdrop data        # JSON detected → data.json
clipdrop readme      # Markdown → readme.md
clipdrop screenshot  # Image → screenshot.png
```

### 2. 📝 **Append Mode** - Build Documents Over Time
Never lose a thought. Keep adding to files:
```bash
clipdrop journal.md -a   # Morning thoughts
clipdrop journal.md -a   # Afternoon notes
clipdrop journal.md -a   # Evening reflection
```

### 3. 🎵 **Audio Transcription** (macOS 26.0+)
Turn recordings into text using Apple Intelligence:
```bash
# Copy an audio file, then:
clipdrop              # → transcript_20240323_143022.srt
clipdrop meeting.txt  # → meeting notes as plain text
```

### 4. 🤖 **On-Device Summaries** (macOS 26.0+)
Get an executive-ready recap before the raw transcript:
```bash
# Save article + structured summary at the top
clipdrop research-notes.md --summarize

# Works for YouTube transcripts and audio, too
clipdrop -yt briefing.md --summarize
clipdrop --audio meeting.txt --summarize
```
Summaries include:
- **Overall** headline sentence
- Sections for **Key Takeaways**, **Action Items**, and **Questions**
- **Handles transcripts of any length** - automatically uses hierarchical processing for long content
- Local fallback when Apple Intelligence is busy, so you always get something useful

### 5. 🎥 **YouTube Transcripts**
Research videos efficiently:
```bash
# Copy YouTube URL, then:
clipdrop -yt                    # Download transcript
clipdrop -yt lecture.md --lang es  # Spanish transcript
clipdrop -yt notes.md --summarize  # Transcript + structured summary
```

### 6. 🔒 **Secret Scanner**
Never accidentally save credentials:
```bash
clipdrop config.env -s           # Scan before saving
clipdrop api-keys.txt --scan-mode redact  # Auto-redact secrets
```

### 7. 🏷️ **Auto-Name** (macOS 26.0+)
Stop inventing filenames. Let the on-device model read the content and propose one:
```bash
clipdrop --auto-name             # → quarterly-revenue-growth.md
clipdrop --auto-name notes.txt   # Honors the extension you give it
clipdrop --ocr --auto-name       # Name a screenshot from its recognized text
```
- A short Title-Case suggestion is slugified into a tidy, filesystem-safe name
- The positional filename is optional; a provided extension is kept, otherwise format detection picks it
- Falls back to a content-based slug when Apple Intelligence isn't available

## 📖 Common Workflows

<details>
<summary><b>Daily Journaling</b></summary>

```bash
# Start your day
echo "Morning thoughts..." | pbcopy
clipdrop journal.md -a

# Add throughout the day
clipdrop journal.md -a

# Review before saving
clipdrop journal.md -a -p
```
</details>

<details>
<summary><b>Code Snippet Collection</b></summary>

```bash
# Save useful code snippets
clipdrop snippets.py -a

# Preview before adding
clipdrop snippets.py -a -p

# Force overwrite when needed
clipdrop snippets.py -f
```
</details>

<details>
<summary><b>Research & Notes</b></summary>

```bash
# Save web content as PDF
clipdrop article.pdf

# Download YouTube lectures
clipdrop -yt lecture.md
clipdrop -yt lecture.md --summarize

# Build research document
clipdrop research.md -a

# Append AI summary (macOS 26.0+)
clipdrop research.md --summarize
```
</details>

<details>
<summary><b>Screenshot Management</b></summary>

```bash
# Quick save
clipdrop screenshot.png

# Preview dimensions first
clipdrop mockup.png -p

# Save only the image (ignore text)
clipdrop design.png --image-only
```
</details>

## 🛠️ Installation

### Quick Install
```bash
pip install clipdrop
```

### With YouTube Support
```bash
pip install clipdrop[youtube]
```

### Other Methods
```bash
# Using uv (fast)
uv add clipdrop

# Using pipx (isolated)
pipx install clipdrop

# From source
git clone https://github.com/prateekjain24/clipdrop.git
cd clipdrop && pip install -e .
```

## ⚡ Command Reference

### Core Commands
```bash
clipdrop <filename>      # Save clipboard to file
clipdrop -a <filename>   # Append to existing file
clipdrop -p <filename>   # Preview before saving
clipdrop -f <filename>   # Force overwrite
```

### Input Sources
```bash
clipdrop -yt            # YouTube transcript mode
clipdrop --audio        # Force audio transcription
```

### Filters & Options
```bash
clipdrop --text-only    # Ignore images
clipdrop --image-only   # Ignore text
clipdrop --ocr          # Extract text from a clipboard image (macOS, on-device)
clipdrop --auto-name    # Let ClipDrop name the file from its content
clipdrop -s             # Scan for secrets
clipdrop --lang es      # Set language
```

> 🏷️ **Auto-name** asks the on-device model for a short title and turns it
> into a tidy slug (`clipdrop --auto-name` → `q3-roadmap-plan.md`). No filename
> needed; a provided extension is kept. Falls back to a content-based slug when
> Apple Intelligence isn't available.

> 🔎 **OCR** turns a copied screenshot into text using Apple's on-device Vision
> framework — no data leaves your Mac. It composes with other flags, e.g.
> `clipdrop slide.md --ocr --summarize`.

### ✨ Transform clipboard text (macOS, on-device)

"Writing Tools for the terminal" — reshape what you copied on the way to a file:

```bash
clipdrop email.txt --rewrite formal          # rewrite in a style (concise/friendly/…)
clipdrop notes.md  --prompt "extract the action items"   # any freeform instruction
clipdrop data.md   --to-table                # messy text → Markdown table
clipdrop data.csv  --to-table                # …or CSV when the name ends in .csv
```

These run entirely on-device via Apple Intelligence and compose with everything
else, e.g. `clipdrop --ocr --to-table table.csv` or `clipdrop draft.md --rewrite concise --auto-name`.

[📚 **Full Command Documentation →**](./usage.md)

## 🎯 Pro Tips

1. **Shell Aliases** - Add to your `.zshrc`:
   ```bash
   alias cda='clipdrop -a'  # Quick append
   alias cdp='clipdrop -p'  # Preview first
   ```

2. **Auto-transcribe** - Copy audio → `clipdrop` → instant transcript

3. **Mixed content** - Copy text + image → `clipdrop doc.pdf` → perfect PDF

4. **Safe secrets** - Always use `-s` for sensitive content

## 🤝 Contributing

We love contributions! Check out [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📄 License

MIT © [Prateek Jain](https://github.com/prateekjain24)

## 🔗 Links

- 📖 [Full Documentation](./usage.md)
- 🐛 [Report Issues](https://github.com/prateekjain24/clipdrop/issues)
- ⭐ [Star on GitHub](https://github.com/prateekjain24/clipdrop)

---

<p align="center">
  <b>Stop copying and pasting. Start ClipDropping.</b><br>
  <sub>Made with ❤️ for the clipboard warriors</sub>
</p>
