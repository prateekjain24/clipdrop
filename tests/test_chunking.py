import json

from clipdrop.chunking import build_chunked_request, create_semantic_chunks
from clipdrop.macos_ai import summarize_content_with_chunking


def test_create_semantic_chunks_respects_limits():
    content = "\n\n".join(["Paragraph " + str(i) + " " + ("word " * 100) for i in range(6)])

    max_chars = 600
    chunks = create_semantic_chunks(content, max_chunk_chars=max_chars)

    assert len(chunks) >= 2
    reconstructed = "\n\n".join(chunk.text for chunk in chunks)
    assert reconstructed.split() == content.split()

    for chunk in chunks:
        assert chunk.char_length <= max_chars
        assert chunk.token_estimate > 0

    ids = {chunk.id for chunk in chunks}
    assert len(ids) == len(chunks)


def test_build_chunked_request_matches_protocol_shape():
    content = "Paragraph one." * 800
    request = build_chunked_request(
        content,
        content_format="markdown",
        origin="clipdrop-cli",
        language="en-GB",
        instructions="Summarize politely",
        max_chunk_chars=800,
        retry_attempt=1,
    )

    payload = request.to_payload()
    assert payload["version"] == "1.0"
    assert payload["mode"] == "chunked"
    assert payload["content_format"] == "markdown"
    assert payload["origin"] == "clipdrop-cli"
    assert payload["strategy"]["language"] == "en-GB"
    assert payload["strategy"]["retry_attempt"] == 1
    assert len(payload["chunks"]) >= 1
    assert request.to_json()  # Should serialize without error


def test_summarize_content_with_chunking_success(monkeypatch, tmp_path):
    from clipdrop import macos_ai

    helper_path = tmp_path / "clipdrop-summarize"
    helper_path.write_text("binary")

    monkeypatch.setattr(macos_ai, "get_swift_helper_path", lambda name: helper_path)

    captured = {}

    def fake_run(*args, **kwargs):
        captured["input"] = kwargs.get("input")
        return macos_ai.subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps({"success": True, "summary": "Chunk summary"}),
            stderr="",
        )

    monkeypatch.setattr(macos_ai.subprocess, "run", fake_run)

    content = "\n\n".join(["Paragraph" + str(i) + " " + ("word " * 200) for i in range(5)])

    result = macos_ai.summarize_content_with_chunking(content, max_chunk_chars=500)

    assert result.success is True
    assert result.summary == "Chunk summary"
    payload = json.loads(captured["input"])
    assert payload["mode"] == "chunked"
    assert len(payload["chunks"]) >= 2
    assert payload["strategy"]["max_chunk_chars"] == 500


def test_summarize_content_with_chunking_failure(monkeypatch, tmp_path):
    from clipdrop import macos_ai

    helper_path = tmp_path / "clipdrop-summarize"
    helper_path.write_text("binary")

    monkeypatch.setattr(macos_ai, "get_swift_helper_path", lambda name: helper_path)

    def fake_run(*args, **kwargs):  # noqa: ARG001
        return macos_ai.subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout=json.dumps(
                {
                    "success": False,
                    "error": "Model not ready",
                    "retryable": True,
                    "stage": "precheck",
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(macos_ai.subprocess, "run", fake_run)

    content = "\n\n".join(["Paragraph" + str(i) + " " + ("word " * 200) for i in range(5)])

    result = macos_ai.summarize_content_with_chunking(content, max_chunk_chars=500)

    assert result.success is False
    assert "Model not ready" in (result.error or "")
    assert result.retryable is True
    assert result.stage == "precheck"
