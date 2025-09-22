"""Tests for YouTube URL handling and yt-dlp integration."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from src.clipdrop.youtube import (
    validate_youtube_url,
    extract_video_id,
    check_ytdlp_installed,
    list_captions,
    select_caption_track,
    get_cache_dir,
    ensure_cache_dir,
    sanitize_filename,
    download_vtt,
    get_video_info
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


class TestCacheHelpers:
    """Test cache helper functions."""

    def test_get_cache_dir_default(self):
        """Test getting cache directory with default path."""
        video_id = "dQw4w9WgXcQ"
        cache_dir = get_cache_dir(video_id)

        expected = Path.home() / ".cache" / "clipdrop" / "youtube" / video_id
        assert cache_dir == expected

    def test_get_cache_dir_custom(self):
        """Test getting cache directory with custom path."""
        video_id = "dQw4w9WgXcQ"
        custom_base = "/tmp/custom_cache"
        cache_dir = get_cache_dir(video_id, custom_base)

        expected = Path("/tmp/custom_cache") / video_id
        assert cache_dir == expected

    def test_ensure_cache_dir(self):
        """Test cache directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test" / "nested" / "cache"
            ensure_cache_dir(cache_path)

            assert cache_path.exists()
            assert cache_path.is_dir()

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test with special characters
        title = 'Test: Video <with> "Special" Characters/Slash\\Back|Question?'
        sanitized = sanitize_filename(title)
        assert sanitized == 'Test_ Video _with_ _Special_ Characters_Slash_Back_Question_'

        # Test truncation
        long_title = "a" * 250
        sanitized = sanitize_filename(long_title)
        assert len(sanitized) == 200

        # Test leading/trailing spaces and dots
        title = "  .Test Title.  "
        sanitized = sanitize_filename(title)
        assert sanitized == "Test Title"


class TestVTTDownload:
    """Test VTT download functionality."""

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    @patch('src.clipdrop.youtube.Path.exists')
    def test_download_vtt_from_cache(self, mock_exists, mock_check, mock_run):
        """Test returning VTT from cache when it exists."""
        mock_check.return_value = (True, "yt-dlp found")
        mock_exists.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            result = download_vtt(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "en",
                tmpdir
            )

            # Should return cached path without running yt-dlp
            assert "dQw4w9WgXcQ.en.vtt" in result
            mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    @patch('src.clipdrop.youtube.Path.exists')
    @patch('src.clipdrop.youtube.ensure_cache_dir')
    def test_download_vtt_new(self, mock_ensure, mock_exists, mock_check, mock_run):
        """Test downloading new VTT file."""
        mock_check.return_value = (True, "yt-dlp found")
        # First call checks cache (doesn't exist), second checks after download
        mock_exists.side_effect = [False, True]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            result = download_vtt(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "en",
                tmpdir
            )

            assert "dQw4w9WgXcQ.en.vtt" in result
            mock_run.assert_called_once()

            # Check yt-dlp command
            call_args = mock_run.call_args[0][0]
            assert 'yt-dlp' in call_args
            assert '--skip-download' in call_args
            assert '--sub-format' in call_args
            assert 'vtt' in call_args
            assert '--sub-lang' in call_args
            assert 'en' in call_args

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    def test_download_vtt_no_captions(self, mock_check, mock_run):
        """Test handling when no captions are available."""
        import pytest
        from src.clipdrop.exceptions import NoCaptionsError

        mock_check.return_value = (True, "yt-dlp found")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "No subtitles found"
        mock_run.return_value = mock_result

        with pytest.raises(NoCaptionsError):
            download_vtt("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "en")

    def test_download_vtt_invalid_url(self):
        """Test downloading VTT with invalid URL."""
        import pytest
        from src.clipdrop.exceptions import YouTubeURLError

        with pytest.raises(YouTubeURLError):
            download_vtt("https://vimeo.com/123456789", "en")

    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    def test_download_vtt_ytdlp_not_installed(self, mock_check):
        """Test downloading VTT when yt-dlp is not installed."""
        import pytest
        from src.clipdrop.exceptions import YTDLPNotFoundError

        mock_check.return_value = (False, "yt-dlp not found")

        with pytest.raises(YTDLPNotFoundError):
            download_vtt("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "en")


class TestVideoInfo:
    """Test video info fetching functionality."""

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.clipdrop.youtube.Path.exists')
    @patch('src.clipdrop.youtube.ensure_cache_dir')
    def test_get_video_info_from_cache(self, mock_ensure, mock_exists, mock_file_open, mock_check, mock_run):
        """Test returning video info from cache."""
        mock_check.return_value = (True, "yt-dlp found")
        mock_exists.return_value = True

        cached_data = {
            'title': 'Test Video',
            'id': 'dQw4w9WgXcQ',
            'cached_at': datetime.now().isoformat()
        }
        mock_file_open.return_value.read.return_value = json.dumps(cached_data)

        # Configure mock to properly handle json.load
        mock_file_open.return_value.__enter__.return_value.read.return_value = json.dumps(cached_data)

        result = get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert result['title'] == 'Test Video'
        assert result['id'] == 'dQw4w9WgXcQ'
        mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.clipdrop.youtube.Path.exists')
    @patch('src.clipdrop.youtube.ensure_cache_dir')
    def test_get_video_info_expired_cache(self, mock_ensure, mock_exists, mock_file_open, mock_check, mock_run):
        """Test fetching new info when cache is expired."""
        mock_check.return_value = (True, "yt-dlp found")
        mock_exists.return_value = True

        # Create expired cache (8 days old)
        old_time = datetime.now() - timedelta(days=8)
        cached_data = {
            'title': 'Old Title',
            'id': 'dQw4w9WgXcQ',
            'cached_at': old_time.isoformat()
        }

        # Configure mock to handle json.load for reading
        mock_file_open.return_value.__enter__.return_value.read.return_value = json.dumps(cached_data)

        # Mock yt-dlp response
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '"New Title"\n"dQw4w9WgXcQ"\n"TestUser"\n300\n"20240101"\n"Description"\n1000\n50'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert result['title'] == 'New Title'
        mock_run.assert_called_once()

    @patch('subprocess.run')
    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.clipdrop.youtube.Path.exists')
    @patch('src.clipdrop.youtube.ensure_cache_dir')
    def test_get_video_info_new(self, mock_ensure, mock_exists, mock_file_open, mock_check, mock_run):
        """Test fetching new video info."""
        mock_check.return_value = (True, "yt-dlp found")
        mock_exists.return_value = False

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '"Test Video"\n"dQw4w9WgXcQ"\n"TestUser"\n300\n"20240101"\n"Test Description"\n1000000\n50000'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert result['title'] == 'Test Video'
        assert result['id'] == 'dQw4w9WgXcQ'
        assert result['uploader'] == 'TestUser'
        assert result['duration'] == 300
        assert result['view_count'] == 1000000
        assert result['like_count'] == 50000

        # Check yt-dlp was called with correct parameters
        call_args = mock_run.call_args[0][0]
        assert 'yt-dlp' in call_args
        assert '--skip-download' in call_args
        assert '--print' in call_args

    def test_get_video_info_invalid_url(self):
        """Test getting info with invalid URL."""
        import pytest
        from src.clipdrop.exceptions import YouTubeURLError

        with pytest.raises(YouTubeURLError):
            get_video_info("https://vimeo.com/123456789")

    @patch('src.clipdrop.youtube.check_ytdlp_installed')
    def test_get_video_info_ytdlp_not_installed(self, mock_check):
        """Test getting info when yt-dlp is not installed."""
        import pytest
        from src.clipdrop.exceptions import YTDLPNotFoundError

        mock_check.return_value = (False, "yt-dlp not found")

        with pytest.raises(YTDLPNotFoundError):
            get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")