"""PDF creation and manipulation functions for ClipDrop.

This module provides functions to create PDF files from various clipboard content types,
including text, images, and mixed content. It preserves the original order and structure
of the content as it was copied (WYCWYG - What You Copy is What You Get).
"""

import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
from reportlab.platypus import Image as RLImage

from .exceptions import FileWriteError


class ContentChunk:
    """Represents a chunk of content with its type and metadata."""

    def __init__(self, content_type: str, content: Any, metadata: Optional[Dict] = None):
        self.type = content_type  # 'text', 'image', 'table', 'code'
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()


def analyze_clipboard_content(text: Optional[str], image: Optional[Image.Image]) -> List[ContentChunk]:
    """
    Analyze clipboard content and return ordered list of content chunks.

    Preserves the original order and relationship of content as it exists
    in the clipboard. This is the foundation of the WYCWYG principle.

    Args:
        text: Text content from clipboard
        image: Image content from clipboard

    Returns:
        List of ContentChunk objects in their original order
    """
    chunks = []

    # Check for HTML content (richest format)
    if text and text.strip().startswith('<') and '<html' in text.lower():
        # Parse HTML to extract structure
        chunks.extend(_parse_html_content(text))

    # Check for RTF content
    elif text and text.strip().startswith('{\\rtf'):
        # Parse RTF to extract structure
        chunks.extend(_parse_rtf_content(text))

    # Handle separate text and image
    else:
        if text:
            # Detect if it's code
            if _is_code(text):
                chunks.append(ContentChunk('code', text, {'language': _detect_language(text)}))
            else:
                chunks.append(ContentChunk('text', text))

        if image:
            chunks.append(ContentChunk('image', image, {
                'width': image.width,
                'height': image.height,
                'mode': image.mode
            }))

    return chunks


def _parse_html_content(html: str) -> List[ContentChunk]:
    """Parse HTML content and extract ordered chunks."""
    # Simplified HTML parsing - in production would use BeautifulSoup
    chunks = []

    # For now, just treat as formatted text
    # TODO: Implement proper HTML parsing with embedded images
    import re
    text = re.sub('<[^<]+?>', '', html)  # Strip HTML tags
    if text.strip():
        chunks.append(ContentChunk('text', text.strip(), {'format': 'html'}))

    return chunks


def _parse_rtf_content(rtf: str) -> List[ContentChunk]:
    """Parse RTF content and extract ordered chunks."""
    # Simplified RTF parsing
    chunks = []

    # For now, just extract plain text
    # TODO: Implement proper RTF parsing with formatting
    import re
    text = re.sub(r'\\[a-z]+\d*\s?', '', rtf)  # Remove RTF commands
    text = text.replace('{', '').replace('}', '')
    if text.strip():
        chunks.append(ContentChunk('text', text.strip(), {'format': 'rtf'}))

    return chunks


def _is_code(text: str) -> bool:
    """Detect if text appears to be code."""
    code_indicators = [
        'def ', 'class ', 'import ', 'from ',  # Python
        'function ', 'const ', 'let ', 'var ',  # JavaScript
        '#include', 'int main', 'void ',  # C/C++
        'public class', 'private ', 'package ',  # Java
    ]

    # Check for common code patterns
    lines = text.split('\n')
    if len(lines) > 1:
        # Check for indentation patterns
        indented = sum(1 for line in lines if line.startswith(('    ', '\t')))
        if indented > len(lines) * 0.3:  # 30% of lines are indented
            return True

    # Check for code keywords
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in code_indicators)


def _detect_language(text: str) -> str:
    """Detect programming language from code text."""
    # Simple heuristic-based detection
    if 'def ' in text or 'import ' in text or 'print(' in text:
        return 'python'
    elif 'function' in text or 'const ' in text or '===' in text:
        return 'javascript'
    elif '#include' in text or 'int main' in text:
        return 'cpp'
    elif 'public class' in text or 'package ' in text:
        return 'java'
    else:
        return 'plain'


def create_pdf_from_text(
    text: str,
    output_path: Path,
    title: Optional[str] = None,
    preserve_formatting: bool = True
) -> None:
    """
    Create a PDF file from text content.

    Args:
        text: Text content to convert to PDF
        output_path: Path where PDF will be saved
        title: Optional title for the PDF
        preserve_formatting: Whether to preserve text formatting
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    story = []
    styles = getSampleStyleSheet()

    # Add title if provided
    if title:
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2E3440'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

    # Add metadata
    metadata_style = ParagraphStyle(
        'Metadata',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        spaceAfter=20,
    )
    story.append(Paragraph(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", metadata_style))
    story.append(Spacer(1, 12))

    # Process text content
    if preserve_formatting:
        # Preserve line breaks and indentation
        lines = text.split('\n')
        for line in lines:
            if line.strip():
                # Escape special characters for ReportLab
                escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(escaped_line, styles['Code']))
            else:
                story.append(Spacer(1, 6))
    else:
        # Treat as paragraph text
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                escaped_para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(escaped_para, styles['Normal']))
                story.append(Spacer(1, 12))

    # Build PDF
    doc.build(story)


def create_pdf_from_image(
    image: Image.Image,
    output_path: Path,
    title: Optional[str] = None,
    fit_to_page: bool = True
) -> None:
    """
    Create a PDF file from an image.

    Args:
        image: PIL Image object
        output_path: Path where PDF will be saved
        title: Optional title for the PDF
        fit_to_page: Whether to fit image to page size
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    story = []
    styles = getSampleStyleSheet()

    # Add title if provided
    if title:
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2E3440'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph(title, title_style))

    # Add image metadata
    metadata_style = ParagraphStyle(
        'Metadata',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        spaceAfter=10,
    )
    metadata = f"Dimensions: {image.width}x{image.height} | Mode: {image.mode} | Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(metadata, metadata_style))
    story.append(Spacer(1, 12))

    # Calculate image size to fit page
    page_width = letter[0] - 72  # 72 points margin
    page_height = letter[1] - 144  # Top and bottom margins plus title space

    if fit_to_page:
        # Calculate scaling to fit page
        img_width = image.width
        img_height = image.height

        width_ratio = page_width / img_width
        height_ratio = page_height / img_height

        scale = min(width_ratio, height_ratio, 1.0)  # Don't upscale

        display_width = img_width * scale
        display_height = img_height * scale
    else:
        display_width = min(image.width, page_width)
        display_height = image.height * (display_width / image.width)

    # Convert image for PDF
    img_buffer = io.BytesIO()

    # Convert RGBA to RGB if necessary (PDF doesn't support transparency well)
    if image.mode == 'RGBA':
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[3] if len(image.split()) > 3 else None)
        rgb_image.save(img_buffer, format='PNG')
    else:
        image.save(img_buffer, format='PNG')

    img_buffer.seek(0)

    # Add image to story
    rl_image = RLImage(img_buffer, width=display_width, height=display_height)
    story.append(rl_image)

    # Build PDF
    doc.build(story)


def create_pdf_from_mixed(
    chunks: List[ContentChunk],
    output_path: Path,
    title: Optional[str] = None,
    preserve_order: bool = True
) -> None:
    """
    Create a PDF from mixed content chunks, preserving original order.

    This is the core function that implements the WYCWYG principle,
    maintaining the exact sequence and relationship of content as it
    was copied to the clipboard.

    Args:
        chunks: List of ContentChunk objects in order
        output_path: Path where PDF will be saved
        title: Optional title for the PDF
        preserve_order: Whether to preserve the original order (default: True)
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    story = []
    styles = getSampleStyleSheet()

    # Add title if provided
    if title:
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2E3440'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

    # Add creation metadata
    metadata_style = ParagraphStyle(
        'Metadata',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        spaceAfter=20,
    )
    content_types = [chunk.type for chunk in chunks]
    metadata = f"Content: {', '.join(content_types)} | Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(metadata, metadata_style))
    story.append(Spacer(1, 20))

    # Process each chunk in order
    for i, chunk in enumerate(chunks):
        if chunk.type == 'text':
            # Process Markdown-formatted text
            text = chunk.content
            lines = text.split('\n')

            for line in lines:
                if not line.strip():
                    # Empty line - add spacing
                    story.append(Spacer(1, 6))
                    continue

                # Escape HTML special characters first
                escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                # Check for Markdown headers
                if line.startswith('# '):
                    # H1
                    style = ParagraphStyle(
                        'H1', parent=styles['Heading1'],
                        fontSize=20, spaceAfter=12, spaceBefore=12,
                        textColor=colors.HexColor('#000000'), bold=True
                    )
                    story.append(Paragraph(escaped[2:], style))
                elif line.startswith('## '):
                    # H2
                    style = ParagraphStyle(
                        'H2', parent=styles['Heading2'],
                        fontSize=16, spaceAfter=10, spaceBefore=10
                    )
                    story.append(Paragraph(escaped[3:], style))
                elif line.startswith('### '):
                    # H3
                    style = ParagraphStyle(
                        'H3', parent=styles['Heading3'],
                        fontSize=14, spaceAfter=8, spaceBefore=8
                    )
                    story.append(Paragraph(escaped[4:], style))
                elif line.startswith('- ') or line.startswith('* '):
                    # Bullet list
                    bullet_style = ParagraphStyle(
                        'Bullet', parent=styles['Normal'],
                        leftIndent=20, bulletIndent=10
                    )
                    story.append(Paragraph('• ' + escaped[2:], bullet_style))
                elif re.match(r'^\d+\. ', line):
                    # Numbered list
                    list_style = ParagraphStyle(
                        'NumberedList', parent=styles['Normal'],
                        leftIndent=20
                    )
                    story.append(Paragraph(escaped, list_style))
                else:
                    # Regular paragraph - process inline formatting
                    formatted = escaped

                    # Convert **bold** to <b>bold</b>
                    formatted = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', formatted)
                    # Convert *italic* or _italic_ to <i>italic</i>
                    formatted = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', formatted)
                    formatted = re.sub(r'_([^_]+)_', r'<i>\1</i>', formatted)
                    # Convert `code` to monospace
                    formatted = re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', formatted)
                    # Handle markdown links [text](url) - just keep the text for now
                    formatted = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', formatted)

                    if formatted.strip():
                        story.append(Paragraph(formatted, styles['Normal']))
                        story.append(Spacer(1, 3))

        elif chunk.type == 'code':
            # Add code with syntax highlighting (basic)
            code_style = ParagraphStyle(
                'Code',
                parent=styles['Code'],
                fontSize=10,
                leftIndent=20,
                backgroundColor=colors.HexColor('#F5F5F5'),
            )

            language = chunk.metadata.get('language', 'plain')
            story.append(Paragraph(f"Code ({language}):", styles['Normal']))
            story.append(Spacer(1, 6))

            lines = chunk.content.split('\n')
            for line in lines:
                escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(escaped_line or ' ', code_style))

        elif chunk.type == 'image':
            # Add image
            image = chunk.content

            # Calculate size
            page_width = letter[0] - 144
            img_width = image.width
            img_height = image.height

            # Scale to fit width if needed
            if img_width > page_width:
                scale = page_width / img_width
                display_width = page_width
                display_height = img_height * scale
            else:
                display_width = img_width
                display_height = img_height

            # Convert image
            img_buffer = io.BytesIO()
            if image.mode == 'RGBA':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3] if len(image.split()) > 3 else None)
                rgb_image.save(img_buffer, format='PNG')
            else:
                image.save(img_buffer, format='PNG')

            img_buffer.seek(0)

            # Add to story
            rl_image = RLImage(img_buffer, width=display_width, height=display_height)
            story.append(rl_image)

            # Add image caption with dimensions
            caption_style = ParagraphStyle(
                'Caption',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            )
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"Image: {img_width}x{img_height}px", caption_style))

        # Add spacing between chunks
        if i < len(chunks) - 1:
            story.append(Spacer(1, 20))

    # Build PDF
    try:
        doc.build(story)
    except Exception as e:
        raise FileWriteError(f"Failed to create PDF: {str(e)}")


def create_pdf(
    output_path: Path,
    text: Optional[str] = None,
    image: Optional[Image.Image] = None,
    force: bool = False
) -> Tuple[bool, str]:
    """
    Main entry point for PDF creation from clipboard content.

    Automatically detects content type and creates appropriate PDF,
    preserving the original structure and order of mixed content.

    Args:
        output_path: Path where PDF will be saved
        text: Text content from clipboard
        image: Image content from clipboard
        force: Whether to overwrite existing file

    Returns:
        Tuple of (success, message)
    """
    # Check if file exists
    if output_path.exists() and not force:
        return False, f"File already exists: {output_path}"

    # Analyze content
    chunks = analyze_clipboard_content(text, image)

    if not chunks:
        return False, "No content to save as PDF"

    # Extract title from filename
    title = output_path.stem.replace('_', ' ').replace('-', ' ').title()

    try:
        # Determine PDF type and create
        if len(chunks) == 1:
            chunk = chunks[0]
            if chunk.type in ('text', 'code'):
                create_pdf_from_text(
                    chunk.content,
                    output_path,
                    title=title,
                    preserve_formatting=(chunk.type == 'code')
                )
            elif chunk.type == 'image':
                create_pdf_from_image(
                    chunk.content,
                    output_path,
                    title=title
                )
        else:
            # Mixed content - use the mixed handler
            create_pdf_from_mixed(
                chunks,
                output_path,
                title=title,
                preserve_order=True  # Always preserve order
            )

        # Calculate file size
        file_size = output_path.stat().st_size

        # Create success message
        content_summary = []
        text_chunks = [c for c in chunks if c.type in ('text', 'code')]
        image_chunks = [c for c in chunks if c.type == 'image']

        if text_chunks:
            total_chars = sum(len(c.content) for c in text_chunks)
            content_summary.append(f"{total_chars} characters")
        if image_chunks:
            content_summary.append(f"{len(image_chunks)} image(s)")

        size_str = _format_file_size(file_size)
        content_str = ' + '.join(content_summary) if content_summary else 'content'

        return True, f"Created PDF ({content_str}, {size_str}) at {output_path}"

    except Exception as e:
        return False, f"Failed to create PDF: {str(e)}"


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def has_mixed_content(text: Optional[str], image: Optional[Image.Image]) -> bool:
    """
    Check if clipboard has mixed content (both text and image).

    Args:
        text: Text content from clipboard
        image: Image content from clipboard

    Returns:
        True if both text and image content are present
    """
    return bool(text and text.strip()) and image is not None


def should_suggest_pdf(text: Optional[str], image: Optional[Image.Image]) -> bool:
    """
    Determine if PDF should be suggested as the default format.

    Args:
        text: Text content from clipboard
        image: Image content from clipboard

    Returns:
        True if PDF should be suggested (mixed content scenario)
    """
    return has_mixed_content(text, image)


def create_pdf_from_html_content(
    html_text: str,
    html_images: List[Image.Image],
    output_path: Path,
    title: Optional[str] = None
) -> None:
    """
    Create PDF from HTML clipboard content with embedded images.

    Args:
        html_text: Extracted text from HTML
        html_images: List of PIL Image objects from HTML
        output_path: Path where PDF will be saved
        title: Optional title for the PDF (not used by default)
    """
    # Convert to content chunks for mixed content handler
    chunks = []

    # Add ALL text as one chunk to preserve original structure
    if html_text and html_text.strip():
        chunks.append(ContentChunk('text', html_text))

    # Add all images after text
    for img in html_images:
        if img:
            chunks.append(ContentChunk('image', img, {
                'width': img.width,
                'height': img.height,
                'mode': img.mode
            }))

    # Create PDF WITHOUT title (unless explicitly provided)
    if chunks:
        create_pdf_from_mixed(chunks, output_path, title=None, preserve_order=True)


def create_pdf_from_html_ordered_content(
    ordered_chunks: List[Tuple[str, Any]],
    output_path: Path,
    title: Optional[str] = None
) -> None:
    """
    Create PDF from ordered HTML content chunks.

    Args:
        ordered_chunks: List of (type, content) tuples in document order
        output_path: Path where PDF will be saved
        title: Optional title for the PDF (not used by default)
    """
    # Convert to ContentChunk objects
    chunks = []

    for chunk_type, content in ordered_chunks:
        if chunk_type == 'text':
            chunks.append(ContentChunk('text', content))
        elif chunk_type == 'image' and content:
            chunks.append(ContentChunk('image', content, {
                'width': content.width,
                'height': content.height,
                'mode': content.mode
            }))

    # Create PDF preserving the order
    if chunks:
        create_pdf_from_mixed(chunks, output_path, title=None, preserve_order=True)


def create_pdf_from_enhanced_html(
    enhanced_chunks: List[Tuple[str, Any, Dict]],
    output_path: Path,
    title: Optional[str] = None,
    educational_mode: bool = True
) -> None:
    """
    Create PDF from enhanced HTML content with better formatting.
    Optimized for educational and cognitive support content.

    Args:
        enhanced_chunks: List of (type, content, metadata) tuples
        output_path: Path where PDF will be saved
        title: Optional title for the PDF
        educational_mode: Enable educational content optimizations
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    story = []
    styles = getSampleStyleSheet()

    # Create custom styles for educational content
    custom_styles = {
        'H1': ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            spaceBefore=10,
            keepWithNext=True,
        ),
        'H2': ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=20,
            textColor=colors.HexColor('#2a2a2a'),
            spaceAfter=16,
            spaceBefore=8,
            keepWithNext=True,
        ),
        'H3': ParagraphStyle(
            'CustomH3',
            parent=styles['Heading3'],
            fontSize=16,
            textColor=colors.HexColor('#3a3a3a'),
            spaceAfter=12,
            spaceBefore=6,
            keepWithNext=True,
        ),
        'H4': ParagraphStyle(
            'CustomH4',
            parent=styles['Heading4'],
            fontSize=14,
            textColor=colors.HexColor('#4a4a4a'),
            spaceAfter=10,
            spaceBefore=4,
            keepWithNext=True,
        ),
        'Body': ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY if educational_mode else TA_LEFT,
            spaceAfter=8,
        ),
        'Callout': ParagraphStyle(
            'Callout',
            parent=styles['Normal'],
            fontSize=11,
            leftIndent=20,
            rightIndent=20,
            backgroundColor=colors.HexColor('#fff3cd'),
            borderColor=colors.HexColor('#ffc107'),
            borderWidth=1,
            borderPadding=10,
            spaceAfter=12,
            spaceBefore=12,
        ),
        'Blockquote': ParagraphStyle(
            'Blockquote',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=30,
            rightIndent=30,
            textColor=colors.HexColor('#555555'),
            fontName='Helvetica-Oblique',
            spaceAfter=10,
            spaceBefore=10,
        ),
        'CodeBlock': ParagraphStyle(
            'CodeBlock',
            parent=styles['Code'],
            fontSize=9,
            backgroundColor=colors.HexColor('#f5f5f5'),
            borderColor=colors.HexColor('#dddddd'),
            borderWidth=1,
            borderPadding=8,
            leftIndent=10,
            rightIndent=10,
            spaceAfter=10,
            spaceBefore=10,
        ),
        'ListItem': ParagraphStyle(
            'ListItem',
            parent=styles['Normal'],
            fontSize=11,
            leftIndent=30,
            bulletIndent=20,
            spaceAfter=4,
        ),
    }

    # Add title if provided
    if title:
        title_style = ParagraphStyle(
            'DocumentTitle',
            parent=styles['Title'],
            fontSize=28,
            textColor=colors.HexColor('#000000'),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 20))

    # Process enhanced chunks
    for i, (chunk_type, content, metadata) in enumerate(enhanced_chunks):
        depth = metadata.get('depth', 0)

        if chunk_type == 'heading':
            level = metadata.get('level', 1)
            style_name = f'H{min(level, 4)}'  # Cap at H4
            style = custom_styles[style_name]

            # Escape HTML characters
            text = str(content).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(text, style))

        elif chunk_type == 'paragraph':
            # Handle emphasized or highlighted paragraphs
            style = custom_styles['Body']
            text = str(content).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            if metadata.get('highlight'):
                text = f'<b><font color="#ff6b6b">{text}</font></b>'
            elif metadata.get('emphasis') == 'strong':
                text = f'<b>{text}</b>'
            elif metadata.get('emphasis') == 'italic':
                text = f'<i>{text}</i>'

            story.append(Paragraph(text, style))

        elif chunk_type == 'list':
            list_type = metadata.get('type', 'unordered')
            items = content if isinstance(content, list) else [content]

            for idx, item in enumerate(items):
                if list_type == 'ordered':
                    bullet_text = f"{idx + 1}. "
                else:
                    bullet_text = "• "

                text = str(item).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                full_text = bullet_text + text
                story.append(Paragraph(full_text, custom_styles['ListItem']))

            story.append(Spacer(1, 6))

        elif chunk_type == 'blockquote':
            text = str(content).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(f'"{text}"', custom_styles['Blockquote']))

        elif chunk_type == 'code':
            # Preserve code formatting
            lines = str(content).split('\n')
            for line in lines:
                escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') or ' '
                story.append(Paragraph(escaped_line, custom_styles['CodeBlock']))

        elif chunk_type == 'special':
            # Callouts and special highlighted content
            text = str(content).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            if metadata.get('type') == 'callout':
                story.append(Paragraph(f'<b>Note:</b> {text}', custom_styles['Callout']))
            elif metadata.get('highlight'):
                story.append(Paragraph(f'<font color="#ff6b6b"><b>{text}</b></font>', custom_styles['Body']))
            else:
                story.append(Paragraph(text, custom_styles['Body']))

        elif chunk_type == 'table':
            # Create table with proper formatting
            rows = content if isinstance(content, list) else [[content]]

            if rows:
                # Create table
                table = Table(rows)

                # Apply table style
                table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),  # Header row
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('PADDING', (0, 0), (-1, -1), 6),
                ])

                # Alternate row coloring for better readability
                for i in range(1, len(rows)):
                    if i % 2 == 0:
                        table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9f9f9'))

                table.setStyle(table_style)
                story.append(table)
                story.append(Spacer(1, 12))

        elif chunk_type == 'image':
            # Handle images
            if content:
                try:
                    # Calculate image size
                    page_width = letter[0] - 144  # Account for margins
                    max_height = letter[1] * 0.5  # Max 50% of page height

                    if hasattr(content, 'width') and hasattr(content, 'height'):
                        img_width = content.width
                        img_height = content.height

                        # Scale to fit
                        width_scale = page_width / img_width if img_width > page_width else 1
                        height_scale = max_height / img_height if img_height > max_height else 1
                        scale = min(width_scale, height_scale, 1)

                        display_width = img_width * scale
                        display_height = img_height * scale

                        # Convert image for PDF
                        img_buffer = io.BytesIO()
                        if content.mode == 'RGBA':
                            rgb_image = Image.new('RGB', content.size, (255, 255, 255))
                            rgb_image.paste(content, mask=content.split()[3] if len(content.split()) > 3 else None)
                            rgb_image.save(img_buffer, format='PNG')
                        else:
                            content.save(img_buffer, format='PNG')

                        img_buffer.seek(0)

                        # Add image to story
                        rl_image = RLImage(img_buffer, width=display_width, height=display_height)
                        story.append(rl_image)

                        # Add caption if available
                        alt_text = metadata.get('alt', '')
                        if alt_text:
                            caption_style = ParagraphStyle(
                                'Caption',
                                parent=styles['Normal'],
                                fontSize=9,
                                textColor=colors.grey,
                                alignment=TA_CENTER,
                                spaceAfter=10,
                            )
                            story.append(Paragraph(f'<i>{alt_text}</i>', caption_style))
                        else:
                            story.append(Spacer(1, 10))
                except Exception:
                    # Skip problematic images
                    pass

        elif chunk_type == 'text':
            # Plain text
            text = str(content).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            if text.strip():
                story.append(Paragraph(text, custom_styles['Body']))

        # Add appropriate spacing
        if i < len(enhanced_chunks) - 1:
            next_type = enhanced_chunks[i + 1][0] if i + 1 < len(enhanced_chunks) else None
            if chunk_type in ['heading', 'table'] or next_type == 'heading':
                story.append(Spacer(1, 12))
            else:
                story.append(Spacer(1, 6))

    # Build the PDF
    try:
        doc.build(story)
    except Exception as e:
        raise FileWriteError(f"Failed to create enhanced PDF: {str(e)}")