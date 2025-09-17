"""Tests for HTML parsing and image extraction."""

import base64
import io
from unittest.mock import Mock, patch, MagicMock
import subprocess

import pytest
from PIL import Image

from clipdrop import html_parser
from clipdrop.exceptions import ClipboardError


class TestGetHtmlFromClipboard:
    """Test HTML clipboard access."""

    @patch('subprocess.run')
    def test_get_html_success(self, mock_run):
        """Test successful HTML retrieval from clipboard."""
        # Simulate HTML hex data from AppleScript
        html_content = '<html><body>Test</body></html>'
        hex_data = html_content.encode('utf-8').hex()
        mock_output = f'«data HTML{hex_data}»'

        mock_run.return_value = Mock(
            returncode=0,
            stdout=mock_output.encode('utf-8')
        )

        result = html_parser.get_html_from_clipboard()
        assert result == html_content

    @patch('subprocess.run')
    def test_get_html_no_content(self, mock_run):
        """Test when clipboard has no HTML."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout=b''
        )

        result = html_parser.get_html_from_clipboard()
        assert result is None

    @patch('subprocess.run')
    def test_get_html_invalid_format(self, mock_run):
        """Test when clipboard returns invalid format."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=b'Invalid data'
        )

        result = html_parser.get_html_from_clipboard()
        assert result is None

    @patch('subprocess.run')
    def test_get_html_timeout(self, mock_run):
        """Test timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 2)

        result = html_parser.get_html_from_clipboard()
        assert result is None


class TestParseHtmlContent:
    """Test HTML parsing and extraction."""

    def test_parse_simple_html(self):
        """Test parsing simple HTML."""
        html = '''
        <html>
            <body>
                <h1>Title</h1>
                <p>Paragraph text</p>
            </body>
        </html>
        '''

        text, images = html_parser.parse_html_content(html)
        assert 'Title' in text
        assert 'Paragraph text' in text
        assert len(images) == 0

    def test_parse_html_with_images(self):
        """Test parsing HTML with image tags."""
        html = '''
        <html>
            <body>
                <img src="https://example.com/image.png" alt="Test Image">
                <img src="data:image/png;base64,iVBORw0KGg==" alt="Base64 Image">
                <img src="//cdn.example.com/img.jpg">
            </body>
        </html>
        '''

        text, images = html_parser.parse_html_content(html)
        assert len(images) == 3

        # Check first image (URL)
        assert images[0]['src'] == 'https://example.com/image.png'
        assert images[0]['alt'] == 'Test Image'
        assert images[0]['type'] == 'url'

        # Check second image (base64)
        assert images[1]['type'] == 'base64'
        assert images[1]['alt'] == 'Base64 Image'

        # Check third image (protocol-relative)
        assert images[2]['type'] == 'url'
        assert images[2]['src'] == 'https://cdn.example.com/img.jpg'

    def test_parse_html_removes_scripts(self):
        """Test that script tags are removed."""
        html = '''
        <html>
            <body>
                <p>Content</p>
                <script>alert('test');</script>
                <style>body { color: red; }</style>
            </body>
        </html>
        '''

        text, images = html_parser.parse_html_content(html)
        assert 'alert' not in text
        assert 'color: red' not in text
        assert 'Content' in text

    def test_parse_empty_html(self):
        """Test parsing empty HTML."""
        text, images = html_parser.parse_html_content('')
        assert text == ''
        assert images == []


class TestExtractBase64Image:
    """Test base64 image extraction."""

    def test_extract_valid_base64(self):
        """Test extracting valid base64 image."""
        # Create a small 1x1 red pixel PNG
        img = Image.new('RGB', (1, 1), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        base64_data = base64.b64encode(buffer.getvalue()).decode()
        data_url = f'data:image/png;base64,{base64_data}'

        result = html_parser.extract_base64_image(data_url)
        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == (1, 1)

    def test_extract_invalid_base64(self):
        """Test extracting invalid base64 data."""
        data_url = 'data:image/png;base64,invalid_base64_data'

        result = html_parser.extract_base64_image(data_url)
        assert result is None

    def test_extract_no_comma_separator(self):
        """Test data URL without comma separator."""
        data_url = 'data:image/png;base64'

        result = html_parser.extract_base64_image(data_url)
        assert result is None


class TestDownloadImage:
    """Test image downloading."""

    @patch('requests.get')
    def test_download_success(self, mock_get):
        """Test successful image download."""
        # Create a mock image
        img = Image.new('RGB', (10, 10), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'image/png'}
        mock_response.content = buffer.getvalue()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = html_parser.download_image('https://example.com/image.png')
        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == (10, 10)

    @patch('requests.get')
    def test_download_non_image_content(self, mock_get):
        """Test downloading non-image content."""
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = html_parser.download_image('https://example.com/page.html')
        assert result is None

    @patch('requests.get')
    def test_download_timeout(self, mock_get):
        """Test download timeout."""
        import requests
        mock_get.side_effect = requests.Timeout()

        result = html_parser.download_image('https://example.com/image.png')
        assert result is None

    @patch('requests.get')
    def test_download_http_error(self, mock_get):
        """Test HTTP error during download."""
        import requests
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_get.return_value = mock_response

        result = html_parser.download_image('https://example.com/image.png')
        assert result is None


class TestProcessHtmlImages:
    """Test image processing from HTML."""

    def test_process_base64_images(self):
        """Test processing base64 images."""
        # Create a test image
        img = Image.new('RGB', (5, 5), color='green')

        images = [
            {
                'type': 'base64',
                'data': img,
                'src': 'data:image/png;base64,...'
            }
        ]

        result = html_parser.process_html_images(images)
        assert len(result) == 1
        assert result[0] == img

    @patch('clipdrop.html_parser.download_image')
    def test_process_url_images(self, mock_download):
        """Test processing URL images."""
        mock_img = Image.new('RGB', (8, 8), color='yellow')
        mock_download.return_value = mock_img

        images = [
            {
                'type': 'url',
                'src': 'https://example.com/img.jpg'
            }
        ]

        result = html_parser.process_html_images(images)
        assert len(result) == 1
        assert result[0] == mock_img
        mock_download.assert_called_once_with('https://example.com/img.jpg')

    @patch('clipdrop.html_parser.download_image')
    def test_process_mixed_images(self, mock_download):
        """Test processing mixed image types."""
        base64_img = Image.new('RGB', (3, 3), color='red')
        url_img = Image.new('RGB', (4, 4), color='blue')
        mock_download.return_value = url_img

        images = [
            {
                'type': 'base64',
                'data': base64_img
            },
            {
                'type': 'url',
                'src': 'https://example.com/img.png'
            },
            {
                'type': 'unknown'  # Should be skipped
            }
        ]

        result = html_parser.process_html_images(images)
        assert len(result) == 2
        assert result[0] == base64_img
        assert result[1] == url_img


class TestHasHtmlContent:
    """Test HTML content detection."""

    @patch('clipdrop.html_parser.get_html_from_clipboard')
    def test_has_html_true(self, mock_get):
        """Test when HTML content exists."""
        mock_get.return_value = '<html>Content</html>'

        result = html_parser.has_html_content()
        assert result is True

    @patch('clipdrop.html_parser.get_html_from_clipboard')
    def test_has_html_false(self, mock_get):
        """Test when no HTML content."""
        mock_get.return_value = None

        result = html_parser.has_html_content()
        assert result is False

    @patch('clipdrop.html_parser.get_html_from_clipboard')
    def test_has_html_empty_string(self, mock_get):
        """Test when HTML is empty string."""
        mock_get.return_value = '   '

        result = html_parser.has_html_content()
        assert result is False


class TestGetHtmlWithImages:
    """Test combined HTML and image extraction."""

    @patch('clipdrop.html_parser.get_html_from_clipboard')
    @patch('clipdrop.html_parser.extract_content_from_html')
    def test_get_html_with_images_success(self, mock_extract, mock_get):
        """Test successful HTML and image extraction."""
        html = '<html><body>Test</body></html>'
        text = 'Test'
        images = [Image.new('RGB', (2, 2))]

        mock_get.return_value = html
        mock_extract.return_value = (text, images)

        result = html_parser.get_html_with_images()
        assert result is not None
        assert result[0] == html  # Raw HTML
        assert result[1] == text  # Extracted text
        assert result[2] == images  # Extracted images

    @patch('clipdrop.html_parser.get_html_from_clipboard')
    def test_get_html_with_images_no_content(self, mock_get):
        """Test when no HTML content available."""
        mock_get.return_value = None

        result = html_parser.get_html_with_images()
        assert result is None


class TestExtractContentFromHtml:
    """Test main content extraction function."""

    @patch('clipdrop.html_parser.process_html_images')
    def test_extract_content_full_flow(self, mock_process):
        """Test full extraction flow."""
        html = '''
        <html>
            <body>
                <h1>Article Title</h1>
                <p>Some content here.</p>
                <img src="https://example.com/img.jpg" alt="Image">
            </body>
        </html>
        '''

        mock_img = Image.new('RGB', (10, 10))
        mock_process.return_value = [mock_img]

        text, images = html_parser.extract_content_from_html(html)

        assert 'Article Title' in text
        assert 'Some content here' in text
        assert len(images) == 1
        assert images[0] == mock_img

    def test_extract_content_empty_html(self):
        """Test extraction from empty HTML."""
        text, images = html_parser.extract_content_from_html('')
        assert text == ''
        assert images == []

    def test_extract_content_none_html(self):
        """Test extraction from None."""
        text, images = html_parser.extract_content_from_html(None)
        assert text == ''
        assert images == []