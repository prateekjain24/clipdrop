"""Tests for YouTube CLI integration."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open
import pytest
from typer.testing import CliRunner
from clipdrop.main import app
from clipdrop.exceptions import YouTubeError, NoCaptionsError, YTDLPNotFoundError


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

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.get_video_info')
    @patch('clipdrop.youtube.list_captions')
    @patch('clipdrop.youtube.select_caption_track')
    @patch('clipdrop.youtube.download_vtt')
    @patch('builtins.open', new_callable=mock_open, read_data='WEBVTT\n\n00:00.000 --> 00:05.000\nTest caption')
    @patch('clipdrop.files.write_text')
    def test_youtube_with_custom_filename(self, mock_write, mock_file, mock_download, mock_select, mock_list, mock_info, mock_clipboard):
        """Test --youtube with filename argument."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Mock YouTube functions
        mock_info.return_value = {
            'title': 'Test Video',
            'id': 'dQw4w9WgXcQ',
            'uploader': 'TestUser',
            'chapters': None
        }
        mock_list.return_value = [
            ('en', 'English', False)
        ]
        mock_select.return_value = ('en', 'English', False)
        mock_download.return_value = '/tmp/test.vtt'

        result = runner.invoke(app, ["--youtube", "custom_name.txt"])

        assert result.exit_code == 0
        mock_write.assert_called_once()
        assert "custom_name.txt" in mock_write.call_args[0][0]

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.get_video_info')
    @patch('clipdrop.youtube.list_captions')
    @patch('clipdrop.youtube.select_caption_track')
    @patch('clipdrop.youtube.download_vtt')
    @patch('builtins.open', new_callable=mock_open, read_data='WEBVTT\n\n00:00.000 --> 00:05.000\nTest caption')
    @patch('clipdrop.files.write_text')
    def test_youtube_without_filename(self, mock_write, mock_file, mock_download, mock_select, mock_list, mock_info, mock_clipboard):
        """Test auto-naming from video title when no filename provided."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Mock YouTube functions
        mock_info.return_value = {
            'title': 'My Test Video Title',
            'id': 'dQw4w9WgXcQ',
            'uploader': 'TestUser',
            'chapters': None
        }
        mock_list.return_value = [
            ('en', 'English', False)
        ]
        mock_select.return_value = ('en', 'English', False)
        mock_download.return_value = '/tmp/test.vtt'

        result = runner.invoke(app, ["--youtube"])

        assert result.exit_code == 0
        mock_write.assert_called_once()
        # Title should be sanitized and used as filename
        assert "My_Test_Video_Title" in mock_write.call_args[0][0]


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
    @patch('clipdrop.youtube.get_video_info')
    @patch('clipdrop.youtube.list_captions')
    @patch('clipdrop.youtube.select_caption_track')
    def test_language_not_found(self, mock_select, mock_list, mock_info, mock_clipboard):
        """Test error when requested language not available."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        mock_info.return_value = {
            'title': 'Test Video',
            'id': 'dQw4w9WgXcQ'
        }
        mock_list.return_value = [
            ('en', 'English', False),
            ('es', 'Spanish', True)
        ]
        # Return None when language not found
        mock_select.return_value = None

        result = runner.invoke(app, ["--youtube", "--lang", "fr"])

        assert "No captions found for language: 'fr'" in result.stdout
        assert "Available languages:" in result.stdout
        assert "en: English" in result.stdout
        assert "es: Spanish (auto-generated)" in result.stdout
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


class TestYouTubeSuccessFlow:
    """Test successful YouTube download flows."""

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.subprocess.run')
    @patch('clipdrop.youtube.check_ytdlp_installed')
    @patch('builtins.open', new_callable=mock_open, read_data='WEBVTT\n\n00:00.000 --> 00:05.000\nHello world')
    @patch('clipdrop.files.write_text')
    @patch('pathlib.Path.exists')
    def test_successful_download_srt(self, mock_exists, mock_write, mock_file, mock_check, mock_run, mock_clipboard):
        """Test successful SRT format download."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        mock_check.return_value = (True, "yt-dlp found")
        mock_exists.return_value = True  # VTT cache exists

        # Mock video info
        info_result = MagicMock()
        info_result.returncode = 0
        info_result.stdout = '"Test Video"\n"dQw4w9WgXcQ"\n"TestUser"\n300\n"20240101"\n"Description"\n1000\n50\nnull'

        # Mock caption list
        caption_result = MagicMock()
        caption_result.returncode = 0
        caption_result.stdout = json.dumps([
            {"language": "en", "ext": "vtt", "name": "English", "automatic": False}
        ])

        mock_run.side_effect = [info_result, caption_result]

        result = runner.invoke(app, ["--youtube", "output.srt"])

        assert result.exit_code == 0
        assert "Found YouTube video: dQw4w9WgXcQ" in result.stdout
        assert "Selected: English (manual)" in result.stdout
        mock_write.assert_called_once()
        # Check SRT conversion happened
        call_args = mock_write.call_args[0]
        assert "output.srt" in call_args[0]
        # SRT format should have sequence numbers
        assert "1\n" in call_args[1]
        assert "00:00:00,000 --> 00:00:05,000" in call_args[1]

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.subprocess.run')
    @patch('clipdrop.youtube.check_ytdlp_installed')
    @patch('builtins.open', new_callable=mock_open)
    @patch('clipdrop.files.write_text')
    @patch('pathlib.Path.exists')
    def test_successful_download_with_chapters(self, mock_exists, mock_write, mock_file, mock_check, mock_run, mock_clipboard):
        """Test successful download with chapters."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        mock_check.return_value = (True, "yt-dlp found")
        mock_exists.return_value = True  # VTT cache exists
        mock_file.return_value.read.return_value = 'WEBVTT\n\n00:00.000 --> 00:05.000\nHello world'

        # Mock video info with chapters
        info_result = MagicMock()
        info_result.returncode = 0
        chapters_json = json.dumps([{"title": "Introduction", "start_time": 0}, {"title": "Main Content", "start_time": 60}])
        info_result.stdout = f'"Test Video"\n"dQw4w9WgXcQ"\n"TestUser"\n300\n"20240101"\n"Description"\n1000\n50\n{chapters_json}'

        # Mock caption list
        caption_result = MagicMock()
        caption_result.returncode = 0
        caption_result.stdout = json.dumps([
            {"language": "en", "ext": "vtt", "name": "English", "automatic": False}
        ])

        mock_run.side_effect = [info_result, caption_result]

        result = runner.invoke(app, ["--youtube", "--chapters", "output.txt"])

        assert result.exit_code == 0
        assert "Adding 2 chapter markers" in result.stdout
        mock_write.assert_called_once()
        # Check chapters are included
        content = mock_write.call_args[0][1]
        assert "CHAPTERS" in content
        assert "Introduction" in content
        assert "Main Content" in content

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.subprocess.run')
    @patch('clipdrop.youtube.check_ytdlp_installed')
    @patch('builtins.open', new_callable=mock_open, read_data='WEBVTT\n\n00:00.000 --> 00:05.000\nBonjour')
    @patch('clipdrop.files.write_text')
    @patch('pathlib.Path.exists')
    def test_successful_download_with_lang(self, mock_exists, mock_write, mock_file, mock_check, mock_run, mock_clipboard):
        """Test successful download with specific language."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        mock_check.return_value = (True, "yt-dlp found")
        mock_exists.return_value = True

        # Mock video info
        info_result = MagicMock()
        info_result.returncode = 0
        info_result.stdout = '"Test Video"\n"dQw4w9WgXcQ"\n"TestUser"\n300\n"20240101"\n"Description"\n1000\n50\nnull'

        # Mock caption list with multiple languages
        caption_result = MagicMock()
        caption_result.returncode = 0
        caption_result.stdout = json.dumps([
            {"language": "en", "ext": "vtt", "name": "English", "automatic": False},
            {"language": "fr", "ext": "vtt", "name": "French", "automatic": False}
        ])

        mock_run.side_effect = [info_result, caption_result]

        result = runner.invoke(app, ["--youtube", "--lang", "fr"])

        assert result.exit_code == 0
        assert "Selected: French (manual)" in result.stdout
        mock_write.assert_called_once()


class TestYouTubeParanoidMode:
    """Test YouTube paranoid mode integration."""

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.subprocess.run')
    @patch('clipdrop.youtube.check_ytdlp_installed')
    @patch('builtins.open', new_callable=mock_open, read_data='WEBVTT\n\n00:00.000 --> 00:05.000\nMy password is secret123')
    @patch('clipdrop.files.write_text')
    @patch('pathlib.Path.exists')
    def test_paranoid_mode_with_transcript(self, mock_exists, mock_write, mock_file, mock_check, mock_run, mock_clipboard):
        """Test paranoid mode applies to transcript text formats."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        mock_check.return_value = (True, "yt-dlp found")
        mock_exists.return_value = True

        # Mock video info
        info_result = MagicMock()
        info_result.returncode = 0
        info_result.stdout = '"Test Video"\n"dQw4w9WgXcQ"\n"TestUser"\n300\n"20240101"\n"Description"\n1000\n50\nnull'

        # Mock caption list
        caption_result = MagicMock()
        caption_result.returncode = 0
        caption_result.stdout = json.dumps([
            {"language": "en", "ext": "vtt", "name": "English", "automatic": False}
        ])

        mock_run.side_effect = [info_result, caption_result]

        result = runner.invoke(app, ["--youtube", "--paranoid", "redact", "output.txt"])

        assert result.exit_code == 0
        mock_write.assert_called_once()
        # Content should be redacted
        content = mock_write.call_args[0][1]
        assert "secret123" not in content
        assert "[REDACTED]" in content

    @patch('clipdrop.clipboard.get_text')
    @patch('clipdrop.youtube.subprocess.run')
    @patch('clipdrop.youtube.check_ytdlp_installed')
    @patch('builtins.open', new_callable=mock_open, read_data='WEBVTT\n\n00:00.000 --> 00:05.000\nMy password is secret123')
    @patch('clipdrop.files.write_text')
    @patch('pathlib.Path.exists')
    def test_paranoid_skip_for_vtt(self, mock_exists, mock_write, mock_file, mock_check, mock_run, mock_clipboard):
        """Test paranoid mode is skipped for VTT format."""
        mock_clipboard.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        mock_check.return_value = (True, "yt-dlp found")
        mock_exists.return_value = True

        # Mock video info
        info_result = MagicMock()
        info_result.returncode = 0
        info_result.stdout = '"Test Video"\n"dQw4w9WgXcQ"\n"TestUser"\n300\n"20240101"\n"Description"\n1000\n50\nnull'

        # Mock caption list
        caption_result = MagicMock()
        caption_result.returncode = 0
        caption_result.stdout = json.dumps([
            {"language": "en", "ext": "vtt", "name": "English", "automatic": False}
        ])

        mock_run.side_effect = [info_result, caption_result]

        result = runner.invoke(app, ["--youtube", "--paranoid", "redact", "output.vtt"])

        assert result.exit_code == 0
        mock_write.assert_called_once()
        # VTT format should preserve original content
        content = mock_write.call_args[0][1]
        assert "secret123" in content  # Original content preserved
        assert "[REDACTED]" not in content