"""HTML parsing and image extraction for clipboard content.

This module handles parsing HTML from clipboard, extracting images,
and preparing content for PDF generation.
"""

import base64
import io
import re
import subprocess
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from PIL import Image



def get_html_from_clipboard() -> Optional[str]:
    """
    Get HTML format content from macOS clipboard.

    Returns:
        HTML string if available, None otherwise
    """
    try:
        # Get HTML format from clipboard using AppleScript
        # The clipboard stores HTML as hex-encoded data
        result = subprocess.run(
            ['osascript', '-e', 'the clipboard as «class HTML»'],
            capture_output=True,
            text=False,
            timeout=2
        )

        if result.returncode == 0 and result.stdout:
            # The output is in format: «data HTML[hex]»
            output = result.stdout.decode('utf-8', errors='ignore')

            # Extract hex data between «data HTML and »
            match = re.search(r'«data HTML([0-9A-Fa-f]+)»', output)
            if match:
                hex_data = match.group(1)
                # Convert hex to bytes then decode as UTF-8
                html_bytes = bytes.fromhex(hex_data)
                return html_bytes.decode('utf-8', errors='ignore')
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception):
        pass

    return None


def parse_html_content(html: str) -> Tuple[str, List[dict]]:
    """
    Parse HTML content and extract text and images.

    Args:
        html: HTML string to parse

    Returns:
        Tuple of (text content, list of image info dicts)
    """
    soup = BeautifulSoup(html, 'lxml')

    # Extract clean text
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text with preserved structure
    text = soup.get_text(separator='\n', strip=True)

    # Find all images
    images = []
    for idx, img in enumerate(soup.find_all('img')):
        src = img.get('src', '')
        alt = img.get('alt', f'Image {idx + 1}')

        if not src:
            continue

        image_info = {
            'src': src,
            'alt': alt,
            'type': 'unknown',
            'data': None,
            'position': idx
        }

        if src.startswith('data:image'):
            # Base64 embedded image
            image_info['type'] = 'base64'
            image_info['data'] = extract_base64_image(src)
        elif src.startswith(('http://', 'https://')):
            # External image URL
            image_info['type'] = 'url'
            # Store URL for later download
        elif src.startswith('//'):
            # Protocol-relative URL
            image_info['type'] = 'url'
            image_info['src'] = 'https:' + src

        images.append(image_info)

    return text, images


def extract_base64_image(data_url: str) -> Optional[Image.Image]:
    """
    Extract image from base64 data URL.

    Args:
        data_url: Base64 data URL string

    Returns:
        PIL Image object or None if extraction fails
    """
    try:
        # Format: data:image/png;base64,[base64_data]
        if ',' in data_url:
            header, base64_data = data_url.split(',', 1)

            # Decode base64
            image_data = base64.b64decode(base64_data)

            # Create PIL Image
            image = Image.open(io.BytesIO(image_data))
            return image
    except Exception:
        pass

    return None


def download_image(url: str, timeout: int = 5) -> Optional[Image.Image]:
    """
    Download image from URL.

    Args:
        url: Image URL to download
        timeout: Request timeout in seconds

    Returns:
        PIL Image object or None if download fails
    """
    try:
        # Set headers to appear as a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            return None

        # Create PIL Image from response content
        image = Image.open(io.BytesIO(response.content))
        return image

    except (requests.RequestException, IOError):
        pass

    return None


def process_html_images(images: List[dict]) -> List[Image.Image]:
    """
    Process list of image info and return PIL Image objects.

    Args:
        images: List of image info dictionaries

    Returns:
        List of PIL Image objects
    """
    processed_images = []

    for img_info in images:
        pil_image = None

        if img_info['type'] == 'base64' and img_info.get('data'):
            # Already extracted
            pil_image = img_info['data']
        elif img_info['type'] == 'url' and img_info.get('src'):
            # Download the image
            pil_image = download_image(img_info['src'])

        if pil_image:
            processed_images.append(pil_image)

    return processed_images


def extract_content_from_html(html: str) -> Tuple[str, List[Image.Image]]:
    """
    Main function to extract text and images from HTML clipboard content.

    Args:
        html: HTML string from clipboard

    Returns:
        Tuple of (text content, list of PIL Image objects)
    """
    if not html:
        return "", []

    # Parse HTML
    text, image_infos = parse_html_content(html)

    # Process images
    images = process_html_images(image_infos)

    return text, images


def has_html_content() -> bool:
    """
    Check if clipboard has HTML content.

    Returns:
        True if HTML content is available
    """
    html = get_html_from_clipboard()
    return html is not None and len(html.strip()) > 0


def get_html_with_images() -> Optional[Tuple[str, str, List[Image.Image]]]:
    """
    Get HTML content with extracted text and images.

    Returns:
        Tuple of (raw HTML, text, images) or None if no HTML
    """
    html = get_html_from_clipboard()
    if not html:
        return None

    text, images = extract_content_from_html(html)
    return html, text, images