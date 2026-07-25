"""Clipboard format conversions between Markdown, rich text, and plain text.

Renders clipboard Markdown into a clean semantic HTML fragment that paste
targets like Confluence, Google Docs, Gmail, and Slack map cleanly into
their internal document models. Also converts Markdown to clean plain text
(for email/chat) and clipboard HTML back to Markdown (for feeding rich
content into LLMs and notes).
"""

import html2text
from bs4 import BeautifulSoup, NavigableString
from markdown_it import MarkdownIt

# Languages Confluence's code macro recognizes; unknown languages fall back
# to plain text on paste, so unrecognized classes are stripped entirely.
CONFLUENCE_LANGUAGES = frozenset({
    'actionscript3', 'applescript', 'bash', 'c', 'clojure', 'coldfusion',
    'cpp', 'csharp', 'css', 'delphi', 'diff', 'elixir', 'erlang', 'go',
    'graphql', 'groovy', 'haskell', 'html', 'java', 'javascript', 'json',
    'kotlin', 'livescript', 'lua', 'mathematica', 'matlab', 'objectivec',
    'perl', 'php', 'plaintext', 'powershell', 'python', 'qml', 'r', 'ruby',
    'rust', 'sass', 'scala', 'scheme', 'shell', 'sql', 'swift', 'text',
    'typescript', 'vb', 'xml', 'yaml',
})

LANGUAGE_ALIASES = {
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'sh': 'bash',
    'zsh': 'bash',
    'shell-session': 'shell',
    'console': 'shell',
    'yml': 'yaml',
    'py': 'python',
    'python3': 'python',
    'rb': 'ruby',
    'golang': 'go',
    'c++': 'cpp',
    'c#': 'csharp',
    'cs': 'csharp',
    'objective-c': 'objectivec',
    'objc': 'objectivec',
    'md': 'text',
    'markdown': 'text',
    'txt': 'text',
    'plain': 'text',
    'htm': 'html',
    'xhtml': 'html',
    'svg': 'xml',
    'postgres': 'sql',
    'postgresql': 'sql',
    'mysql': 'sql',
    'sqlite': 'sql',
    'ps1': 'powershell',
    'dockerfile': 'bash',
    'makefile': 'bash',
}

_md = MarkdownIt("commonmark").enable(["table", "strikethrough"])


def render_markdown(md_text: str) -> str:
    """
    Render Markdown to an HTML fragment.

    Args:
        md_text: Markdown source text

    Returns:
        HTML fragment string (no document wrapper)
    """
    return _md.render(md_text)


def _normalize_code_language(class_list: list) -> list:
    """Map a code element's classes to a single recognized language class."""
    for cls in class_list:
        if not cls.startswith('language-'):
            continue
        lang = cls[len('language-'):].lower()
        lang = LANGUAGE_ALIASES.get(lang, lang)
        if lang in CONFLUENCE_LANGUAGES:
            return [f'language-{lang}']
    return []


def postprocess_html(html: str) -> str:
    """
    Scrub rendered HTML for safe pasting into rich-text editors.

    Unwraps <span> tags, strips style/class attributes (keeping only
    recognized code-language classes on <pre><code>), so editors like
    Confluence's don't mangle the paste.

    Args:
        html: HTML fragment to clean

    Returns:
        Cleaned HTML fragment
    """
    # html.parser keeps the fragment as-is (lxml would add <html><body>)
    soup = BeautifulSoup(html, 'html.parser')

    for span in soup.find_all('span'):
        span.unwrap()

    for tag in soup.find_all(True):
        tag.attrs.pop('style', None)
        classes = tag.attrs.pop('class', None)
        if classes and tag.name == 'code' and tag.parent and tag.parent.name == 'pre':
            normalized = _normalize_code_language(list(classes))
            if normalized:
                tag.attrs['class'] = normalized

    return str(soup)


def markdown_to_rich_html(md_text: str) -> str:
    """
    Convert Markdown to a Confluence-safe HTML fragment.

    Args:
        md_text: Markdown source text

    Returns:
        Cleaned HTML fragment

    Raises:
        ValueError: If input or rendered output is empty
    """
    if not md_text or not md_text.strip():
        raise ValueError("No text content to convert")

    html = postprocess_html(render_markdown(md_text))
    if not html.strip():
        raise ValueError("Markdown rendered to empty HTML")
    return html


def _inline_text(el) -> str:
    """Flatten an element to plain text, keeping link URLs and <br> breaks."""
    parts = []
    for child in el.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif child.name == 'a':
            text = _inline_text(child).strip()
            href = (child.get('href') or '').strip()
            # Keep the URL only when it adds information over the visible text
            if href and href not in (text, f'mailto:{text}') and href.rstrip('/') != text:
                parts.append(f"{text} ({href})" if text else href)
            else:
                parts.append(text or href)
        elif child.name == 'br':
            parts.append('\n')
        else:
            parts.append(_inline_text(child))
    return ''.join(parts)


def _normalize_inline(text: str) -> str:
    """Collapse whitespace per line while keeping intentional line breaks."""
    return '\n'.join(' '.join(line.split()) for line in text.split('\n')).strip()


def _list_lines(el, depth: int = 0) -> list:
    """Render a <ul>/<ol> to indented plain-text bullet/numbered lines."""
    ordered = el.name == 'ol'
    lines = []
    index = int(el.get('start', 1)) if ordered else 0
    for li in el.find_all('li', recursive=False):
        own_parts = []
        nested = []
        for child in li.children:
            if getattr(child, 'name', None) in ('ul', 'ol'):
                nested.append(child)
            elif isinstance(child, NavigableString):
                own_parts.append(str(child))
            else:
                own_parts.append(_inline_text(child))
        marker = f"{index}." if ordered else "-"
        text = ' '.join(' '.join(own_parts).split())
        lines.append(f"{'  ' * depth}{marker} {text}")
        for sublist in nested:
            lines.extend(_list_lines(sublist, depth + 1))
        index += 1
    return lines


def _table_lines(el) -> list:
    """Render a <table> to tab-separated rows (pastes cleanly into Sheets)."""
    lines = []
    for row in el.find_all('tr'):
        cells = [
            ' '.join(_inline_text(cell).split())
            for cell in row.find_all(['th', 'td'], recursive=False)
        ]
        lines.append('\t'.join(cells))
    return lines


def _plain_blocks(container) -> list:
    """Convert a parsed HTML fragment's children into plain-text blocks."""
    blocks = []
    for el in container.children:
        if isinstance(el, NavigableString):
            text = _normalize_inline(str(el))
            if text:
                blocks.append(text)
            continue
        name = el.name
        if name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'):
            text = _normalize_inline(_inline_text(el))
            if text:
                blocks.append(text)
        elif name in ('ul', 'ol'):
            lines = _list_lines(el)
            if lines:
                blocks.append('\n'.join(lines))
        elif name == 'pre':
            code = el.get_text().rstrip('\n')
            if code:
                blocks.append(code)
        elif name == 'blockquote':
            blocks.extend(_plain_blocks(el))
        elif name == 'table':
            lines = _table_lines(el)
            if lines:
                blocks.append('\n'.join(lines))
        elif name == 'hr':
            continue
        else:
            text = _normalize_inline(el.get_text())
            if text:
                blocks.append(text)
    return blocks


def markdown_to_plain(md_text: str) -> str:
    """
    Convert Markdown to clean plain text for email, chat, and social posts.

    Strips markdown syntax while keeping readable structure: list bullets,
    paragraph breaks, verbatim code blocks, link URLs in parentheses, and
    tables as tab-separated rows.

    Args:
        md_text: Markdown source text

    Returns:
        Plain text string

    Raises:
        ValueError: If input or converted output is empty
    """
    if not md_text or not md_text.strip():
        raise ValueError("No text content to convert")

    soup = BeautifulSoup(render_markdown(md_text), 'html.parser')
    result = '\n\n'.join(_plain_blocks(soup)).strip()
    if not result:
        raise ValueError("Markdown converted to empty text")
    return result


def html_to_markdown(html: str) -> str:
    """
    Convert HTML (e.g. the clipboard's rich text flavor) to GFM Markdown.

    Args:
        html: HTML string to convert

    Returns:
        Markdown string

    Raises:
        ValueError: If input or converted output is empty
    """
    if not html or not html.strip():
        raise ValueError("No HTML content to convert")

    h = html2text.HTML2Text()
    h.body_width = 0  # Don't wrap lines
    h.unicode_snob = True
    h.skip_internal_links = False
    h.inline_links = True
    h.ul_item_mark = '-'  # GFM-style dashes for unordered lists
    result = h.handle(html).strip()
    if not result:
        raise ValueError("HTML converted to empty Markdown")
    return result
