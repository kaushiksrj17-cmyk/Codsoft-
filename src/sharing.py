"""Secure file sharing, access token generation, and expiration checking.

Implements cryptographically random token generation and expiration validation
for time-limited, role-restricted public and peer share links.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple


def generate_share_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure URL-safe random token."""
    return secrets.token_urlsafe(nbytes)


def calculate_expiration_datetime(hours: int) -> str:
    """Calculate future ISO-8601 UTC timestamp based on an expiry duration in hours."""
    if hours <= 0:
        raise ValueError("Expiration duration must be a positive integer.")
    expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
    return expiry.isoformat()


def is_share_expired(expires_at_iso: Optional[str]) -> bool:
    """Check whether a share link's expiration timestamp has passed.

    If expires_at_iso is None, the share has no expiration and is permanent until revoked.
    """
    if not expires_at_iso:
        return False

    try:
        # Support ISO 8601 with or without Z/offset
        exp_dt = datetime.fromisoformat(expires_at_iso)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        return now >= exp_dt
    except (ValueError, TypeError):
        # Malformed expiration timestamps fail closed (treated as expired)
        return True


def validate_share_access(share_record: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate whether a share link is currently valid and active."""
    if not share_record:
        return False, "Share link does not exist."

    if bool(share_record.get("is_revoked", False)):
        return False, "This share link has been revoked by the owner."

    expires_at = share_record.get("expires_at")
    if is_share_expired(expires_at):
        return False, "This share link has expired."

    return True, "Share link is valid and active."
