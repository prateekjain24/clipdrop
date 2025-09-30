import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clipdrop import detect
from clipdrop.main import app, handle_audio_transcription
from clipdrop.macos_ai import (
    SummaryResult,
    SummarizationNotAvailableError,
    summarize_content,
)

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
    summary_text = """**Overall:** Concise summary\n### Key Takeaways\n- Key point\n### Action Items\n- None\n### Questions\n- None"""

    monkeypatch.setattr(
        "clipdrop.main.summarize_content",
        lambda _content: SummaryResult(success=True, summary=summary_text),
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["notes", "--summarize"])
        assert result.exit_code == 0

        saved = Path("notes.txt").read_text(encoding="utf-8")
        assert saved.startswith("**Overall:**")
        assert "### Key Takeaways" in saved
        assert summary_text in saved
        assert "\n---\n" in saved
        _, _, body = saved.partition("\n---\n\n")
        assert body.strip().startswith("Sentence")


def test_cli_summarize_handles_failure(monkeypatch):
    monkeypatch.setattr(
        "clipdrop.main.summarize_content",
        lambda _content: SummaryResult(success=False, error="helper unavailable"),
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["report", "--summarize"])
        assert result.exit_code == 0

        saved = Path("report.txt").read_text(encoding="utf-8")
        assert saved.startswith("> _Fallback summary generated locally")
        assert "**Overall:**" in saved
        assert "### Key Takeaways" in saved
        assert "⚠️ Summarizer unavailable" in result.stdout
        _, _, body = saved.partition("\n---\n\n")
        assert body.strip().startswith("Sentence")


def test_cli_summarize_long_content_uses_chunking(monkeypatch):
    from clipdrop import main as clipdrop_main

    long_content = ("paragraph " * 4001).strip()
    summary_text = """**Overall:** Chunked summary\n### Key Takeaways\n- Insight one\n### Action Items\n- None\n### Questions\n- None"""

    monkeypatch.setattr(
        "clipdrop.main.summarize_content",
        lambda *_args, **_kwargs: pytest.fail("Should not use single-pass summarizer"),
    )

    captured = {}

    def fake_chunker(content: str, **kwargs):
        captured["kwargs"] = kwargs
        return SummaryResult(
            success=True,
            summary=summary_text,
            stage_results=[{"stage": "chunk_summaries", "status": "ok", "processed": 4}],
        )

    monkeypatch.setattr("clipdrop.main.summarize_content_with_chunking", fake_chunker)

    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: long_content)
    monkeypatch.setattr(
        clipdrop_main.clipboard,
        "get_content_preview",
        lambda max_chars=200: long_content[:max_chars],
    )

    monkeypatch.setattr(
        "clipdrop.detect.is_summarizable_content",
        lambda _content, _format: (False, detect.SINGLE_PASS_LIMIT_REASON),
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["scroll", "--summarize"])
        assert result.exit_code == 0

        saved = Path("scroll.txt").read_text(encoding="utf-8")
        assert saved.startswith("**Overall:**")
        assert summary_text in saved
        assert "### Key Takeaways" in saved
        _, _, body = saved.partition("\n---\n\n")
        assert body.strip().lower().startswith("paragraph")

        kwargs = captured["kwargs"]
        assert kwargs["content_format"] == "plaintext"
        assert kwargs["metadata"]["source_filename"] == "scroll.txt"
        assert kwargs["language"] == "en-US"


def test_cli_chunking_stage_output(monkeypatch, tmp_path):
    from clipdrop import main as clipdrop_main

    long_content = Path("tests/fixtures/long_text.txt").read_text(encoding="utf-8")

    monkeypatch.setattr(
        "clipdrop.main.summarize_content",
        lambda *_args, **_kwargs: pytest.fail("Should not use single-pass summarizer"),
    )

    stage_results = [
        {"stage": "precheck", "status": "ok"},
        {"stage": "chunk_summaries", "status": "ok", "processed": 5},
        {"stage": "aggregation", "status": "ok"},
    ]

    monkeypatch.setattr(
        "clipdrop.main.summarize_content_with_chunking",
        lambda *_args, **_kwargs: SummaryResult(
            success=True,
            summary="""**Overall:** Chunked success summary\n### Key Takeaways\n- Insight\n### Action Items\n- None\n### Questions\n- None""",
            stage_results=stage_results,
        ),
    )

    monkeypatch.setattr(
        "clipdrop.detect.is_summarizable_content",
        lambda _content, _format: (False, detect.SINGLE_PASS_LIMIT_REASON),
    )

    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: long_content)
    monkeypatch.setattr(
        clipdrop_main.clipboard,
        "get_content_preview",
        lambda max_chars=200: long_content[:max_chars],
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["chunked", "--summarize"])
        assert result.exit_code == 0

        stdout = result.stdout
        assert "📊 Summarization stages:" in stdout
        assert "chunk_summaries" in stdout
        saved = Path("chunked.txt").read_text(encoding="utf-8")
        assert saved.startswith("**Overall:**")
        assert "Chunked success summary" in saved
        assert "### Key Takeaways" in saved
        _, _, body = saved.partition("\n---\n\n")
        assert body.strip().startswith("Paragraph")


def test_cli_chunking_failure_reports_stage(monkeypatch):
    from clipdrop import main as clipdrop_main

    long_content = Path("tests/fixtures/long_text.txt").read_text(encoding="utf-8")

    monkeypatch.setattr(
        "clipdrop.main.summarize_content",
        lambda *_args, **_kwargs: pytest.fail("Should not use single-pass summarizer"),
    )

    def failing_chunker(*_args, **_kwargs):
        return SummaryResult(
            success=False,
            summary=None,
            error="Model not ready",
            retryable=True,
            stage="chunk_summaries",
            stage_results=[{"stage": "chunk_summaries", "status": "error", "processed": 2}],
        )

    monkeypatch.setattr("clipdrop.main.summarize_content_with_chunking", failing_chunker)
    monkeypatch.setattr(
        "clipdrop.detect.is_summarizable_content",
        lambda _content, _format: (False, detect.SINGLE_PASS_LIMIT_REASON),
    )

    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: long_content)
    monkeypatch.setattr(
        clipdrop_main.clipboard,
        "get_content_preview",
        lambda max_chars=200: long_content[:max_chars],
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["chunked-fail", "--summarize"])
        assert result.exit_code == 0
        stdout = result.stdout
        assert "chunk_summaries" in stdout
        assert "⚠️ Summarizer unavailable; appended fallback summary" in stdout
        saved = Path("chunked-fail.txt").read_text(encoding="utf-8")
        assert saved.startswith("> _Fallback summary generated locally")
        assert "**Overall:**" in saved
        assert "### Key Takeaways" in saved
        _, _, body = saved.partition("\n---\n\n")
        assert body.strip().startswith("Paragraph")


def test_youtube_summarize_adds_structured_summary(monkeypatch, tmp_path):
    summary_text = (
        "**Overall:** Video recap\n"
        "### Key Takeaways\n- Highlight\n"
        "### Action Items\n- None\n"
        "### Questions\n- None"
    )

    monkeypatch.setattr("clipdrop.clipboard.get_text", lambda: "https://youtu.be/example")
    monkeypatch.setattr("clipdrop.main.validate_youtube_url", lambda _url: True)
    monkeypatch.setattr("clipdrop.main.extract_video_id", lambda _url: "abc123")
    monkeypatch.setattr("clipdrop.main.get_video_info", lambda _url: {"title": "Test Video"})
    monkeypatch.setattr("clipdrop.main.list_captions", lambda _url: [("en", "English", False)])
    monkeypatch.setattr("clipdrop.main.select_caption_track", lambda captions, _lang: captions[0])
    monkeypatch.setattr("clipdrop.youtube.sanitize_filename", lambda title: "Test Video")

    def fake_download_vtt(_url, _lang_code):
        vtt_path = tmp_path / "captions.vtt"
        vtt_path.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHello world\n", encoding="utf-8")
        return str(vtt_path)

    monkeypatch.setattr("clipdrop.main.download_vtt", fake_download_vtt)
    monkeypatch.setattr("clipdrop.main.vtt_to_srt", lambda _vtt: "1\n00:00:00,000 --> 00:00:02,000\nHello world\n")
    monkeypatch.setattr("clipdrop.main.summarize_content", lambda _content: SummaryResult(success=True, summary=summary_text))
    monkeypatch.setattr("clipdrop.main.summarize_content_with_chunking", lambda *_, **__: pytest.fail("chunking not expected"))
    monkeypatch.setattr("clipdrop.detect.is_summarizable_content", lambda _content, _format: (True, ""))

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["--youtube", "--summarize"])
        assert result.exit_code == 0
        saved = Path("Test Video.srt").read_text(encoding="utf-8")
        assert saved.startswith("**Overall:**")
        assert "### Key Takeaways" in saved
        _, _, body = saved.partition("\n---\n\n")
        assert "Hello world" in body


def test_audio_transcription_summarize_adds_summary(monkeypatch, tmp_path):
    segments = [{"start": 0.0, "end": 1.2, "text": "Hello world"}]

    def fake_stream(lang=None, progress_callback=None):  # noqa: ARG001
        for idx, segment in enumerate(segments, 1):
            if callable(progress_callback):
                progress_callback(segment, idx)
            yield segment

    monkeypatch.setattr("clipdrop.macos_ai.transcribe_from_clipboard_stream", fake_stream)
    monkeypatch.setattr("clipdrop.main.to_srt", lambda _segments: "1\n00:00:00,000 --> 00:00:01,200\nHello world\n")
    summary_text = (
        "**Overall:** Audio recap\n"
        "### Key Takeaways\n- Phrases captured\n"
        "### Action Items\n- None\n"
        "### Questions\n- None"
    )

    monkeypatch.setattr("clipdrop.main.summarize_content", lambda _content: SummaryResult(success=True, summary=summary_text))
    monkeypatch.setattr("clipdrop.main.summarize_content_with_chunking", lambda *_, **__: pytest.fail("chunking not expected"))
    monkeypatch.setattr("clipdrop.detect.is_summarizable_content", lambda _content, _format: (True, ""))
    monkeypatch.setattr("clipdrop.main.console.print", lambda *args, **kwargs: None)

    monkeypatch.chdir(tmp_path)

    handle_audio_transcription(filename="audio.srt", summarize=True)

    saved = Path("audio.srt").read_text(encoding="utf-8")
    assert saved.startswith("**Overall:**")
    assert "### Key Takeaways" in saved
    _, _, body = saved.partition("\n---\n\n")
    assert "Hello world" in body
