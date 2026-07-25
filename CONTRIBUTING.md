# Contributing to ClipDrop

Thank you for your interest in contributing to ClipDrop! We welcome contributions from the community and are grateful for any help you can provide.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/clipdrop.git
   cd clipdrop
   ```
3. **Set up development environment** using uv:
   ```bash
   uv pip install -e .[dev]
   ```

## 🔧 Development Workflow

### Setting Up

We use `uv` for package management. If you don't have it installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_clipboard.py

# Run performance tests
uv run pytest tests/test_performance.py -v
```

### Code Quality

```bash
# Lint code (enforced in CI)
uv run ruff check src tests
```

Black and mypy are available in the `dev` extra as optional local tools,
but CI only enforces `ruff check`.

## 📝 Contribution Guidelines

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add type hints where appropriate
- Keep functions focused and small

### Commit Messages

This repo uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <imperative subject>
```

Types in use: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `build`, `ci`.
Keep the subject under 72 characters; reference issue numbers when applicable.

Real examples from this repo's history:
- `feat(youtube): harden transcript downloads against YouTube blocking`
- `fix(ci): pin ruff lint rules to pre-0.16 defaults`
- `chore(deps): require yt-dlp >= 2026.7.4 for current YouTube fixes`
- `refactor(pdf): single source of truth for code detection in detect.py`

Release-prep commits always use `chore(release): X.Y.Z`.

### Pull Requests

1. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit them

3. **Add tests** for new functionality

4. **Ensure all tests pass**:
   ```bash
   uv run pytest
   ```

5. **Push to your fork** and create a pull request

6. **Describe your changes** in the PR description:
   - What problem does it solve?
   - How does it work?
   - Any breaking changes?

### Testing

- Write tests for new features
- Ensure existing tests still pass
- Aim for high test coverage (>80%)
- Include both unit tests and integration tests

### Documentation

- Update README.md if adding new features
- Add docstrings to new functions and classes
- Update the `[Unreleased]` section of CHANGELOG.md with user-facing changes
  (the release script rolls it into the next version heading)
- Include examples in docstrings where helpful

## 📦 Releasing

Releases are cut from `main` by pushing a tag; CI does the rest.

1. Make sure `[Unreleased]` in CHANGELOG.md describes everything since the
   last release — the release script refuses to run if it's empty.
2. Run the release prep script:
   ```bash
   python scripts/release.py X.Y.Z
   ```
   It bumps `pyproject.toml` and `src/clipdrop/__init__.py`, rolls the
   CHANGELOG (`[Unreleased]` → `[X.Y.Z] - <date>` plus compare links), and
   prints the exact git commands for the remaining steps.
3. Commit as `chore(release): X.Y.Z`, open a PR, let CI pass, merge.
4. Tag the merge commit on `main` — always annotated, always on main:
   ```bash
   git switch main && git pull
   git tag -a vX.Y.Z -m "clipdrop X.Y.Z"
   git push origin vX.Y.Z
   ```
5. The Release workflow then verifies the tag matches `pyproject.toml`,
   `__init__.py`, and the top CHANGELOG heading, runs tests + ruff, builds
   the package, creates the GitHub Release with the CHANGELOG section as
   its body, and uploads to PyPI (idempotent via `--skip-existing`).
6. If the verify job fails, nothing was published. Delete the tag, fix on
   `main`, and re-tag:
   ```bash
   git push origin :refs/tags/vX.Y.Z && git tag -d vX.Y.Z
   ```

Notes:
- CHANGELOG version headings (`## [X.Y.Z] - YYYY-MM-DD`) are maintained by
  the script — don't hand-edit their shape, CI matches it exactly.
- The pipeline can be dry-run from the Actions tab: run "Release" via
  *workflow_dispatch* with an existing version number — it verifies and
  builds but skips the GitHub Release and PyPI upload.

## 🐛 Reporting Issues

### Bug Reports

When reporting bugs, please include:
- ClipDrop version (`clipdrop --version`)
- Python version (`python --version`)
- Operating system and version
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Error messages (if any)

### Feature Requests

For feature requests, please describe:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered
- Examples of how it would be used

## 💡 Areas for Contribution

### Current Priorities

- **Cross-platform support**: Windows and Linux compatibility
- **Additional formats**: Support for more file formats
- **Performance**: Optimization for large files
- **Testing**: Increase test coverage
- **Documentation**: Improve user guides and examples

### Good First Issues

Look for issues labeled `good first issue` or `help wanted` on GitHub.

### Feature Ideas

- Shell completions (bash, zsh, fish)
- Configuration file support
- Multiple clipboard history
- Cloud storage integration
- Plugin system for custom formats

## 🎵 Testing Audio Transcription (macOS 26.0+)

### Prerequisites

- macOS 26.0 or later with Apple Intelligence
- Swift transcription helper built (see below)
- Test audio file: `jfk.mp3` (provided in repo)

### Building the Swift Helper

If the helper isn't built yet:
```bash
cd swift/TranscribeClipboard
swift build -c release
cp .build/release/clipdrop-transcribe-clipboard ../../src/clipdrop/bin/
```

### Running Smoke Tests

We provide an automated smoke test script that validates the entire transcription pipeline:

```bash
# Run all tests
./scripts/test_transcription.sh

# Keep test outputs for inspection
./scripts/test_transcription.sh --keep

# Expected output:
✅ macOS version: 26.0
✅ Swift helper found
✅ Test audio found: jfk.mp3
✅ clipdrop command available
✅ Audio copied to clipboard
✅ Transcribed to srt: test_output/transcript_test.srt (2.5 KB)
✅ Transcribed to txt: test_output/transcript_test.txt (1.8 KB)
✅ Transcribed to md: test_output/transcript_test.md (2.2 KB)
✅ All smoke tests passed!
```

### Manual Testing

1. **Copy audio to clipboard** (choose one method):
   ```bash
   # Method 1: Use Finder
   # Navigate to clipdrop folder, select jfk.mp3, press ⌘C

   # Method 2: Use the test script's copy function
   osascript -e 'set the clipboard to (POSIX file "'"$(pwd)/jfk.mp3"'")'
   ```

2. **Test auto-detection**:
   ```bash
   clipdrop                    # Auto-generates: transcript_YYYYMMDD_HHMMSS.srt
   ```

3. **Test specific formats**:
   ```bash
   clipdrop transcript.srt -tr    # SRT format with timestamps
   clipdrop transcript.txt -tr    # Plain text
   clipdrop transcript.md -tr     # Markdown with timestamp headers
   ```

4. **Test with language preference**:
   ```bash
   clipdrop transcript.srt -tr --lang en-US
   ```

### Expected Results

The transcription of `jfk.mp3` should produce text from President Kennedy's speech. Example SRT output:
```srt
1
00:00:00,000 --> 00:00:02,500
And so my fellow Americans

2
00:00:02,500 --> 00:00:05,000
ask not what your country can do for you
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Swift helper not found" | Build the helper: `cd swift/TranscribeClipboard && swift build` |
| "No audio in clipboard" | Ensure you copied the audio file using Finder (⌘C) |
| "macOS version too old" | Requires macOS 26.0+ with Apple Intelligence |
| "Transcription failed" | Check Speech Recognition permissions in System Settings |
| Empty output files | Verify the audio file has speech content |

### Testing Different Audio Files

You can test with your own audio files:
1. Supported formats: `.m4a`, `.mp3`, `.wav`, `.aiff`
2. Copy the file in Finder (⌘C)
3. Run `clipdrop --transcribe`

## 🤝 Code of Conduct

### Be Respectful
- Treat all contributors with respect
- Welcome newcomers and help them get started
- Be patient with questions

### Be Constructive
- Provide constructive feedback
- Focus on what is best for the community
- Be open to different viewpoints

## 📄 License

By contributing to ClipDrop, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

All contributors will be recognized in our README.md file. Thank you for helping make ClipDrop better!

## 📧 Contact

- **Issues**: [GitHub Issues](https://github.com/prateekjain24/clipdrop/issues)
- **Discussions**: [GitHub Discussions](https://github.com/prateekjain24/clipdrop/discussions)

---

Thank you for contributing to ClipDrop! 🎉