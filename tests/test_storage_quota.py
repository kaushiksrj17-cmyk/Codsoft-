"""Unit tests for storage quota calculations, formatting, and capacity checks."""

from __future__ import annotations

import pytest
from src.storage_quota import (
    bytes_to_mb,
    check_quota_availability,
    calculate_usage_percentage,
    format_bytes,
    get_remaining_quota_bytes,
    mb_to_bytes,
)


@pytest.mark.unit
class TestStorageUnitConversions:
    """Tests for byte-to-MB and byte-formatting conversions."""

    def test_bytes_to_mb(self) -> None:
        assert bytes_to_mb(1024 * 1024) == 1.0
        assert bytes_to_mb(52428800) == 50.0

    def test_mb_to_bytes(self) -> None:
        assert mb_to_bytes(1.0) == 1024 * 1024
        assert mb_to_bytes(500) == 524288000

    def test_format_bytes(self) -> None:
        assert format_bytes(500) == "500 B"
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(1048576) == "1.00 MB"
        assert format_bytes(1073741824) == "1.00 GB"
        assert format_bytes(-1) == "0 B"


@pytest.mark.unit
class TestUsagePercentageAndRemaining:
    """Tests for usage percentage calculations and capacity bounds."""

    def test_calculate_usage_percentage_normal(self) -> None:
        quota = 1000
        used = 250
        assert calculate_usage_percentage(used, quota) == 25.0

    def test_calculate_usage_percentage_empty(self) -> None:
        assert calculate_usage_percentage(0, 1000) == 0.0
        assert calculate_usage_percentage(100, 0) == 0.0

    def test_calculate_usage_percentage_capped_at_100(self) -> None:
        # If user somehow exceeded quota, percentage should not break UI
        assert calculate_usage_percentage(1500, 1000) == 100.0

    def test_get_remaining_quota_bytes(self) -> None:
        assert get_remaining_quota_bytes(used_bytes=200, quota_bytes=1000) == 800
        assert get_remaining_quota_bytes(used_bytes=1000, quota_bytes=1000) == 0
        assert get_remaining_quota_bytes(used_bytes=1200, quota_bytes=1000) == 0


@pytest.mark.unit
class TestCheckQuotaAvailability:
    """Tests for upload boundary checking against quota."""

    def test_upload_fits_within_quota(self) -> None:
        used = 100 * 1024 * 1024
        quota = 500 * 1024 * 1024
        incoming = 50 * 1024 * 1024  # 50 MB fits in 400 MB remaining
        fits, msg = check_quota_availability(used, quota, incoming)
        assert fits is True
        assert "passed" in msg.lower()

    def test_upload_exceeds_remaining_quota_rejected(self) -> None:
        used = 480 * 1024 * 1024
        quota = 500 * 1024 * 1024
        incoming = 30 * 1024 * 1024  # 30 MB does not fit in 20 MB remaining
        fits, msg = check_quota_availability(used, quota, incoming)
        assert fits is False
        assert "exceeded" in msg.lower()

    def test_zero_incoming_bytes_rejected(self) -> None:
        fits, msg = check_quota_availability(0, 500, 0)
        assert fits is False
        assert "zero" in msg.lower()
