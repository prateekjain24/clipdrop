"""Tests for hardening: SSRF guard, decompression-bomb-safe image open,
and the path-traversal exception wiring."""

import io
from unittest.mock import patch

import pytest
from PIL import Image

from clipdrop import files, html_parser
from clipdrop.exceptions import PathTraversalError


def _addrinfo(ip: str):
    return [(2, 1, 6, "", (ip, 443))]


# --- SSRF guard -----------------------------------------------------------

def test_safe_url_allows_public_ip():
    with patch("clipdrop.html_parser.socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
        assert html_parser._is_safe_public_url("https://example.com/x.png") is True


@pytest.mark.parametrize("ip", ["10.0.0.5", "127.0.0.1", "169.254.169.254", "192.168.1.1", "::1"])
def test_safe_url_blocks_internal_ips(ip):
    with patch("clipdrop.html_parser.socket.getaddrinfo", return_value=_addrinfo(ip)):
        assert html_parser._is_safe_public_url(f"http://host/{ip}") is False


def test_safe_url_blocks_non_http_scheme():
    assert html_parser._is_safe_public_url("file:///etc/passwd") is False
    assert html_parser._is_safe_public_url("ftp://example.com/x") is False


def test_safe_url_blocks_unresolvable():
    import socket as _socket
    with patch("clipdrop.html_parser.socket.getaddrinfo", side_effect=_socket.gaierror):
        assert html_parser._is_safe_public_url("https://nope.invalid/x") is False


# --- decompression-bomb-safe open -----------------------------------------

def test_safe_open_valid_image():
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, format="PNG")
    img = html_parser._safe_open_image(buf.getvalue())
    assert isinstance(img, Image.Image)


def test_safe_open_rejects_garbage():
    assert html_parser._safe_open_image(b"not an image") is None


def test_safe_open_rejects_oversized():
    too_big = b"x" * (html_parser.MAX_IMAGE_BYTES + 1)
    assert html_parser._safe_open_image(too_big) is None


def test_safe_open_rejects_decompression_bomb():
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, format="PNG")
    data = buf.getvalue()
    # Force any image to look like a bomb.
    with patch.object(Image, "open", side_effect=Image.DecompressionBombError("boom")):
        assert html_parser._safe_open_image(data) is None


# --- path-traversal handler wiring ----------------------------------------

def test_files_exposes_path_traversal_error():
    # Regression: main.py catches files.PathTraversalError; it must resolve.
    assert files.PathTraversalError is PathTraversalError


def test_write_text_raises_path_traversal(tmp_path):
    with pytest.raises(PathTraversalError):
        files.write_text(tmp_path / ".." / "escape.txt", "data", force=True)
