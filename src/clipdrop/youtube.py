"""YouTube URL handling and yt-dlp integration."""

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any


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


def list_captions(url: str) -> List[Tuple[str, str, bool]]:
    """
    List available captions for a YouTube video.

    Args:
        url: The YouTube URL

    Returns:
        List of tuples: (lang_code, name, is_auto_generated)
        Example: [('en', 'English', False), ('es', 'Spanish (auto-generated)', True)]

    Raises:
        YTDLPNotFoundError: If yt-dlp is not installed
        YouTubeURLError: If URL is invalid
        NoCaptionsError: If no captions are available
        YouTubeError: For other yt-dlp errors
    """
    from .exceptions import YTDLPNotFoundError, YouTubeURLError, NoCaptionsError, YouTubeError

    # Check if URL is valid
    if not validate_youtube_url(url):
        raise YouTubeURLError(url)

    # Check if yt-dlp is installed
    is_installed, _ = check_ytdlp_installed()
    if not is_installed:
        raise YTDLPNotFoundError()

    try:
        # Run yt-dlp to get video info with subtitles
        cmd = [
            'yt-dlp',
            '--quiet',
            '--no-warnings',
            '--print', '%(subtitles)j',
            '--print', '%(automatic_captions)j',
            url
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            raise YouTubeError(f"Failed to fetch video info: {error_msg}")

        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            raise NoCaptionsError(extract_video_id(url))

        # Parse the JSON outputs
        try:
            manual_subs = json.loads(lines[0]) if lines[0] and lines[0] != 'null' else {}
            auto_subs = json.loads(lines[1]) if lines[1] and lines[1] != 'null' else {}
        except json.JSONDecodeError:
            manual_subs = {}
            auto_subs = {}

        captions = []

        # Process manual subtitles
        for lang_code, formats in manual_subs.items():
            # Get the language name from the first format entry
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

    except subprocess.TimeoutExpired:
        raise YouTubeError("Timeout while fetching video information")
    except subprocess.CalledProcessError as e:
        raise YouTubeError(f"Failed to run yt-dlp: {str(e)}")
    except FileNotFoundError:
        raise YTDLPNotFoundError()


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

    # If no preference specified, return first manual caption or first caption
    if not preferred_lang:
        # Try to find a manual caption first
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
    max_length = 200
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
    try:
        # Build yt-dlp command
        output_template = str(video_cache_dir / f"{video_id}.%(lang)s.%(ext)s")

        cmd = [
            'yt-dlp',
            '--quiet',
            '--no-warnings',
            '--skip-download',  # Don't download video
            '--write-sub',      # Write manual subtitles
            '--write-auto-sub', # Write auto-generated if manual not available
            '--sub-format', 'vtt',  # Force VTT format
            '--sub-lang', lang_code,  # Specific language
            '-o', output_template,  # Output template
            url
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )

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
                raise NoCaptionsError(f"No captions downloaded for language: {lang_code}")

        return str(vtt_path)

    except subprocess.TimeoutExpired:
        raise YouTubeError("Timeout while downloading VTT file")
    except subprocess.CalledProcessError as e:
        raise YouTubeError(f"Failed to run yt-dlp: {str(e)}")
    except FileNotFoundError:
        raise YTDLPNotFoundError()


def get_video_info(url: str, cache_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Get video information from YouTube URL.

    Args:
        url: The YouTube URL
        cache_dir: Optional cache directory path

    Returns:
        Dictionary containing video info (title, id, uploader, duration, etc.)

    Raises:
        YTDLPNotFoundError: If yt-dlp is not installed
        YouTubeURLError: If URL is invalid
        YouTubeError: For other errors
    """
    from .exceptions import YTDLPNotFoundError, YouTubeURLError, YouTubeError

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

    # Check if info already exists in cache
    info_path = video_cache_dir / "info.json"

    if info_path.exists():
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                cached_info = json.load(f)
                # Check if cache is recent (within 7 days)
                if 'cached_at' in cached_info:
                    cached_time = datetime.fromisoformat(cached_info['cached_at'])
                    if (datetime.now() - cached_time).days < 7:
                        return cached_info
        except (json.JSONDecodeError, ValueError):
            # Invalid cache, will re-fetch
            pass

    # Fetch video info using yt-dlp
    try:
        cmd = [
            'yt-dlp',
            '--quiet',
            '--no-warnings',
            '--skip-download',
            '--print', '%(title)j',
            '--print', '%(id)j',
            '--print', '%(uploader)j',
            '--print', '%(duration)j',
            '--print', '%(upload_date)j',
            '--print', '%(description)j',
            '--print', '%(view_count)j',
            '--print', '%(like_count)j',
            url
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            raise YouTubeError(f"Failed to fetch video info: {error_msg}")

        lines = result.stdout.strip().split('\n')
        if len(lines) < 8:
            raise YouTubeError("Incomplete video information received")

        # Parse the output
        video_info = {
            'title': json.loads(lines[0]) if lines[0] != 'null' else 'Unknown Title',
            'id': json.loads(lines[1]) if lines[1] != 'null' else video_id,
            'uploader': json.loads(lines[2]) if lines[2] != 'null' else 'Unknown',
            'duration': json.loads(lines[3]) if lines[3] != 'null' else 0,
            'upload_date': json.loads(lines[4]) if lines[4] != 'null' else None,
            'description': json.loads(lines[5]) if lines[5] != 'null' else '',
            'view_count': json.loads(lines[6]) if lines[6] != 'null' else 0,
            'like_count': json.loads(lines[7]) if lines[7] != 'null' else 0,
            'url': url,
            'cached_at': datetime.now().isoformat()
        }

        # Save to cache
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(video_info, f, indent=2, ensure_ascii=False)

        return video_info

    except subprocess.TimeoutExpired:
        raise YouTubeError("Timeout while fetching video information")
    except subprocess.CalledProcessError as e:
        raise YouTubeError(f"Failed to run yt-dlp: {str(e)}")
    except FileNotFoundError:
        raise YTDLPNotFoundError()
    except (json.JSONDecodeError, IndexError) as e:
        raise YouTubeError(f"Failed to parse video information: {str(e)}")


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