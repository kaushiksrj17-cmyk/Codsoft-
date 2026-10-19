"""Authentication, password hashing, and user credential validation.

Utilizes bcrypt for adaptive, salted one-way password hashing.
"""

from __future__ import annotations

import re
from typing import Tuple

try:
    import bcrypt

    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password complexity.

    Requires at least 8 characters, an uppercase letter, a lowercase letter,
    and a digit.
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit (0-9)."

    return True, "Password meets strength criteria."


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    if not _BCRYPT_AVAILABLE:
        raise RuntimeError(
            "bcrypt package is not installed. Please install requirements via setup script."
        )

    # Encode to bytes and generate salt
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an existing bcrypt hash."""
    if not _BCRYPT_AVAILABLE:
        raise RuntimeError(
            "bcrypt package is not installed. Please install requirements via setup script."
        )

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False
