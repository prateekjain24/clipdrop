"""Tests for the clipboard history module and CLI."""

import json
import os
import stat
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from clipdrop import history
from clipdrop.main import app


runner = CliRunner()

FAKE_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"


@pytest.fixture
def history_dir(tmp_path, monkeypatch):
    """Point the history store at a temp directory."""
    store = tmp_path / '.clipdrop'
    monkeypatch.setattr(history, 'HISTORY_DIR', store)
    return store


class TestAddEntry:
    """Test storing clips."""

    def test_stores_and_reads_back(self, history_dir):
        assert history.add_entry("hello world") is True
        entries = history.get_entries()
        assert len(entries) == 1
        assert entries[0].text == "hello world"

    def test_newest_first_ordering(self, history_dir):
        history.add_entry("first")
        history.add_entry("second")
        history.add_entry("third")
        texts = [e.text for e in history.get_entries()]
        assert texts == ["third", "second", "first"]

    def test_empty_clip_skipped(self, history_dir):
        assert history.add_entry("") is False
        assert history.add_entry("   \n ") is False
        assert history.get_entries() == []

    def test_duplicate_of_most_recent_skipped(self, history_dir):
        assert history.add_entry("same") is True
        assert history.add_entry("same") is False
        assert len(history.get_entries()) == 1

    def test_non_adjacent_duplicate_stored(self, history_dir):
        history.add_entry("a")
        history.add_entry("b")
        assert history.add_entry("a") is True
        assert len(history.get_entries()) == 3

    def test_oversized_clip_skipped(self, history_dir):
        huge = "x" * (history.HISTORY_MAX_ITEM_BYTES + 1)
        assert history.add_entry(huge) is False
        assert history.get_entries() == []

    def test_secret_clip_never_persisted(self, history_dir):
        """The privacy guarantee: clips with secrets don't touch disk."""
        assert history.add_entry(f"key = {FAKE_AWS_KEY}") is False
        assert history.get_entries() == []
        # Nothing containing the secret may exist on disk at all
        path = history.get_history_file()
        if path.exists():
            assert FAKE_AWS_KEY not in path.read_text()

    def test_cap_trims_oldest(self, history_dir):
        for i in range(history.HISTORY_MAX_ENTRIES + 5):
            history.add_entry(f"clip {i}")
        entries = history.get_entries()
        assert len(entries) == history.HISTORY_MAX_ENTRIES
        assert entries[0].text == f"clip {history.HISTORY_MAX_ENTRIES + 4}"
        assert all(e.text != "clip 0" for e in entries)

    def test_unicode_round_trip(self, history_dir):
        history.add_entry("Héllo 世界 🌍")
        assert history.get_entries()[0].text == "Héllo 世界 🌍"

    def test_file_permissions_owner_only(self, history_dir):
        history.add_entry("private")
        path = history.get_history_file()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


class TestGetEntry:
    """Test 1-based entry lookup."""

    def test_one_based_indexing(self, history_dir):
        history.add_entry("older")
        history.add_entry("newest")
        assert history.get_entry(1).text == "newest"
        assert history.get_entry(2).text == "older"

    def test_out_of_range_raises(self, history_dir):
        history.add_entry("only")
        with pytest.raises(IndexError):
            history.get_entry(2)
        with pytest.raises(IndexError):
            history.get_entry(0)

    def test_empty_history_raises(self, history_dir):
        with pytest.raises(IndexError):
            history.get_entry(1)


class TestStoreResilience:
    """Test corrupt data handling."""

    def test_corrupt_lines_skipped(self, history_dir):
        history.add_entry("good clip")
        path = history.get_history_file()
        with path.open('a') as f:
            f.write("not json at all\n")
            f.write('{"ts": "2026-01-01T00:00:00+00:00"}\n')  # missing text
        entries = history.get_entries()
        assert len(entries) == 1
        assert entries[0].text == "good clip"

    def test_missing_file_returns_empty(self, history_dir):
        assert history.get_entries() == []

    def test_clear_history(self, history_dir):
        history.add_entry("bye")
        history.clear_history()
        assert history.get_entries() == []
        assert not history.get_history_file().exists()

    def test_clear_missing_file_is_noop(self, history_dir):
        history.clear_history()  # must not raise


class TestWatchClipboard:
    """Test the capture polling loop."""

    def test_captures_changes(self, history_dir):
        pastes = iter(["one", "one", "two", "two", "three"])
        with patch('clipdrop.history.pyperclip.paste',
                   side_effect=lambda: next(pastes)), \
             patch('clipdrop.history.time.sleep'):
            captured = history.watch_clipboard(max_iterations=5)

        assert captured == 3
        assert [e.text for e in history.get_entries()] == \
            ["three", "two", "one"]

    def test_ignores_empty_and_errors(self, history_dir):
        def flaky():
            for value in ["", None, "real"]:
                yield value
            raise RuntimeError("clipboard busy")

        gen = flaky()
        with patch('clipdrop.history.pyperclip.paste',
                   side_effect=lambda: next(gen)), \
             patch('clipdrop.history.time.sleep'):
            captured = history.watch_clipboard(max_iterations=4)

        assert captured == 1
        assert history.get_entries()[0].text == "real"

    def test_secret_clip_not_captured(self, history_dir):
        pastes = iter([f"token={FAKE_AWS_KEY}", "safe"])
        with patch('clipdrop.history.pyperclip.paste',
                   side_effect=lambda: next(pastes)), \
             patch('clipdrop.history.time.sleep'):
            captured = history.watch_clipboard(max_iterations=2)

        assert captured == 1
        assert [e.text for e in history.get_entries()] == ["safe"]

    def test_on_capture_callback(self, history_dir):
        seen = []
        with patch('clipdrop.history.pyperclip.paste', return_value="clip"), \
             patch('clipdrop.history.time.sleep'):
            history.watch_clipboard(max_iterations=3, on_capture=seen.append)

        assert seen == ["clip"]


class TestFormatAge:
    """Test human-readable ages."""

    def test_recent_and_older(self, history_dir):
        history.add_entry("now")
        assert history.format_age(history.get_entries()[0].ts).endswith("s ago")

    def test_invalid_timestamp(self):
        assert history.format_age("garbage") == "?"


class TestHistoryCLI:
    """Test the --history* / --last / --pick flags."""

    def test_history_empty_shows_hint(self, history_dir):
        result = runner.invoke(app, ["--history"])
        assert result.exit_code == 0
        assert "No clipboard history yet" in result.stdout
        assert "--history-daemon" in result.stdout

    def test_history_lists_entries(self, history_dir):
        history.add_entry("alpha clip content")
        history.add_entry("beta clip content")
        result = runner.invoke(app, ["--history"])
        assert result.exit_code == 0
        assert "alpha clip content" in result.stdout
        assert "beta clip content" in result.stdout

    @patch('clipdrop.clipboard.copy_to_clipboard')
    def test_last_restores_nth_entry(self, mock_copy, history_dir):
        history.add_entry("older")
        history.add_entry("newest")
        result = runner.invoke(app, ["--last", "2"])
        assert result.exit_code == 0
        mock_copy.assert_called_once_with("older")

    def test_last_out_of_range_errors(self, history_dir):
        history.add_entry("only")
        result = runner.invoke(app, ["--last", "5"])
        assert result.exit_code == 1
        assert "out of range" in result.stdout

    def test_last_with_empty_history_errors(self, history_dir):
        result = runner.invoke(app, ["--last", "1"])
        assert result.exit_code == 1
        assert "No clipboard history yet" in result.stdout

    def test_last_saves_to_file(self, history_dir, temp_directory):
        history.add_entry('{"kind": "json data"}')
        cwd = os.getcwd()
        os.chdir(temp_directory)
        try:
            result = runner.invoke(app, ["--last", "1", "snippet"])
        finally:
            os.chdir(cwd)
        assert result.exit_code == 0
        saved = list(temp_directory.glob("snippet.*"))
        assert len(saved) == 1
        assert json.loads(saved[0].read_text()) == {"kind": "json data"}

    @patch('clipdrop.clipboard.copy_to_clipboard')
    def test_pick_prompts_and_restores(self, mock_copy, history_dir):
        history.add_entry("older")
        history.add_entry("newest")
        with patch('clipdrop.main.IntPrompt.ask', return_value=2):
            result = runner.invoke(app, ["--pick"])
        assert result.exit_code == 0
        mock_copy.assert_called_once_with("older")

    @patch('clipdrop.clipboard.copy_to_clipboard')
    def test_pick_with_yes_takes_most_recent(self, mock_copy, history_dir):
        history.add_entry("older")
        history.add_entry("newest")
        result = runner.invoke(app, ["--pick", "--yes"])
        assert result.exit_code == 0
        mock_copy.assert_called_once_with("newest")

    def test_history_clear_with_force(self, history_dir):
        history.add_entry("gone soon")
        result = runner.invoke(app, ["--history-clear", "-f"])
        assert result.exit_code == 0
        assert history.get_entries() == []

    def test_history_clear_empty_is_friendly(self, history_dir):
        result = runner.invoke(app, ["--history-clear"])
        assert result.exit_code == 0
        assert "already empty" in result.stdout

    def test_daemon_flag_starts_watch(self, history_dir):
        with patch('clipdrop.main.history_store.watch_clipboard',
                   side_effect=KeyboardInterrupt) as mock_watch:
            result = runner.invoke(app, ["--history-daemon"])
        assert result.exit_code == 0
        assert mock_watch.called
        assert "Watching the clipboard" in result.stdout

    def test_history_conflicts_with_bridge_mode(self, history_dir):
        result = runner.invoke(app, ["--history", "--rich"])
        assert result.exit_code == 1
        assert "can't be combined" in result.stdout

    def test_two_history_ops_conflict(self, history_dir):
        result = runner.invoke(app, ["--history", "--pick"])
        assert result.exit_code == 1
        assert "can't be combined" in result.stdout

    def test_history_conflicts_with_audio(self, history_dir):
        result = runner.invoke(app, ["--last", "1", "--audio"])
        assert result.exit_code == 1
        assert "can't be combined" in result.stdout
