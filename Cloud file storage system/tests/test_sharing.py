"""Unit and integration tests for file sharing, token validation, access control, and revocation."""

from __future__ import annotations

import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from src.activity_logger import get_recent_activities
from src.auth import create_user
from src.config import AppConfig
from src.database import get_connection, get_db_cursor, init_db
from src.sharing import (
    access_shared_file,
    build_share_url,
    calculate_expiration_datetime,
    create_share_link,
    generate_share_token,
    get_share_by_token,
    get_sharing_metrics,
    is_share_expired,
    list_shares_by_user,
    list_shares_shared_with_email,
    revoke_share_link,
    validate_share_access,
)


@pytest.fixture
def sharing_env(tmp_path: Path):
    """Setup an isolated database, test configuration, users, and files for sharing tests."""
    db_file = str(tmp_path / "test_sharing.db")
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

    # 1. Owner user
    owner = create_user(
        username="alice_owner",
        email="alice@example.com",
        plain_password="SecurePassword123!",
        quota_bytes=10 * 1024 * 1024,
        db_path=db_file,
    )

    # 2. Collaborator recipient
    collab = create_user(
        username="bob_collab",
        email="bob@example.com",
        plain_password="SecurePassword123!",
        quota_bytes=10 * 1024 * 1024,
        db_path=db_file,
    )

    # 3. Unauthorized stranger user
    stranger = create_user(
        username="eve_stranger",
        email="eve@example.com",
        plain_password="SecurePassword123!",
        quota_bytes=10 * 1024 * 1024,
        db_path=db_file,
    )

    # 4. Admin user
    admin = create_user(
        username="admin_super",
        email="admin@example.com",
        plain_password="SecurePassword123!",
        role="admin",
        quota_bytes=50 * 1024 * 1024,
        db_path=db_file,
    )

    # Insert test files for owner
    with get_db_cursor(db_file) as cursor:
        cursor.execute(
            """
            INSERT INTO files (user_id, original_name, s3_key, s3_bucket, file_size_bytes, content_type, checksum_sha256, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                owner["id"],
                "project_proposal.pdf",
                f"users/{owner['id']}/files/project_proposal.pdf",
                cfg.s3_bucket_name,
                2048,
                "application/pdf",
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
        )
        file_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO files (user_id, original_name, s3_key, s3_bucket, file_size_bytes, content_type, checksum_sha256, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                owner["id"],
                "deleted_notes.txt",
                f"users/{owner['id']}/files/deleted_notes.txt",
                cfg.s3_bucket_name,
                512,
                "text/plain",
                "f3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b899",
            ),
        )
        deleted_file_id = cursor.lastrowid

    # Mock S3 storage manager
    mock_mgr = unittest.mock.MagicMock()
    mock_mgr.generate_presigned_download_url.side_effect = (
        lambda s3_key, expires_in_seconds=300: f"https://{cfg.s3_bucket_name}.s3.{cfg.aws_region}.amazonaws.com/{s3_key}?presigned=true&exp={expires_in_seconds}"
    )

    return {
        "db_path": db_file,
        "config": cfg,
        "owner": owner,
        "collab": collab,
        "stranger": stranger,
        "admin": admin,
        "file_id": file_id,
        "deleted_file_id": deleted_file_id,
        "mock_mgr": mock_mgr,
    }


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

    def test_token_unpredictability_and_high_entropy(self) -> None:
        tokens = {generate_share_token(32) for _ in range(100)}
        assert len(tokens) == 100
        for tok in tokens:
            assert len(tok) >= 40


@pytest.mark.unit
class TestShareExpiration:
    """Tests for expiration calculation and timestamp evaluation."""

    def test_calculate_expiration_datetime(self) -> None:
        expiry_iso = calculate_expiration_datetime(hours=24)
        exp_dt = datetime.fromisoformat(expiry_iso)
        now = datetime.now(timezone.utc)

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
    """Tests for raw share record access validation."""

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


@pytest.mark.unit
class TestShareCreationWorkflow:
    """Tests for creating share links, access control, and audit logging."""

    def test_authorized_share_creation_by_owner(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        res = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            user_role=owner.get("role", "user"),
            permission_level="download",
            expires_in_hours=24,
            db_path=db_path,
        )

        assert res["file_id"] == file_id
        assert res["shared_by_user_id"] == owner["id"]
        assert res["permission_level"] == "download"
        assert res["is_revoked"] == 0
        assert res["access_count"] == 0
        assert res["share_token"] is not None
        assert "Shared_Files?share=" in res["share_url"]

        # Verify DB persistence
        with get_db_cursor(db_path) as cursor:
            cursor.execute(
                "SELECT * FROM file_shares WHERE share_token = ?", (res["share_token"],)
            )
            row = cursor.fetchone()
            assert row is not None
            assert row["file_id"] == file_id
            assert row["permission_level"] == "download"

        # Verify audit log
        logs = get_recent_activities(user_id=owner["id"], db_path=db_path)
        assert any(
            log["action"] == "SHARE_CREATE" and log["status"] == "SUCCESS"
            for log in logs
        )

    def test_admin_share_creation_for_other_user_file(self, sharing_env) -> None:
        admin = sharing_env["admin"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        res = create_share_link(
            user_id=admin["id"],
            file_id=file_id,
            user_role="admin",
            permission_level="view",
            expires_in_hours=72,
            db_path=db_path,
        )

        assert res["permission_level"] == "view"
        assert res["shared_by_user_id"] == admin["id"]

    def test_unauthorized_share_creation_rejected(self, sharing_env) -> None:
        stranger = sharing_env["stranger"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        with pytest.raises(PermissionError) as exc_info:
            create_share_link(
                user_id=stranger["id"],
                file_id=file_id,
                user_role="user",
                permission_level="view",
                db_path=db_path,
            )

        assert "not authorized" in str(exc_info.value).lower()

        # Verify failed audit log recorded
        logs = get_recent_activities(user_id=stranger["id"], db_path=db_path)
        assert any(
            log["action"] == "SHARE_CREATE" and log["status"] == "FAILED"
            for log in logs
        )

    def test_share_creation_nonexistent_file(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        db_path = sharing_env["db_path"]

        with pytest.raises(ValueError) as exc:
            create_share_link(
                user_id=owner["id"],
                file_id=99999,
                user_role="user",
                db_path=db_path,
            )
        assert "not found" in str(exc.value).lower()

    def test_share_creation_deleted_file(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        deleted_file_id = sharing_env["deleted_file_id"]
        db_path = sharing_env["db_path"]

        with pytest.raises(ValueError) as exc:
            create_share_link(
                user_id=owner["id"],
                file_id=deleted_file_id,
                user_role="user",
                db_path=db_path,
            )
        assert "deleted" in str(exc.value).lower()

    def test_share_creation_invalid_permission(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        with pytest.raises(ValueError) as exc:
            create_share_link(
                user_id=owner["id"],
                file_id=file_id,
                permission_level="superadmin",
                db_path=db_path,
            )
        assert "invalid permission level" in str(exc.value).lower()

    def test_share_creation_with_recipient_email(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        res = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            permission_level="view",
            expires_in_hours=1,
            shared_with_email="  Bob@Example.com  ",
            db_path=db_path,
        )

        assert res["shared_with_email"] == "bob@example.com"


@pytest.mark.unit
class TestShareAccessWorkflow:
    """Tests for accessing shared links, permissions enforcement, and validation."""

    def test_valid_link_access_view_only(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]
        mock_mgr = sharing_env["mock_mgr"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            permission_level="view",
            expires_in_hours=24,
            db_path=db_path,
        )

        res = access_shared_file(
            share_token=share["share_token"],
            storage_manager=mock_mgr,
            db_path=db_path,
        )

        assert res["filename"] == "project_proposal.pdf"
        assert res["permission_level"] == "view"
        assert res["can_download"] is False
        assert res["download_url"] is None
        assert res["access_count"] == 1
        # S3 presigned download URL generation must NOT have been called
        mock_mgr.generate_presigned_download_url.assert_not_called()

        # Verify access count updated in DB
        updated_share = get_share_by_token(share["share_token"], db_path=db_path)
        assert updated_share["access_count"] == 1

        # Verify audit log
        logs = get_recent_activities(db_path=db_path)
        assert any(
            log["action"] == "SHARE_ACCESS"
            and log["status"] == "SUCCESS"
            and "view" in log["details"].lower()
            for log in logs
        )

    def test_valid_link_access_download_permission(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]
        mock_mgr = sharing_env["mock_mgr"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            permission_level="download",
            expires_in_hours=24,
            db_path=db_path,
        )

        res = access_shared_file(
            share_token=share["share_token"],
            storage_manager=mock_mgr,
            db_path=db_path,
        )

        assert res["can_download"] is True
        assert res["download_url"] is not None
        assert "presigned=true" in res["download_url"]
        mock_mgr.generate_presigned_download_url.assert_called_once()

    def test_access_with_invalid_token(self, sharing_env) -> None:
        db_path = sharing_env["db_path"]

        with pytest.raises(ValueError) as exc:
            access_shared_file(
                share_token="nonexistent_invalid_token_123",
                db_path=db_path,
            )

        assert "does not exist" in str(exc.value).lower()

        # Verify failed audit log
        logs = get_recent_activities(db_path=db_path)
        assert any(
            log["action"] == "SHARE_ACCESS" and log["status"] == "FAILED"
            for log in logs
        )

    def test_access_to_expired_link(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            permission_level="view",
            expires_in_hours=1,
            db_path=db_path,
        )

        # Force expire in DB
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        with get_db_cursor(db_path) as cursor:
            cursor.execute(
                "UPDATE file_shares SET expires_at = ? WHERE id = ?",
                (past_iso, share["id"]),
            )

        with pytest.raises(ValueError) as exc:
            access_shared_file(share["share_token"], db_path=db_path)

        assert "expired" in str(exc.value).lower()

    def test_access_to_revoked_link(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            permission_level="view",
            db_path=db_path,
        )

        revoke_share_link(user_id=owner["id"], share_id=share["id"], db_path=db_path)

        with pytest.raises(PermissionError) as exc:
            access_shared_file(share["share_token"], db_path=db_path)

        assert "revoked" in str(exc.value).lower()

    def test_access_to_deleted_file(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            permission_level="view",
            db_path=db_path,
        )

        # Soft delete the file in files table
        with get_db_cursor(db_path) as cursor:
            cursor.execute("UPDATE files SET is_deleted = 1 WHERE id = ?", (file_id,))

        with pytest.raises(FileNotFoundError) as exc:
            access_shared_file(share["share_token"], db_path=db_path)

        assert "deleted" in str(exc.value).lower()

    def test_recipient_email_restriction(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        collab = sharing_env["collab"]
        stranger = sharing_env["stranger"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            shared_with_email=collab["email"],
            db_path=db_path,
        )

        # Authorized collaborator access
        res = access_shared_file(
            share["share_token"],
            recipient_email=collab["email"],
            db_path=db_path,
        )
        assert res["filename"] == "project_proposal.pdf"

        # Unauthorized stranger access
        with pytest.raises(PermissionError) as exc:
            access_shared_file(
                share["share_token"],
                recipient_email=stranger["email"],
                db_path=db_path,
            )
        assert "restricted" in str(exc.value).lower()

        # Anonymous access rejected when email is required
        with pytest.raises(PermissionError):
            access_shared_file(
                share["share_token"],
                recipient_email=None,
                db_path=db_path,
            )


@pytest.mark.unit
class TestShareRevocationWorkflow:
    """Tests for link revocation by owners and admins, authorization checks, and audit trails."""

    def test_successful_owner_revocation(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            db_path=db_path,
        )

        res = revoke_share_link(
            user_id=owner["id"],
            share_id=share["id"],
            user_role="user",
            db_path=db_path,
        )

        assert res["success"] is True
        assert res["share_id"] == share["id"]

        # Verify DB is_revoked == 1
        with get_db_cursor(db_path) as cursor:
            cursor.execute(
                "SELECT is_revoked FROM file_shares WHERE id = ?", (share["id"],)
            )
            row = cursor.fetchone()
            assert row["is_revoked"] == 1

        # Subsequent access must immediately fail
        with pytest.raises(PermissionError):
            access_shared_file(share["share_token"], db_path=db_path)

        # Audit log verified
        logs = get_recent_activities(user_id=owner["id"], db_path=db_path)
        assert any(
            log["action"] == "SHARE_REVOKE" and log["status"] == "SUCCESS"
            for log in logs
        )

    def test_successful_admin_revocation(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        admin = sharing_env["admin"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            db_path=db_path,
        )

        res = revoke_share_link(
            user_id=admin["id"],
            share_id=share["id"],
            user_role="admin",
            db_path=db_path,
        )
        assert res["success"] is True

    def test_unauthorized_user_revocation_rejected(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        stranger = sharing_env["stranger"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            db_path=db_path,
        )

        with pytest.raises(PermissionError) as exc:
            revoke_share_link(
                user_id=stranger["id"],
                share_id=share["id"],
                user_role="user",
                db_path=db_path,
            )

        assert "not authorized" in str(exc.value).lower()

        # Verify share is still active
        with get_db_cursor(db_path) as cursor:
            cursor.execute(
                "SELECT is_revoked FROM file_shares WHERE id = ?", (share["id"],)
            )
            assert cursor.fetchone()["is_revoked"] == 0

        # Failed audit log recorded
        logs = get_recent_activities(user_id=stranger["id"], db_path=db_path)
        assert any(
            log["action"] == "SHARE_REVOKE" and log["status"] == "FAILED"
            for log in logs
        )

    def test_revocation_does_not_delete_audit_logs(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        share = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            db_path=db_path,
        )
        revoke_share_link(
            user_id=owner["id"],
            share_id=share["id"],
            db_path=db_path,
        )

        logs = get_recent_activities(user_id=owner["id"], db_path=db_path)
        create_logs = [l for l in logs if l["action"] == "SHARE_CREATE"]
        revoke_logs = [l for l in logs if l["action"] == "SHARE_REVOKE"]

        assert len(create_logs) >= 1
        assert len(revoke_logs) >= 1


@pytest.mark.unit
class TestShareListingAndTelemetry:
    """Tests for listing user shares, received shares, and aggregate metrics."""

    def test_list_shares_by_user_with_statuses(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        # Active share
        s_act = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            expires_in_hours=48,
            db_path=db_path,
        )

        # Expired share
        s_exp = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            expires_in_hours=1,
            db_path=db_path,
        )
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        with get_db_cursor(db_path) as cursor:
            cursor.execute(
                "UPDATE file_shares SET expires_at = ? WHERE id = ?",
                (past_iso, s_exp["id"]),
            )

        # Revoked share
        s_rev = create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            db_path=db_path,
        )
        revoke_share_link(user_id=owner["id"], share_id=s_rev["id"], db_path=db_path)

        shares = list_shares_by_user(owner["id"], db_path=db_path)
        status_map = {s["id"]: s["status"] for s in shares}

        assert status_map[s_act["id"]] == "Active"
        assert status_map[s_exp["id"]] == "Expired"
        assert status_map[s_rev["id"]] == "Revoked"

    def test_list_shares_shared_with_email(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        collab = sharing_env["collab"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            shared_with_email=collab["email"],
            db_path=db_path,
        )

        in_shares = list_shares_shared_with_email(collab["email"], db_path=db_path)
        assert len(in_shares) == 1
        assert in_shares[0]["filename"] == "project_proposal.pdf"
        assert in_shares[0]["owner_username"] == owner["username"]

    def test_get_sharing_metrics(self, sharing_env) -> None:
        owner = sharing_env["owner"]
        collab = sharing_env["collab"]
        file_id = sharing_env["file_id"]
        db_path = sharing_env["db_path"]

        # 1 active
        create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            expires_in_hours=24,
            db_path=db_path,
        )

        # 1 share for collab
        create_share_link(
            user_id=owner["id"],
            file_id=file_id,
            shared_with_email=collab["email"],
            db_path=db_path,
        )

        metrics = get_sharing_metrics(
            user_id=collab["id"],
            user_role="user",
            email=collab["email"],
            db_path=db_path,
        )
        assert metrics["received_shares_count"] == 1
        assert metrics["active_shares_count"] == 0
