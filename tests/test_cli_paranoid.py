import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clipdrop.main import app


runner = CliRunner()


@contextmanager
def isolated_filesystem():
    """Run a block inside a fresh temp directory.

    Drop-in replacement for ``CliRunner.isolated_filesystem``, which was
    removed in Click 8.4 (pulled in via Typer).
    """
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            yield Path(tmp)
        finally:
            os.chdir(cwd)


@pytest.fixture(autouse=True)
def mock_clipboard(monkeypatch):
    from clipdrop import main as clipdrop_main

    sample = '{"token": "sk-ABCDEFGHIJKLMNOPQRSTUVWX"}'

    monkeypatch.setattr(clipdrop_main.clipboard, "get_content_type", lambda: "text")
    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: sample)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image", lambda: None)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image_info", lambda: None)
    monkeypatch.setattr(
        clipdrop_main.clipboard,
        "get_content_preview",
        lambda max_chars=200: sample[:max_chars],
    )

    yield


def test_cli_paranoid_redact():
    filename = "data.json"

    with isolated_filesystem():
        result = runner.invoke(app, [filename, "--scan-mode", "redact"])

        assert result.exit_code == 0

        saved = Path(filename).read_text(encoding="utf-8")
        assert "[REDACTED:SK_TOKEN]" in saved


def test_cli_paranoid_block():
    filename = "secrets.txt"

    with isolated_filesystem():
        result = runner.invoke(app, [filename, "--scan-mode", "block"])

        assert result.exit_code == 17
        assert not Path(filename).exists()


def test_cli_paranoid_prompt_yes():
    filename = "notes.txt"

    with isolated_filesystem():
        result = runner.invoke(app, [filename, "-s", "--yes"])

        assert result.exit_code == 0

        saved = Path(filename).read_text(encoding="utf-8")
        assert "sk-ABCDEFGHIJKLMNOPQRSTUVWX" in saved


def test_cli_paranoid_warn():
    filename = "warn.txt"

    with isolated_filesystem():
        result = runner.invoke(app, [filename, "--scan-mode", "warn"])

        assert result.exit_code == 0
        saved = Path(filename).read_text(encoding="utf-8")
        assert "sk-ABCDEFGHIJKLMNOPQRSTUVWX" in saved
