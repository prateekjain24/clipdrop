"""Tests for on-device OCR (Vision helper) integration."""

import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from clipdrop import macos_ai
from clipdrop.macos_ai import OCRNotAvailableError, ocr_image
from clipdrop.main import app


runner = CliRunner()


@contextmanager
def isolated_filesystem():
    """Run a block inside a fresh temp directory (Click 8.4 removed the helper)."""
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            yield Path(tmp)
        finally:
            os.chdir(cwd)


@pytest.fixture
def sample_image():
    return Image.new("RGB", (40, 20), color="white")


# --- ocr_image unit tests -------------------------------------------------

def test_ocr_image_returns_recognized_text(monkeypatch, tmp_path, sample_image):
    helper = tmp_path / "clipdrop-ocr"
    helper.write_text("binary")
    monkeypatch.setattr(macos_ai, "get_ocr_helper_path", lambda: helper)

    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        # The image should have been written to a real temp PNG path.
        assert Path(args[1]).exists()
        return subprocess.CompletedProcess(args, returncode=0, stdout="Hello world\nLine two\n", stderr="")

    monkeypatch.setattr(macos_ai.subprocess, "run", fake_run)

    result = ocr_image(sample_image)
    assert result == "Hello world\nLine two"
    assert captured["args"][0] == str(helper)


def test_ocr_image_passes_language(monkeypatch, tmp_path, sample_image):
    helper = tmp_path / "clipdrop-ocr"
    helper.write_text("binary")
    monkeypatch.setattr(macos_ai, "get_ocr_helper_path", lambda: helper)

    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(args, returncode=0, stdout="hola", stderr="")

    monkeypatch.setattr(macos_ai.subprocess, "run", fake_run)

    ocr_image(sample_image, lang="es-ES")
    assert "--lang" in captured["args"]
    assert captured["args"][captured["args"].index("--lang") + 1] == "es-ES"


def test_ocr_image_empty_when_no_text(monkeypatch, tmp_path, sample_image):
    helper = tmp_path / "clipdrop-ocr"
    helper.write_text("binary")
    monkeypatch.setattr(macos_ai, "get_ocr_helper_path", lambda: helper)
    monkeypatch.setattr(
        macos_ai.subprocess,
        "run",
        lambda args, **kw: subprocess.CompletedProcess(args, returncode=1, stdout="", stderr=""),
    )

    assert ocr_image(sample_image) == ""


def test_ocr_image_raises_on_helper_error(monkeypatch, tmp_path, sample_image):
    helper = tmp_path / "clipdrop-ocr"
    helper.write_text("binary")
    monkeypatch.setattr(macos_ai, "get_ocr_helper_path", lambda: helper)
    monkeypatch.setattr(
        macos_ai.subprocess,
        "run",
        lambda args, **kw: subprocess.CompletedProcess(args, returncode=2, stdout="", stderr="could not load image"),
    )

    with pytest.raises(RuntimeError, match="could not load image"):
        ocr_image(sample_image)


def test_ocr_image_cleans_up_temp_file(monkeypatch, tmp_path, sample_image):
    helper = tmp_path / "clipdrop-ocr"
    helper.write_text("binary")
    monkeypatch.setattr(macos_ai, "get_ocr_helper_path", lambda: helper)

    seen = {}

    def fake_run(args, **kwargs):
        seen["path"] = args[1]
        return subprocess.CompletedProcess(args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(macos_ai.subprocess, "run", fake_run)

    ocr_image(sample_image)
    # Temp PNG must be removed after the helper runs.
    assert not Path(seen["path"]).exists()


def test_get_ocr_helper_path_non_macos(monkeypatch):
    monkeypatch.setattr(macos_ai.platform, "system", lambda: "Linux")
    with pytest.raises(OCRNotAvailableError):
        macos_ai.get_ocr_helper_path()


# --- CLI --ocr tests ------------------------------------------------------

@pytest.fixture
def mock_image_clipboard(monkeypatch):
    from clipdrop import main as clipdrop_main

    fake_image = object()
    monkeypatch.setattr(clipdrop_main.clipboard, "get_content_type", lambda: "image")
    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: None)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image", lambda: fake_image)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image_info", lambda: None)
    return fake_image


def test_cli_ocr_saves_recognized_text(monkeypatch, mock_image_clipboard):
    monkeypatch.setattr(macos_ai, "ocr_image", lambda image, lang=None: "Recognized screenshot text")

    with isolated_filesystem():
        result = runner.invoke(app, ["notes", "--ocr"])
        assert result.exit_code == 0
        saved = Path("notes.txt").read_text(encoding="utf-8")
        assert "Recognized screenshot text" in saved


def test_cli_ocr_no_image(monkeypatch):
    from clipdrop import main as clipdrop_main

    monkeypatch.setattr(clipdrop_main.clipboard, "get_content_type", lambda: "text")
    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: "just text")
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image", lambda: None)

    with isolated_filesystem():
        result = runner.invoke(app, ["notes", "--ocr"])
        assert result.exit_code == 1
        assert "No image" in result.stdout


def test_cli_ocr_no_text_detected(monkeypatch, mock_image_clipboard):
    monkeypatch.setattr(macos_ai, "ocr_image", lambda image, lang=None: "")

    with isolated_filesystem():
        result = runner.invoke(app, ["notes", "--ocr"])
        assert result.exit_code == 1
        assert "No text detected" in result.stdout


def test_cli_ocr_unavailable(monkeypatch, mock_image_clipboard):
    def raise_unavailable(image, lang=None):
        raise OCRNotAvailableError("On-device OCR is only available on macOS.")

    monkeypatch.setattr(macos_ai, "ocr_image", raise_unavailable)

    with isolated_filesystem():
        result = runner.invoke(app, ["notes", "--ocr"])
        assert result.exit_code == 2
        assert "only available on macOS" in result.stdout
