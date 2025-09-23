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

## 🎯 Top 5 Killer Features

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

### 4. 🎥 **YouTube Transcripts**
Research videos efficiently:
```bash
# Copy YouTube URL, then:
clipdrop -yt                    # Download transcript
clipdrop -yt lecture.md --lang es  # Spanish transcript
```

### 5. 🔒 **Secret Scanner**
Never accidentally save credentials:
```bash
clipdrop config.env -s           # Scan before saving
clipdrop api-keys.txt --scan-mode redact  # Auto-redact secrets
```

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

# Build research document
clipdrop research.md -a
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
clipdrop -s             # Scan for secrets
clipdrop --lang es      # Set language
```

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