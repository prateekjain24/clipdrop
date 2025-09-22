"""Tests for YouTube URL handling and yt-dlp integration."""

import json
from unittest.mock import patch, MagicMock
from src.clipdrop.youtube import (
    validate_youtube_url,
    extract_video_id,
    check_ytdlp_installed,
    list_captions,
    select_caption_track
)


class TestYouTubeURLValidation:
    """Test YouTube URL validation functionality."""

    def test_valid_youtube_urls(self):
        """Test that valid YouTube URLs are recognized."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "www.youtube.com/watch?v=dQw4w9WgXcQ",
            "youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/v/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/live/dQw4w9WgXcQ",
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            "//www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
            "https://www.youtube.com/watch?time_continue=506&v=dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            assert validate_youtube_url(url) is True, f"Failed to validate: {url}"

    def test_invalid_youtube_urls(self):
        """Test that invalid URLs are rejected."""
        invalid_urls = [
            "",
            None,
            "not a url",
            "https://vimeo.com/123456789",
            "https://www.dailymotion.com/video/x2v8j3k",
            "https://youtube.com/",
            "https://youtube.com/channel/UC1234567890",
            "https://youtube.com/user/username",
            "https://youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
            "https://google.com",
            "youtube.com/watch?v=",  # Missing video ID
            "youtube.com/watch?v=tooshort",  # Video ID too short
            "youtube.com/watch?v=toolongvideoid",  # Video ID too long
        ]

        for url in invalid_urls:
            if url is not None:  # Skip None test for validate function
                assert validate_youtube_url(url) is False, f"Should have rejected: {url}"


class TestVideoIDExtraction:
    """Test video ID extraction functionality."""

    def test_extract_from_standard_urls(self):
        """Test extraction from standard watch URLs."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("http://www.youtube.com/watch?v=_OBlgSz8sSM", "_OBlgSz8sSM"),
            ("youtube.com/watch?v=DFYRQ_zQ-gk&feature=share", "DFYRQ_zQ-gk"),
            ("https://www.youtube.com/watch?time_continue=506&v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=yZ-K7nCVnBI&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf", "yZ-K7nCVnBI"),
        ]

        for url, expected_id in test_cases:
            result = extract_video_id(url)
            assert result == expected_id, f"Failed to extract from {url}. Got {result}, expected {expected_id}"

    def test_extract_from_short_urls(self):
        """Test extraction from youtu.be short URLs."""
        test_cases = [
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("youtu.be/DFYRQ_zQ-gk", "DFYRQ_zQ-gk"),
            ("http://youtu.be/oTJRivZTMLs?list=PLToa5JuFMsXTNkrLJbRlB--76IAOjRM9b", "oTJRivZTMLs"),
        ]

        for url, expected_id in test_cases:
            result = extract_video_id(url)
            assert result == expected_id, f"Failed to extract from {url}. Got {result}, expected {expected_id}"

    def test_extract_from_embed_urls(self):
        """Test extraction from embed URLs."""
        test_cases = [
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("www.youtube.com/embed/DFYRQ_zQ-gk?rel=0", "DFYRQ_zQ-gk"),
            ("https://www.youtube-nocookie.com/embed/up_lNV-yoK4?rel=0", "up_lNV-yoK4"),
        ]

        for url, expected_id in test_cases:
            result = extract_video_id(url)
            assert result == expected_id, f"Failed to extract from {url}. Got {result}, expected {expected_id}"

    def test_extract_from_v_urls(self):
        """Test extraction from /v/ URLs."""
        test_cases = [
            ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("youtube.com/v/DFYRQ_zQ-gk?fs=1&amp;hl=en_US&amp;rel=0", "DFYRQ_zQ-gk"),
        ]

        for url, expected_id in test_cases:
            result = extract_video_id(url)
            assert result == expected_id, f"Failed to extract from {url}. Got {result}, expected {expected_id}"

    def test_extract_from_shorts_and_live(self):
        """Test extraction from shorts and live URLs."""
        test_cases = [
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("youtube.com/shorts/DFYRQ_zQ-gk", "DFYRQ_zQ-gk"),
            ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("youtube.com/live/DFYRQ_zQ-gk?feature=share", "DFYRQ_zQ-gk"),
        ]

        for url, expected_id in test_cases:
            result = extract_video_id(url)
            assert result == expected_id, f"Failed to extract from {url}. Got {result}, expected {expected_id}"

    def test_extract_from_music_youtube(self):
        """Test extraction from music.youtube.com URLs."""
        test_cases = [
            ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("music.youtube.com/watch?v=DFYRQ_zQ-gk&feature=share", "DFYRQ_zQ-gk"),
        ]

        for url, expected_id in test_cases:
            result = extract_video_id(url)
            assert result == expected_id, f"Failed to extract from {url}. Got {result}, expected {expected_id}"

    def test_extract_with_special_characters(self):
        """Test extraction with video IDs containing special characters."""
        test_cases = [
            ("https://www.youtube.com/watch?v=yZ-K7nCVnBI", "yZ-K7nCVnBI"),  # Hyphens
            ("https://youtu.be/oTJRivZTMLs", "oTJRivZTMLs"),  # Mixed case
            ("https://www.youtube.com/watch?v=_OBlgSz8sSM", "_OBlgSz8sSM"),  # Underscore
        ]

        for url, expected_id in test_cases:
            result = extract_video_id(url)
            assert result == expected_id, f"Failed to extract from {url}. Got {result}, expected {expected_id}"

    def test_extract_returns_none_for_invalid(self):
        """Test that extraction returns None for invalid URLs."""
        invalid_urls = [
            "",
            None,
            "not a url",
            "https://vimeo.com/123456789",
            "https://youtube.com/",
            "https://youtube.com/channel/UC1234567890",
            "youtube.com/watch?v=",  # Missing video ID
            "youtube.com/watch?v=short",  # Too short
            "youtube.com/watch?v=waytoolongvideoid",  # Too long
        ]

        for url in invalid_urls:
            result = extract_video_id(url)
            assert result is None, f"Should return None for {url}, got {result}"


class TestYTDLPCheck:
    """Test yt-dlp availability checking."""

    @patch('shutil.which')
    def test_ytdlp_installed(self, mock_which):
        """Test when yt-dlp is installed."""
        mock_which.return_value = "/usr/local/bin/yt-dlp"

        is_installed, message = check_ytdlp_installed()

        assert is_installed is True
        assert "yt-dlp found at: /usr/local/bin/yt-dlp" in message
        mock_which.assert_called_once_with('yt-dlp')

    @patch('shutil.which')
    def test_ytdlp_not_installed(self, mock_which):
        """Test when yt-dlp is not installed."""
        mock_which.return_value = None

        is_installed, message = check_ytdlp_installed()

        assert is_installed is False
        assert "yt-dlp not found" in message
        assert "pip install clipdrop[youtube]" in message
        mock_which.assert_called_once_with('yt-dlp')

    @patch('shutil.which')
    def test_ytdlp_different_path(self, mock_which):
        """Test when yt-dlp is installed in a different location."""
        mock_which.return_value = "/opt/homebrew/bin/yt-dlp"

        is_installed, message = check_ytdlp_installed()

        assert is_installed is True
        assert "yt-dlp found at: /opt/homebrew/bin/yt-dlp" in message
        mock_which.assert_called_once_with('yt-dlp')


class TestCaptionListing:
    """Test caption listing functionality."""

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    def test_list_captions_with_manual_and_auto(self, mock_check, mock_run):
        """Test listing captions with both manual and auto-generated subtitles."""
        mock_check.return_value = (True, "yt-dlp found")

        # Mock yt-dlp output
        manual_subs = {
            "en": [{"name": "English", "ext": "vtt"}],
            "es": [{"name": "Spanish", "ext": "vtt"}]
        }
        auto_subs = {
            "fr": [{"name": "French", "ext": "vtt"}],
            "en": [{"name": "English", "ext": "vtt"}]  # Should be skipped
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = f"{json.dumps(manual_subs)}\n{json.dumps(auto_subs)}"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        captions = list_captions("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert len(captions) == 3
        assert ("en", "English", False) in captions
        assert ("es", "Spanish", False) in captions
        assert ("fr", "French (auto-generated)", True) in captions

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    def test_list_captions_auto_only(self, mock_check, mock_run):
        """Test listing captions with only auto-generated subtitles."""
        mock_check.return_value = (True, "yt-dlp found")

        manual_subs = {}
        auto_subs = {
            "en": [{"name": "English", "ext": "vtt"}]
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = f"{json.dumps(manual_subs)}\n{json.dumps(auto_subs)}"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        captions = list_captions("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert len(captions) == 1
        assert captions[0] == ("en", "English (auto-generated)", True)

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    def test_list_captions_no_captions(self, mock_check, mock_run):
        """Test listing captions when no captions are available."""
        import pytest
        from src.clipdrop.exceptions import NoCaptionsError

        mock_check.return_value = (True, "yt-dlp found")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "{}\n{}"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with pytest.raises(NoCaptionsError):
            list_captions("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_list_captions_invalid_url(self):
        """Test listing captions with invalid URL."""
        import pytest
        from src.clipdrop.exceptions import YouTubeURLError

        with pytest.raises(YouTubeURLError):
            list_captions("https://vimeo.com/123456789")

    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    def test_list_captions_ytdlp_not_installed(self, mock_check):
        """Test listing captions when yt-dlp is not installed."""
        import pytest
        from src.clipdrop.exceptions import YTDLPNotFoundError

        mock_check.return_value = (False, "yt-dlp not found")

        with pytest.raises(YTDLPNotFoundError):
            list_captions("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    def test_list_captions_ytdlp_error(self, mock_check, mock_run):
        """Test handling yt-dlp errors."""
        import pytest
        from src.clipdrop.exceptions import YouTubeError

        mock_check.return_value = (True, "yt-dlp found")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Video unavailable"
        mock_run.return_value = mock_result

        with pytest.raises(YouTubeError) as exc_info:
            list_captions("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert "Failed to fetch video info" in str(exc_info.value)


class TestCaptionSelection:
    """Test caption selection logic."""

    def test_select_exact_match_manual(self):
        """Test selecting exact match with manual caption."""
        captions = [
            ("en", "English", False),
            ("es", "Spanish", False),
            ("en", "English (auto-generated)", True)
        ]

        selected = select_caption_track(captions, "en")
        assert selected == ("en", "English", False)

    def test_select_exact_match_auto(self):
        """Test selecting exact match with auto-generated caption."""
        captions = [
            ("es", "Spanish", False),
            ("en", "English (auto-generated)", True)
        ]

        selected = select_caption_track(captions, "en")
        assert selected == ("en", "English (auto-generated)", True)

    def test_select_variant_match(self):
        """Test selecting language variant match."""
        captions = [
            ("en-US", "English (United States)", False),
            ("es", "Spanish", False)
        ]

        selected = select_caption_track(captions, "en")
        assert selected == ("en-US", "English (United States)", False)

    def test_select_variant_match_reverse(self):
        """Test selecting with full language code matching base."""
        captions = [
            ("en", "English", False),
            ("es-MX", "Spanish (Mexico)", False)
        ]

        selected = select_caption_track(captions, "en-GB")
        assert selected == ("en", "English", False)

    def test_select_prefer_manual_over_auto(self):
        """Test preferring manual over auto-generated captions."""
        captions = [
            ("en", "English (auto-generated)", True),
            ("en", "English", False)
        ]

        selected = select_caption_track(captions, "en")
        assert selected == ("en", "English", False)

    def test_select_no_preference(self):
        """Test selecting without language preference."""
        captions = [
            ("es", "Spanish (auto-generated)", True),
            ("en", "English", False),
            ("fr", "French", False)
        ]

        selected = select_caption_track(captions, None)
        # Should return first manual caption
        assert selected == ("en", "English", False)

    def test_select_no_preference_auto_only(self):
        """Test selecting without preference when only auto captions available."""
        captions = [
            ("es", "Spanish (auto-generated)", True),
            ("en", "English (auto-generated)", True)
        ]

        selected = select_caption_track(captions, None)
        # Should return first caption
        assert selected == ("es", "Spanish (auto-generated)", True)

    def test_select_fallback(self):
        """Test falling back when preferred language not available."""
        captions = [
            ("es", "Spanish", False),
            ("fr", "French (auto-generated)", True)
        ]

        selected = select_caption_track(captions, "en")
        # Should return best available (manual Spanish)
        assert selected == ("es", "Spanish", False)

    def test_select_empty_list(self):
        """Test selecting from empty caption list."""
        selected = select_caption_track([], "en")
        assert selected is None

    def test_select_case_insensitive(self):
        """Test case-insensitive language matching."""
        captions = [
            ("EN", "English", False),
            ("es", "Spanish", False)
        ]

        selected = select_caption_track(captions, "en")
        assert selected == ("EN", "English", False)