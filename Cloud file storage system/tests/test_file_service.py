"""Unit and integration tests for file_service upload, listing, quota, and rollback."""

from __future__ import annotations

import unittest.mock
from pathlib import Path

import pytest
from src.activity_logger import get_recent_activities
from src.auth import create_user
from src.config import AppConfig
from src.database import get_connection, init_db
from src.file_service import (
    delete_file,
    download_file,
    download_historical_version,
    get_file_version_history,
    get_user_quota_info,
    list_user_files,
    upload_file,
)


@pytest.fixture
def test_env(tmp_path: Path):
    """Setup an isolated database and test AppConfig."""
    db_file = str(tmp_path / "test_cloud_storage.db")
    init_db(db_file)

    cfg = AppConfig(
        app_env="testing",
        aws_region="ap-south-1",
        s3_bucket_name="test-cloud-storage-bucket",
        aws_access_key_id="AKIAIOSFODNN7REALKEY",
        aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYREALKEY",
        database_path=db_file,
        max_file_size_mb=10,
        default_storage_quota_mb=50,
        share_link_max_expiry_hours=168,
    )

    # Create primary test user
    user = create_user(
        username="test_user",
        email="test_user@example.com",
        plain_password="SecurePassword123!",
        quota_bytes=5 * 1024 * 1024,  # 5 MB
        db_path=db_file,
    )

    mock_mgr = unittest.mock.MagicMock()
    mock_mgr.build_s3_key.side_effect = lambda uid, fn, version=None: (
        f"users/{uid}/files/v{version}/{fn}" if version else f"users/{uid}/files/{fn}"
    )

    return {
        "db_path": db_file,
        "config": cfg,
        "user": user,
        "mock_mgr": mock_mgr,
    }


@pytest.mark.unit
class TestFileUploadWorkflow:
    """Tests for file upload validation, S3 coordination, and persistence."""

    def test_successful_upload(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        payload = b"Hello, Amazon S3 and SQLite!"
        res = upload_file(
            user_id=user["id"],
            file_bytes=payload,
            filename="quarterly_report.pdf",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        assert res["filename"] == "quarterly_report.pdf"
        assert res["version"] == 1
        assert res["size_bytes"] == len(payload)
        assert res["s3_key"] == f"users/{user['id']}/files/quarterly_report.pdf"

        # Verify S3 mock upload was called with AES256
        mock_mgr.upload_file_bytes.assert_called_once()
        call_kwargs = mock_mgr.upload_file_bytes.call_args[1]
        assert call_kwargs["s3_key"] == res["s3_key"]
        assert call_kwargs["content_type"] == "application/pdf"
        assert call_kwargs["metadata"]["sha256"] == res["checksum"]

        # Verify database record
        conn = get_connection(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM files WHERE id = ?", (res["file_id"],))
            row = cur.fetchone()
            assert row is not None
            assert row["original_name"] == "quarterly_report.pdf"
            assert row["file_size_bytes"] == len(payload)
            assert row["is_deleted"] == 0

            # Verify quota updated in users table
            cur.execute("SELECT used_storage_bytes FROM users WHERE id = ?", (user["id"],))
            user_row = cur.fetchone()
            assert user_row["used_storage_bytes"] == len(payload)
        finally:
            conn.close()

        # Verify audit log
        logs = get_recent_activities(user_id=user["id"], limit=5, db_path=db_path)
        assert len(logs) >= 1
        assert logs[0]["action"] == "FILE_UPLOAD"
        assert logs[0]["status"] == "SUCCESS"

    def test_invalid_extension_rejected(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        with pytest.raises(ValueError, match="Security Policy.*blocked"):
            upload_file(
                user_id=user["id"],
                file_bytes=b"malicious payload",
                filename="script.exe",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        mock_mgr.upload_file_bytes.assert_not_called()

    def test_invalid_filename_rejected(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        with pytest.raises(ValueError, match="Invalid filename"):
            upload_file(
                user_id=user["id"],
                file_bytes=b"data",
                filename="../../etc/passwd",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        mock_mgr.upload_file_bytes.assert_not_called()

    def test_file_exceeding_size_limit_rejected(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        # Configured max_file_size_mb is 10 MB
        oversized = b"x" * (11 * 1024 * 1024)
        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            upload_file(
                user_id=user["id"],
                file_bytes=oversized,
                filename="large_data.zip",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        mock_mgr.upload_file_bytes.assert_not_called()

    def test_quota_exceeded_rejected(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        # User quota is 5 MB. Attempt 6 MB upload.
        payload = b"y" * (6 * 1024 * 1024)
        with pytest.raises(ValueError, match="Storage quota exceeded"):
            upload_file(
                user_id=user["id"],
                file_bytes=payload,
                filename="huge_archive.zip",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        mock_mgr.upload_file_bytes.assert_not_called()

    def test_s3_upload_failure_handled(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        mock_mgr.upload_file_bytes.side_effect = RuntimeError("AWS Connection Timeout")

        with pytest.raises(RuntimeError, match="Cloud storage upload error"):
            upload_file(
                user_id=user["id"],
                file_bytes=b"sample payload",
                filename="doc.pdf",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # Confirm no record was inserted in database
        files = list_user_files(user_id=user["id"], db_path=db_path)
        assert len(files) == 0

        # Confirm failed audit log was captured
        logs = get_recent_activities(user_id=user["id"], db_path=db_path)
        assert len(logs) >= 1
        assert logs[0]["status"] == "FAILED"

    def test_database_insertion_failure_triggers_s3_cleanup(self, test_env, monkeypatch) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        # Mock database insertion to fail after S3 upload
        import src.file_service
        from contextlib import contextmanager

        real_get_db_cursor = src.file_service.get_db_cursor
        failed = {"done": False}

        @contextmanager
        def failing_cursor(path=None):
            if mock_mgr.upload_file_bytes.called and not failed["done"]:
                failed["done"] = True
                raise RuntimeError("Database Disk Full Failure")
            with real_get_db_cursor(path) as cur:
                yield cur

        monkeypatch.setattr("src.file_service.get_db_cursor", failing_cursor)

        with pytest.raises(RuntimeError, match="Database error during metadata recording"):
            upload_file(
                user_id=user["id"],
                file_bytes=b"sample payload",
                filename="doc_fail.pdf",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # Confirm compensating rollback called delete_object on the uploaded S3 key
        mock_mgr.delete_object.assert_called_once_with(f"users/{user['id']}/files/doc_fail.pdf")

    def test_duplicate_filename_creates_new_version(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        # Initial upload (v1)
        res1 = upload_file(
            user_id=user["id"],
            file_bytes=b"Version 1 content",
            filename="notes.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert res1["version"] == 1
        assert res1["s3_key"] == f"users/{user['id']}/files/notes.txt"

        # Attempt exact duplicate content -> rejected
        with pytest.raises(ValueError, match="identical SHA-256 checksum is already stored"):
            upload_file(
                user_id=user["id"],
                file_bytes=b"Version 1 content",
                filename="notes.txt",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # Upload modified content under same name -> creates v2
        res2 = upload_file(
            user_id=user["id"],
            file_bytes=b"Version 2 updated content with new insights",
            filename="notes.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert res2["version"] == 2
        assert res2["file_id"] == res1["file_id"]
        assert res2["s3_key"] == f"users/{user['id']}/files/v2/notes.txt"

        # Query listing
        files = list_user_files(user_id=user["id"], db_path=db_path)
        assert len(files) == 1
        assert files[0]["current_version"] == 2


@pytest.mark.unit
class TestFileListingAndTenantIsolation:
    """Tests verifying user ownership filtering, sorting, and quota calculations."""

    def test_user_ownership_filtering(self, test_env) -> None:
        user1 = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        # Create user 2
        user2 = create_user(
            username="second_user",
            email="second@example.com",
            plain_password="SecurePassword456!",
            db_path=db_path,
        )

        # Upload for user 1
        upload_file(
            user_id=user1["id"],
            file_bytes=b"User 1 secret file",
            filename="user1_doc.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        # Upload for user 2
        upload_file(
            user_id=user2["id"],
            file_bytes=b"User 2 confidential report",
            filename="user2_doc.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        # User 1 should strictly see only their file
        u1_files = list_user_files(user_id=user1["id"], user_role="user", db_path=db_path)
        assert len(u1_files) == 1
        assert u1_files[0]["original_name"] == "user1_doc.txt"

        # User 2 should strictly see only their file
        u2_files = list_user_files(user_id=user2["id"], user_role="user", db_path=db_path)
        assert len(u2_files) == 1
        assert u2_files[0]["original_name"] == "user2_doc.txt"

        # Admin user can see all files across tenants
        admin_files = list_user_files(user_id=user1["id"], user_role="admin", db_path=db_path)
        assert len(admin_files) == 2

    def test_quota_calculation_accuracy(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        # Check initial quota
        q0 = get_user_quota_info(user["id"], db_path=db_path)
        assert q0["used_bytes"] == 0
        assert q0["usage_percentage"] == 0.0

        # Upload 100 KB
        payload = b"k" * (100 * 1024)
        upload_file(
            user_id=user["id"],
            file_bytes=payload,
            filename="sample.bin",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        q1 = get_user_quota_info(user["id"], db_path=db_path)
        assert q1["used_bytes"] == 100 * 1024
        assert q1["remaining_bytes"] == (5 * 1024 * 1024) - (100 * 1024)
        assert q1["usage_percentage"] > 0.0


@pytest.mark.unit
class TestFileDownloadDeletionAndVersionHistory:
    """Tests for file download, soft-deletion, version history, and quota consistency."""

    def test_authorized_current_version_download(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        mock_mgr.generate_presigned_download_url.return_value = "https://s3.ap-south-1.amazonaws.com/test-bucket/users/1/files/report.pdf?sig=123"
        mock_mgr.object_exists.return_value = True

        up_res = upload_file(
            user_id=user["id"],
            file_bytes=b"PDF payload content",
            filename="report.pdf",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        dl_res = download_file(
            user_id=user["id"],
            file_id=file_id,
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert dl_res["file_id"] == file_id
        assert dl_res["filename"] == "report.pdf"
        assert "sig=123" in dl_res["download_url"]
        mock_mgr.generate_presigned_download_url.assert_called_with(f"users/{user['id']}/files/report.pdf", expires_in_seconds=300)

        # Confirm download activity was logged
        logs = get_recent_activities(user_id=user["id"], db_path=db_path)
        assert logs[0]["action"] == "FILE_DOWNLOAD"
        assert logs[0]["status"] == "SUCCESS"

    def test_unauthorized_cross_user_download(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        # Create second user
        other_user = create_user(
            username="other_user",
            email="other@example.com",
            plain_password="Password123!",
            quota_bytes=10 * 1024 * 1024,
            db_path=db_path,
        )

        up_res = upload_file(
            user_id=user["id"],
            file_bytes=b"Confidential user 1 content",
            filename="private.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        # User 2 attempts to download User 1's file
        with pytest.raises(PermissionError, match="does not have download permissions"):
            download_file(
                user_id=other_user["id"],
                file_id=file_id,
                user_role="user",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_download_of_deleted_files(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        up_res = upload_file(
            user_id=user["id"],
            file_bytes=b"Delete me content",
            filename="temp.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        delete_file(
            user_id=user["id"],
            file_id=file_id,
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        with pytest.raises(ValueError, match="has been deleted and cannot be downloaded"):
            download_file(
                user_id=user["id"],
                file_id=file_id,
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_presigned_url_generation_failure(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        up_res = upload_file(
            user_id=user["id"],
            file_bytes=b"Sample content",
            filename="sample.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        mock_mgr.generate_presigned_download_url.side_effect = RuntimeError("AWS presign timeout")
        mock_mgr.object_exists.return_value = True

        with pytest.raises(RuntimeError, match="Failed to generate download URL"):
            download_file(
                user_id=user["id"],
                file_id=file_id,
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_successful_soft_deletion_and_quota_recovery(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        payload = b"q" * 2048  # 2 KB
        up_res = upload_file(
            user_id=user["id"],
            file_bytes=payload,
            filename="cleanup.bin",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        q_before = get_user_quota_info(user["id"], db_path=db_path)
        assert q_before["used_bytes"] == 2048

        # Execute soft delete
        del_res = delete_file(
            user_id=user["id"],
            file_id=file_id,
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert del_res["success"] is True
        assert del_res["freed_bytes"] == 2048
        assert del_res["already_deleted"] is False

        # Quota must be zeroed out
        q_after = get_user_quota_info(user["id"], db_path=db_path)
        assert q_after["used_bytes"] == 0

        # S3 delete_object was called for active key
        mock_mgr.delete_object.assert_called_with(f"users/{user['id']}/files/cleanup.bin")

        # Confirm file does not appear in normal listing
        active_files = list_user_files(user_id=user["id"], db_path=db_path)
        assert len(active_files) == 0

        # Activity log check
        logs = get_recent_activities(user_id=user["id"], db_path=db_path)
        assert logs[0]["action"] == "FILE_DELETE"
        assert logs[0]["status"] == "SUCCESS"

    def test_unauthorized_deletion(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        other_user = create_user(
            username="other_del_user",
            email="other_del@example.com",
            plain_password="Password123!",
            quota_bytes=10 * 1024 * 1024,
            db_path=db_path,
        )

        up_res = upload_file(
            user_id=user["id"],
            file_bytes=b"Protected content",
            filename="protected.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        with pytest.raises(PermissionError, match="is not authorized to delete file"):
            delete_file(
                user_id=other_user["id"],
                file_id=file_id,
                user_role="user",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # Verify file is still active
        with get_connection(db_path) as conn:
            row = conn.execute("SELECT is_deleted FROM files WHERE id = ?", (file_id,)).fetchone()
            assert row["is_deleted"] == 0

    def test_repeated_deletion_without_double_quota_deduction(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        payload = b"d" * 4096
        up_res = upload_file(
            user_id=user["id"],
            file_bytes=payload,
            filename="double_del.bin",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        # First deletion
        r1 = delete_file(
            user_id=user["id"],
            file_id=file_id,
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert r1["already_deleted"] is False
        assert r1["freed_bytes"] == 4096

        # Second deletion (idempotent retry)
        r2 = delete_file(
            user_id=user["id"],
            file_id=file_id,
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert r2["already_deleted"] is True
        assert r2["freed_bytes"] == 0

        # Quota remains non-negative and 0
        q = get_user_quota_info(user["id"], db_path=db_path)
        assert q["used_bytes"] == 0

    def test_version_history_retrieval(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        # Upload v1
        upload_file(
            user_id=user["id"],
            file_bytes=b"Initial version content",
            filename="changelog.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        # Upload v2 with modified content
        up2 = upload_file(
            user_id=user["id"],
            file_bytes=b"Second version content with updates",
            filename="changelog.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up2["file_id"]

        history = get_file_version_history(user_id=user["id"], file_id=file_id, db_path=db_path)
        assert len(history) == 2
        assert history[0]["version_number"] == 2
        assert history[0]["is_current"] is True
        assert history[0]["version_label"] == "v2"
        assert history[1]["version_number"] == 1
        assert history[1]["is_current"] is False
        assert history[1]["version_label"] == "v1"

    def test_historical_version_download(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        mock_mgr.generate_presigned_download_url.return_value = "https://s3.ap-south-1.amazonaws.com/test-bucket/users/1/files/history.txt?v=1"
        mock_mgr.object_exists.return_value = True

        upload_file(
            user_id=user["id"],
            file_bytes=b"Version 1 text",
            filename="history.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        up2 = upload_file(
            user_id=user["id"],
            file_bytes=b"Version 2 updated text",
            filename="history.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up2["file_id"]

        # Download v1
        h_dl = download_historical_version(
            user_id=user["id"],
            file_id=file_id,
            version_number=1,
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert h_dl["version_number"] == 1
        assert "users/1/files/history.txt" in h_dl["s3_key"]
        mock_mgr.generate_presigned_download_url.assert_called_with(f"users/{user['id']}/files/history.txt", expires_in_seconds=300)

    def test_missing_historical_s3_object_raises_error(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        up1 = upload_file(
            user_id=user["id"],
            file_bytes=b"Version 1",
            filename="missing_obj.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up1["file_id"]

        # Object missing in bucket
        mock_mgr.object_exists.return_value = False

        with pytest.raises(FileNotFoundError, match="storage object for 'missing_obj.txt' not found in S3 bucket"):
            download_historical_version(
                user_id=user["id"],
                file_id=file_id,
                version_number=1,
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_s3_deletion_failure_leaves_db_consistent(self, test_env) -> None:
        user = test_env["user"]
        db_path = test_env["db_path"]
        mock_mgr = test_env["mock_mgr"]
        cfg = test_env["config"]

        up = upload_file(
            user_id=user["id"],
            file_bytes=b"Important file",
            filename="s3_fail.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up["file_id"]

        # S3 delete raises exception
        mock_mgr.delete_object.side_effect = RuntimeError("AWS S3 500 Internal Error")

        with pytest.raises(RuntimeError, match="Cloud storage deletion error"):
            delete_file(
                user_id=user["id"],
                file_id=file_id,
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # Database record must NOT be deleted
        with get_connection(db_path) as conn:
            row = conn.execute("SELECT is_deleted FROM files WHERE id = ?", (file_id,)).fetchone()
            assert row["is_deleted"] == 0

        # Quota must not be deducted
        q = get_user_quota_info(user["id"], db_path=db_path)
        assert q["used_bytes"] == len(b"Important file")

