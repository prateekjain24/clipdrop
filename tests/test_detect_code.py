"""Truth-table tests for the canonical code detector in detect.py.

detect.is_code / detect.detect_language are the single source of truth for the
code-vs-prose decision that drives PDF block styling (formerly duplicated as
pdf._is_code / pdf._detect_language).
"""

import pytest

from clipdrop import detect


class TestIsCode:
    @pytest.mark.parametrize(
        "text",
        [
            "def hello():\n    print('Hello')\n    return True",  # python keyword
            "const hello = () => {\n  console.log('hi');\n};",  # js + structural
            "#include <stdio.h>\nint main() { return 0; }",  # c
            "public class Foo {\n  private int x;\n}",  # java
            "First line\n    Indented\n    Another\n        Deep",  # >30% indented
            "```\nsome fenced block\n```",  # fenced code
        ],
    )
    def test_detects_code(self, text):
        assert detect.is_code(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "Hello, world!",
            "This is a normal sentence about a project deadline.",
            "Meeting notes: we discussed the roadmap and the budget.",
            "A short paragraph with no code-like tokens at all here.",
            "",
        ],
    )
    def test_rejects_prose(self, text):
        assert detect.is_code(text) is False

    def test_indented_prose_below_threshold_is_not_code(self):
        # Only 1 of 5 lines indented (20% < 30%), no keywords/tokens.
        text = "Line one\nLine two\n    indented note\nLine four\nLine five"
        assert detect.is_code(text) is False


class TestDetectLanguage:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("def hello():\n    print('Hello')", "python"),
            ("import os", "python"),
            ("const x = () => {}", "javascript"),
            ("function foo() {}", "javascript"),
            ("#include <stdio.h>\nint main() {}", "cpp"),
            ("public class Foo {}", "java"),
            ("package com.example;", "java"),
            ("just some words", "plain"),
        ],
    )
    def test_language(self, text, expected):
        assert detect.detect_language(text) == expected
