"""Tests for Markdown to rich text (HTML) conversion."""

import pytest

from clipdrop.richtext import (
    html_to_markdown,
    markdown_to_plain,
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


class TestMarkdownToPlain:
    """Test Markdown to clean plain text conversion."""

    def test_heading_becomes_plain_line(self):
        assert markdown_to_plain("# Big Title") == "Big Title"

    def test_emphasis_stripped(self):
        result = markdown_to_plain("**bold** and *italic* and ~~gone~~")
        assert result == "bold and italic and gone"

    def test_inline_code_stripped(self):
        assert markdown_to_plain("run `pytest` now") == "run pytest now"

    def test_link_with_distinct_url_keeps_url(self):
        result = markdown_to_plain("[Docs](https://example.com/docs)")
        assert result == "Docs (https://example.com/docs)"

    def test_bare_autolink_not_duplicated(self):
        result = markdown_to_plain("<https://example.com>")
        assert result == "https://example.com"

    def test_unordered_list_bullets(self):
        result = markdown_to_plain("- one\n- two")
        assert result == "- one\n- two"

    def test_ordered_list_numbering(self):
        result = markdown_to_plain("1. first\n2. second")
        assert result == "1. first\n2. second"

    def test_nested_list_indentation(self):
        result = markdown_to_plain("- outer\n  - inner")
        assert result == "- outer\n  - inner"

    def test_paragraphs_separated_by_blank_line(self):
        result = markdown_to_plain("first para\n\nsecond para")
        assert result == "first para\n\nsecond para"

    def test_code_block_kept_verbatim(self):
        result = markdown_to_plain("```python\ndef f():\n    return 1\n```")
        assert "def f():\n    return 1" in result
        assert "```" not in result

    def test_table_becomes_tab_separated(self):
        result = markdown_to_plain("| A | B |\n|---|---|\n| 1 | 2 |")
        assert "A\tB" in result
        assert "1\t2" in result
        assert "|" not in result

    def test_blockquote_text_kept(self):
        result = markdown_to_plain("> wise words")
        assert result == "wise words"

    def test_horizontal_rule_dropped(self):
        result = markdown_to_plain("above\n\n---\n\nbelow")
        assert result == "above\n\nbelow"

    def test_full_document(self, sample_markdown):
        result = markdown_to_plain(sample_markdown)
        assert "Test Document" in result
        assert "Bold text" in result
        for token in ("**", "# ", "](", "```"):
            assert token not in result

    def test_unicode(self):
        assert markdown_to_plain("**Héllo 世界 🌍**") == "Héllo 世界 🌍"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            markdown_to_plain("   ")


class TestHtmlToMarkdown:
    """Test HTML (rich clipboard flavor) to Markdown conversion."""

    def test_heading(self):
        assert html_to_markdown("<h1>Title</h1>").startswith("# Title")

    def test_emphasis(self):
        result = html_to_markdown("<p><strong>bold</strong> and <em>italic</em></p>")
        assert "**bold**" in result
        assert "_italic_" in result or "*italic*" in result

    def test_link_inline(self):
        result = html_to_markdown('<a href="https://example.com">Example</a>')
        assert "[Example](https://example.com)" in result

    def test_unordered_list_dashes(self):
        result = html_to_markdown("<ul><li>one</li><li>two</li></ul>")
        assert "- one" in result
        assert "- two" in result

    def test_code_block(self):
        result = html_to_markdown("<pre><code>x = 1\ny = 2</code></pre>")
        assert "x = 1" in result

    def test_no_line_wrapping(self):
        long_text = "word " * 60
        result = html_to_markdown(f"<p>{long_text.strip()}</p>")
        assert result.count("\n") == 0

    def test_span_soup_flattened(self):
        result = html_to_markdown(
            '<p><span style="color:red">just</span> <span>text</span></p>'
        )
        assert result == "just text"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            html_to_markdown("")

    def test_whitespace_only_html_raises(self):
        with pytest.raises(ValueError):
            html_to_markdown("<p>   </p>")
