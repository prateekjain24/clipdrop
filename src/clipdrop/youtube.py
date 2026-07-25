"""YouTube URL handling and yt-dlp integration."""

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

# Environment variables for working around YouTube blocking.
# YouTube aggressively bot-checks datacenter/VPN IPs and rate-limits the
# caption endpoints; authenticated cookies are the reliable workaround.
ENV_COOKIES_FILE = 'CLIPDROP_YT_COOKIES'
ENV_COOKIES_FROM_BROWSER = 'CLIPDROP_YT_COOKIES_FROM_BROWSER'
ENV_PLAYER_CLIENT = 'CLIPDROP_YT_PLAYER_CLIENT'

# Player client tried as a fallback when the default clients hit a
# bot-verification wall (mobile web is often exempted when web is not).
FALLBACK_PLAYER_CLIENT = 'mweb'

# Metadata cache freshness window
METADATA_CACHE_DAYS = 7

# Retry behavior for transient failures (timeouts, HTTP 429)
MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 2.0  # seconds; doubles each retry


def validate_youtube_url(url: str) -> bool:
    """
    Validate if a given URL is a valid YouTube URL.

    Supports:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/shorts/VIDEO_ID
    - youtube.com/embed/VIDEO_ID
    - youtube.com/v/VIDEO_ID
    - youtube.com/live/VIDEO_ID
    - music.youtube.com variants
    - m.youtube.com variants

    Args:
        url: The URL string to validate

    Returns:
        True if valid YouTube URL, False otherwise
    """
    if not url:
        return False

    # Comprehensive regex pattern for YouTube URLs
    pattern = r'^(?:(?:https?:)?\/\/)?(?:(?:(?:www|m(?:usic)?)\.)?youtu(?:\.be|be\.com)\/(?:shorts\/|live\/|v\/|e(?:mbed)?\/|watch(?:\/|\?(?:\S+=\S+&)*v=)|oembed\?url=https?:\/\/(?:www|m(?:usic)?)\.youtube\.com\/watch\?(?:\S+=\S+&)*v=|attribution_link\?(?:\S+=\S+&)*u=(?:\/|%2F)watch(?:\?|%3F)v(?:=|%3D))?|www\.youtube-nocookie\.com\/embed\/)([\w\-]{11})(?:[\?&#].*)?$'

    match = re.match(pattern, url, re.IGNORECASE)
    return match is not None


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract the 11-character video ID from a YouTube URL.

    Args:
        url: The YouTube URL string

    Returns:
        The 11-character video ID if found, None otherwise
    """
    if not url:
        return None

    # Remove any whitespace
    url = url.strip()

    # Pattern 1: youtu.be/VIDEO_ID
    match = re.search(r'youtu\.be\/([a-zA-Z0-9_\-]{11})', url, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 2: youtube.com/watch?v=VIDEO_ID (and variants with additional parameters)
    match = re.search(r'[?&]v=([a-zA-Z0-9_\-]{11})(?:[&#]|$)', url, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 3: youtube.com/embed/VIDEO_ID or /v/VIDEO_ID
    match = re.search(r'(?:embed|v)\/([a-zA-Z0-9_\-]{11})(?:[?&#]|$)', url, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 4: youtube.com/shorts/VIDEO_ID or /live/VIDEO_ID
    match = re.search(r'(?:shorts|live)\/([a-zA-Z0-9_\-]{11})(?:[?&#]|$)', url, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 5: youtube-nocookie.com/embed/VIDEO_ID
    match = re.search(r'youtube-nocookie\.com\/embed\/([a-zA-Z0-9_\-]{11})(?:[?&#]|$)', url, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 6: attribution_link with encoded watch URL
    match = re.search(r'attribution_link\?.*u=(?:\/|%2F)watch(?:\?|%3F)v(?:=|%3D)([a-zA-Z0-9_\-]{11})', url, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def check_ytdlp_installed() -> Tuple[bool, str]:
    """
    Check if yt-dlp is installed and available in PATH.

    Returns:
        A tuple of (is_installed, message) where:
        - is_installed: True if yt-dlp is found, False otherwise
        - message: Descriptive message about the status
    """
    ytdlp_path = shutil.which('yt-dlp')

    if ytdlp_path:
        return True, f"yt-dlp found at: {ytdlp_path}"
    else:
        return False, "yt-dlp not found. Install with: pip install clipdrop[youtube]"


def get_ytdlp_version() -> Optional[str]:
    """
    Get the installed yt-dlp version string (e.g. '2026.03.17').

    Returns:
        Version string, or None if it cannot be determined
    """
    try:
        result = subprocess.run(
            ['yt-dlp', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def ytdlp_age_days(version: Optional[str] = None) -> Optional[int]:
    """
    Estimate how old the installed yt-dlp release is, in days.

    yt-dlp uses date-based versions (YYYY.MM.DD). A stale yt-dlp is the
    most common cause of YouTube extraction failures, since YouTube
    changes its site frequently and yt-dlp ships fixes in response.

    Args:
        version: Version string to parse (fetched from yt-dlp if omitted)

    Returns:
        Age in days, or None if the version cannot be determined/parsed
    """
    if version is None:
        version = get_ytdlp_version()
    if not version:
        return None

    match = re.match(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})', version)
    if not match:
        return None

    try:
        release_date = datetime(
            int(match.group(1)), int(match.group(2)), int(match.group(3))
        )
    except ValueError:
        return None

    return max(0, (datetime.now() - release_date).days)


def _classify_ytdlp_error(stderr: str):
    """
    Classify yt-dlp stderr output into a specific exception, if recognized.

    Args:
        stderr: Captured stderr text from a failed yt-dlp run

    Returns:
        An exception instance for bot-check or rate-limit errors,
        None for anything else (caller decides how to report it)
    """
    from .exceptions import YouTubeBotCheckError, YouTubeRateLimitError

    if not stderr:
        return None

    lowered = stderr.lower()

    # "Sign in to confirm you're not a bot" (apostrophe varies by locale/encoding)
    if 'sign in to confirm' in lowered or 'not a bot' in lowered:
        return YouTubeBotCheckError()

    if 'http error 429' in lowered or 'too many requests' in lowered:
        return YouTubeRateLimitError()

    return None


def _build_base_cmd(player_client: Optional[str] = None) -> List[str]:
    """
    Build the base yt-dlp command with hardening flags applied.

    Honors environment variables:
    - CLIPDROP_YT_COOKIES: path to a Netscape-format cookies file
    - CLIPDROP_YT_COOKIES_FROM_BROWSER: browser to read cookies from
      (chrome, firefox, safari, edge, brave, ...)
    - CLIPDROP_YT_PLAYER_CLIENT: override yt-dlp's player client list

    Args:
        player_client: Explicit player client override (takes precedence
            over the environment variable; used for bot-check fallback)

    Returns:
        Base command list to extend with per-call arguments
    """
    cmd = [
        'yt-dlp',
        '--quiet',
        '--no-warnings',
        '--no-playlist',
        '--socket-timeout', '15',
        '--retries', '3',
        '--extractor-retries', '3',
    ]

    cookies_file = os.environ.get(ENV_COOKIES_FILE)
    cookies_browser = os.environ.get(ENV_COOKIES_FROM_BROWSER)
    if cookies_file:
        cmd += ['--cookies', cookies_file]
    elif cookies_browser:
        cmd += ['--cookies-from-browser', cookies_browser]

    client = player_client or os.environ.get(ENV_PLAYER_CLIENT)
    if client:
        cmd += ['--extractor-args', f'youtube:player_client={client}']

    return cmd


def _run_ytdlp(
    args: List[str],
    timeout: int = 30,
    max_attempts: int = MAX_ATTEMPTS,
) -> subprocess.CompletedProcess:
    """
    Run yt-dlp with retries, backoff, and blocking-error detection.

    Transient failures (timeouts, HTTP 429) are retried with exponential
    backoff. A bot-verification block is retried once with the fallback
    player client before giving up, since YouTube often blocks the default
    web client while leaving others working.

    Args:
        args: Command arguments to append to the base command
        timeout: Per-attempt timeout in seconds
        max_attempts: Maximum number of attempts for transient failures

    Returns:
        CompletedProcess for a successful run, or the final failed run
        whose error was not recognized (caller reports it)

    Raises:
        YTDLPNotFoundError: If yt-dlp is not installed
        YouTubeBotCheckError: If YouTube demands bot verification
        YouTubeRateLimitError: If rate-limited after all retries
        YouTubeError: If every attempt times out
    """
    from .exceptions import (
        YTDLPNotFoundError,
        YouTubeError,
        YouTubeBotCheckError,
        YouTubeRateLimitError,
    )

    user_set_client = bool(os.environ.get(ENV_PLAYER_CLIENT))
    player_client = None
    tried_fallback_client = False
    delay = RETRY_BASE_DELAY

    attempt = 0
    while True:
        attempt += 1
        cmd = _build_base_cmd(player_client) + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        except FileNotFoundError:
            raise YTDLPNotFoundError()
        except subprocess.TimeoutExpired:
            if attempt < max_attempts:
                time.sleep(delay)
                delay *= 2
                continue
            raise YouTubeError(
                "Timeout while contacting YouTube (network may be slow "
                "or YouTube may be throttling this connection)"
            )

        if result.returncode == 0:
            return result

        error = _classify_ytdlp_error(result.stderr)

        if isinstance(error, YouTubeRateLimitError):
            if attempt < max_attempts:
                time.sleep(delay)
                delay *= 2
                continue
            raise error

        if isinstance(error, YouTubeBotCheckError):
            # Retry once with the fallback client, unless the user pinned
            # their own client choice via the environment.
            if not tried_fallback_client and not user_set_client:
                tried_fallback_client = True
                player_client = FALLBACK_PLAYER_CLIENT
                continue
            raise error

        # Unrecognized failure: return it for the caller to report with
        # context-specific messaging.
        return result


def _trim_caption_map(caption_map: Any) -> Dict[str, List[Dict[str, str]]]:
    """
    Reduce a yt-dlp subtitles/automatic_captions map to just track names.

    The full map contains per-format download URLs that are bulky and
    expire quickly; only language codes and display names are cached.
    """
    trimmed: Dict[str, List[Dict[str, str]]] = {}
    if not isinstance(caption_map, dict):
        return trimmed
    for lang_code, formats in caption_map.items():
        if formats and isinstance(formats, list):
            name = formats[0].get('name', lang_code) if isinstance(formats[0], dict) else lang_code
            trimmed[lang_code] = [{'name': name}]
        else:
            trimmed[lang_code] = []
    return trimmed


def _fetch_metadata(url: str, cache_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch video metadata and caption listings in a single yt-dlp call.

    Video info and available captions come from the same underlying
    player request, so fetching them together (and caching the result)
    means one network round-trip per video instead of two — halving the
    exposure to YouTube's bot checks and rate limits.

    Args:
        url: The YouTube URL
        cache_dir: Optional cache directory path

    Returns:
        Metadata dictionary including 'subtitles' and 'automatic_captions'

    Raises:
        YTDLPNotFoundError: If yt-dlp is not installed
        YouTubeURLError: If URL is invalid
        YouTubeBotCheckError: If YouTube demands bot verification
        YouTubeRateLimitError: If rate-limited
        YouTubeError: For other errors
    """
    from .exceptions import YTDLPNotFoundError, YouTubeURLError, YouTubeError

    if not validate_youtube_url(url):
        raise YouTubeURLError(url)

    video_id = extract_video_id(url)
    if not video_id:
        raise YouTubeURLError(url)

    is_installed, _ = check_ytdlp_installed()
    if not is_installed:
        raise YTDLPNotFoundError()

    video_cache_dir = get_cache_dir(video_id, cache_dir)
    ensure_cache_dir(video_cache_dir)
    metadata_path = video_cache_dir / "metadata.json"

    # Serve from cache when fresh
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            if 'cached_at' in cached:
                cached_time = datetime.fromisoformat(cached['cached_at'])
                if (datetime.now() - cached_time).days < METADATA_CACHE_DAYS:
                    return cached
        except (json.JSONDecodeError, ValueError, OSError):
            pass  # Invalid cache, re-fetch

    # --ignore-no-formats-error: captions are often still extractable when
    # YouTube blocks the media formats themselves; don't fail the whole
    # request over formats we never download.
    args = [
        '--skip-download',
        '--ignore-no-formats-error',
        '-J',
        url,
    ]

    result = _run_ytdlp(args, timeout=45)

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        raise YouTubeError(f"Failed to fetch video info: {error_msg}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise YouTubeError(f"Failed to parse video information: {str(e)}")

    if not isinstance(data, dict):
        raise YouTubeError("Unexpected video information format")

    metadata = {
        'title': data.get('title') or 'Unknown Title',
        'id': data.get('id') or video_id,
        'uploader': data.get('uploader') or 'Unknown',
        'duration': data.get('duration') or 0,
        'upload_date': data.get('upload_date'),
        'description': data.get('description') or '',
        'view_count': data.get('view_count') or 0,
        'like_count': data.get('like_count') or 0,
        'chapters': data.get('chapters'),
        'subtitles': _trim_caption_map(data.get('subtitles')),
        'automatic_captions': _trim_caption_map(data.get('automatic_captions')),
        'url': url,
        'cached_at': datetime.now().isoformat()
    }

    try:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except OSError:
        pass  # Cache write failure shouldn't fail the request

    return metadata


def list_captions(url: str, cache_dir: Optional[str] = None) -> List[Tuple[str, str, bool]]:
    """
    List available captions for a YouTube video.

    Args:
        url: The YouTube URL
        cache_dir: Optional cache directory path

    Returns:
        List of tuples: (lang_code, name, is_auto_generated)
        Example: [('en', 'English', False), ('es', 'Spanish (auto-generated)', True)]

    Raises:
        YTDLPNotFoundError: If yt-dlp is not installed
        YouTubeURLError: If URL is invalid
        NoCaptionsError: If no captions are available
        YouTubeBotCheckError: If YouTube demands bot verification
        YouTubeRateLimitError: If rate-limited
        YouTubeError: For other yt-dlp errors
    """
    from .exceptions import NoCaptionsError

    metadata = _fetch_metadata(url, cache_dir)

    manual_subs = metadata.get('subtitles') or {}
    auto_subs = metadata.get('automatic_captions') or {}

    captions = []

    # Process manual subtitles
    for lang_code, formats in manual_subs.items():
        if formats and isinstance(formats, list) and len(formats) > 0:
            name = formats[0].get('name', lang_code)
        else:
            name = lang_code
        captions.append((lang_code, name, False))

    # Process auto-generated captions
    for lang_code, formats in auto_subs.items():
        # Skip if we already have manual subs for this language
        if lang_code not in manual_subs:
            if formats and isinstance(formats, list) and len(formats) > 0:
                name = formats[0].get('name', lang_code)
                # Add (auto-generated) to the name if not already present
                if '(auto-generated)' not in name.lower():
                    name = f"{name} (auto-generated)"
            else:
                name = f"{lang_code} (auto-generated)"
            captions.append((lang_code, name, True))

    if not captions:
        raise NoCaptionsError(extract_video_id(url))

    # Sort by language code for consistency
    captions.sort(key=lambda x: x[0])

    return captions


def select_caption_track(
    captions: List[Tuple[str, str, bool]],
    preferred_lang: Optional[str] = None
) -> Optional[Tuple[str, str, bool]]:
    """
    Select the best caption track based on language preference.

    Args:
        captions: List of available captions from list_captions()
        preferred_lang: Preferred language code (e.g., 'en', 'es', 'en-US')

    Returns:
        Best matching caption tuple or None if no captions available

    Selection priority:
    1. Exact match with manual caption
    2. Exact match with auto-generated caption
    3. Language variant match with manual caption (en matches en-US)
    4. Language variant match with auto-generated caption
    5. First manual caption
    6. First auto-generated caption
    """
    if not captions:
        return None

    # If no preference specified, default to English
    if not preferred_lang:
        # Try English first (most common for tech content)
        for caption in captions:
            lang_code, name, is_auto = caption
            if lang_code.lower().startswith('en'):
                # Prefer manual over auto-generated
                if not is_auto:
                    return caption

        # Try auto-generated English if no manual English found
        for caption in captions:
            lang_code, name, is_auto = caption
            if lang_code.lower().startswith('en') and is_auto:
                return caption

        # No English found, try to find any manual caption
        for caption in captions:
            if not caption[2]:  # Not auto-generated
                return caption

        # Fall back to first caption
        return captions[0]

    # Normalize the preferred language (lowercase, strip whitespace)
    preferred_lang = preferred_lang.lower().strip()

    # Extract base language code (e.g., 'en' from 'en-US')
    preferred_base = preferred_lang.split('-')[0]

    # Score each caption
    scored_captions = []
    for caption in captions:
        lang_code, name, is_auto = caption
        normalized_code = lang_code.lower()
        base_code = normalized_code.split('-')[0]

        # Calculate score (higher is better)
        score = 0

        # Exact match
        if normalized_code == preferred_lang:
            score = 100
        # Base language match (en matches en-US)
        elif base_code == preferred_base:
            score = 50
        # No match
        else:
            score = 1

        # Prefer manual over auto-generated
        if not is_auto:
            score += 10

        scored_captions.append((score, caption))

    # Sort by score (highest first)
    scored_captions.sort(key=lambda x: x[0], reverse=True)

    # Return the best match
    return scored_captions[0][1] if scored_captions else None


def get_cache_dir(video_id: str, base_cache_dir: Optional[str] = None) -> Path:
    """
    Get the cache directory path for a video.

    Args:
        video_id: The YouTube video ID
        base_cache_dir: Base cache directory path (defaults to ~/.cache/clipdrop/youtube)

    Returns:
        Path object for the video's cache directory
    """
    if base_cache_dir:
        base_path = Path(base_cache_dir)
    else:
        # Default cache location
        base_path = Path.home() / ".cache" / "clipdrop" / "youtube"

    return base_path / video_id


def ensure_cache_dir(cache_dir: Path) -> None:
    """
    Ensure cache directory exists, create if necessary.

    Args:
        cache_dir: Path to the cache directory
    """
    cache_dir.mkdir(parents=True, exist_ok=True)


def sanitize_filename(title: str) -> str:
    """
    Sanitize video title for use as filename.

    Args:
        title: Video title to sanitize

    Returns:
        Sanitized filename-safe string
    """
    # Replace problematic characters with underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        title = title.replace(char, '_')

    # Remove leading/trailing spaces and dots
    title = title.strip(' .')

    # Truncate if too long (leave room for extensions)
    max_length = 30
    if len(title) > max_length:
        title = title[:max_length].rstrip()

    return title


def download_vtt(
    url: str,
    lang_code: str,
    cache_dir: Optional[str] = None
) -> str:
    """
    Download VTT subtitles for a YouTube video.

    Args:
        url: The YouTube URL
        lang_code: Language code for subtitles (e.g., 'en', 'es')
        cache_dir: Optional cache directory path

    Returns:
        Path to the downloaded VTT file

    Raises:
        YTDLPNotFoundError: If yt-dlp is not installed
        YouTubeURLError: If URL is invalid
        NoCaptionsError: If no captions available for the language
        YouTubeError: For other download errors
    """
    from .exceptions import YTDLPNotFoundError, YouTubeURLError, NoCaptionsError, YouTubeError

    # Validate URL and get video ID
    if not validate_youtube_url(url):
        raise YouTubeURLError(url)

    video_id = extract_video_id(url)
    if not video_id:
        raise YouTubeURLError(url)

    # Check if yt-dlp is installed
    is_installed, _ = check_ytdlp_installed()
    if not is_installed:
        raise YTDLPNotFoundError()

    # Set up cache directory
    video_cache_dir = get_cache_dir(video_id, cache_dir)
    ensure_cache_dir(video_cache_dir)

    # Check if VTT already exists in cache
    vtt_filename = f"{video_id}.{lang_code}.vtt"
    vtt_path = video_cache_dir / vtt_filename

    if vtt_path.exists():
        return str(vtt_path)

    # Download VTT using yt-dlp
    output_template = str(video_cache_dir / f"{video_id}.%(lang)s.%(ext)s")

    args = [
        '--skip-download',  # Don't download video
        '--write-sub',      # Write manual subtitles
        '--write-auto-sub', # Write auto-generated if manual not available
        '--sub-format', 'vtt',  # Force VTT format
        '--sub-lang', lang_code,  # Specific language
        '-o', output_template,  # Output template
        url
    ]

    result = _run_ytdlp(args, timeout=60)

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"

        # Check if it's a "no subtitles" error
        if "no subtitles" in error_msg.lower() or "subtitle" in error_msg.lower():
            raise NoCaptionsError(f"No captions available for language: {lang_code}")

        raise YouTubeError(f"Failed to download VTT: {error_msg}")

    # Check if file was created
    if not vtt_path.exists():
        # Try with just the language code (without region)
        alt_vtt_path = video_cache_dir / f"{video_id}.{lang_code.split('-')[0]}.vtt"
        if alt_vtt_path.exists():
            # Rename to expected name
            alt_vtt_path.rename(vtt_path)
        else:
            # Try with NA prefix (yt-dlp sometimes adds this)
            na_vtt_path = video_cache_dir / f"{video_id}.NA.{lang_code}.vtt"
            if na_vtt_path.exists():
                # Rename to expected name
                na_vtt_path.rename(vtt_path)
            else:
                # Try with NA and short lang code
                na_short_vtt_path = video_cache_dir / f"{video_id}.NA.{lang_code.split('-')[0]}.vtt"
                if na_short_vtt_path.exists():
                    na_short_vtt_path.rename(vtt_path)
                else:
                    raise NoCaptionsError(f"No captions downloaded for language: {lang_code}")

    return str(vtt_path)


def get_video_info(url: str, cache_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Get video information from YouTube URL.

    Shares a single cached metadata fetch with list_captions(), so calling
    both costs one network request instead of two.

    Args:
        url: The YouTube URL
        cache_dir: Optional cache directory path

    Returns:
        Dictionary containing video info (title, id, uploader, duration, etc.)

    Raises:
        YTDLPNotFoundError: If yt-dlp is not installed
        YouTubeURLError: If URL is invalid
        YouTubeBotCheckError: If YouTube demands bot verification
        YouTubeRateLimitError: If rate-limited
        YouTubeError: For other errors
    """
    return _fetch_metadata(url, cache_dir)


def parse_vtt(vtt_content: str) -> List[Dict[str, Any]]:
    """
    Parse VTT content into structured data.

    Args:
        vtt_content: The VTT file content as a string

    Returns:
        List of cue dictionaries with start_time, end_time, and text
    """
    if not vtt_content:
        return []

    cues = []
    lines = vtt_content.strip().split('\n')

    # Skip WEBVTT header and any metadata
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('WEBVTT'):
            i += 1
            continue
        if line.startswith('NOTE') or line.startswith('STYLE'):
            # Skip NOTE and STYLE blocks
            i += 1
            while i < len(lines) and lines[i].strip():
                i += 1
            continue
        break

    # Parse cues
    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if this is a timestamp line or cue identifier
        # Pattern handles both HH:MM:SS.mmm and MM:SS.mmm formats
        timestamp_pattern = r'(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})'
        timestamp_match = re.search(timestamp_pattern, line)

        if timestamp_match:
            # Found timestamp directly
            start_time = timestamp_match.group(1).replace(',', '.')
            end_time = timestamp_match.group(2).replace(',', '.')

            # Collect subtitle text
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip() and not re.search(timestamp_pattern, lines[i]):
                text_lines.append(lines[i].strip())
                i += 1

            cues.append({
                'start_time': start_time,
                'end_time': end_time,
                'text': '\n'.join(text_lines)
            })
        else:
            # This might be a cue identifier, check next line for timestamp
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                timestamp_match = re.search(timestamp_pattern, next_line)
                if timestamp_match:
                    # Skip cue identifier and move to timestamp line
                    start_time = timestamp_match.group(1).replace(',', '.')
                    end_time = timestamp_match.group(2).replace(',', '.')

                    # Collect subtitle text (starting from line after timestamp)
                    i += 2
                    text_lines = []
                    while i < len(lines) and lines[i].strip() and not re.search(timestamp_pattern, lines[i]):
                        text_lines.append(lines[i].strip())
                        i += 1

                    cues.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': '\n'.join(text_lines)
                    })
                else:
                    i += 1
            else:
                i += 1

    return cues


def vtt_to_srt(vtt_content: str) -> str:
    """
    Convert VTT subtitle content to SRT format.

    Args:
        vtt_content: The VTT file content as a string

    Returns:
        The converted SRT content as a string

    Conversion includes:
    - Removing WEBVTT header
    - Adding sequence numbers
    - Converting timestamps from . to ,
    - Removing VTT-specific formatting
    """
    if not vtt_content or not vtt_content.strip():
        return ""

    # Parse VTT into structured data
    cues = parse_vtt(vtt_content)

    if not cues:
        return ""

    srt_lines = []
    for i, cue in enumerate(cues, start=1):
        # Add sequence number
        srt_lines.append(str(i))

        # Convert timestamps (replace . with ,)
        start_time = cue['start_time'].replace('.', ',')
        end_time = cue['end_time'].replace('.', ',')

        # Ensure timestamps have hours:minutes:seconds,milliseconds format
        if start_time.count(':') == 1:  # Missing hours
            start_time = '00:' + start_time
        if end_time.count(':') == 1:  # Missing hours
            end_time = '00:' + end_time

        srt_lines.append(f"{start_time} --> {end_time}")

        # Add text (clean up any HTML tags)
        text = cue['text']
        # Remove common HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove VTT positioning tags
        text = re.sub(r'\{.*?\}', '', text)

        srt_lines.append(text)

        # Add blank line separator (except for the last entry)
        if i < len(cues):
            srt_lines.append("")

    return '\n'.join(srt_lines)


def vtt_to_txt(vtt_content: str, preserve_paragraphs: bool = True) -> str:
    """
    Extract plain text from VTT subtitle content.

    Args:
        vtt_content: The VTT file content as a string
        preserve_paragraphs: Whether to add paragraph breaks for readability

    Returns:
        The extracted plain text

    Extraction includes:
    - Removing all timestamps and cue identifiers
    - Stripping HTML and formatting tags
    - Concatenating text with appropriate spacing
    """
    if not vtt_content or not vtt_content.strip():
        return ""

    # Parse VTT into structured data
    cues = parse_vtt(vtt_content)

    if not cues:
        return ""

    text_parts = []
    last_text = None

    for cue in cues:
        # Clean up text
        text = cue['text']
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove VTT formatting
        text = re.sub(r'\{.*?\}', '', text)
        # Clean up extra whitespace
        text = ' '.join(text.split())

        # Skip duplicate text (when same subtitle appears multiple times)
        if text and text != last_text:
            text_parts.append(text)
            last_text = text

    if preserve_paragraphs:
        # Join with paragraph breaks for better readability
        # Group consecutive short lines as paragraphs
        result = []
        current_paragraph = []

        for text in text_parts:
            if len(text) > 80 or text.endswith(('.', '!', '?')):
                # End of sentence or long text, start new paragraph
                if current_paragraph:
                    result.append(' '.join(current_paragraph))
                    current_paragraph = []
                result.append(text)
            else:
                current_paragraph.append(text)

        if current_paragraph:
            result.append(' '.join(current_paragraph))

        return '\n\n'.join(result)
    else:
        # Simple concatenation with spaces
        return ' '.join(text_parts)


def vtt_to_md(vtt_content: str, include_timestamps: bool = True) -> str:
    """
    Convert VTT subtitle content to Markdown format.

    Args:
        vtt_content: The VTT file content as a string
        include_timestamps: Whether to include timestamp ranges in the output

    Returns:
        The converted Markdown content as a string

    Conversion includes:
    - Adding a Transcript heading
    - Optional timestamp ranges in bold
    - Cleaning HTML tags and VTT formatting
    - Paragraph formatting for readability
    """
    if not vtt_content or not vtt_content.strip():
        return ""

    # Parse VTT into structured data
    cues = parse_vtt(vtt_content)

    if not cues:
        return ""

    # Start with heading
    md_lines = ["# Transcript", ""]

    if include_timestamps:
        # Format with timestamp ranges
        for cue in cues:
            # Format timestamps (remove milliseconds for cleaner display)
            start_time = cue['start_time'].split('.')[0]
            end_time = cue['end_time'].split('.')[0]

            # Add hours if missing (for consistency)
            if start_time.count(':') == 1:
                start_time = '00:' + start_time
            if end_time.count(':') == 1:
                end_time = '00:' + end_time

            # Add timestamp range in bold
            md_lines.append(f"**{start_time} - {end_time}**")

            # Clean and add text
            text = cue['text']
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            # Remove VTT formatting
            text = re.sub(r'\{.*?\}', '', text)

            # Preserve line breaks in multi-line subtitles
            if '\n' in text:
                # Multi-line text - preserve structure
                lines = text.split('\n')
                for line in lines:
                    md_lines.append(line.strip())
            else:
                md_lines.append(text)

            # Add blank line for readability
            md_lines.append("")

    else:
        # Format without timestamps (similar to txt but with better structure)
        text_parts = []
        last_text = None

        for cue in cues:
            # Clean up text
            text = cue['text']
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            # Remove VTT formatting
            text = re.sub(r'\{.*?\}', '', text)
            # Clean up extra whitespace
            text = ' '.join(text.split())

            # Skip duplicate text
            if text and text != last_text:
                text_parts.append(text)
                last_text = text

        # Group into paragraphs for better readability
        current_paragraph = []
        for text in text_parts:
            if len(text) > 80 or text.endswith(('.', '!', '?')):
                # End of sentence or long text
                if current_paragraph:
                    md_lines.append(' '.join(current_paragraph))
                    md_lines.append("")
                    current_paragraph = []
                md_lines.append(text)
                md_lines.append("")
            else:
                current_paragraph.append(text)

        if current_paragraph:
            md_lines.append(' '.join(current_paragraph))
            md_lines.append("")

    # Remove trailing empty lines and return
    while md_lines and md_lines[-1] == "":
        md_lines.pop()

    return '\n'.join(md_lines)