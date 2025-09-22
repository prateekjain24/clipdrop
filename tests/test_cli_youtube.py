"""Tests for YouTube CLI integration."""

import json
from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner
from clipdrop.main import app


runner = CliRunner()


class TestYouTubeCLIFlags:
    """Test YouTube CLI flag handling."""

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.subprocess.run')
    @patch('clipdrop.youtube.check_ytdlp_installed')
    def test_youtube_flag_triggers_handler(self, mock_check, mock_run, mock_clipboard):
        """Test --youtube flag routes to handle_youtube_transcript."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        mock_check.return_value = (True, "yt-dlp found")

        # Mock yt-dlp responses
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '"Test Video"\n"dQw4w9WgXcQ"\n"TestUser"\n300\n"20240101"\n"Description"\n1000\n50\nnull'
        mock_run.return_value = mock_result

        result = runner.invoke(app, ["--youtube"])

        assert "Found YouTube video: dQw4w9WgXcQ" in result.stdout
        assert result.exit_code == 1  # Will fail on caption listing

    @patch('clipdrop.clipboard.get_text')
    def test_yt_short_flag_works(self, mock_clipboard):
        """Test -yt alias works."""
        mock_clipboard.return_value = "not a youtube url"

        result = runner.invoke(app, ["-yt"])

        assert "No YouTube URL in clipboard" in result.stdout
        assert result.exit_code == 1


class TestYouTubeErrorMessages:
    """Test YouTube error handling and messages."""

    def test_no_url_in_clipboard(self):
        """Test error when clipboard is empty."""
        with patch('clipdrop.clipboard.get_text', return_value=""):
            result = runner.invoke(app, ["--youtube"])

            assert "Your clipboard is empty" in result.stdout
            assert result.exit_code == 1

    def test_invalid_url_in_clipboard(self):
        """Test error when clipboard has non-YouTube URL."""
        with patch('clipdrop.clipboard.get_text', return_value="https://example.com"):
            result = runner.invoke(app, ["--youtube"])

            assert "No YouTube URL in clipboard" in result.stdout
            assert result.exit_code == 1

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.get_video_info')
    @patch('clipdrop.youtube.list_captions')
    def test_no_captions_available(self, mock_list, mock_info, mock_clipboard):
        """Test error when video has no captions."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        mock_info.return_value = {
            'title': 'Test Video',
            'id': 'dQw4w9WgXcQ'
        }
        # Return empty caption list
        mock_list.return_value = []

        result = runner.invoke(app, ["--youtube"])

        assert "No captions available" in result.stdout
        assert result.exit_code == 1

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.check_ytdlp_installed')
    def test_ytdlp_not_installed(self, mock_check, mock_clipboard):
        """Test error when yt-dlp is not installed."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        mock_check.return_value = (False, "yt-dlp not found")

        result = runner.invoke(app, ["--youtube"])

        assert "yt-dlp is not installed" in result.stdout
        assert result.exit_code == 1