"""File validation and sanitization utilities.

Enforces strict input validation to guard against path traversal attacks,
dangerous executable files, excessive payload sizes, and malformed filenames.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import re
from pathlib import Path
from typing import BinaryIO, Optional, Set, Tuple

# Dangerous extensions blocked by default to prevent malicious payload uploads
BLOCKED_EXTENSIONS: Set[str] = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".vbs",
    ".msi",
    ".ps1",
    ".com",
    ".scr",
    ".pif",
    ".jar",
    ".wsf",
    ".reg",
}

# Windows reserved device names that cannot be used as filenames
WINDOWS_RESERVED_NAMES: Set[str] = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}

# Maximum filename length
MAX_FILENAME_LENGTH = 255


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by stripping directory separators, control characters, and unsafe symbols.

    Returns a clean, base-only filename.
    """
    if not filename:
        return "unnamed_file"

    # Extract basename only to prevent directory traversal
    clean_name = os.path.basename(filename.strip().replace("\\", "/"))

    # Remove non-printable or null characters
    clean_name = re.sub(r"[\x00-\x1f\x7f]", "", clean_name)

    # Replace forbidden path characters with underscores
    clean_name = re.sub(r'[/\\:*?"<>|]', "_", clean_name)

    # Avoid leading dots to prevent hidden file exploits
    clean_name = clean_name.lstrip(".")

    # Fallback if empty after stripping
    if not clean_name:
        clean_name = "unnamed_file"

    # Enforce maximum length while preserving extension
    if len(clean_name) > MAX_FILENAME_LENGTH:
        name_part, ext = os.path.splitext(clean_name)
        keep_len = MAX_FILENAME_LENGTH - len(ext)
        clean_name = name_part[:keep_len] + ext

    return clean_name


def validate_filename(filename: str) -> Tuple[bool, str]:
    """Validate filename for path traversal, illegal characters, length, and reserved names."""
    if not filename or not filename.strip():
        return False, "Filename cannot be empty."

    raw = filename.strip()

    # Detect path traversal sequences
    if ".." in raw or "/" in raw or "\\" in raw:
        return False, "Path traversal sequences and directory separators are not allowed."

    # Check length
    if len(raw) > MAX_FILENAME_LENGTH:
        return False, f"Filename exceeds maximum length of {MAX_FILENAME_LENGTH} characters."

    # Check for reserved Windows filenames
    base_stem = Path(raw).stem.upper()
    if base_stem in WINDOWS_RESERVED_NAMES:
        return False, f"'{base_stem}' is a reserved system filename."

    # Check for illegal filesystem characters
    if re.search(r'[*?"<>|]', raw):
        return False, "Filename contains invalid characters (*, ?, \", <, >, |)."

    return True, "Filename is valid."


def validate_file_size(size_bytes: int, max_bytes: int) -> Tuple[bool, str]:
    """Validate that file size is positive and within configured maximum boundary."""
    if size_bytes <= 0:
        return False, "File is empty (0 bytes). Zero-byte uploads are not permitted."

    if size_bytes > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        actual_mb = size_bytes / (1024 * 1024)
        return (
            False,
            f"File size ({actual_mb:.2f} MB) exceeds maximum allowed size ({max_mb:.1f} MB).",
        )

    return True, "File size is within allowed limits."


def validate_file_extension(
    filename: str,
    allowed_extensions: Optional[Set[str]] = None,
    blocked_extensions: Optional[Set[str]] = None,
) -> Tuple[bool, str]:
    """Validate file extension against blocked and allowed lists."""
    ext = os.path.splitext(filename.lower())[1]

    blocked = blocked_extensions if blocked_extensions is not None else BLOCKED_EXTENSIONS
    if ext in blocked:
        return False, f"File extension '{ext}' is blocked for security reasons."

    if allowed_extensions is not None and len(allowed_extensions) > 0:
        if ext not in allowed_extensions:
            return False, f"File extension '{ext}' is not in the allowed list."

    return True, "File extension is permitted."


def get_content_type(filename: str) -> str:
    """Determine MIME content type from filename with safe fallback."""
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def compute_sha256(data: bytes | BinaryIO) -> str:
    """Compute SHA-256 checksum of raw bytes or a readable binary stream."""
    hasher = hashlib.sha256()
    if isinstance(data, bytes):
        hasher.update(data)
    else:
        # Save position if seekable
        seekable = hasattr(data, "seek") and hasattr(data, "tell")
        current_pos = data.tell() if seekable else 0
        while chunk := data.read(64 * 1024):
            hasher.update(chunk)
        if seekable:
            data.seek(current_pos)
    return hasher.hexdigest()
