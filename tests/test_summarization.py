import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clipdrop import detect
from clipdrop.main import app
from clipdrop.macos_ai import SummaryResult, SummarizationNotAvailableError, summarize_content

runner = CliRunner()


def test_is_summarizable_content_allows_text():
    content = "Lorem ipsum " * 300
    is_ok, reason = detect.is_summarizable_content(content, "txt")
    assert is_ok
    assert reason == ""


def test_is_summarizable_content_blocks_code():
    code_content = "\n".join([
        "def hello():",
        "    print('hi')",
        "",
        "def goodbye():",
        "    return 'bye'",
    ]) * 20
    is_ok, reason = detect.is_summarizable_content(code_content, "txt")
    assert is_ok is False
    assert "code" in reason.lower()


def test_summarize_content_short_text_returns_error():
    result = summarize_content("Too short")
    assert result.success is False
    assert "too short" in result.error.lower()


def test_summarize_content_helper_missing(monkeypatch):
    from clipdrop import macos_ai

    def fake_get_helper(_name: str):
        raise SummarizationNotAvailableError("Not available")

    monkeypatch.setattr(macos_ai, "get_swift_helper_path", fake_get_helper)

    content = "word " * 300
    result = macos_ai.summarize_content(content)
    assert result.success is False
    assert "Not available" in result.error


def test_summarize_content_success(monkeypatch, tmp_path):
    from clipdrop import macos_ai

    helper_path = tmp_path / "clipdrop-summarize"
    helper_path.write_text("binary")

    monkeypatch.setattr(
        macos_ai,
        "get_swift_helper_path",
        lambda name: helper_path,
    )

    def fake_run(*_args, **_kwargs):
        return macos_ai.subprocess.CompletedProcess(
            args=[str(helper_path)],
            returncode=0,
            stdout=json.dumps({"success": True, "summary": "Hello world"}),
            stderr="",
        )

    monkeypatch.setattr(macos_ai.subprocess, "run", fake_run)

    content = "word " * 300
    result = macos_ai.summarize_content(content)

    assert result.success is True
    assert result.summary == "Hello world"


def test_summarize_content_failure(monkeypatch, tmp_path):
    from clipdrop import macos_ai

    helper_path = tmp_path / "clipdrop-summarize"
    helper_path.write_text("binary")

    monkeypatch.setattr(
        macos_ai,
        "get_swift_helper_path",
        lambda name: helper_path,
    )

    def fake_run(*_args, **_kwargs):
        return macos_ai.subprocess.CompletedProcess(
            args=[str(helper_path)],
            returncode=1,
            stdout=json.dumps({"success": False, "error": "Model busy"}),
            stderr="",
        )

    monkeypatch.setattr(macos_ai.subprocess, "run", fake_run)

    content = "word " * 300
    result = macos_ai.summarize_content(content)

    assert result.success is False
    assert "Model busy" in result.error


@pytest.fixture(autouse=True)
def mock_clipboard_for_summary(monkeypatch):
    from clipdrop import main as clipdrop_main

    sample = ("Sentence " * 80).strip()

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


def test_cli_summarize_appends_summary(monkeypatch):
    summary_text = "Concise summary"

    monkeypatch.setattr(
        "clipdrop.main.summarize_content",
        lambda _content: SummaryResult(success=True, summary=summary_text),
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["notes", "--summarize"])
        assert result.exit_code == 0

        saved = Path("notes.txt").read_text(encoding="utf-8")
        assert "## Summary" in saved
        assert summary_text in saved


def test_cli_summarize_handles_failure(monkeypatch):
    monkeypatch.setattr(
        "clipdrop.main.summarize_content",
        lambda _content: SummaryResult(success=False, error="helper unavailable"),
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["report", "--summarize"])
        assert result.exit_code == 0

        saved = Path("report.txt").read_text(encoding="utf-8")
        assert "## Summary" not in saved
