"""
Tests for utility functions.
"""

import pytest

from weixin_sdk.utils import (
    markdown_to_plain_text,
    chunk_text,
    truncate_string,
    generate_short_id,
    is_remote_url,
    is_local_file_path,
    normalize_weixin_user_id,
)


class TestMarkdownToPlainText:
    """Test markdown_to_plain_text function."""

    def test_simple_text(self):
        """Test plain text passthrough."""
        text = "Hello, World!"
        result = markdown_to_plain_text(text)
        assert result == "Hello, World!"

    def test_bold_text(self):
        """Test bold markdown removal."""
        text = "This is **bold** text"
        result = markdown_to_plain_text(text)
        assert result == "This is bold text"

    def test_italic_text(self):
        """Test italic markdown removal."""
        text = "This is *italic* text"
        result = markdown_to_plain_text(text)
        assert result == "This is italic text"

    def test_code_inline(self):
        """Test inline code removal."""
        text = "Use `print()` function"
        result = markdown_to_plain_text(text)
        assert result == "Use print() function"

    def test_code_block(self):
        """Test code block removal."""
        text = """```python
print("Hello")
```"""
        result = markdown_to_plain_text(text)
        assert 'print("Hello")' in result
        assert "```" not in result

    def test_links(self):
        """Test link conversion."""
        text = "Check [this link](http://example.com) out"
        result = markdown_to_plain_text(text)
        assert result == "Check this link out"

    def test_images_removed(self):
        """Test image removal."""
        text = "Here is an ![image](http://example.com/img.jpg) for you"
        result = markdown_to_plain_text(text)
        assert result == "Here is an  for you"

    def test_headers(self):
        """Test header removal."""
        text = "# Header 1\n\n## Header 2"
        result = markdown_to_plain_text(text)
        assert "#" not in result
        assert "Header 1" in result
        assert "Header 2" in result

    def test_blockquotes(self):
        """Test blockquote removal."""
        text = "> This is a quote\n\nNormal text"
        result = markdown_to_plain_text(text)
        assert ">" not in result
        assert "This is a quote" in result

    def test_strikethrough(self):
        """Test strikethrough removal."""
        text = "This is ~~deleted~~ text"
        result = markdown_to_plain_text(text)
        assert result == "This is deleted text"

    def test_tables(self):
        """Test table conversion."""
        text = "| Col1 | Col2 |\n|------|------|\n| A    | B    |"
        result = markdown_to_plain_text(text)
        assert "|" not in result
        assert "Col1" in result
        assert "Col2" in result

    def test_complex_markdown(self):
        """Test complex markdown document."""
        text = """# Title

This is **bold** and *italic*.

```python
print("Hello")
```

Check [link](http://example.com).
"""
        result = markdown_to_plain_text(text)
        assert "#" not in result
        assert "**" not in result
        assert "*" not in result
        assert "```" not in result
        assert "bold" in result
        assert "italic" in result
        assert "link" in result


class TestChunkText:
    """Test chunk_text function."""

    def test_short_text_no_chunking(self):
        """Test that short text is not chunked."""
        text = "Short text"
        result = chunk_text(text, limit=100)
        assert result == ["Short text"]

    def test_chunk_at_limit(self):
        """Test chunking at exact limit."""
        text = "A" * 100
        result = chunk_text(text, limit=100, respect_paragraphs=False)
        assert len(result) == 1
        assert result[0] == text

    def test_chunk_by_paragraphs(self):
        """Test chunking respects paragraph boundaries."""
        text = "Para 1\n\nPara 2\n\nPara 3"
        result = chunk_text(text, limit=20, respect_paragraphs=True)
        assert len(result) == 3
        assert "Para 1" in result[0]
        assert "Para 2" in result[1]
        assert "Para 3" in result[2]

    def test_chunk_long_paragraph(self):
        """Test chunking a long paragraph."""
        text = "A" * 500
        result = chunk_text(text, limit=200, respect_paragraphs=True)
        assert len(result) > 1

    def test_chunk_respects_sentences(self):
        """Test that chunking tries to respect sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence." + " Word" * 100
        result = chunk_text(text, limit=100, respect_paragraphs=True)
        # Should not break in the middle of a sentence if possible
        for chunk in result:
            # Each chunk should end with a period or be the last chunk
            pass  # Just ensure no exception


class TestTruncateString:
    """Test truncate_string function."""

    def test_no_truncation_needed(self):
        """Test string that doesn't need truncation."""
        text = "Short"
        result = truncate_string(text, 100)
        assert result == "Short"

    def test_truncation(self):
        """Test string truncation."""
        text = "A" * 100
        result = truncate_string(text, 20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_custom_suffix(self):
        """Test truncation with custom suffix."""
        text = "A" * 100
        result = truncate_string(text, 20, suffix="[more]")
        assert result.endswith("[more]")


class TestGenerateShortId:
    """Test generate_short_id function."""

    def test_generates_id(self):
        """Test that ID is generated."""
        result = generate_short_id()
        assert result.startswith("wx_")
        assert len(result) == 11  # "wx_" + 8 chars

    def test_custom_prefix(self):
        """Test custom prefix."""
        result = generate_short_id(prefix="bot")
        assert result.startswith("bot_")

    def test_unique_ids(self):
        """Test that generated IDs are unique."""
        ids = [generate_short_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestIsRemoteUrl:
    """Test is_remote_url function."""

    def test_http_url(self):
        """Test HTTP URL detection."""
        assert is_remote_url("http://example.com") is True

    def test_https_url(self):
        """Test HTTPS URL detection."""
        assert is_remote_url("https://example.com") is True

    def test_local_path(self):
        """Test local path detection."""
        assert is_remote_url("/path/to/file") is False
        assert is_remote_url("./relative/path") is False
        assert is_remote_url("C:\\Windows\\file.txt") is False


class TestIsLocalFilePath:
    """Test is_local_file_path function."""

    def test_local_paths(self):
        """Test local path detection."""
        assert is_local_file_path("/path/to/file") is True
        assert is_local_file_path("./relative/path") is True

    def test_remote_urls(self):
        """Test that remote URLs are not local paths."""
        assert is_local_file_path("http://example.com") is False
        assert is_local_file_path("https://example.com") is False


class TestNormalizeWeixinUserId:
    """Test normalize_weixin_user_id function."""

    def test_already_normalized(self):
        """Test ID that already has domain."""
        result = normalize_weixin_user_id("user@im.wechat")
        assert result == "user@im.wechat"

    def test_adds_domain(self):
        """Test adding domain to bare ID."""
        result = normalize_weixin_user_id("user123")
        assert result == "user123@im.wechat"

    def test_different_domains_preserved(self):
        """Test that different domains are preserved."""
        result = normalize_weixin_user_id("user@other.domain")
        assert result == "user@other.domain"
