"""End-to-end tests for YouTube functionality with real URLs."""

import os
import pytest
import requests

from clipdrop.youtube import (
    check_ytdlp_installed,
    validate_youtube_url,
    extract_video_id,
    get_video_info,
    list_captions,
    download_vtt,
    vtt_to_srt,
    vtt_to_txt,
    vtt_to_md,
    parse_vtt
)


# Test video: "Me at the zoo" - First YouTube video (has captions)
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
TEST_VIDEO_ID = "jNQXAC9IVRw"
TEST_VIDEO_TITLE = "Me at the zoo"


def network_available():
    """Check if network is available."""
    try:
        response = requests.get("https://www.youtube.com", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def ytdlp_available():
    """Check if yt-dlp is installed."""
    is_installed, _ = check_ytdlp_installed()
    return is_installed


# Skip all tests if network or yt-dlp not available
pytestmark = [
    pytest.mark.skipif(not network_available(), reason="Network not available"),
    pytest.mark.skipif(not ytdlp_available(), reason="yt-dlp not installed")
]


class TestE2EYouTube:
    """End-to-end tests with real YouTube video."""

    def test_validate_real_url(self):
        """Test URL validation with real YouTube URL."""
        assert validate_youtube_url(TEST_VIDEO_URL)
        assert extract_video_id(TEST_VIDEO_URL) == TEST_VIDEO_ID

    def test_get_video_info_real(self):
        """Test fetching real video information."""
        info = get_video_info(TEST_VIDEO_URL)

        assert info is not None
        assert 'title' in info
        assert 'id' in info
        assert info['id'] == TEST_VIDEO_ID
        # Title should contain "Me at the zoo" (case-insensitive)
        assert "zoo" in info['title'].lower()

    def test_list_captions_real(self):
        """Test listing captions for real video."""
        captions = list_captions(TEST_VIDEO_URL)

        # "Me at the zoo" should have at least captions
        assert len(captions) > 0

        # Check caption structure (returns tuples)
        for caption in captions:
            assert isinstance(caption, tuple)
            assert len(caption) == 3
            # Should have (lang_code, name, is_auto_generated)
            lang_code, name, is_auto = caption
            assert isinstance(lang_code, str)
            assert isinstance(name, str)
            assert isinstance(is_auto, bool)

    def test_download_and_convert_formats(self, tmp_path):
        """Test downloading VTT and converting to all formats."""
        # Get available captions
        captions = list_captions(TEST_VIDEO_URL)
        assert len(captions) > 0

        # Select first available caption (prefer English if available)
        selected_lang_code = None
        for caption in captions:
            lang_code, name, is_auto = caption
            if 'en' in lang_code.lower():
                selected_lang_code = lang_code
                break

        if not selected_lang_code:
            # Use first available caption
            selected_lang_code = captions[0][0]

        # Download VTT
        vtt_path = download_vtt(TEST_VIDEO_URL, selected_lang_code)
        assert vtt_path is not None
        assert os.path.exists(vtt_path)

        # Read VTT content
        with open(vtt_path, 'r', encoding='utf-8') as f:
            vtt_content = f.read()

        assert vtt_content.startswith("WEBVTT")

        # Parse VTT
        parsed_cues = parse_vtt(vtt_content)
        assert len(parsed_cues) > 0

        # Test VTT to SRT conversion
        srt_content = vtt_to_srt(vtt_content)
        assert srt_content
        # SRT should have sequence numbers
        assert "\n1\n" in srt_content or srt_content.startswith("1\n")
        # SRT uses comma for milliseconds
        assert "," in srt_content
        # SRT uses --> for time ranges
        assert " --> " in srt_content

        # Test VTT to TXT conversion
        txt_content = vtt_to_txt(vtt_content)
        assert txt_content
        # TXT should not have timestamps or WEBVTT header
        assert "WEBVTT" not in txt_content
        assert "-->" not in txt_content
        # Should have actual text content
        assert len(txt_content.strip()) > 0

        # Test VTT to MD conversion (without timestamps)
        md_content = vtt_to_md(vtt_content, include_timestamps=False)
        assert md_content
        # MD should have title
        assert "# Transcript" in md_content
        # Should not have timestamps
        assert "-->" not in md_content
        assert "**[" not in md_content

        # Test VTT to MD conversion (with timestamps)
        md_content_with_time = vtt_to_md(vtt_content, include_timestamps=True)
        assert md_content_with_time
        # Should have timestamps in markdown (format: **HH:MM:SS - HH:MM:SS**)
        assert "**" in md_content_with_time
        assert " - " in md_content_with_time

    def test_full_workflow_with_caching(self):
        """Test full workflow including caching."""
        # First download
        get_video_info(TEST_VIDEO_URL)  # Cache video info
        captions1 = list_captions(TEST_VIDEO_URL)

        # Select a caption
        selected_lang_code = None
        for caption in captions1:
            lang_code, name, is_auto = caption
            if 'en' in lang_code.lower():
                selected_lang_code = lang_code
                break

        if not selected_lang_code:
            selected_lang_code = captions1[0][0]

        # Download VTT (will cache)
        vtt_path1 = download_vtt(TEST_VIDEO_URL, selected_lang_code)

        # Second download (should use cache)
        vtt_path2 = download_vtt(TEST_VIDEO_URL, selected_lang_code)

        # Should be the same cached file
        assert vtt_path1 == vtt_path2
        assert os.path.exists(vtt_path1)

    def test_video_with_chapters(self):
        """Test that chapter information is fetched if available."""
        info = get_video_info(TEST_VIDEO_URL)

        # Chapters field should exist (may be None or empty list)
        assert 'chapters' in info

        # If chapters exist, verify structure
        if info['chapters']:
            for chapter in info['chapters']:
                assert 'title' in chapter
                assert 'start_time' in chapter
                assert 'end_time' in chapter