"""Unit tests for file validation, filename sanitization, size checking, and SHA-256."""

from __future__ import annotations

import io
import pytest
from src.file_validation import (
    MAX_FILENAME_LENGTH,
    compute_sha256,
    get_content_type,
    sanitize_filename,
    validate_file_extension,
    validate_file_size,
    validate_filename,
)


@pytest.mark.unit
class TestFilenameValidation:
    """Tests for filename validation and traversal prevention."""

    def test_valid_filename(self) -> None:
        valid, msg = validate_filename("annual_report_2026.pdf")
        assert valid is True
        assert "valid" in msg.lower()

    def test_empty_filename_rejected(self) -> None:
        valid, msg = validate_filename("   ")
        assert valid is False
        assert "empty" in msg.lower()

    def test_path_traversal_double_dot_rejected(self) -> None:
        valid, msg = validate_filename("../secret.env")
        assert valid is False
        assert "traversal" in msg.lower()

    def test_path_traversal_forward_slash_rejected(self) -> None:
        valid, msg = validate_filename("subfolder/file.txt")
        assert valid is False
        assert "traversal" in msg.lower()

    def test_path_traversal_backslash_rejected(self) -> None:
        valid, msg = validate_filename("subfolder\\file.txt")
        assert valid is False
        assert "traversal" in msg.lower()

    def test_illegal_characters_rejected(self) -> None:
        for char in ['*', '?', '"', '<', '>', '|']:
            valid, msg = validate_filename(f"test{char}file.pdf")
            assert valid is False
            assert "invalid" in msg.lower()

    def test_windows_reserved_device_names_rejected(self) -> None:
        for reserved in ["CON.txt", "prn.pdf", "AUX", "NUL.doc", "com1.png", "lpt2.bin"]:
            valid, msg = validate_filename(reserved)
            assert valid is False
            assert "reserved" in msg.lower()

    def test_filename_exceeding_max_length_rejected(self) -> None:
        long_name = "a" * (MAX_FILENAME_LENGTH + 1) + ".txt"
        valid, msg = validate_filename(long_name)
        assert valid is False
        assert "exceeds" in msg.lower()


@pytest.mark.unit
class TestFilenameSanitization:
    """Tests for filename sanitization logic."""

    def test_sanitize_strips_directory_paths(self) -> None:
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("C:\\Windows\\System32\\calc.exe") == "calc.exe"

    def test_sanitize_replaces_illegal_characters(self) -> None:
        assert sanitize_filename('test*<?>|"file.pdf') == "test______file.pdf"

    def test_sanitize_empty_fallback(self) -> None:
        assert sanitize_filename("") == "unnamed_file"
        assert sanitize_filename("...") == "unnamed_file"


@pytest.mark.unit
class TestFileSizeValidation:
    """Tests for file size boundaries."""

    def test_zero_byte_file_rejected(self) -> None:
        valid, msg = validate_file_size(0, max_bytes=50 * 1024 * 1024)
        assert valid is False
        assert "zero-byte" in msg.lower() or "empty" in msg.lower()

    def test_negative_byte_file_rejected(self) -> None:
        valid, _ = validate_file_size(-10, max_bytes=50 * 1024 * 1024)
        assert valid is False

    def test_valid_file_size(self) -> None:
        size = 10 * 1024 * 1024  # 10 MB
        max_size = 50 * 1024 * 1024
        valid, _ = validate_file_size(size, max_size)
        assert valid is True

    def test_file_exceeding_max_size_rejected(self) -> None:
        size = 60 * 1024 * 1024  # 60 MB
        max_size = 50 * 1024 * 1024
        valid, msg = validate_file_size(size, max_size)
        assert valid is False
        assert "exceeds" in msg.lower()


@pytest.mark.unit
class TestExtensionValidation:
    """Tests for extension blacklists and whitelists."""

    def test_blocked_executable_extensions(self) -> None:
        for ext in [".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".msi"]:
            valid, msg = validate_file_extension(f"payload{ext}")
            assert valid is False
            assert "blocked" in msg.lower()

    def test_allowed_standard_extensions(self) -> None:
        for ext in [".pdf", ".png", ".jpg", ".docx", ".csv", ".zip"]:
            valid, _ = validate_file_extension(f"document{ext}")
            assert valid is True


@pytest.mark.unit
class TestContentTypeAndChecksum:
    """Tests for MIME detection and SHA-256 calculation."""

    def test_content_type_detection(self) -> None:
        assert get_content_type("doc.pdf") == "application/pdf"
        assert get_content_type("pic.png") == "image/png"
        assert get_content_type("data.json") == "application/json"
        assert get_content_type("unknown_ext.xyz123") == "application/octet-stream"

    def test_compute_sha256_bytes(self) -> None:
        data = b"Hello, Cloud File Storage System!"
        # SHA-256 of b"Hello, Cloud File Storage System!"
        expected = "35f012c493c603a4d60d2613114e67930ed695ba770bb45bf2b3c6400b7947c7"
        assert compute_sha256(data) == expected

    def test_compute_sha256_stream(self) -> None:
        stream = io.BytesIO(b"Hello, Cloud File Storage System!")
        expected = "35f012c493c603a4d60d2613114e67930ed695ba770bb45bf2b3c6400b7947c7"
        assert compute_sha256(stream) == expected
