"""HTML parsing and image extraction for clipboard content.

This module handles parsing HTML from clipboard, extracting images,
and preparing content for PDF generation.
"""

import base64
import io
import ipaddress
import re
import socket
import subprocess
import warnings
from typing import List, Optional, Tuple, Any, Dict
from urllib.parse import urlparse

import html2text
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image


# Cap on bytes fetched/decoded for a single remote image (defense-in-depth
# against decompression bombs and oversized downloads).
MAX_IMAGE_BYTES = 25 * 1024 * 1024


def _safe_open_image(data: bytes) -> Optional[Image.Image]:
    """Open image bytes, refusing decompression bombs and malformed data.

    Pillow only *warns* between MAX_IMAGE_PIXELS and 2x; promote that to an
    error so untrusted images can't exhaust memory.
    """
    if not data or len(data) > MAX_IMAGE_BYTES:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(data))
            image.load()  # force decode so bomb/format checks actually run
            return image
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, ValueError):
        return None


def _is_safe_public_url(url: str) -> bool:
    """Return True only for http(s) URLs that resolve to a public IP.

    Blocks SSRF vectors: non-http(s) schemes and private / loopback /
    link-local / reserved / multicast addresses (incl. cloud metadata
    endpoints like 169.254.169.254).
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False

    try:
        # Resolve every address the host maps to (A + AAAA) and require all
        # of them to be public, to defend against DNS-rebinding tricks.
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except (socket.gaierror, UnicodeError, ValueError):
        return False

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False
    return True



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


def parse_html_content_ordered(html: str, allow_remote: bool = False) -> List[Tuple[str, Any]]:
    """
    Parse HTML content and extract ordered chunks of text and images.
    Preserves formatting using Markdown.

    Args:
        html: HTML string to parse
        allow_remote: Whether to fetch remote (http/https) images

    Returns:
        List of (type, content) tuples in document order
    """
    soup = BeautifulSoup(html, 'lxml')

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    chunks = []

    # Create a custom HTML with placeholders for images
    img_counter = 0
    img_map = {}

    # Process images and replace with placeholders
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src:
            placeholder = f"[IMAGE_{img_counter}]"
            img_map[placeholder] = src
            # Replace image with placeholder text
            img.replace_with(soup.new_string(placeholder))
            img_counter += 1

    # Convert HTML to Markdown
    h = html2text.HTML2Text()
    h.body_width = 0  # Don't wrap lines
    h.unicode_snob = True  # Use unicode
    h.skip_internal_links = False
    h.inline_links = True  # Keep links inline
    h.protect_links = True
    h.wrap_links = False
    h.ul_style_dash = True  # Use dashes for unordered lists

    # Convert the modified HTML to Markdown
    markdown_text = h.handle(str(soup))

    # Split text by image placeholders and reconstruct with images
    current_text = []
    lines = markdown_text.split('\n')

    for line in lines:
        # Check if line contains an image placeholder
        found_placeholder = None
        for placeholder in img_map.keys():
            if placeholder in line:
                found_placeholder = placeholder
                break

        if found_placeholder:
            # Add accumulated text before image
            if current_text:
                text = '\n'.join(current_text).strip()
                if text:
                    chunks.append(('text', text))
                current_text.clear()

            # Process and add the image
            src = img_map[found_placeholder]
            img_data = None

            if src.startswith('data:image'):
                img_data = extract_base64_image(src)
            elif src.startswith(('http://', 'https://')):
                img_data = download_image(src, allow_remote=allow_remote)
            elif src.startswith('//'):
                img_data = download_image('https:' + src, allow_remote=allow_remote)

            if img_data:
                chunks.append(('image', img_data))

            # Remove the placeholder from the line and continue
            remaining_text = line.replace(found_placeholder, '').strip()
            if remaining_text:
                current_text.append(remaining_text)
        else:
            # Regular text line
            current_text.append(line)

    # Add any remaining text
    if current_text:
        text = '\n'.join(current_text).strip()
        if text:
            chunks.append(('text', text))

    return chunks


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
            _, base64_data = data_url.split(',', 1)
            image_data = base64.b64decode(base64_data)
            return _safe_open_image(image_data)
    except (ValueError, base64.binascii.Error):
        pass

    return None


def download_image(url: str, timeout: int = 5, allow_remote: bool = False) -> Optional[Image.Image]:
    """
    Download an image from a remote URL.

    Remote fetching is opt-in: by default this returns ``None`` so ClipDrop
    never silently reaches out to the network (privacy) or to internal hosts
    (SSRF). When enabled, only public http(s) URLs are fetched.

    Args:
        url: Image URL to download
        timeout: Request timeout in seconds
        allow_remote: Must be True to actually perform the network request

    Returns:
        PIL Image object or None if fetching is disabled/unsafe/fails
    """
    if not allow_remote:
        return None

    if not _is_safe_public_url(url):
        return None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            return None

        # Bound the amount we read to guard against oversized payloads.
        chunks = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            chunks.extend(chunk)
            if len(chunks) > MAX_IMAGE_BYTES:
                return None

        return _safe_open_image(bytes(chunks))

    except (requests.RequestException, IOError):
        return None


def process_html_images(images: List[dict], allow_remote: bool = False) -> List[Image.Image]:
    """
    Process list of image info and return PIL Image objects.

    Args:
        images: List of image info dictionaries
        allow_remote: Whether to fetch remote (http/https) images

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
            pil_image = download_image(img_info['src'], allow_remote=allow_remote)

        if pil_image:
            processed_images.append(pil_image)

    return processed_images


def extract_content_from_html(html: str, allow_remote: bool = False) -> Tuple[str, List[Image.Image]]:
    """
    Main function to extract text and images from HTML clipboard content.

    Args:
        html: HTML string from clipboard
        allow_remote: Whether to fetch remote (http/https) images

    Returns:
        Tuple of (text content, list of PIL Image objects)
    """
    if not html:
        return "", []

    # Parse HTML
    text, image_infos = parse_html_content(html)

    # Process images
    images = process_html_images(image_infos, allow_remote=allow_remote)

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


def parse_html_content_enhanced(html: str, allow_remote: bool = False) -> List[Tuple[str, Any, Dict]]:
    """
    Enhanced HTML parsing that preserves more structure and formatting.
    Specifically optimized for educational content.

    Args:
        html: HTML string to parse

    Returns:
        List of (type, content, metadata) tuples preserving document structure
    """
    soup = BeautifulSoup(html, 'lxml')

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    chunks = []

    def process_element(element, depth=0):
        """Recursively process HTML elements preserving structure."""
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                return [('text', text, {'depth': depth})]
            return []

        if not isinstance(element, Tag):
            return []

        element_chunks = []
        tag_name = element.name.lower()

        # Handle different HTML elements
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Headers
            text = element.get_text(strip=True)
            if text:
                level = int(tag_name[1])
                element_chunks.append(('heading', text, {'level': level, 'depth': depth}))

        elif tag_name == 'p':
            # Paragraphs
            text = element.get_text(strip=True)
            if text:
                # Check for special paragraph types (bold, highlighted, etc)
                has_strong = element.find('strong') or element.find('b')
                has_em = element.find('em') or element.find('i')
                has_mark = element.find('mark')

                metadata = {'depth': depth}
                if has_strong:
                    metadata['emphasis'] = 'strong'
                if has_em:
                    metadata['emphasis'] = 'italic'
                if has_mark:
                    metadata['highlight'] = True

                element_chunks.append(('paragraph', text, metadata))

        elif tag_name in ['ul', 'ol']:
            # Lists
            list_items = []
            for li in element.find_all('li', recursive=False):
                item_text = li.get_text(strip=True)
                if item_text:
                    list_items.append(item_text)

            if list_items:
                list_type = 'ordered' if tag_name == 'ol' else 'unordered'
                element_chunks.append(('list', list_items, {'type': list_type, 'depth': depth}))

        elif tag_name == 'blockquote':
            # Block quotes - important for educational content
            text = element.get_text(strip=True)
            if text:
                element_chunks.append(('blockquote', text, {'depth': depth}))

        elif tag_name == 'pre':
            # Code blocks - only process <pre> tags, not standalone <code>
            text = element.get_text(strip=False)  # Preserve formatting
            if text:
                element_chunks.append(('code', text, {'depth': depth}))
        elif tag_name == 'code':
            # Inline code - skip if inside <pre> (will be handled by parent)
            if element.parent and element.parent.name == 'pre':
                pass  # Skip, already handled by parent <pre>
            else:
                # Standalone inline code
                text = element.get_text(strip=False)
                if text:
                    element_chunks.append(('code', text, {'depth': depth, 'inline': True}))

        elif tag_name == 'table':
            # Tables - common in educational content
            rows = []
            for tr in element.find_all('tr'):
                cells = []
                for cell in tr.find_all(['td', 'th']):
                    cells.append(cell.get_text(strip=True))
                if cells:
                    rows.append(cells)

            if rows:
                element_chunks.append(('table', rows, {'depth': depth}))

        elif tag_name == 'img':
            # Images
            src = element.get('src', '')
            alt = element.get('alt', '')
            if src:
                img_data = None
                if src.startswith('data:image'):
                    img_data = extract_base64_image(src)
                elif src.startswith(('http://', 'https://')):
                    img_data = download_image(src, allow_remote=allow_remote)
                elif src.startswith('//'):
                    img_data = download_image('https:' + src, allow_remote=allow_remote)

                if img_data:
                    element_chunks.append(('image', img_data, {'alt': alt, 'depth': depth}))

        elif tag_name == 'div':
            # Check for special div classes (callouts, highlights, etc)
            classes = element.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()

            # Common educational content patterns
            is_callout = any(c in classes for c in ['callout', 'alert', 'note', 'tip', 'warning', 'info'])
            is_highlight = any(c in classes for c in ['highlight', 'important', 'key-point'])

            if is_callout:
                # Callout div - treat entire content as special
                text = element.get_text(strip=True)
                if text:
                    metadata = {'depth': depth, 'type': 'callout'}
                    element_chunks.append(('special', text, metadata))
            elif is_highlight:
                # Highlight div - process children separately to preserve structure
                # First add any direct text as special
                direct_text = ''.join(str(c) for c in element.children if isinstance(c, NavigableString)).strip()
                if direct_text:
                    metadata = {'depth': depth, 'highlight': True}
                    element_chunks.append(('special', direct_text, metadata))
                # Then process child elements
                for child in element.children:
                    if not isinstance(child, NavigableString):
                        element_chunks.extend(process_element(child, depth + 1))
            else:
                # Process children for regular divs
                for child in element.children:
                    element_chunks.extend(process_element(child, depth + 1))
            return element_chunks
        else:
            # For other elements, process their children
            for child in element.children:
                element_chunks.extend(process_element(child, depth + 1))
            return element_chunks

        # After processing the element itself, process its children if not already done
        if tag_name not in ['div', 'ul', 'ol', 'table']:
            for child in element.children:
                if isinstance(child, Tag) and child.name not in ['li', 'tr', 'td', 'th']:
                    element_chunks.extend(process_element(child, depth + 1))

        return element_chunks

    # Process the body or the entire soup if no body
    body = soup.body if soup.body else soup
    for element in body.children:
        chunks.extend(process_element(element))

    return chunks