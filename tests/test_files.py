"""Tests for file operations module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import typer

from clipdrop import files


class TestCheckExists:
    """Tests for check_exists function."""

    def test_exists_with_existing_file(self, temp_directory):
        """Test checking an existing file."""
        test_file = temp_directory / "test.txt"
        test_file.write_text("content")

        assert files.check_exists(test_file) is True

    def test_exists_with_nonexistent_file(self, temp_directory):
        """Test checking a non-existent file."""
        test_file = temp_directory / "nonexistent.txt"

        assert files.check_exists(test_file) is False

    def test_exists_with_directory(self, temp_directory):
        """Test that directories return False."""
        subdir = temp_directory / "subdir"
        subdir.mkdir()

        assert files.check_exists(subdir) is False


class TestEnsureParentDir:
    """Tests for ensure_parent_dir function."""

    def test_create_parent_directory(self, temp_directory):
        """Test creating parent directory when it doesn't exist."""
        nested_file = temp_directory / "level1" / "level2" / "file.txt"

        files.ensure_parent_dir(nested_file)

        assert nested_file.parent.exists()
        assert nested_file.parent.is_dir()

    def test_existing_parent_directory(self, temp_directory):
        """Test when parent directory already exists."""
        test_file = temp_directory / "test.txt"

        # Should not raise any exception
        files.ensure_parent_dir(test_file)
        assert test_file.parent.exists()

    def test_permission_error(self, temp_directory):
        """Test handling permission errors."""
        with patch.object(Path, 'mkdir', side_effect=PermissionError("No permission")):
            test_file = Path("/restricted/path/file.txt")

            with pytest.raises(PermissionError) as exc_info:
                files.ensure_parent_dir(test_file)

            assert "Cannot create directory" in str(exc_info.value)


class TestConfirmOverwrite:
    """Tests for confirm_overwrite function."""

    def test_confirm_yes(self, mock_confirm_prompt):
        """Test when user confirms overwrite."""
        mock_confirm_prompt.return_value = True
        test_path = Path("test.txt")

        result = files.confirm_overwrite(test_path)

        assert result is True
        mock_confirm_prompt.assert_called_once()

    def test_confirm_no(self, mock_confirm_prompt):
        """Test when user declines overwrite."""
        mock_confirm_prompt.return_value = False
        test_path = Path("test.txt")

        result = files.confirm_overwrite(test_path)

        assert result is False

    def test_confirm_prompt_message(self, mock_confirm_prompt):
        """Test that the correct prompt message is shown."""
        mock_confirm_prompt.return_value = True
        test_path = Path("important.txt")

        files.confirm_overwrite(test_path)

        call_args = mock_confirm_prompt.call_args[0][0]
        assert "important.txt" in call_args
        assert "exists" in call_args.lower()


class TestGetFileSize:
    """Tests for get_file_size function."""

    def test_size_bytes(self):
        """Test file size in bytes."""
        content = "Hello"  # 5 bytes
        result = files.get_file_size(content)
        assert result == "5 B"

    def test_size_kilobytes(self):
        """Test file size in KB."""
        content = "x" * 1500  # 1.5 KB
        result = files.get_file_size(content)
        assert result == "1.5 KB"

    def test_size_megabytes(self):
        """Test file size in MB."""
        content = "x" * 1500000  # ~1.5 MB
        result = files.get_file_size(content)
        assert result == "1.4 MB"  # Due to 1024 conversion

    def test_size_unicode(self, sample_unicode):
        """Test file size with Unicode content."""
        result = files.get_file_size(sample_unicode)
        # Unicode characters take more bytes
        assert "B" in result
        size_value = float(result.split()[0])
        assert size_value > len(sample_unicode)  # More bytes than characters

    def test_empty_content(self):
        """Test file size for empty content."""
        result = files.get_file_size("")
        assert result == "0 B"


class TestWriteText:
    """Tests for write_text function."""

    def test_write_basic(self, temp_directory):
        """Test basic file writing."""
        test_file = temp_directory / "test.txt"
        content = "Hello, World!"

        files.write_text(test_file, content, force=True)

        assert test_file.exists()
        assert test_file.read_text() == content

    def test_write_unicode(self, temp_directory, sample_unicode):
        """Test writing Unicode content."""
        test_file = temp_directory / "unicode.txt"

        files.write_text(test_file, sample_unicode, force=True)

        assert test_file.read_text(encoding='utf-8') == sample_unicode

    def test_write_create_parent_dirs(self, temp_directory):
        """Test creating parent directories during write."""
        nested_file = temp_directory / "dir1" / "dir2" / "file.txt"
        content = "Nested content"

        files.write_text(nested_file, content, force=True)

        assert nested_file.exists()
        assert nested_file.read_text() == content

    def test_write_overwrite_with_force(self, temp_directory):
        """Test overwriting existing file with force flag."""
        test_file = temp_directory / "existing.txt"
        test_file.write_text("Old content")

        files.write_text(test_file, "New content", force=True)

        assert test_file.read_text() == "New content"

    def test_write_overwrite_protection(self, temp_directory, mock_confirm_prompt):
        """Test overwrite protection without force flag."""
        test_file = temp_directory / "protected.txt"
        test_file.write_text("Original")
        mock_confirm_prompt.return_value = False

        with pytest.raises(typer.Abort):
            files.write_text(test_file, "New content", force=False)

        # Original content should remain
        assert test_file.read_text() == "Original"

    def test_write_overwrite_confirmed(self, temp_directory, mock_confirm_prompt):
        """Test overwriting when user confirms."""
        test_file = temp_directory / "confirmed.txt"
        test_file.write_text("Original")
        mock_confirm_prompt.return_value = True

        files.write_text(test_file, "New content", force=False)

        assert test_file.read_text() == "New content"

    def test_write_empty_content_error(self, temp_directory):
        """Test that empty content raises an error."""
        test_file = temp_directory / "empty.txt"

        with pytest.raises(ValueError, match="Cannot write empty content"):
            files.write_text(test_file, "", force=True)

    def test_write_json_prettification(self, temp_directory, sample_json):
        """Test JSON pretty-printing when writing .json files."""
        json_file = temp_directory / "data.json"

        files.write_text(json_file, sample_json, force=True)

        written_content = json_file.read_text()
        # Should be pretty-printed with indentation
        assert "  " in written_content  # Has indentation
        assert written_content != sample_json  # Different from compact input

        # Should be valid JSON
        parsed = json.loads(written_content)
        assert parsed["name"] == "ClipDrop Test"

    def test_write_invalid_json_as_text(self, temp_directory):
        """Test writing invalid JSON to .json file."""
        json_file = temp_directory / "invalid.json"
        invalid_json = "{this is not valid json}"

        files.write_text(json_file, invalid_json, force=True)

        # Should write as-is without prettification
        assert json_file.read_text() == invalid_json

    def test_write_path_traversal_prevention(self, temp_directory):
        """Test prevention of path traversal attacks."""
        dangerous_path = temp_directory / "../../../etc/passwd"

        with pytest.raises(ValueError, match="Path traversal not allowed"):
            files.write_text(dangerous_path, "content", force=True)

    def test_write_string_path(self, temp_directory):
        """Test writing with string path instead of Path object."""
        str_path = str(temp_directory / "string_path.txt")
        content = "String path content"

        files.write_text(str_path, content, force=True)

        assert Path(str_path).read_text() == content

    def test_write_permission_error(self, temp_directory):
        """Test handling write permission errors."""
        test_file = temp_directory / "test.txt"

        with patch.object(Path, 'write_text', side_effect=PermissionError("No write permission")):
            with pytest.raises(PermissionError, match="Cannot write to"):
                files.write_text(test_file, "content", force=True)


class TestValidateFilename:
    """Tests for validate_filename function."""

    def test_valid_filename(self):
        """Test validation of valid filenames."""
        assert files.validate_filename("test.txt") is True
        assert files.validate_filename("my-file_123.json") is True
        assert files.validate_filename("document.md") is True

    def test_invalid_characters(self):
        """Test detection of invalid characters."""
        assert files.validate_filename("file/name.txt") is False
        assert files.validate_filename("file\\name.txt") is False
        assert files.validate_filename("file:name.txt") is False
        assert files.validate_filename("file*name.txt") is False
        assert files.validate_filename("file?name.txt") is False
        assert files.validate_filename("file<name>.txt") is False
        assert files.validate_filename("file|name.txt") is False

    def test_path_traversal(self):
        """Test detection of path traversal attempts."""
        assert files.validate_filename("../etc/passwd") is False
        assert files.validate_filename("..\\windows\\system32") is False
        assert files.validate_filename("file/../other") is False

    def test_null_byte(self):
        """Test detection of null bytes."""
        assert files.validate_filename("file\x00name.txt") is False


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_sanitize_invalid_chars(self):
        """Test sanitization of invalid characters."""
        result = files.sanitize_filename("file/name:test*.txt")
        assert "/" not in result
        assert ":" not in result
        assert "*" not in result
        assert "_" in result  # Replaced with underscore

    def test_sanitize_path_traversal(self):
        """Test sanitization of path traversal."""
        result = files.sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_sanitize_empty_result(self):
        """Test handling when sanitization results in empty string."""
        # If everything is invalid
        result = files.sanitize_filename("///")
        assert result == "clipboard_content"

    def test_sanitize_preserves_valid(self):
        """Test that valid characters are preserved."""
        original = "valid-file_name.txt"
        result = files.sanitize_filename(original)
        assert result == original

    def test_sanitize_whitespace_only(self):
        """Test sanitizing whitespace-only filename."""
        result = files.sanitize_filename("   \t\n  ")
        assert result == "clipboard_content"


class TestPerformance:
    """Performance tests for file operations."""

    def test_write_large_file_performance(self, temp_directory, performance_timer):
        """Test performance of writing large files."""
        large_file = temp_directory / "large.txt"
        large_content = "x" * 10000000  # 10MB

        performance_timer.start()
        files.write_text(large_file, large_content, force=True)
        performance_timer.stop()

        # Should write 10MB reasonably quickly
        assert performance_timer.elapsed < 2.0
        assert large_file.stat().st_size > 9000000

    def test_multiple_writes_performance(self, temp_directory, performance_timer):
        """Test performance of multiple write operations."""
        content = "Test content"

        performance_timer.start()
        for i in range(100):
            test_file = temp_directory / f"file_{i}.txt"
            files.write_text(test_file, content, force=True)
        performance_timer.stop()

        # 100 small file writes should be fast
        assert performance_timer.elapsed < 5.0
        assert len(list(temp_directory.glob("*.txt"))) == 100