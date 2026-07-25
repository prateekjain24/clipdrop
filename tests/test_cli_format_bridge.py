"""Tests for the --plain and --md CLI flags (clipboard format bridge)."""

import os
from unittest.mock import patch
from typer.testing import CliRunner

from clipdrop.main import app


runner = CliRunner()

SAMPLE_MD = "# Title\n\nSome **bold** text and a [link](https://example.com/x).\n"
SAMPLE_HTML = '<h1>Title</h1><p>Some <strong>bold</strong> text.</p>'


class TestPlainFlag:
    """Test --plain: markdown → clean plain text."""

    @patch('clipdrop.clipboard.copy_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_plain_strips_markdown_and_copies(self, mock_get, mock_copy):
        mock_get.return_value = SAMPLE_MD

        result = runner.invoke(app, ["--plain"])

        assert result.exit_code == 0
        assert "Plain text copied" in result.stdout
        copied, = mock_copy.call_args.args
        assert "Title" in copied
        assert "bold" in copied
        for token in ("#", "**", "]("):
            assert token not in copied

    @patch('clipdrop.clipboard.copy_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_short_flag(self, mock_get, mock_copy):
        mock_get.return_value = SAMPLE_MD

        result = runner.invoke(app, ["-P"])

        assert result.exit_code == 0
        assert mock_copy.called

    @patch('clipdrop.clipboard.get_text')
    def test_empty_clipboard_errors(self, mock_get):
        mock_get.return_value = None

        result = runner.invoke(app, ["--plain"])

        assert result.exit_code == 1
        assert "clipboard is empty" in result.stdout

    @patch('clipdrop.clipboard.copy_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_filename_saves_txt(self, mock_get, mock_copy, temp_directory):
        mock_get.return_value = SAMPLE_MD

        cwd = os.getcwd()
        os.chdir(temp_directory)
        try:
            result = runner.invoke(app, ["--plain", "note"])
        finally:
            os.chdir(cwd)

        assert result.exit_code == 0
        output = temp_directory / "note.txt"
        assert output.exists()
        assert "Title" in output.read_text()

    @patch('clipdrop.clipboard.copy_to_clipboard')
    @patch('clipdrop.clipboard.get_text')
    def test_preview_decline_cancels(self, mock_get, mock_copy):
        mock_get.return_value = SAMPLE_MD

        with patch('clipdrop.main.Confirm.ask', return_value=False):
            result = runner.invoke(app, ["--plain", "--preview"])

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout
        assert not mock_copy.called


class TestMdFlag:
    """Test --md: rich clipboard HTML → markdown."""

    @patch('clipdrop.clipboard.copy_to_clipboard')
    @patch('clipdrop.html_parser.get_html_from_clipboard')
    def test_md_converts_html_and_copies(self, mock_html, mock_copy):
        mock_html.return_value = SAMPLE_HTML

        result = runner.invoke(app, ["--md"])

        assert result.exit_code == 0
        assert "Markdown copied" in result.stdout
        copied, = mock_copy.call_args.args
        assert "# Title" in copied
        assert "**bold**" in copied

    @patch('clipdrop.clipboard.copy_to_clipboard')
    @patch('clipdrop.html_parser.get_html_from_clipboard')
    def test_short_flag(self, mock_html, mock_copy):
        mock_html.return_value = SAMPLE_HTML

        result = runner.invoke(app, ["-M"])

        assert result.exit_code == 0
        assert mock_copy.called

    @patch('clipdrop.html_parser.get_html_from_clipboard')
    def test_no_html_flavor_errors(self, mock_html):
        mock_html.return_value = None

        result = runner.invoke(app, ["--md"])

        assert result.exit_code == 1
        assert "No rich text" in result.stdout

    @patch('clipdrop.clipboard.copy_to_clipboard')
    @patch('clipdrop.html_parser.get_html_from_clipboard')
    def test_filename_saves_md(self, mock_html, mock_copy, temp_directory):
        mock_html.return_value = SAMPLE_HTML

        cwd = os.getcwd()
        os.chdir(temp_directory)
        try:
            result = runner.invoke(app, ["--md", "page"])
        finally:
            os.chdir(cwd)

        assert result.exit_code == 0
        output = temp_directory / "page.md"
        assert output.exists()
        assert "# Title" in output.read_text()

    @patch('clipdrop.clipboard.copy_to_clipboard')
    @patch('clipdrop.html_parser.get_html_from_clipboard')
    def test_secret_scan_runs_on_converted_markdown(self, mock_html, mock_copy):
        """--md with --scan-mode redact must redact secrets in the output."""
        mock_html.return_value = (
            '<p>key: AKIAIOSFODNN7EXAMPLE</p>'
        )

        result = runner.invoke(app, ["--md", "--scan-mode", "redact"])

        assert result.exit_code == 0
        copied, = mock_copy.call_args.args
        assert "AKIAIOSFODNN7EXAMPLE" not in copied


class TestModeExclusivity:
    """Bridge modes can't be combined."""

    def test_rich_and_plain_conflict(self):
        result = runner.invoke(app, ["--rich", "--plain"])
        assert result.exit_code == 1
        assert "can't be combined" in result.stdout

    def test_plain_and_md_conflict(self):
        result = runner.invoke(app, ["--plain", "--md"])
        assert result.exit_code == 1
        assert "can't be combined" in result.stdout

    def test_all_three_conflict(self):
        result = runner.invoke(app, ["--rich", "--plain", "--md"])
        assert result.exit_code == 1
        assert "can't be combined" in result.stdout
