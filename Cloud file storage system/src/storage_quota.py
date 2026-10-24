"""Storage quota calculations, formatting, and boundary validation.

Guarantees that user uploads strictly respect allocated storage limits.
"""

from __future__ import annotations

from typing import Tuple


def bytes_to_mb(size_bytes: int) -> float:
    """Convert bytes to megabytes (base-2 binary MB, 1024^2)."""
    return size_bytes / (1024 * 1024)


def mb_to_bytes(size_mb: float) -> int:
    """Convert megabytes to bytes."""
    return int(size_mb * 1024 * 1024)


def format_bytes(size_bytes: int) -> str:
    """Format a byte count into a human-readable string (B, KB, MB, GB, TB)."""
    if size_bytes < 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"

    units = ["KB", "MB", "GB", "TB", "PB"]
    value = float(size_bytes)
    for unit in units:
        value /= 1024.0
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}"

    return f"{value:.2f} PB"


def calculate_usage_percentage(used_bytes: int, quota_bytes: int) -> float:
    """Calculate the percentage of allocated quota used, capped at 100.0%."""
    if quota_bytes <= 0:
        return 0.0
    if used_bytes <= 0:
        return 0.0

    percentage = (used_bytes / quota_bytes) * 100.0
    return min(round(percentage, 2), 100.0)


def get_remaining_quota_bytes(used_bytes: int, quota_bytes: int) -> int:
    """Calculate remaining quota in bytes (minimum 0)."""
    remaining = quota_bytes - used_bytes
    return max(0, remaining)


def check_quota_availability(
    used_bytes: int, quota_bytes: int, incoming_bytes: int
) -> Tuple[bool, str]:
    """Check whether an incoming file upload will fit within remaining quota."""
    if incoming_bytes <= 0:
        return False, "Cannot upload a zero or negative byte payload."

    remaining = get_remaining_quota_bytes(used_bytes, quota_bytes)
    if incoming_bytes > remaining:
        incoming_str = format_bytes(incoming_bytes)
        remaining_str = format_bytes(remaining)
        quota_str = format_bytes(quota_bytes)
        return (
            False,
            f"Storage quota exceeded. File size ({incoming_str}) exceeds "
            f"remaining capacity ({remaining_str} of {quota_str}).",
        )

    return True, "Storage quota check passed."
