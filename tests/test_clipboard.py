"""Tests for clipboard operations module."""

from unittest.mock import patch

from clipdrop import clipboard


class TestGetText:
    """Tests for get_text function."""

    def test_get_text_with_content(self, mock_clipboard):
        """Test getting text when clipboard has content."""
        test_content = "Hello, World!"
        mock_clipboard['set_content'](test_content)

        result = clipboard.get_text()
        assert result == test_content

    def test_get_text_empty_clipboard(self, mock_clipboard):
        """Test getting text when clipboard is empty."""
        mock_clipboard['set_content']("")

        result = clipboard.get_text()
        assert result is None

    def test_get_text_unicode_content(self, mock_clipboard, sample_unicode):
        """Test getting Unicode text from clipboard."""
        mock_clipboard['set_content'](sample_unicode)

        result = clipboard.get_text()
        assert result == sample_unicode
        assert "世界" in result
        assert "🌍" in result

    def test_get_text_multiline_content(self, mock_clipboard):
        """Test getting multiline text from clipboard."""
        multiline = "Line 1\nLine 2\nLine 3"
        mock_clipboard['set_content'](multiline)

        result = clipboard.get_text()
        assert result == multiline
        assert result.count('\n') == 2

    def test_get_text_large_content(self, mock_clipboard, sample_large_text):
        """Test getting large text content from clipboard."""
        mock_clipboard['set_content'](sample_large_text)

        result = clipboard.get_text()
        assert result == sample_large_text
        assert len(result) > 500000  # Should be ~600KB

    def test_get_text_with_exception(self):
        """Test handling exceptions when accessing clipboard."""
        with patch('pyperclip.paste', side_effect=Exception("Clipboard error")):
            result = clipboard.get_text()
            assert result is None

    def test_get_text_whitespace_only(self, mock_clipboard):
        """Test getting whitespace-only content."""
        mock_clipboard['set_content']("   \n\t  ")

        result = clipboard.get_text()
        assert result == "   \n\t  "  # Should return whitespace as-is


class TestHasContent:
    """Tests for has_content function."""

    def test_has_content_with_text(self, mock_clipboard):
        """Test checking content when clipboard has text."""
        mock_clipboard['set_content']("Some content")

        assert clipboard.has_content() is True

    def test_has_content_when_empty(self, mock_clipboard):
        """Test checking content when clipboard is empty."""
        mock_clipboard['set_content']("")

        assert clipboard.has_content() is False

    def test_has_content_with_whitespace(self, mock_clipboard):
        """Test checking content with whitespace."""
        mock_clipboard['set_content']("   ")

        assert clipboard.has_content() is True  # Whitespace is still content

    def test_has_content_with_error(self):
        """Test has_content when clipboard access fails."""
        with patch('pyperclip.paste', side_effect=Exception("Error")):
            assert clipboard.has_content() is False


class TestGetContentType:
    """Tests for get_content_type function."""

    def test_content_type_text(self, mock_clipboard):
        """Test detecting text content type."""
        mock_clipboard['set_content']("Regular text")

        assert clipboard.get_content_type() == 'text'

    def test_content_type_empty(self, mock_clipboard):
        """Test detecting empty clipboard."""
        mock_clipboard['set_content']("")

        assert clipboard.get_content_type() == 'none'

    def test_content_type_with_error(self):
        """Test content type when clipboard access fails."""
        with patch('pyperclip.paste', side_effect=Exception("Error")):
            assert clipboard.get_content_type() == 'none'


class TestGetContentPreview:
    """Tests for get_content_preview function."""

    def test_preview_short_text(self, mock_clipboard):
        """Test preview when text is shorter than limit."""
        short_text = "Short text"
        mock_clipboard['set_content'](short_text)

        result = clipboard.get_content_preview(100)
        assert result == short_text
        assert "..." not in result

    def test_preview_truncation(self, mock_clipboard):
        """Test preview truncation for long text."""
        long_text = "a" * 200
        mock_clipboard['set_content'](long_text)

        result = clipboard.get_content_preview(100)
        assert len(result) == 103  # 100 chars + "..."
        assert result.endswith("...")
        assert result.startswith("a" * 100)

    def test_preview_empty_clipboard(self, mock_clipboard):
        """Test preview when clipboard is empty."""
        mock_clipboard['set_content']("")

        result = clipboard.get_content_preview()
        assert result is None

    def test_preview_custom_length(self, mock_clipboard):
        """Test preview with custom max length."""
        text = "0123456789" * 10
        mock_clipboard['set_content'](text)

        result = clipboard.get_content_preview(50)
        assert len(result) == 53  # 50 + "..."
        assert result[:50] == text[:50]

    def test_preview_exact_length(self, mock_clipboard):
        """Test preview when text is exactly max length."""
        text = "x" * 100
        mock_clipboard['set_content'](text)

        result = clipboard.get_content_preview(100)
        assert result == text
        assert "..." not in result

    def test_preview_unicode_truncation(self, mock_clipboard, sample_unicode):
        """Test preview truncation with Unicode characters."""
        mock_clipboard['set_content'](sample_unicode)

        result = clipboard.get_content_preview(20)
        assert len(result) == 23  # 20 + "..."
        assert result.endswith("...")


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_null_bytes_in_content(self, mock_clipboard):
        """Test handling null bytes in content."""
        content_with_null = "Hello\x00World"
        mock_clipboard['set_content'](content_with_null)

        result = clipboard.get_text()
        assert result == content_with_null

    def test_very_long_single_line(self, mock_clipboard):
        """Test handling very long single line."""
        long_line = "x" * 1000000  # 1MB single line
        mock_clipboard['set_content'](long_line)

        result = clipboard.get_text()
        assert result == long_line

    def test_special_characters(self, mock_clipboard):
        """Test handling special characters."""
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        mock_clipboard['set_content'](special)

        result = clipboard.get_text()
        assert result == special

    def test_tab_characters(self, mock_clipboard):
        """Test handling tab characters."""
        tabbed = "Column1\tColumn2\tColumn3"
        mock_clipboard['set_content'](tabbed)

        result = clipboard.get_text()
        assert result == tabbed
        assert result.count('\t') == 2

    def test_carriage_returns(self, mock_clipboard):
        """Test handling different line endings."""
        # Windows-style CRLF
        crlf_text = "Line1\r\nLine2\r\nLine3"
        mock_clipboard['set_content'](crlf_text)

        result = clipboard.get_text()
        assert result == crlf_text


class TestPerformance:
    """Performance-related tests."""

    def test_repeated_calls_performance(self, mock_clipboard, performance_timer):
        """Test performance of repeated get_text calls."""
        mock_clipboard['set_content']("Test content")

        performance_timer.start()
        for _ in range(1000):
            clipboard.get_text()
        performance_timer.stop()

        # Should complete 1000 calls quickly (< 1 second)
        assert performance_timer.elapsed < 1.0

    def test_large_content_performance(self, mock_clipboard, performance_timer):
        """Test performance with large content."""
        large_content = "x" * 10000000  # 10MB
        mock_clipboard['set_content'](large_content)

        performance_timer.start()
        result = clipboard.get_text()
        performance_timer.stop()

        assert result == large_content
        # Should handle 10MB in reasonable time (< 0.5 seconds)
        assert performance_timer.elapsed < 0.5

class TestRichTextClipboard:
    """Tests for rich text (HTML) clipboard writing."""

    def test_build_script_hex_round_trip(self):
        """HTML in the script hex-decodes back to the original."""
        import re
        html = "<h1>Héllo 世界</h1>"
        script = clipboard.build_rich_clipboard_script(html, "fallback")

        match = re.search(r'«data HTML([0-9A-Fa-f]+)»', script)
        assert match is not None
        assert bytes.fromhex(match.group(1)).decode('utf-8') == html

    def test_build_script_escapes_plain_text(self):
        """Plain-text part escapes quotes, backslashes, and newlines."""
        script = clipboard.build_rich_clipboard_script(
            "<p>x</p>", 'say "hi"\nback\\slash'
        )
        assert '\\"hi\\"' in script
        assert '\\n' in script
        assert '\\\\slash' in script
        # No raw newlines may survive inside the single-line script
        assert '\n' not in script

    def test_build_script_sets_both_flavors(self):
        script = clipboard.build_rich_clipboard_script("<p>x</p>", "md source")
        assert script.startswith('set the clipboard to {text:"')
        assert '«class HTML»' in script

    @patch('clipdrop.clipboard.sys.platform', 'darwin')
    @patch('clipdrop.clipboard.subprocess.run')
    def test_copy_rich_text_invokes_osascript_via_stdin(self, mock_run):
        mock_run.return_value.returncode = 0
        clipboard.copy_rich_text_to_clipboard("<h1>Hi</h1>", "# Hi")

        args, kwargs = mock_run.call_args
        assert args[0] == ['osascript', '-']
        script = kwargs['input'].decode('utf-8')
        assert '«class HTML»' in script
        assert 'set the clipboard to' in script

    @patch('clipdrop.clipboard.sys.platform', 'darwin')
    @patch('clipdrop.clipboard.subprocess.run')
    def test_copy_rich_text_updates_cache(self, mock_run):
        mock_run.return_value.returncode = 0
        clipboard.copy_rich_text_to_clipboard("<h1>Hi</h1>", "# Hi")
        assert clipboard._clipboard_cache['content'] == "# Hi"

    @patch('clipdrop.clipboard.sys.platform', 'darwin')
    @patch('clipdrop.clipboard.subprocess.run')
    def test_copy_rich_text_osascript_failure(self, mock_run):
        from clipdrop.exceptions import ClipboardAccessError
        import pytest

        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = b"execution error"

        with pytest.raises(ClipboardAccessError):
            clipboard.copy_rich_text_to_clipboard("<h1>Hi</h1>", "# Hi")

    @patch('clipdrop.clipboard.sys.platform', 'linux')
    def test_copy_rich_text_requires_macos(self):
        from clipdrop.exceptions import ClipboardAccessError
        import pytest

        with pytest.raises(ClipboardAccessError, match="macOS"):
            clipboard.copy_rich_text_to_clipboard("<h1>Hi</h1>", "# Hi")

    def test_copy_rich_text_content_too_large(self):
        from clipdrop.exceptions import ContentTooLargeError
        import pytest

        huge_html = "x" * (clipboard.MAX_RICH_CONTENT_SIZE + 1)
        with pytest.raises(ContentTooLargeError):
            clipboard.copy_rich_text_to_clipboard(huge_html, "fallback")
