"""Tests for transform verbs: --rewrite, --prompt, --to-table."""

import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clipdrop import macos_ai
from clipdrop.macos_ai import (
    SummarizationNotAvailableError,
    TransformNotAvailableError,
    transform_content,
)
from clipdrop.main import app, render_csv_table, render_markdown_table


runner = CliRunner()


@contextmanager
def isolated_filesystem():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            yield Path(tmp)
        finally:
            os.chdir(cwd)


def _helper(monkeypatch, tmp_path):
    helper = tmp_path / "clipdrop-transform"
    helper.write_text("binary")
    monkeypatch.setattr(macos_ai, "get_swift_helper_path", lambda name: helper)
    return helper


# --- transform_content ----------------------------------------------------

def test_transform_rewrite_success(monkeypatch, tmp_path):
    _helper(monkeypatch, tmp_path)
    captured = {}

    def fake_run(args, **kwargs):
        captured["input"] = json.loads(kwargs["input"])
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps({"success": True, "result": "Formal text."}), stderr=""
        )

    monkeypatch.setattr(macos_ai.subprocess, "run", fake_run)

    data = transform_content("hello there", "rewrite", style="formal", language="en-US")
    assert data["result"] == "Formal text."
    assert captured["input"]["operation"] == "rewrite"
    assert captured["input"]["style"] == "formal"
    assert captured["input"]["language"] == "en-US"


def test_transform_table_success(monkeypatch, tmp_path):
    _helper(monkeypatch, tmp_path)
    table = {"headers": ["Name", "Age"], "rows": [["Ada", "36"], ["Alan", "41"]]}
    monkeypatch.setattr(
        macos_ai.subprocess,
        "run",
        lambda a, **k: subprocess.CompletedProcess(a, returncode=0, stdout=json.dumps({"success": True, "table": table}), stderr=""),
    )

    data = transform_content("Ada is 36. Alan is 41.", "table")
    assert data["table"]["headers"] == ["Name", "Age"]


def test_transform_unavailable(monkeypatch):
    def raise_unavailable(name):
        raise SummarizationNotAvailableError("not macOS")

    monkeypatch.setattr(macos_ai, "get_swift_helper_path", raise_unavailable)
    with pytest.raises(TransformNotAvailableError):
        transform_content("content here", "rewrite", style="formal")


def test_transform_helper_failure(monkeypatch, tmp_path):
    _helper(monkeypatch, tmp_path)
    monkeypatch.setattr(
        macos_ai.subprocess,
        "run",
        lambda a, **k: subprocess.CompletedProcess(a, returncode=1, stdout=json.dumps({"success": False, "error": "model busy"}), stderr=""),
    )
    with pytest.raises(RuntimeError, match="model busy"):
        transform_content("content here", "prompt", instruction="do it")


def test_transform_empty_content():
    with pytest.raises(RuntimeError, match="No content"):
        transform_content("   ", "rewrite", style="formal")


def test_transform_too_long():
    with pytest.raises(RuntimeError, match="too long"):
        transform_content("x" * 10_001, "rewrite", style="formal")


# --- table rendering ------------------------------------------------------

def test_render_markdown_table():
    table = {"headers": ["Name", "Age"], "rows": [["Ada", "36"], ["Alan", "41"]]}
    md = render_markdown_table(table)
    assert "| Name | Age |" in md
    assert "| --- | --- |" in md
    assert "| Ada | 36 |" in md


def test_render_markdown_table_pads_ragged_rows():
    table = {"headers": ["A", "B", "C"], "rows": [["1"], ["2", "3", "4", "5"]]}
    md = render_markdown_table(table)
    assert "| 1 |  |  |" in md      # padded
    assert "| 2 | 3 | 4 |" in md    # truncated to width


def test_render_markdown_table_escapes_pipes():
    table = {"headers": ["X"], "rows": [["a|b"]]}
    assert "a\\|b" in render_markdown_table(table)


def test_render_markdown_table_derives_headers():
    table = {"rows": [["1", "2"]]}
    md = render_markdown_table(table)
    assert "Column 1" in md and "Column 2" in md


def test_render_csv_table():
    table = {"headers": ["Name", "Age"], "rows": [["Ada", "36"]]}
    csv_out = render_csv_table(table)
    assert "Name,Age" in csv_out
    assert "Ada,36" in csv_out


def test_render_empty_table():
    assert render_markdown_table({}) == ""
    assert render_csv_table({}) == ""


# --- CLI ------------------------------------------------------------------

@pytest.fixture
def mock_text_clipboard(monkeypatch):
    from clipdrop import main as clipdrop_main

    sample = "Some prose copied to the clipboard for transformation."
    monkeypatch.setattr(clipdrop_main.clipboard, "get_content_type", lambda: "text")
    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: sample)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image", lambda: None)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image_info", lambda: None)
    return sample


def test_cli_rewrite(monkeypatch, mock_text_clipboard):
    monkeypatch.setattr(
        macos_ai, "transform_content",
        lambda content, op, **kw: {"success": True, "result": "A more formal version."},
    )
    with isolated_filesystem():
        result = runner.invoke(app, ["notes.txt", "--rewrite", "formal"])
        assert result.exit_code == 0, result.stdout
        assert "A more formal version." in Path("notes.txt").read_text(encoding="utf-8")


def test_cli_prompt(monkeypatch, mock_text_clipboard):
    monkeypatch.setattr(
        macos_ai, "transform_content",
        lambda content, op, **kw: {"success": True, "result": "- release note one"},
    )
    with isolated_filesystem():
        result = runner.invoke(app, ["out.md", "--prompt", "turn into release notes"])
        assert result.exit_code == 0, result.stdout
        assert "release note one" in Path("out.md").read_text(encoding="utf-8")


def test_cli_to_table_markdown(monkeypatch, mock_text_clipboard):
    table = {"headers": ["Name", "Age"], "rows": [["Ada", "36"]]}
    monkeypatch.setattr(macos_ai, "transform_content", lambda content, op, **kw: {"success": True, "table": table})
    with isolated_filesystem():
        result = runner.invoke(app, ["people.md", "--to-table"])
        assert result.exit_code == 0, result.stdout
        saved = Path("people.md").read_text(encoding="utf-8")
        assert "| Name | Age |" in saved


def test_cli_to_table_csv(monkeypatch, mock_text_clipboard):
    table = {"headers": ["Name", "Age"], "rows": [["Ada", "36"]]}
    monkeypatch.setattr(macos_ai, "transform_content", lambda content, op, **kw: {"success": True, "table": table})
    with isolated_filesystem():
        result = runner.invoke(app, ["people.csv", "--to-table"])
        assert result.exit_code == 0, result.stdout
        saved = Path("people.csv").read_text(encoding="utf-8")
        assert "Name,Age" in saved
        assert "Ada,36" in saved


def test_cli_transform_mutually_exclusive(monkeypatch, mock_text_clipboard):
    with isolated_filesystem():
        result = runner.invoke(app, ["x.txt", "--rewrite", "formal", "--prompt", "do it"])
        assert result.exit_code == 1
        assert "only one transform" in result.stdout.lower()


def test_cli_transform_no_text(monkeypatch):
    from clipdrop import main as clipdrop_main

    monkeypatch.setattr(clipdrop_main.clipboard, "get_content_type", lambda: "image")
    monkeypatch.setattr(clipdrop_main.clipboard, "get_text", lambda: None)
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image", lambda: object())
    monkeypatch.setattr(clipdrop_main.clipboard, "get_image_info", lambda: None)

    with isolated_filesystem():
        result = runner.invoke(app, ["x.txt", "--rewrite", "formal"])
        assert result.exit_code == 1
        assert "No text content" in result.stdout


def test_cli_transform_unavailable(monkeypatch, mock_text_clipboard):
    def raise_unavailable(content, op, **kw):
        raise TransformNotAvailableError("On-device transformation requires macOS 26.0 or later.")

    monkeypatch.setattr(macos_ai, "transform_content", raise_unavailable)
    with isolated_filesystem():
        result = runner.invoke(app, ["x.txt", "--rewrite", "formal"])
        assert result.exit_code == 2
        assert "macOS 26" in result.stdout
