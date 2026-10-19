"""AWS S3 Storage client wrapper and lifecycle management.

Provides an interface for Amazon S3 object storage operations using Boto3,
including secure uploads, presigned download URLs, and safe deletion.

NOTE: In Phase 1, this module validates configuration and provides the foundational
interface. Real cloud API calls are gated behind configuration checks to prevent
accidental charges or execution failures when credentials are absent.
"""

from __future__ import annotations

import logging
from typing import Any, BinaryIO, Dict, Optional, Tuple

from src.config import AppConfig, get_config

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import BotoCoreError, ClientError

    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False


class S3StorageManager:
    """Manages secure communication with Amazon Simple Storage Service (S3)."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or get_config()
        self._client: Any = None

    @property
    def is_configured(self) -> bool:
        """Return True if AWS S3 settings and non-dummy credentials are set."""
        return self.config.is_aws_configured()

    def get_client(self) -> Any:
        """Lazily initialize and return a Boto3 S3 client with modern retry configuration."""
        if not _BOTO3_AVAILABLE:
            raise RuntimeError(
                "Boto3 is not installed. Please install project requirements."
            )

        if not self.is_configured:
            raise RuntimeError(
                "AWS S3 is not configured. Please supply valid credentials and bucket name in .env."
            )

        if self._client is None:
            boto_cfg = BotoConfig(
                region_name=self.config.aws_region,
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            )
            self._client = boto3.client(
                "s3",
                region_name=self.config.aws_region,
                aws_access_key_id=self.config.aws_access_key_id,
                aws_secret_access_key=self.config.aws_secret_access_key,
                config=boto_cfg,
            )
        return self._client

    def check_bucket_accessibility(self) -> Tuple[bool, str]:
        """Verify that the target S3 bucket exists and is accessible.

        Returns (True, message) if accessible, (False, error_message) otherwise.
        """
        if not self.is_configured:
            return (
                False,
                "AWS S3 is in development mode. Credentials or bucket name are not configured.",
            )

        try:
            client = self.get_client()
            client.head_bucket(Bucket=self.config.s3_bucket_name)
            return True, f"Bucket '{self.config.s3_bucket_name}' is accessible."
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                return False, f"Bucket '{self.config.s3_bucket_name}' does not exist."
            elif error_code in ("403", "AccessDenied"):
                return False, "Access denied. Check IAM user permissions for head_bucket."
            return False, f"AWS ClientError [{error_code}]: {e}"
        except Exception as e:
            return False, f"Failed to connect to AWS S3: {e}"

    def build_s3_key(self, user_id: int, filename: str, version: Optional[int] = None) -> str:
        """Construct a scoped, user-isolated S3 key prefix."""
        version_prefix = f"v{version}/" if version else ""
        return f"users/{user_id}/files/{version_prefix}{filename}"

    def upload_file_bytes(
        self,
        file_bytes: bytes | BinaryIO,
        s3_key: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload binary file content to S3 (to be fully integrated in Phase 2)."""
        client = self.get_client()
        extra_args: Dict[str, Any] = {
            "ContentType": content_type,
            "ServerSideEncryption": "AES256",
        }
        if metadata:
            extra_args["Metadata"] = metadata

        if isinstance(file_bytes, bytes):
            return client.put_object(
                Bucket=self.config.s3_bucket_name,
                Key=s3_key,
                Body=file_bytes,
                **extra_args,
            )
        else:
            return client.upload_fileobj(
                Fileobj=file_bytes,
                Bucket=self.config.s3_bucket_name,
                Key=s3_key,
                ExtraArgs=extra_args,
            )

    def generate_presigned_download_url(
        self, s3_key: str, expires_in_seconds: int = 3600
    ) -> str:
        """Generate a secure, time-limited presigned URL for downloading a private S3 object."""
        client = self.get_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.config.s3_bucket_name, "Key": s3_key},
            ExpiresIn=expires_in_seconds,
        )
        return str(url)

    def delete_object(self, s3_key: str) -> bool:
        """Delete an object from the S3 bucket."""
        client = self.get_client()
        client.delete_object(Bucket=self.config.s3_bucket_name, Key=s3_key)
        return True
