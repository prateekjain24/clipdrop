"""Tests for PDF creation functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from clipdrop import pdf
from clipdrop.pdf import ContentChunk, analyze_clipboard_content


class TestContentAnalysis:
    """Test content analysis and chunk detection."""

    def test_analyze_text_only(self):
        """Test analyzing plain text content."""
        chunks = analyze_clipboard_content("Hello, world!", None)
        assert len(chunks) == 1
        assert chunks[0].type == 'text'
        assert chunks[0].content == "Hello, world!"

    def test_analyze_code_content(self):
        """Test detecting code in text content."""
        code = "def hello():\n    print('Hello')\n    return True"
        chunks = analyze_clipboard_content(code, None)
        assert len(chunks) == 1
        assert chunks[0].type == 'code'
        assert chunks[0].metadata.get('language') == 'python'

    def test_analyze_image_only(self):
        """Test analyzing image-only content."""
        img = Image.new('RGB', (100, 100), color='red')
        chunks = analyze_clipboard_content(None, img)
        assert len(chunks) == 1
        assert chunks[0].type == 'image'
        assert chunks[0].metadata['width'] == 100
        assert chunks[0].metadata['height'] == 100

    def test_analyze_mixed_content(self):
        """Test analyzing mixed text and image content."""
        img = Image.new('RGB', (100, 100), color='blue')
        chunks = analyze_clipboard_content("Some text", img)
        assert len(chunks) == 2
        assert chunks[0].type == 'text'
        assert chunks[1].type == 'image'

    def test_analyze_html_content(self):
        """Test detecting HTML content."""
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        chunks = analyze_clipboard_content(html, None)
        assert len(chunks) == 1
        # HTML parsing returns text chunk with HTML format metadata
        assert chunks[0].type == 'text'
        assert chunks[0].metadata.get('format') == 'html'

    def test_analyze_empty_content(self):
        """Test analyzing empty clipboard."""
        chunks = analyze_clipboard_content(None, None)
        assert len(chunks) == 0

    def test_code_detection_javascript(self):
        """Test JavaScript code detection."""
        js_code = "const hello = () => {\n  console.log('Hello');\n};"
        chunks = analyze_clipboard_content(js_code, None)
        assert chunks[0].type == 'code'
        assert chunks[0].metadata.get('language') == 'javascript'

    def test_code_detection_indentation(self):
        """Test code detection based on indentation."""
        indented = "First line\n    Indented line\n    Another indented\n        Deep indent"
        chunks = analyze_clipboard_content(indented, None)
        assert chunks[0].type == 'code'


class TestPDFCreation:
    """Test PDF creation functions."""

    def test_create_pdf_from_text(self, tmp_path):
        """Test creating PDF from plain text."""
        output = tmp_path / "test.pdf"
        text = "This is a test document.\nWith multiple lines."

        pdf.create_pdf_from_text(text, output, title="Test Document")

        assert output.exists()
        assert output.stat().st_size > 0

    def test_create_pdf_from_text_with_formatting(self, tmp_path):
        """Test creating PDF preserving text formatting."""
        output = tmp_path / "formatted.pdf"
        text = "Line 1\n    Indented line\n        More indent\nBack to start"

        pdf.create_pdf_from_text(text, output, preserve_formatting=True)

        assert output.exists()
        assert output.stat().st_size > 0

    def test_create_pdf_from_image(self, tmp_path):
        """Test creating PDF from image."""
        output = tmp_path / "image.pdf"
        img = Image.new('RGB', (200, 150), color='green')

        pdf.create_pdf_from_image(img, output, title="Test Image")

        assert output.exists()
        assert output.stat().st_size > 0

    def test_create_pdf_from_rgba_image(self, tmp_path):
        """Test creating PDF from RGBA image (with transparency)."""
        output = tmp_path / "rgba.pdf"
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))

        pdf.create_pdf_from_image(img, output)

        assert output.exists()
        assert output.stat().st_size > 0

    def test_create_pdf_from_large_image(self, tmp_path):
        """Test PDF creation with image scaling."""
        output = tmp_path / "large.pdf"
        img = Image.new('RGB', (3000, 2000), color='blue')

        pdf.create_pdf_from_image(img, output, fit_to_page=True)

        assert output.exists()
        assert output.stat().st_size > 0

    def test_create_pdf_from_mixed_content(self, tmp_path):
        """Test creating PDF from mixed content chunks."""
        output = tmp_path / "mixed.pdf"
        img = Image.new('RGB', (150, 100), color='yellow')

        chunks = [
            ContentChunk('text', "First paragraph of text"),
            ContentChunk('image', img, {'width': 150, 'height': 100}),
            ContentChunk('text', "Second paragraph after image"),
        ]

        pdf.create_pdf_from_mixed(chunks, output, title="Mixed Content")

        assert output.exists()
        assert output.stat().st_size > 0

    def test_create_pdf_with_code_chunk(self, tmp_path):
        """Test creating PDF with code chunks."""
        output = tmp_path / "code.pdf"

        chunks = [
            ContentChunk('text', "Here's some code:"),
            ContentChunk('code', "def hello():\n    print('Hello')", {'language': 'python'}),
            ContentChunk('text', "That was Python code."),
        ]

        pdf.create_pdf_from_mixed(chunks, output)

        assert output.exists()
        assert output.stat().st_size > 0

    def test_create_pdf_main_function(self, tmp_path):
        """Test the main create_pdf function."""
        output = tmp_path / "main.pdf"
        text = "Test content"
        img = Image.new('RGB', (50, 50), color='red')

        success, message = pdf.create_pdf(output, text=text, image=img)

        assert success
        assert "Created PDF" in message
        assert output.exists()

    def test_create_pdf_overwrite_protection(self, tmp_path):
        """Test PDF overwrite protection."""
        output = tmp_path / "exists.pdf"
        output.write_text("existing")

        success, message = pdf.create_pdf(output, text="New content", force=False)

        assert not success
        assert "already exists" in message

    def test_create_pdf_force_overwrite(self, tmp_path):
        """Test forced PDF overwrite."""
        output = tmp_path / "overwrite.pdf"
        output.write_text("existing")

        success, message = pdf.create_pdf(output, text="New content", force=True)

        assert success
        assert "Created PDF" in message

    def test_create_pdf_no_content(self, tmp_path):
        """Test PDF creation with no content."""
        output = tmp_path / "empty.pdf"

        success, message = pdf.create_pdf(output)

        assert not success
        assert "No content" in message

    def test_special_characters_in_text(self, tmp_path):
        """Test PDF creation with special characters."""
        output = tmp_path / "special.pdf"
        text = "Special chars: < > & ' \" \n\t"

        pdf.create_pdf_from_text(text, output)

        assert output.exists()
        assert output.stat().st_size > 0


class TestMixedContentDetection:
    """Test mixed content detection functions."""

    def test_has_mixed_content_true(self):
        """Test detecting mixed content."""
        text = "Some text"
        img = Image.new('RGB', (10, 10))

        assert pdf.has_mixed_content(text, img)

    def test_has_mixed_content_text_only(self):
        """Test with text only."""
        assert not pdf.has_mixed_content("Text", None)

    def test_has_mixed_content_image_only(self):
        """Test with image only."""
        img = Image.new('RGB', (10, 10))
        assert not pdf.has_mixed_content(None, img)

    def test_has_mixed_content_empty_text(self):
        """Test with empty text."""
        img = Image.new('RGB', (10, 10))
        assert not pdf.has_mixed_content("", img)
        assert not pdf.has_mixed_content("   ", img)

    def test_should_suggest_pdf(self):
        """Test PDF suggestion logic."""
        text = "Content"
        img = Image.new('RGB', (10, 10))

        # Mixed content should suggest PDF
        assert pdf.should_suggest_pdf(text, img)

        # Single content type should not
        assert not pdf.should_suggest_pdf(text, None)
        assert not pdf.should_suggest_pdf(None, img)


class TestHelperFunctions:
    """Test helper functions."""

    def test_format_file_size(self):
        """Test file size formatting."""
        assert pdf._format_file_size(500) == "500.0 B"
        assert pdf._format_file_size(1500) == "1.5 KB"
        assert pdf._format_file_size(1500000) == "1.4 MB"
        assert pdf._format_file_size(1500000000) == "1.4 GB"

    def test_is_code_detection(self):
        """Test code detection heuristics."""
        # Python code
        assert pdf._is_code("def hello():\n    print('hi')")

        # JavaScript code
        assert pdf._is_code("function test() {\n  return true;\n}")

        # Plain text
        assert not pdf._is_code("This is just plain text.")

        # Indented text (might be code)
        indented = "Line 1\n    Line 2\n    Line 3\n    Line 4"
        assert pdf._is_code(indented)

    def test_detect_language(self):
        """Test programming language detection."""
        assert pdf._detect_language("def test():\n    import os") == "python"
        assert pdf._detect_language("function test() { const x = 1; }") == "javascript"
        assert pdf._detect_language("#include <stdio.h>\nint main()") == "cpp"
        assert pdf._detect_language("public class Test { }") == "java"
        assert pdf._detect_language("unknown code") == "plain"


class TestContentChunk:
    """Test ContentChunk class."""

    def test_content_chunk_creation(self):
        """Test creating content chunks."""
        chunk = ContentChunk('text', "Hello", {'key': 'value'})

        assert chunk.type == 'text'
        assert chunk.content == "Hello"
        assert chunk.metadata['key'] == 'value'
        assert hasattr(chunk, 'timestamp')

    def test_content_chunk_defaults(self):
        """Test content chunk with defaults."""
        chunk = ContentChunk('image', "data")

        assert chunk.type == 'image'
        assert chunk.content == "data"
        assert chunk.metadata == {}
        assert chunk.timestamp is not None


@pytest.mark.integration
class TestPDFIntegration:
    """Integration tests for PDF functionality."""

    def test_end_to_end_text_pdf(self, tmp_path):
        """Test complete text to PDF workflow."""
        output = tmp_path / "e2e_text.pdf"
        text = "# Markdown Header\n\nSome **bold** text and *italic* text."

        success, message = pdf.create_pdf(output, text=text)

        assert success
        assert output.exists()
        assert "characters" in message

    def test_end_to_end_image_pdf(self, tmp_path):
        """Test complete image to PDF workflow."""
        output = tmp_path / "e2e_image.pdf"
        img = Image.new('RGB', (300, 200), color='purple')

        success, message = pdf.create_pdf(output, image=img)

        assert success
        assert output.exists()
        assert "image" in message.lower()

    def test_end_to_end_mixed_pdf(self, tmp_path):
        """Test complete mixed content to PDF workflow."""
        output = tmp_path / "e2e_mixed.pdf"
        text = "Document with text and image"
        img = Image.new('RGB', (200, 100), color='orange')

        success, message = pdf.create_pdf(output, text=text, image=img)

        assert success
        assert output.exists()
        assert "characters" in message
        assert "image" in message

    def test_pdf_with_very_long_text(self, tmp_path):
        """Test PDF creation with very long text."""
        output = tmp_path / "long_text.pdf"
        text = "Long line of text. " * 500  # Very long text

        success, message = pdf.create_pdf(output, text=text)

        assert success
        assert output.exists()

    def test_pdf_with_unicode(self, tmp_path):
        """Test PDF creation with Unicode characters."""
        output = tmp_path / "unicode.pdf"
        text = "Unicode: 你好世界 🌍 Émojis 🎉 Special: ñáéíóú"

        success, message = pdf.create_pdf(output, text=text)

        assert success
        assert output.exists()