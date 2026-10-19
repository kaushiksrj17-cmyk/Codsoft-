"""Unit and diagnostic tests for AWS S3 configuration and storage manager."""

from __future__ import annotations

import pytest
from src.aws_storage import S3StorageManager
from src.config import AppConfig


@pytest.mark.unit
class TestAWSConfigDetection:
    """Tests verifying safe handling and detection of AWS dummy/missing credentials."""

    def test_dummy_credentials_detected_as_unconfigured(self) -> None:
        cfg = AppConfig(
            app_env="development",
            aws_region="us-east-1",
            s3_bucket_name="my-private-cloud-storage-bucket-placeholder",
            aws_access_key_id="YOUR_AWS_ACCESS_KEY_ID_PLACEHOLDER",
            aws_secret_access_key="YOUR_AWS_SECRET_ACCESS_KEY_PLACEHOLDER",
            database_path="data/test.db",
            max_file_size_mb=50,
            default_storage_quota_mb=500,
            share_link_max_expiry_hours=168,
        )
        assert cfg.is_aws_configured() is False

    def test_empty_credentials_detected_as_unconfigured(self) -> None:
        cfg = AppConfig(
            app_env="development",
            aws_region="us-east-1",
            s3_bucket_name="",
            aws_access_key_id="",
            aws_secret_access_key="",
            database_path="data/test.db",
            max_file_size_mb=50,
            default_storage_quota_mb=500,
            share_link_max_expiry_hours=168,
        )
        assert cfg.is_aws_configured() is False

    def test_valid_credentials_detected_as_configured(self) -> None:
        cfg = AppConfig(
            app_env="production",
            aws_region="us-west-2",
            s3_bucket_name="prod-enterprise-vault-bucket",
            aws_access_key_id="AKIAIOSFODNN7REALKEY",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYREALKEY",
            database_path="data/test.db",
            max_file_size_mb=50,
            default_storage_quota_mb=500,
            share_link_max_expiry_hours=168,
        )
        assert cfg.is_aws_configured() is True

    def test_safe_status_does_not_reveal_secrets(self) -> None:
        secret = "super_secret_aws_key_do_not_leak_12345"
        cfg = AppConfig(
            app_env="production",
            aws_region="eu-central-1",
            s3_bucket_name="my-super-secret-vault",
            aws_access_key_id="AKIA1234567890ABCDEF",
            aws_secret_access_key=secret,
            database_path="data/test.db",
            max_file_size_mb=50,
            default_storage_quota_mb=500,
            share_link_max_expiry_hours=168,
        )
        status = cfg.get_safe_aws_status()
        assert secret not in str(status)
        assert status["is_configured"] is True
        assert "eu-central-1" in status["region"]
        assert "CDEF" in status["credentials_status"]


@pytest.mark.unit
class TestS3StorageManagerUnit:
    """Tests for S3 storage manager scaffolding and key formatting."""

    def test_build_s3_key_unversioned(self) -> None:
        manager = S3StorageManager()
        key = manager.build_s3_key(user_id=12, filename="financial_report.xlsx")
        assert key == "users/12/files/financial_report.xlsx"

    def test_build_s3_key_versioned(self) -> None:
        manager = S3StorageManager()
        key = manager.build_s3_key(user_id=12, filename="financial_report.xlsx", version=3)
        assert key == "users/12/files/v3/financial_report.xlsx"

    def test_unconfigured_s3_check_bucket_returns_safe_false(self) -> None:
        cfg = AppConfig(
            app_env="development",
            aws_region="us-east-1",
            s3_bucket_name="",
            aws_access_key_id="",
            aws_secret_access_key="",
            database_path="data/test.db",
            max_file_size_mb=50,
            default_storage_quota_mb=500,
            share_link_max_expiry_hours=168,
        )
        manager = S3StorageManager(cfg)
        is_ok, msg = manager.check_bucket_accessibility()
        assert is_ok is False
        assert "development mode" in msg.lower() or "not configured" in msg.lower()


@pytest.mark.aws
class TestS3LiveOperationsScaffolding:
    """Placeholder scaffolding for Phase 2 live cloud operations.

    These tests are explicitly skipped in Phase 1 to guarantee zero AWS network
    calls or cloud charges until real infrastructure is provided.
    """

    @pytest.mark.skip(reason="Phase 1 Foundation: Real S3 uploads will be executed in Phase 2.")
    def test_live_s3_upload_and_download(self) -> None:
        pass

    @pytest.mark.skip(reason="Phase 1 Foundation: Presigned URL verification will be executed in Phase 2.")
    def test_live_s3_presigned_url_generation(self) -> None:
        pass
