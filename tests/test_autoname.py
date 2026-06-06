"""Tests for --auto-name (AI-suggested filenames)."""

import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clipdrop import files, macos_ai
from clipdrop.main import app, generate_auto_filename
from clipdrop.macos_ai import SummarizationNotAvailableError, suggest_filename


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


# --- files.slugify --------------------------------------------------------

def test_slugify_basic():
    assert files.slugify("Q3 Roadmap Planning") == "q3-roadmap-planning"


def test_slugify_strips_punctuation():
    assert files.slugify("Hello, World! (Draft #2)") == "hello-world-draft-2"


def test_slugify_caps_words_and_length():
    slug = files.slugify("one two three four five six seven eight", max_words=3)
    assert slug == "one-two-three"


def test_slugify_empty():
    assert files.slugify("   !!!   ") == ""


# --- macos_ai.suggest_filename -------------------------------------------

def test_suggest_filename_success(monkeypatch, tmp_path):
    helper = tmp_path / "clipdrop-suggest-name"
    helper.write_text("binary")
    monkeypatch.setattr(macos_ai, "get_swift_helper_path", lambda name: helper)
    monkeypatch.setattr(
        macos_ai.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a, returncode=0, stdout=json.dumps({"success": True, "title": "Quarterly Roadmap"}), stderr=""
        ),
    )

    assert suggest_filename("some long content here") == "Quarterly Roadmap"


def test_suggest_filename_unavailable(monkeypatch):
    def raise_unavailable(name):
        raise SummarizationNotAvailableError("not macOS")

    monkeypatch.setattr(macos_ai, "get_swift_helper_path", raise_unavailable)
    assert suggest_filename("content") is None


def test_suggest_filename_nonzero_exit(monkeypatch, tmp_path):
    helper = tmp_path / "clipdrop-suggest-name"
    helper.write_text("binary")
    monkeypatch.setattr(macos_ai, "get_swift_helper_path", lambda name: helper)
    monkeypatch.setattr(
        macos_ai.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, returncode=1, stdout="", stderr="model unavailable"),
    )

    assert suggest_filename("content") is None


def test_suggest_filename_bad_json(monkeypatch, tmp_path):
    helper = tmp_path / "clipdrop-suggest-name"
    helper.write_text("binary")
    monkeypatch.setattr(macos_ai, "get_swift_helper_path", lambda name: helper)
    monkeypatch.setattr(
        macos_ai.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, returncode=0, stdout="not json", stderr=""),
    )

    assert suggest_filename("content") is None


def test_suggest_filename_empty_content():
    assert suggest_filename("   ") is None


# --- generate_auto_filename ----------------------------------------------

def test_generate_auto_filename_uses_ai_title(monkeypatch):
    monkeypatch.setattr(macos_ai, "suggest_filename", lambda content, timeout=15: "Project Kickoff Notes")
    # Plain prose -> .txt
    result = generate_auto_filename("We met today to discuss the project kickoff and next steps.", None)
    assert result == "project-kickoff-notes.txt"


def test_generate_auto_filename_honors_provided_extension(monkeypatch):
    monkeypatch.setattr(macos_ai, "suggest_filename", lambda content, timeout=15: "Release Notes")
    result = generate_auto_filename("Lots of prose content here for naming.", "draft.md")
    assert result == "release-notes.md"


def test_generate_auto_filename_heuristic_fallback(monkeypatch):
    # AI unavailable -> slug derived from content itself
    monkeypatch.setattr(macos_ai, "suggest_filename", lambda content, timeout=15: None)
    result = generate_auto_filename("Weekly standup summary for the platform team.", None)
    assert result == "weekly-standup-summary-for-the-platform.txt"


def test_generate_auto_filename_no_content():
    assert generate_auto_filename(None, None) is None
    assert generate_auto_filename("   ", "x.md") is None


# --- CLI ------------------------------------------------------------------

@pytest.fixture
def mock_text_clipboard(monkeypatch):
    from clipdrop import main as clipdrop_main

    sample = "We met today to plan the quarterly roadmap and assign owners."
    monkeypatch.setattr(clipdrop_main.clipboard, "get_content_type", lambda: "text")
    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: sample)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image", lambda: None)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image_info", lambda: None)
    return sample


def test_cli_auto_name_no_filename(monkeypatch, mock_text_clipboard):
    monkeypatch.setattr(macos_ai, "suggest_filename", lambda content, timeout=15: "Quarterly Roadmap Plan")

    with isolated_filesystem():
        result = runner.invoke(app, ["--auto-name"])
        assert result.exit_code == 0, result.stdout
        saved = Path("quarterly-roadmap-plan.txt")
        assert saved.exists()
        assert mock_text_clipboard in saved.read_text(encoding="utf-8")


def test_cli_auto_name_honors_extension(monkeypatch, mock_text_clipboard):
    monkeypatch.setattr(macos_ai, "suggest_filename", lambda content, timeout=15: "Meeting Notes")

    with isolated_filesystem():
        result = runner.invoke(app, ["draft.md", "--auto-name"])
        assert result.exit_code == 0, result.stdout
        assert Path("meeting-notes.md").exists()


def test_cli_auto_name_no_text_errors(monkeypatch):
    from clipdrop import main as clipdrop_main

    monkeypatch.setattr(clipdrop_main.clipboard, "get_content_type", lambda: "image")
    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: None)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image", lambda: object())
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image_info", lambda: None)

    with isolated_filesystem():
        result = runner.invoke(app, ["--auto-name"])
        assert result.exit_code == 1
        assert "Could not auto-name" in result.stdout
