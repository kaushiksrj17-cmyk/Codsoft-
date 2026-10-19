"""Unit tests for share token generation, expiration validation, and access checking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
from src.sharing import (
    calculate_expiration_datetime,
    generate_share_token,
    is_share_expired,
    validate_share_access,
)


@pytest.mark.unit
class TestShareTokenGeneration:
    """Tests for cryptographic token creation."""

    def test_token_length_and_uniqueness(self) -> None:
        t1 = generate_share_token(32)
        t2 = generate_share_token(32)

        assert isinstance(t1, str)
        assert len(t1) >= 40  # Base64-encoded 32 bytes produces ~43 chars
        assert t1 != t2

    def test_custom_token_length(self) -> None:
        t = generate_share_token(16)
        assert len(t) >= 20


@pytest.mark.unit
class TestShareExpiration:
    """Tests for expiration calculation and timestamp evaluation."""

    def test_calculate_expiration_datetime(self) -> None:
        expiry_iso = calculate_expiration_datetime(hours=24)
        exp_dt = datetime.fromisoformat(expiry_iso)
        now = datetime.now(timezone.utc)

        # Should expire approximately 24 hours in the future
        diff = exp_dt - now
        assert 23.9 <= diff.total_seconds() / 3600 <= 24.1

    def test_negative_expiration_duration_raises_error(self) -> None:
        with pytest.raises(ValueError):
            calculate_expiration_datetime(hours=0)
        with pytest.raises(ValueError):
            calculate_expiration_datetime(hours=-5)

    def test_is_share_expired_future_timestamp(self) -> None:
        future_dt = datetime.now(timezone.utc) + timedelta(hours=2)
        assert is_share_expired(future_dt.isoformat()) is False

    def test_is_share_expired_past_timestamp(self) -> None:
        past_dt = datetime.now(timezone.utc) - timedelta(hours=2)
        assert is_share_expired(past_dt.isoformat()) is True

    def test_is_share_expired_none_is_permanent(self) -> None:
        assert is_share_expired(None) is False

    def test_is_share_expired_malformed_string_fails_closed(self) -> None:
        assert is_share_expired("not-a-valid-timestamp") is True


@pytest.mark.unit
class TestValidateShareAccess:
    """Tests for full share record access validation."""

    def test_valid_active_share(self) -> None:
        future_dt = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        share = {
            "share_token": "valid_token",
            "is_revoked": 0,
            "expires_at": future_dt,
        }
        valid, msg = validate_share_access(share)
        assert valid is True
        assert "valid" in msg.lower()

    def test_revoked_share_rejected(self) -> None:
        future_dt = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        share = {
            "share_token": "revoked_token",
            "is_revoked": 1,
            "expires_at": future_dt,
        }
        valid, msg = validate_share_access(share)
        assert valid is False
        assert "revoked" in msg.lower()

    def test_expired_share_rejected(self) -> None:
        past_dt = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        share = {
            "share_token": "expired_token",
            "is_revoked": 0,
            "expires_at": past_dt,
        }
        valid, msg = validate_share_access(share)
        assert valid is False
        assert "expired" in msg.lower()

    def test_empty_share_rejected(self) -> None:
        valid, msg = validate_share_access({})
        assert valid is False
        assert "not exist" in msg.lower()
