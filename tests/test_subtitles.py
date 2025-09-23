"""Tests for subtitle rendering functions."""


from clipdrop.subtitles import _fmt_ts, to_md, to_srt, to_txt


def test_fmt_ts():
    """Test timestamp formatting."""
    assert _fmt_ts(0.0) == "00:00:00,000"
    assert _fmt_ts(90.123) == "00:01:30,123"
    assert _fmt_ts(3661.5) == "01:01:01,500"
    assert _fmt_ts(7200.0) == "02:00:00,000"
    assert _fmt_ts(0.001) == "00:00:00,001"
    assert _fmt_ts(359999.999) == "99:59:59,999"


def test_to_srt():
    """Test SRT format generation."""
    segs = [
        {"start": 0.0, "end": 1.5, "text": "Hello"},
        {"start": 1.5, "end": 3.0, "text": "World"},
    ]
    srt = to_srt(segs)

    # Check structure
    lines = srt.split("\n")
    assert lines[0] == "1"
    assert lines[1] == "00:00:00,000 --> 00:00:01,500"
    assert lines[2] == "Hello"
    assert lines[3] == ""
    assert lines[4] == "2"
    assert lines[5] == "00:00:01,500 --> 00:00:03,000"
    assert lines[6] == "World"

    # Test with empty text (should be skipped)
    segs_with_empty = [
        {"start": 0.0, "end": 1.0, "text": "First"},
        {"start": 1.0, "end": 2.0, "text": ""},
        {"start": 2.0, "end": 3.0, "text": None},
        {"start": 3.0, "end": 4.0, "text": "Last"},
    ]
    srt = to_srt(segs_with_empty)
    assert "First" in srt
    assert "Last" in srt
    assert srt.count(" --> ") == 2  # Only 2 valid segments


def test_to_txt():
    """Test plain text format generation."""
    segs = [
        {"start": 0.0, "end": 1.5, "text": "Hello"},
        {"start": 1.5, "end": 3.0, "text": "World"},
    ]
    txt = to_txt(segs)
    assert txt == "Hello\nWorld\n"

    # Test with empty segments
    segs_with_empty = [
        {"text": "First"},
        {"text": ""},
        {"text": None},
        {"text": "  "},  # Whitespace only
        {"text": "Last"},
    ]
    txt = to_txt(segs_with_empty)
    assert txt == "First\nLast\n"


def test_to_md():
    """Test Markdown format generation."""
    segs = [
        {"start": 0.0, "end": 1.5, "text": "Hello"},
        {"start": 90.5, "end": 92.0, "text": "World"},
    ]
    md = to_md(segs)

    lines = md.split("\n")
    assert lines[0] == "### 00:00:00–00:00:01"
    assert lines[1] == ""
    assert lines[2] == "Hello"
    assert lines[3] == ""
    assert lines[4] == "### 00:01:30–00:01:32"
    assert lines[5] == ""
    assert lines[6] == "World"

    # Test with empty segments
    segs_with_empty = [
        {"start": 0.0, "end": 1.0, "text": "Content"},
        {"start": 1.0, "end": 2.0, "text": ""},
        {"start": 2.0, "end": 3.0, "text": None},
    ]
    md = to_md(segs_with_empty)
    assert "Content" in md
    assert md.count("###") == 1  # Only one valid segment


def test_edge_cases():
    """Test edge cases."""
    # Empty list
    assert to_srt([]) == "\n"
    assert to_txt([]) == "\n"
    assert to_md([]) == "\n"

    # All empty segments
    empty_segs = [
        {"start": 0, "end": 1, "text": ""},
        {"start": 1, "end": 2, "text": None},
    ]
    assert to_srt(empty_segs) == "\n"
    assert to_txt(empty_segs) == "\n"
    assert to_md(empty_segs) == "\n"