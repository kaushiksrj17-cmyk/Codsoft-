"""Centralized application configuration.

Manages environment-based configuration, sensible development defaults,
input validation, and safe handling of AWS credentials and settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

# Attempt to load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv

    # Locate project root (one level above 'src')
    _project_root = Path(__file__).resolve().parent.parent
    _env_path = _project_root / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
    else:
        load_dotenv()
except ImportError:
    pass

# Known placeholder substrings that indicate non-configured dummy values
_DUMMY_INDICATORS = (
    "placeholder",
    "your_aws",
    "dummy",
    "change_me",
    "example",
    "none",
)


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration container."""

    app_env: str
    aws_region: str
    s3_bucket_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    database_path: str
    max_file_size_mb: int
    default_storage_quota_mb: int
    share_link_max_expiry_hours: int

    @property
    def max_file_size_bytes(self) -> int:
        """Return the maximum allowed file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def default_storage_quota_bytes(self) -> int:
        """Return default user storage quota in bytes."""
        return self.default_storage_quota_mb * 1024 * 1024

    def is_aws_configured(self) -> bool:
        """Check whether AWS S3 has non-dummy, non-empty credentials and bucket."""
        if not self.s3_bucket_name or not self.aws_access_key_id or not self.aws_secret_access_key:
            return False

        # Verify against placeholder strings
        lower_bucket = self.s3_bucket_name.lower()
        lower_key = self.aws_access_key_id.lower()
        lower_secret = self.aws_secret_access_key.lower()

        for indicator in _DUMMY_INDICATORS:
            if indicator in lower_bucket or indicator in lower_key or indicator in lower_secret:
                return False

        return True

    def get_safe_aws_status(self) -> Dict[str, Any]:
        """Return safe, non-sensitive AWS status for diagnostics and UI display.

        Never reveals raw secret keys or access credentials.
        """
        configured = self.is_aws_configured()

        # Mask bucket name if present
        bucket_display = "Not configured"
        if self.s3_bucket_name:
            if any(ind in self.s3_bucket_name.lower() for ind in _DUMMY_INDICATORS):
                bucket_display = f"{self.s3_bucket_name} [PLACEHOLDER]"
            else:
                # Mask middle of bucket name for privacy
                b = self.s3_bucket_name
                bucket_display = b[:3] + "***" + b[-2:] if len(b) > 5 else "***"

        # Check key status
        key_status = "Missing"
        if self.aws_access_key_id:
            if any(ind in self.aws_access_key_id.lower() for ind in _DUMMY_INDICATORS):
                key_status = "Placeholder Detected"
            else:
                key_status = f"Active (ends in {self.aws_access_key_id[-4:]})"

        return {
            "is_configured": configured,
            "region": self.aws_region or "us-east-1",
            "bucket_display": bucket_display,
            "credentials_status": key_status,
            "environment": self.app_env,
            "mode": "Live S3 Storage" if configured else "Development Mode (S3 Pending)",
        }


def _parse_positive_int(var_name: str, default: int) -> int:
    """Parse and validate positive integer environment variables."""
    raw = os.getenv(var_name, "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
        if val <= 0:
            return default
        return val
    except ValueError:
        return default


def load_config() -> AppConfig:
    """Load configuration from environment variables with safe defaults and validation."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "testing", "staging", "production"}:
        app_env = "development"

    aws_region = os.getenv("AWS_REGION", "us-east-1").strip()
    s3_bucket_name = os.getenv("S3_BUCKET_NAME", "").strip()
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

    database_path = os.getenv("DATABASE_PATH", "data/cloud_storage.db").strip()
    if not database_path:
        database_path = "data/cloud_storage.db"

    max_file_size_mb = _parse_positive_int("MAX_FILE_SIZE_MB", default=50)
    default_storage_quota_mb = _parse_positive_int("DEFAULT_STORAGE_QUOTA_MB", default=500)
    share_link_max_expiry_hours = _parse_positive_int("SHARE_LINK_MAX_EXPIRY_HOURS", default=168)

    return AppConfig(
        app_env=app_env,
        aws_region=aws_region,
        s3_bucket_name=s3_bucket_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        database_path=database_path,
        max_file_size_mb=max_file_size_mb,
        default_storage_quota_mb=default_storage_quota_mb,
        share_link_max_expiry_hours=share_link_max_expiry_hours,
    )


# Cached configuration instance
_CURRENT_CONFIG: AppConfig | None = None


def get_config(reload: bool = False) -> AppConfig:
    """Get the cached AppConfig instance, or load if not yet initialized."""
    global _CURRENT_CONFIG
    if _CURRENT_CONFIG is None or reload:
        _CURRENT_CONFIG = load_config()
    return _CURRENT_CONFIG
