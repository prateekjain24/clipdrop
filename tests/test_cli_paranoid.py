from pathlib import Path

import pytest
from typer.testing import CliRunner

from clipdrop.main import app


runner = CliRunner()


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

    with runner.isolated_filesystem():
        result = runner.invoke(app, [filename, "--paranoid=redact"])

        assert result.exit_code == 0

        saved = Path(filename).read_text(encoding="utf-8")
        assert "[REDACTED:SK_TOKEN]" in saved


def test_cli_paranoid_block():
    filename = "secrets.txt"

    with runner.isolated_filesystem():
        result = runner.invoke(app, [filename, "--paranoid=block"])

        assert result.exit_code == 17
        assert not Path(filename).exists()


def test_cli_paranoid_prompt_yes():
    filename = "notes.txt"

    with runner.isolated_filesystem():
        result = runner.invoke(app, [filename, "-p", "--yes"])

        assert result.exit_code == 0

        saved = Path(filename).read_text(encoding="utf-8")
        assert "sk-ABCDEFGHIJKLMNOPQRSTUVWX" in saved


def test_cli_paranoid_warn():
    filename = "warn.txt"

    with runner.isolated_filesystem():
        result = runner.invoke(app, [filename, "--paranoid=warn"])

        assert result.exit_code == 0
        saved = Path(filename).read_text(encoding="utf-8")
        assert "sk-ABCDEFGHIJKLMNOPQRSTUVWX" in saved
