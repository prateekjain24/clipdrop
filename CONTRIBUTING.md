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
# Format code
uv run black src tests

# Lint code
uv run ruff check .

# Type checking (if configured)
uv run mypy src
```

## 📝 Contribution Guidelines

### Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting
- Use meaningful variable and function names
- Add type hints where appropriate
- Keep functions focused and small

### Commit Messages

- Use clear and descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Keep the first line under 72 characters
- Reference issue numbers when applicable

Good examples:
- `Add support for WEBP image format`
- `Fix path traversal vulnerability in file validation`
- `Update documentation for image support features`

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
- Update CHANGELOG.md with your changes
- Include examples in docstrings where helpful

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