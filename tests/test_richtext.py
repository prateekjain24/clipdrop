"""Tests for Markdown to rich text (HTML) conversion."""

import pytest

from clipdrop.richtext import (
    markdown_to_rich_html,
    postprocess_html,
    render_markdown,
)


class TestRenderMarkdown:
    """Test Markdown rendering to HTML fragments."""

    def test_headings(self):
        html = render_markdown("# H1\n\n## H2\n\n### H3")
        assert "<h1>H1</h1>" in html
        assert "<h2>H2</h2>" in html
        assert "<h3>H3</h3>" in html

    def test_emphasis(self):
        html = render_markdown("**bold** and *italic*")
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html

    def test_strikethrough(self):
        html = render_markdown("~~gone~~")
        assert "<s>gone</s>" in html

    def test_links(self):
        html = render_markdown("[Example](https://example.com)")
        assert '<a href="https://example.com">Example</a>' in html

    def test_unordered_list(self):
        html = render_markdown("- one\n- two")
        assert "<ul>" in html
        assert "<li>one</li>" in html

    def test_ordered_list(self):
        html = render_markdown("1. first\n2. second")
        assert "<ol>" in html
        assert "<li>first</li>" in html

    def test_nested_list(self):
        html = render_markdown("- outer\n  - inner")
        assert html.count("<ul>") == 2
        assert "inner" in html

    def test_blockquote(self):
        html = render_markdown("> quoted")
        assert "<blockquote>" in html

    def test_horizontal_rule(self):
        html = render_markdown("---")
        assert "<hr />" in html or "<hr>" in html

    def test_inline_code(self):
        html = render_markdown("use `foo()` here")
        assert "<code>foo()</code>" in html

    def test_fenced_code_with_language(self):
        html = render_markdown("```python\nprint('hi')\n```")
        assert '<pre><code class="language-python">' in html

    def test_gfm_table(self):
        html = render_markdown("| A | B |\n|---|---|\n| 1 | 2 |")
        assert "<table>" in html
        assert "<thead>" in html
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html

    def test_task_list_renders_as_plain_list(self):
        html = render_markdown("- [ ] todo\n- [x] done")
        assert "<input" not in html
        assert "<li>" in html


class TestPostprocessHtml:
    """Test the Confluence-safety HTML scrub."""

    def test_unwraps_spans(self):
        html = postprocess_html('<p><span style="color:red">text</span></p>')
        assert "<span" not in html
        assert "text" in html

    def test_strips_style_attributes(self):
        html = postprocess_html('<p style="margin:0">text</p>')
        assert "style=" not in html

    def test_strips_classes_outside_code(self):
        html = postprocess_html('<p class="fancy">text</p>')
        assert "class=" not in html

    def test_keeps_recognized_code_language(self):
        html = postprocess_html(
            '<pre><code class="language-python">x</code></pre>'
        )
        assert 'class="language-python"' in html

    def test_maps_language_alias(self):
        html = postprocess_html('<pre><code class="language-js">x</code></pre>')
        assert 'class="language-javascript"' in html

    def test_strips_unknown_language(self):
        html = postprocess_html(
            '<pre><code class="language-madeuplang">x</code></pre>'
        )
        assert "class=" not in html

    def test_inline_code_class_stripped(self):
        # language classes only make sense on pre>code
        html = postprocess_html('<p><code class="language-python">x</code></p>')
        assert "class=" not in html


class TestMarkdownToRichHtml:
    """Test the end-to-end conversion pipeline."""

    def test_full_document(self, sample_markdown):
        html = markdown_to_rich_html(sample_markdown)
        assert "<h1>Test Document</h1>" in html
        assert "<strong>Bold text</strong>" in html
        assert '<a href="https://example.com">Links</a>' in html
        assert '<pre><code class="language-python">' in html
        assert "<blockquote>" in html
        assert "<table>" in html

    def test_fragment_purity(self, sample_markdown):
        html = markdown_to_rich_html(sample_markdown)
        assert "<!DOCTYPE" not in html
        assert "<html" not in html
        assert "<body" not in html
        assert "<span" not in html
        assert "style=" not in html

    def test_plain_text_renders_as_paragraph(self):
        html = markdown_to_rich_html("just plain text")
        assert "<p>just plain text</p>" in html

    def test_empty_input_raises(self):
        with pytest.raises(ValueError):
            markdown_to_rich_html("")

    def test_whitespace_input_raises(self):
        with pytest.raises(ValueError):
            markdown_to_rich_html("   \n  ")

    def test_unicode_content(self):
        html = markdown_to_rich_html("# Héllo 世界 🌍")
        assert "Héllo 世界 🌍" in html

    def test_raw_html_span_in_markdown_is_unwrapped(self):
        html = markdown_to_rich_html(
            'text with <span style="color:red">styled</span> html'
        )
        assert "<span" not in html
        assert "styled" in html
