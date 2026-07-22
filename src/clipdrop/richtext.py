"""Markdown to rich text (HTML) conversion for clipboard pasting.

Renders clipboard Markdown into a clean semantic HTML fragment that paste
targets like Confluence, Google Docs, Gmail, and Slack map cleanly into
their internal document models.
"""

from bs4 import BeautifulSoup
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
