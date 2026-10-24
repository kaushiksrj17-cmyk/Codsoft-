"""Unit tests for authentication, password hashing, and strength validation."""

from __future__ import annotations

import pytest
from src.auth import hash_password, validate_password_strength, verify_password


@pytest.mark.unit
class TestPasswordValidation:
    """Tests for password complexity and boundary rules."""

    def test_short_password_rejected(self) -> None:
        is_valid, msg = validate_password_strength("Short1A")
        assert is_valid is False
        assert "at least 8 characters" in msg

    def test_missing_uppercase_rejected(self) -> None:
        is_valid, msg = validate_password_strength("lowercase123!")
        assert is_valid is False
        assert "uppercase letter" in msg

    def test_missing_lowercase_rejected(self) -> None:
        is_valid, msg = validate_password_strength("UPPERCASE123!")
        assert is_valid is False
        assert "lowercase letter" in msg

    def test_missing_digit_rejected(self) -> None:
        is_valid, msg = validate_password_strength("NoDigitsHere!")
        assert is_valid is False
        assert "digit" in msg

    def test_valid_password_accepted(self) -> None:
        is_valid, msg = validate_password_strength("SecureCloud2026!")
        assert is_valid is True
        assert "meets strength criteria" in msg


@pytest.mark.unit
class TestBcryptHashing:
    """Tests for salted password hashing and verification."""

    def test_hash_and_verify_success(self) -> None:
        plain = "MySecretCloudPass123"
        hashed = hash_password(plain)
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert verify_password(plain, hashed) is True

    def test_verify_incorrect_password_fails(self) -> None:
        hashed = hash_password("CorrectPassword123")
        assert verify_password("WrongPassword456", hashed) is False

    def test_verify_malformed_hash_fails_safely(self) -> None:
        assert verify_password("AnyPassword123", "not_a_valid_hash") is False
