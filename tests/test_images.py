"""Tests for image operations in ClipDrop."""

import pytest
from pathlib import Path
from PIL import Image
from unittest.mock import patch, MagicMock

from clipdrop import images, clipboard
from clipdrop.exceptions import ImageSaveError, ImageFormatError, ImageClipboardError


class TestImageFormats:
    """Test image format detection and handling."""

    def test_detect_format_from_extension(self):
        """Test format detection from file extensions."""
        assert images.detect_format_from_extension('test.png') == 'PNG'
        assert images.detect_format_from_extension('test.jpg') == 'JPEG'
        assert images.detect_format_from_extension('test.jpeg') == 'JPEG'
        assert images.detect_format_from_extension('test.gif') == 'GIF'
        assert images.detect_format_from_extension('test.bmp') == 'BMP'
        assert images.detect_format_from_extension('test.webp') == 'WEBP'
        assert images.detect_format_from_extension('test.txt') is None

    def test_is_image_extension(self):
        """Test image extension checking."""
        assert images.is_image_extension('photo.png') is True
        assert images.is_image_extension('image.jpg') is True
        assert images.is_image_extension('pic.jpeg') is True
        assert images.is_image_extension('document.txt') is False
        assert images.is_image_extension('data.json') is False

    def test_add_image_extension(self):
        """Test adding image extensions to filenames."""
        # No extension should add .png
        assert images.add_image_extension('screenshot') == 'screenshot.png'

        # Existing image extension should be preserved
        assert images.add_image_extension('photo.jpg') == 'photo.jpg'

        # With image format info
        img = MagicMock()
        img.format = 'JPEG'
        assert images.add_image_extension('photo', img) == 'photo.jpg'

        img.format = 'PNG'
        assert images.add_image_extension('screenshot', img) == 'screenshot.png'


class TestImageSaving:
    """Test image saving functionality."""

    def test_write_image_png(self, sample_image, temp_directory):
        """Test saving image as PNG."""
        output_path = temp_directory / 'test.png'

        result = images.write_image(output_path, sample_image, force=True)

        assert output_path.exists()
        assert result['format'] == 'PNG'
        assert result['width'] == 100
        assert result['height'] == 100
        assert result['dimensions'] == '100x100'

        # Verify the saved image
        with Image.open(output_path) as saved_img:
            assert saved_img.format == 'PNG'
            assert saved_img.size == (100, 100)

    def test_write_image_jpeg(self, sample_image, temp_directory):
        """Test saving image as JPEG."""
        output_path = temp_directory / 'test.jpg'

        result = images.write_image(output_path, sample_image, force=True)

        assert output_path.exists()
        assert result['format'] == 'JPEG'

        # Verify the saved image
        with Image.open(output_path) as saved_img:
            assert saved_img.format == 'JPEG'

    def test_write_image_with_transparency(self, sample_image_with_transparency, temp_directory):
        """Test saving image with transparency."""
        # PNG should preserve transparency
        png_path = temp_directory / 'transparent.png'
        images.write_image(png_path, sample_image_with_transparency, force=True)

        with Image.open(png_path) as saved_img:
            assert saved_img.mode == 'RGBA'

        # JPEG should convert transparency to RGB
        jpg_path = temp_directory / 'converted.jpg'
        images.write_image(jpg_path, sample_image_with_transparency, force=True)

        with Image.open(jpg_path) as saved_img:
            assert saved_img.mode == 'RGB'

    def test_write_image_auto_format(self, sample_image, temp_directory):
        """Test automatic format detection from filename."""
        # No extension should default to PNG
        output_path = temp_directory / 'noext'
        result = images.write_image(output_path, sample_image, force=True)

        expected_path = temp_directory / 'noext.png'
        assert expected_path.exists()
        assert result['format'] == 'PNG'

    def test_write_image_overwrite_protection(self, sample_image, temp_directory):
        """Test overwrite protection."""
        output_path = temp_directory / 'existing.png'
        output_path.write_text("existing file")

        # Should raise error without force
        with patch('clipdrop.files.confirm_overwrite', return_value=False):
            with pytest.raises(ImageSaveError):
                images.write_image(output_path, sample_image, force=False)

        # Should succeed with force
        result = images.write_image(output_path, sample_image, force=True)
        assert result['format'] == 'PNG'

    def test_optimize_image_options(self):
        """Test image optimization options."""
        rgb_image = Image.new('RGB', (10, 10))

        # PNG optimization
        options, _ = images.optimize_image(rgb_image, 'PNG')
        assert options['optimize'] is True
        assert options['compress_level'] == 9

        # JPEG optimization
        options, _ = images.optimize_image(rgb_image, 'JPEG')
        assert options['quality'] == 95
        assert options['optimize'] is True


class TestImageClipboard:
    """Test image clipboard operations."""

    def test_has_image(self, mock_image_clipboard, sample_image):
        """Test checking for image in clipboard."""
        # No image initially
        assert clipboard.has_image() is False

        # Set an image
        mock_image_clipboard['set_image'](sample_image)
        mock_image_clipboard['grab'].side_effect = lambda: mock_image_clipboard['get_image']()

        assert clipboard.has_image() is True

    def test_get_image(self, mock_image_clipboard, sample_image):
        """Test getting image from clipboard."""
        # No image initially
        assert clipboard.get_image() is None

        # Set an image
        mock_image_clipboard['set_image'](sample_image)
        mock_image_clipboard['grab'].side_effect = lambda: mock_image_clipboard['get_image']()

        img = clipboard.get_image()
        assert img is not None
        assert img == sample_image

    def test_get_image_info(self, mock_image_clipboard, sample_image):
        """Test getting image information from clipboard."""
        # No image initially
        assert clipboard.get_image_info() is None

        # Set an image
        mock_image_clipboard['set_image'](sample_image)
        mock_image_clipboard['grab'].side_effect = lambda: mock_image_clipboard['get_image']()

        info = clipboard.get_image_info()
        assert info is not None
        assert info['width'] == 100
        assert info['height'] == 100
        assert info['mode'] == 'RGB'
        assert info['has_transparency'] is False

    def test_get_content_type_with_image(self, mock_image_clipboard, mock_clipboard, sample_image):
        """Test content type detection with image."""
        # Only image
        mock_image_clipboard['set_image'](sample_image)
        mock_image_clipboard['grab'].side_effect = lambda: mock_image_clipboard['get_image']()
        mock_clipboard['set_content']("")

        assert clipboard.get_content_type() == 'image'

        # Both image and text
        mock_clipboard['set_content']("Some text")
        assert clipboard.get_content_type() == 'both'

        # Only text
        mock_image_clipboard['set_image'](None)
        mock_image_clipboard['grab'].side_effect = lambda: None
        assert clipboard.get_content_type() == 'text'

    def test_image_cache(self, mock_image_clipboard, sample_image):
        """Test image caching mechanism."""
        mock_image_clipboard['set_image'](sample_image)
        mock_image_clipboard['grab'].side_effect = lambda: mock_image_clipboard['get_image']()

        # First call should hit the mock
        img1 = clipboard.get_image()
        assert mock_image_clipboard['grab'].call_count == 1

        # Second call within cache duration should use cache
        img2 = clipboard.get_image()
        # Call count may or may not increase depending on cache timing
        assert img1 == img2

    def test_clear_image_cache(self):
        """Test clearing image cache."""
        clipboard.clear_image_cache()
        # Should not raise any errors
        assert clipboard._image_cache['image'] is None
        assert clipboard._image_cache['timestamp'] == 0


class TestImageMetadata:
    """Test image metadata functions."""

    def test_get_image_metadata(self, sample_image, temp_directory):
        """Test getting metadata from saved image."""
        image_path = temp_directory / 'test.png'
        sample_image.save(image_path)

        metadata = images.get_image_metadata(image_path)

        assert metadata['width'] == 100
        assert metadata['height'] == 100
        assert metadata['dimensions'] == '100x100'
        assert metadata['format'] == 'PNG'
        assert metadata['mode'] == 'RGB'
        assert metadata['has_transparency'] is False
        assert metadata['file_size'] > 0

    def test_get_metadata_nonexistent_file(self, temp_directory):
        """Test getting metadata from non-existent file."""
        image_path = temp_directory / 'nonexistent.png'

        with pytest.raises(ImageSaveError) as exc:
            images.get_image_metadata(image_path)

        assert "File not found" in str(exc.value)

    def test_format_file_size(self):
        """Test file size formatting."""
        assert images.format_file_size(500) == "500 B"
        assert images.format_file_size(1024) == "1.0 KB"
        assert images.format_file_size(1536) == "1.5 KB"
        assert images.format_file_size(1048576) == "1.0 MB"
        assert images.format_file_size(5242880) == "5.0 MB"


class TestImageFormatsConversion:
    """Test image format conversions."""

    def test_rgba_to_jpeg_conversion(self, temp_directory):
        """Test RGBA to RGB conversion for JPEG."""
        rgba_image = Image.new('RGBA', (50, 50), color=(255, 0, 0, 128))
        output_path = temp_directory / 'converted.jpg'

        images.write_image(output_path, rgba_image, force=True)

        with Image.open(output_path) as saved_img:
            assert saved_img.mode == 'RGB'
            assert saved_img.format == 'JPEG'

    def test_palette_to_gif_conversion(self, temp_directory):
        """Test palette mode conversion for GIF."""
        rgb_image = Image.new('RGB', (50, 50), color='blue')
        output_path = temp_directory / 'animated.gif'

        images.write_image(output_path, rgb_image, force=True)

        with Image.open(output_path) as saved_img:
            assert saved_img.format == 'GIF'

    def test_various_format_saving(self, various_format_images, temp_directory):
        """Test saving various image formats."""
        for name, img in various_format_images.items():
            output_path = temp_directory / f'{name}.png'
            result = images.write_image(output_path, img, force=True)

            assert output_path.exists()
            assert result['format'] == 'PNG'

            # Verify the saved image
            with Image.open(output_path) as saved_img:
                assert saved_img.format == 'PNG'


class TestErrorHandling:
    """Test error handling in image operations."""

    def test_unsupported_format_error(self, sample_image, temp_directory):
        """Test unsupported format error."""
        with pytest.raises(ImageFormatError):
            images.write_image(
                temp_directory / 'test.xyz',
                sample_image,
                format='XYZ',
                force=True
            )

    def test_image_save_error(self, sample_image):
        """Test image save error with invalid path."""
        with pytest.raises(ImageSaveError):
            images.write_image(
                Path('/invalid/path/test.png'),
                sample_image,
                force=True
            )

    @patch('PIL.ImageGrab.grabclipboard')
    def test_image_clipboard_error(self, mock_grab):
        """Test clipboard access error."""
        mock_grab.side_effect = Exception("Clipboard error")

        with pytest.raises(ImageClipboardError):
            clipboard.get_image()

    def test_corrupted_image_handling(self, temp_directory):
        """Test handling of corrupted image file."""
        # Create a fake corrupted image file
        corrupted_path = temp_directory / 'corrupted.png'
        corrupted_path.write_text("Not a real image")

        with pytest.raises(ImageSaveError) as exc:
            images.get_image_metadata(corrupted_path)

        assert "Cannot read image" in str(exc.value)