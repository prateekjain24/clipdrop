"""Tests for the --rich CLI flag (Markdown → rich text clipboard)."""

import os
from unittest.mock import patch
from typer.testing import CliRunner

from clipdrop.main import app


runner = CliRunner()

SAMPLE_MD = "# Title\n\nSome **bold** text.\n"


class TestRichFlag:
    """Test --rich flag routing and behavior."""

    @patch('clipdrop.clipboard.copy_rich_text_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_rich_flag_copies_html(self, mock_get, mock_copy):
        mock_get.return_value = SAMPLE_MD

        result = runner.invoke(app, ["--rich"])

        assert result.exit_code == 0
        assert "Rich text copied" in result.stdout
        html, = mock_copy.call_args.args
        assert "<h1>Title</h1>" in html
        assert "<strong>bold</strong>" in html
        assert mock_copy.call_args.kwargs['plain_text'] == SAMPLE_MD

    @patch('clipdrop.clipboard.copy_rich_text_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_short_flag_works(self, mock_get, mock_copy):
        mock_get.return_value = SAMPLE_MD

        result = runner.invoke(app, ["-r"])

        assert result.exit_code == 0
        assert mock_copy.called

    @patch('clipdrop.clipboard.get_text')
    def test_empty_clipboard_errors(self, mock_get):
        mock_get.return_value = None

        result = runner.invoke(app, ["--rich"])

        assert result.exit_code == 1
        assert "clipboard is empty" in result.stdout

    @patch('clipdrop.clipboard.copy_rich_text_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_non_markdown_warns_but_converts(self, mock_get, mock_copy):
        mock_get.return_value = "just a plain sentence with no markdown at all"

        result = runner.invoke(app, ["--rich"])

        assert result.exit_code == 0
        assert "doesn't look like Markdown" in result.stdout
        assert mock_copy.called

    @patch('clipdrop.clipboard.copy_rich_text_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_filename_saves_html_file(self, mock_get, mock_copy, temp_directory):
        mock_get.return_value = SAMPLE_MD

        cwd = os.getcwd()
        os.chdir(temp_directory)
        try:
            result = runner.invoke(app, ["--rich", "page"])
        finally:
            os.chdir(cwd)

        assert result.exit_code == 0
        output = temp_directory / "page.html"
        assert output.exists()
        assert "<h1>Title</h1>" in output.read_text()
        assert mock_copy.called

    @patch('clipdrop.clipboard.copy_rich_text_to_clipboard')
    @patch('clipdrop.macos_ai.check_audio_in_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_rich_branches_before_audio_detection(
        self, mock_get, mock_audio, mock_copy
    ):
        """--rich must win even when the clipboard holds audio."""
        mock_get.return_value = SAMPLE_MD
        mock_audio.return_value = True

        result = runner.invoke(app, ["--rich"])

        assert result.exit_code == 0
        assert mock_copy.called
        assert not mock_audio.called

    @patch('clipdrop.clipboard.copy_rich_text_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_clipboard_write_failure_errors(self, mock_get, mock_copy):
        from clipdrop.exceptions import ClipboardAccessError

        mock_get.return_value = SAMPLE_MD
        mock_copy.side_effect = ClipboardAccessError("osascript failed")

        result = runner.invoke(app, ["--rich"])

        assert result.exit_code == 1
        assert "osascript failed" in result.stdout

    @patch('clipdrop.clipboard.copy_rich_text_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_preview_with_yes_skips_confirm(self, mock_get, mock_copy):
        mock_get.return_value = SAMPLE_MD

        result = runner.invoke(app, ["--rich", "--preview", "--yes"])

        assert result.exit_code == 0
        assert "preview" in result.stdout.lower()
        assert mock_copy.called

    @patch('clipdrop.clipboard.copy_rich_text_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_preview_decline_cancels(self, mock_get, mock_copy):
        mock_get.return_value = SAMPLE_MD

        with patch('clipdrop.main.Confirm.ask', return_value=False):
            result = runner.invoke(app, ["--rich", "--preview"])

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout
        assert not mock_copy.called
