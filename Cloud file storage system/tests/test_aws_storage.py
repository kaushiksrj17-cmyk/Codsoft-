"""Unit and diagnostic tests for AWS S3 configuration and storage manager."""

from __future__ import annotations

import os
import unittest.mock
import urllib.request
import uuid
from typing import Any

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

    def test_client_initialization_includes_regional_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured_kwargs: dict[str, Any] = {}

        def mock_boto_client(*args: Any, **kwargs: Any) -> Any:
            captured_kwargs.update(kwargs)
            return unittest.mock.MagicMock()

        monkeypatch.setattr("boto3.client", mock_boto_client)

        cfg = AppConfig(
            app_env="production",
            aws_region="ap-south-1",
            s3_bucket_name="my-test-vault-bucket",
            aws_access_key_id="AKIAIOSFODNN7REALKEY",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYREALKEY",
            database_path="data/test.db",
            max_file_size_mb=50,
            default_storage_quota_mb=500,
            share_link_max_expiry_hours=168,
        )
        manager = S3StorageManager(cfg)
        client = manager.get_client()
        assert client is not None
        assert captured_kwargs.get("endpoint_url") == "https://s3.ap-south-1.amazonaws.com"
        assert captured_kwargs.get("region_name") == "ap-south-1"

    def test_upload_file_bytes_mocked(self) -> None:
        cfg = AppConfig(
            app_env="production",
            aws_region="ap-south-1",
            s3_bucket_name="my-test-vault-bucket",
            aws_access_key_id="AKIAIOSFODNN7REALKEY",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYREALKEY",
            database_path="data/test.db",
            max_file_size_mb=50,
            default_storage_quota_mb=500,
            share_link_max_expiry_hours=168,
        )
        manager = S3StorageManager(cfg)
        mock_client = unittest.mock.MagicMock()
        manager._client = mock_client

        test_bytes = b"hello s3 storage"
        manager.upload_file_bytes(test_bytes, "users/1/files/doc.pdf", content_type="application/pdf")

        mock_client.put_object.assert_called_once_with(
            Bucket="my-test-vault-bucket",
            Key="users/1/files/doc.pdf",
            Body=test_bytes,
            ContentType="application/pdf",
            ServerSideEncryption="AES256",
        )

    def test_generate_presigned_download_url_mocked(self) -> None:
        cfg = AppConfig(
            app_env="production",
            aws_region="ap-south-1",
            s3_bucket_name="my-test-vault-bucket",
            aws_access_key_id="AKIAIOSFODNN7REALKEY",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYREALKEY",
            database_path="data/test.db",
            max_file_size_mb=50,
            default_storage_quota_mb=500,
            share_link_max_expiry_hours=168,
        )
        manager = S3StorageManager(cfg)
        mock_client = unittest.mock.MagicMock()
        mock_client.generate_presigned_url.return_value = (
            "https://s3.ap-south-1.amazonaws.com/my-test-vault-bucket/doc.pdf?signed=1"
        )
        manager._client = mock_client

        url = manager.generate_presigned_download_url("users/1/files/doc.pdf", expires_in_seconds=300)
        assert "https://s3.ap-south-1.amazonaws.com" in url
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "my-test-vault-bucket", "Key": "users/1/files/doc.pdf"},
            ExpiresIn=300,
        )

    def test_delete_object_mocked(self) -> None:
        cfg = AppConfig(
            app_env="production",
            aws_region="ap-south-1",
            s3_bucket_name="my-test-vault-bucket",
            aws_access_key_id="AKIAIOSFODNN7REALKEY",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYREALKEY",
            database_path="data/test.db",
            max_file_size_mb=50,
            default_storage_quota_mb=500,
            share_link_max_expiry_hours=168,
        )
        manager = S3StorageManager(cfg)
        mock_client = unittest.mock.MagicMock()
        manager._client = mock_client

        result = manager.delete_object("users/1/files/doc.pdf")
        assert result is True
        mock_client.delete_object.assert_called_once_with(
            Bucket="my-test-vault-bucket",
            Key="users/1/files/doc.pdf",
        )


@pytest.mark.aws
class TestS3LiveOperationsScaffolding:
    """Live cloud integration tests for Phase 2.

    These tests run only when explicitly opted in via RUN_AWS_INTEGRATION_TESTS=1.
    During ordinary CI or local test runs without this flag, they are safely skipped.
    """

    @pytest.mark.skipif(
        os.getenv("RUN_AWS_INTEGRATION_TESTS") != "1",
        reason="Phase 2 Live AWS: Opt-in with RUN_AWS_INTEGRATION_TESTS=1 to run real S3 upload test.",
    )
    def test_live_s3_upload_and_download(self) -> None:
        from src.config import get_config

        config = get_config()
        if not config.is_aws_configured():
            pytest.skip("AWS credentials not configured in environment.")

        manager = S3StorageManager(config)
        client = manager.get_client()
        unique_id = uuid.uuid4().hex[:12]
        test_key = f"diagnostics/phase2-test-{unique_id}.txt"
        payload = f"Phase 2 test payload {unique_id}".encode("utf-8")

        try:
            manager.upload_file_bytes(payload, test_key, content_type="text/plain")
            resp = client.get_object(Bucket=config.s3_bucket_name, Key=test_key)
            downloaded = resp["Body"].read()
            assert downloaded == payload
        finally:
            try:
                manager.delete_object(test_key)
            except Exception:
                pass

    @pytest.mark.skipif(
        os.getenv("RUN_AWS_INTEGRATION_TESTS") != "1",
        reason="Phase 2 Live AWS: Opt-in with RUN_AWS_INTEGRATION_TESTS=1 to run real presigned URL test.",
    )
    def test_live_s3_presigned_url_generation(self) -> None:
        from src.config import get_config

        config = get_config()
        if not config.is_aws_configured():
            pytest.skip("AWS credentials not configured in environment.")

        manager = S3StorageManager(config)
        unique_id = uuid.uuid4().hex[:12]
        test_key = f"diagnostics/phase2-presign-{unique_id}.txt"
        payload = f"Phase 2 presigned payload {unique_id}".encode("utf-8")

        try:
            manager.upload_file_bytes(payload, test_key, content_type="text/plain")
            presigned_url = manager.generate_presigned_download_url(test_key, expires_in_seconds=120)
            assert f"s3.{config.aws_region}.amazonaws.com" in presigned_url

            req = urllib.request.Request(presigned_url, headers={"User-Agent": "CODSOFT-Verification/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                downloaded = resp.read()
                assert resp.status == 200
                assert downloaded == payload
        finally:
            try:
                manager.delete_object(test_key)
            except Exception:
                pass

