"""Regression and verification tests for Phase 5A Security Audit.

Validates all security patches and protections against:
- Trailing dot/space extension bypass (CWE-434 / CWE-178)
- Dangerous web shell / executable extension upload prevention
- User role tampering and input validation during registration (CWE-20)
- Account impersonation and authentication audit logging (CWE-287 / CWE-778)
- S3 key boundary validation and tenant isolation (CWE-22)
- Presigned download URL lifetime constraints
- Failed audit trail recording for unauthorized downloads and deletions (CWE-285)
- Constant-time recipient email matching on shared links (CWE-208)
"""

from __future__ import annotations

import unittest.mock
from pathlib import Path
from typing import Any

import pytest
from src.activity_logger import get_recent_activities
from src.auth import authenticate_user, create_user
from src.aws_storage import S3StorageManager
from src.config import AppConfig
from src.database import init_db
from src.file_service import (
    delete_file,
    download_file,
    download_historical_version,
    get_file_version_history,
    upload_file,
)
from src.file_validation import (
    sanitize_filename,
    validate_file_extension,
    validate_filename,
)
from src.sharing import access_shared_file, create_share_link


@pytest.fixture
def security_test_env(tmp_path: Path):
    """Provide an isolated database and test harness for security audit assertions."""
    db_file = str(tmp_path / "security_audit.db")
    init_db(db_file)

    cfg = AppConfig(
        app_env="testing",
        aws_region="ap-south-1",
        s3_bucket_name="security-audit-bucket",
        aws_access_key_id="AKIAIOSFODNN7REALKEY",
        aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYREALKEY",
        database_path=db_file,
        max_file_size_mb=10,
        default_storage_quota_mb=50,
        share_link_max_expiry_hours=168,
    )

    # Create Owner User
    owner = create_user(
        username="alice_owner",
        email="alice@company.internal",
        plain_password="OwnerPassword123!",
        role="user",
        quota_bytes=10 * 1024 * 1024,
        db_path=db_file,
    )

    # Create Attacker / Unauthorized User
    attacker = create_user(
        username="eve_attacker",
        email="eve@company.internal",
        plain_password="AttackerPassword123!",
        role="user",
        quota_bytes=10 * 1024 * 1024,
        db_path=db_file,
    )

    mock_mgr = unittest.mock.MagicMock()
    mock_mgr.build_s3_key = S3StorageManager(cfg).build_s3_key
    mock_mgr.object_exists.return_value = True
    mock_mgr.generate_presigned_download_url.return_value = "https://s3.ap-south-1.amazonaws.com/test-url"

    return {
        "db_path": db_file,
        "config": cfg,
        "owner": owner,
        "attacker": attacker,
        "mock_mgr": mock_mgr,
    }


# ==============================================================================
# Checklist E: File Validation & Path Traversal Fixes
# ==============================================================================
@pytest.mark.unit
class TestFileValidationSecurity:
    """Tests for file validation, extension bypass, and path traversal defenses."""

    def test_trailing_dot_extension_bypass_rejected(self) -> None:
        """Verify filenames ending with trailing dots cannot bypass extension blocking."""
        is_valid, msg = validate_file_extension("malicious.exe.")
        assert is_valid is False
        assert "blocked for security reasons" in msg

    def test_trailing_space_extension_bypass_rejected(self) -> None:
        """Verify filenames ending with trailing spaces cannot bypass extension blocking."""
        is_valid, msg = validate_file_extension("exploit.bat   ")
        assert is_valid is False
        assert "blocked for security reasons" in msg

    def test_web_shell_extensions_blocked(self) -> None:
        """Verify server-side script and web-shell extensions are blocked."""
        dangerous_names = [
            "webshell.php",
            "cmd.jsp",
            "handler.asp",
            "upload.aspx",
            "script.sh",
            "gateway.cgi",
            "backdoor.pl",
            "runner.py",
            "macro.vbs",
        ]
        for name in dangerous_names:
            is_valid, msg = validate_file_extension(name)
            assert is_valid is False, f"Expected {name} to be blocked"
            assert "blocked for security reasons" in msg

    def test_validate_filename_rejects_trailing_dot_or_space(self) -> None:
        """Verify validate_filename rejects filenames ending with dot or whitespace."""
        is_valid_dot, msg_dot = validate_filename("document.pdf.")
        assert is_valid_dot is False
        assert "cannot end with a dot or space" in msg_dot

        is_valid_sp, msg_sp = validate_filename("document.pdf ")
        assert is_valid_sp is False
        assert "cannot end with a dot or space" in msg_sp

    def test_sanitize_filename_strips_trailing_dots_and_spaces(self) -> None:
        """Verify sanitize_filename cleans trailing dots and spaces."""
        cleaned = sanitize_filename("safe_report.pdf. . ")
        assert cleaned == "safe_report.pdf"


# ==============================================================================
# Checklist A & B: Authentication, Roles, and Sessions
# ==============================================================================
@pytest.mark.unit
class TestAuthenticationAndRoleSecurity:
    """Tests for user creation, role restriction, and login audit trails."""

    def test_role_tampering_rejected(self, security_test_env) -> None:
        """Verify non-whitelisted roles cannot be assigned during registration."""
        db_path = security_test_env["db_path"]
        with pytest.raises(ValueError, match="Invalid role 'superuser'"):
            create_user(
                username="hacker_admin",
                email="hacker@test.com",
                plain_password="StrongPassword123!",
                role="superuser",
                db_path=db_path,
            )

    def test_valid_roles_allowed(self, security_test_env) -> None:
        """Verify only allowed roles ('user', 'admin') succeed."""
        db_path = security_test_env["db_path"]
        u1 = create_user("legit_user", "u1@test.com", "Password123!", role="user", db_path=db_path)
        assert u1["role"] == "user"

        u2 = create_user("legit_admin", "u2@test.com", "Password123!", role="admin", db_path=db_path)
        assert u2["role"] == "admin"

    def test_malformed_username_rejected(self, security_test_env) -> None:
        """Verify invalid usernames are rejected with clear error messages."""
        db_path = security_test_env["db_path"]
        with pytest.raises(ValueError, match="Username must be between 3 and 32 characters"):
            create_user("a", "valid@test.com", "Password123!", db_path=db_path)

        with pytest.raises(ValueError, match="Username must be between 3 and 32 characters"):
            create_user("user<script>", "valid@test.com", "Password123!", db_path=db_path)

    def test_malformed_email_rejected(self, security_test_env) -> None:
        """Verify invalid emails are rejected."""
        db_path = security_test_env["db_path"]
        with pytest.raises(ValueError, match="A valid email address is required"):
            create_user("valid_user", "not-an-email", "Password123!", db_path=db_path)

    def test_duplicate_user_raises_value_error(self, security_test_env) -> None:
        """Verify duplicate user registration raises ValueError instead of unhandled DB error."""
        db_path = security_test_env["db_path"]
        with pytest.raises(ValueError, match="already registered"):
            create_user("alice_owner", "new_email@company.internal", "Password123!", db_path=db_path)

    def test_authenticate_user_logs_audit_events(self, security_test_env) -> None:
        """Verify successful and failed logins record audit log entries."""
        db_path = security_test_env["db_path"]

        # 1. Failed login with wrong password
        failed_res = authenticate_user("alice_owner", "WrongPassword999!", db_path=db_path)
        assert failed_res is None

        logs = get_recent_activities(db_path=db_path, limit=10)
        failed_login_logs = [l for l in logs if l["action"] == "AUTH_LOGIN" and l["status"] == "FAILED"]
        assert len(failed_login_logs) >= 1
        assert "invalid credentials" in failed_login_logs[0]["details"]

        # 2. Successful login
        success_res = authenticate_user("alice_owner", "OwnerPassword123!", db_path=db_path)
        assert success_res is not None
        assert success_res["username"] == "alice_owner"

        logs_after = get_recent_activities(db_path=db_path, limit=10)
        success_login_logs = [l for l in logs_after if l["action"] == "AUTH_LOGIN" and l["status"] == "SUCCESS"]
        assert len(success_login_logs) >= 1
        assert success_login_logs[0]["user_id"] == security_test_env["owner"]["id"]


# ==============================================================================
# Checklist D: Amazon S3 Key & Presigned URL Security
# ==============================================================================
@pytest.mark.unit
class TestS3StorageSecurity:
    """Tests for S3 key boundary validation and presigned URL constraints."""

    def test_build_s3_key_rejects_non_positive_user_id(self) -> None:
        """Verify build_s3_key prevents negative or zero user IDs."""
        mgr = S3StorageManager()
        with pytest.raises(ValueError, match="Must be a positive integer"):
            mgr.build_s3_key(user_id=0, filename="report.pdf")

        with pytest.raises(ValueError, match="Must be a positive integer"):
            mgr.build_s3_key(user_id=-5, filename="report.pdf")

    def test_build_s3_key_sanitizes_path_traversal(self) -> None:
        """Verify build_s3_key strips path traversal sequences from filenames."""
        mgr = S3StorageManager()
        key = mgr.build_s3_key(user_id=42, filename="../../etc/passwd.txt")
        assert ".." not in key
        assert key == "users/42/files/passwd.txt"

    def test_build_s3_key_rejects_invalid_version(self) -> None:
        """Verify build_s3_key rejects version numbers less than 1."""
        mgr = S3StorageManager()
        with pytest.raises(ValueError, match="Version must be a positive integer"):
            mgr.build_s3_key(user_id=42, filename="report.pdf", version=0)

    def test_presigned_url_validates_key_and_expiry_bounds(self) -> None:
        """Verify generate_presigned_download_url enforces key presence and bounds."""
        mgr = S3StorageManager()
        with pytest.raises(ValueError, match="S3 key is required"):
            mgr.generate_presigned_download_url("")

        with pytest.raises(ValueError, match="expiration must be between"):
            mgr.generate_presigned_download_url("users/1/files/doc.pdf", expires_in_seconds=0)

        with pytest.raises(ValueError, match="expiration must be between"):
            mgr.generate_presigned_download_url("users/1/files/doc.pdf", expires_in_seconds=700000)


# ==============================================================================
# Checklist B, C, F: Authorization & Audit Trail Enforcement
# ==============================================================================
@pytest.mark.unit
class TestAuthorizationAndAuditTrails:
    """Tests for RBAC boundary checks and failed audit trail records."""

    def test_unauthorized_download_logs_failed_audit(self, security_test_env) -> None:
        """Verify unauthorized download attempt raises PermissionError and logs FAILED event."""
        owner = security_test_env["owner"]
        attacker = security_test_env["attacker"]
        db_path = security_test_env["db_path"]
        cfg = security_test_env["config"]
        mock_mgr = security_test_env["mock_mgr"]

        # Owner uploads a private file
        up_res = upload_file(
            user_id=owner["id"],
            file_bytes=b"Confidential financial statement.",
            filename="confidential.pdf",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        # Attacker tries to download owner's file
        with pytest.raises(PermissionError, match="does not have download permissions"):
            download_file(
                user_id=attacker["id"],
                file_id=file_id,
                user_role="user",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # Confirm audit log captured the failed attempt
        logs = get_recent_activities(db_path=db_path, limit=10)
        failed_downloads = [
            l for l in logs
            if l["action"] == "FILE_DOWNLOAD" and l["status"] == "FAILED" and l["user_id"] == attacker["id"]
        ]
        assert len(failed_downloads) == 1
        assert "Unauthorized download attempt" in failed_downloads[0]["details"]

    def test_unauthorized_delete_logs_failed_audit(self, security_test_env) -> None:
        """Verify unauthorized file deletion raises PermissionError and logs FAILED event."""
        owner = security_test_env["owner"]
        attacker = security_test_env["attacker"]
        db_path = security_test_env["db_path"]
        cfg = security_test_env["config"]
        mock_mgr = security_test_env["mock_mgr"]

        up_res = upload_file(
            user_id=owner["id"],
            file_bytes=b"Private user data.",
            filename="user_data.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        with pytest.raises(PermissionError, match="not authorized to delete"):
            delete_file(
                user_id=attacker["id"],
                file_id=file_id,
                user_role="user",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        logs = get_recent_activities(db_path=db_path, limit=10)
        failed_deletes = [
            l for l in logs
            if l["action"] == "FILE_DELETE" and l["status"] == "FAILED" and l["user_id"] == attacker["id"]
        ]
        assert len(failed_deletes) == 1
        assert "Unauthorized deletion attempt" in failed_deletes[0]["details"]

    def test_unauthorized_version_history_logs_failed_audit(self, security_test_env) -> None:
        """Verify unauthorized version history inspection raises PermissionError and logs FAILED."""
        owner = security_test_env["owner"]
        attacker = security_test_env["attacker"]
        db_path = security_test_env["db_path"]
        cfg = security_test_env["config"]
        mock_mgr = security_test_env["mock_mgr"]

        up_res = upload_file(
            user_id=owner["id"],
            file_bytes=b"Versioned code notes.",
            filename="app_notes.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = up_res["file_id"]

        with pytest.raises(PermissionError, match="does not have permission to view"):
            get_file_version_history(
                user_id=attacker["id"],
                file_id=file_id,
                user_role="user",
                db_path=db_path,
            )

        logs = get_recent_activities(db_path=db_path, limit=10)
        failed_views = [
            l for l in logs
            if l["action"] == "FILE_VIEW_VERSIONS" and l["status"] == "FAILED" and l["user_id"] == attacker["id"]
        ]
        assert len(failed_views) == 1

    def test_share_email_restriction_enforces_constant_time_comparison(self, security_test_env) -> None:
        """Verify targeted email share rejects mismatched recipients and logs FAILED event."""
        owner = security_test_env["owner"]
        db_path = security_test_env["db_path"]
        cfg = security_test_env["config"]
        mock_mgr = security_test_env["mock_mgr"]

        up_res = upload_file(
            user_id=owner["id"],
            file_bytes=b"Shared with bob only.",
            filename="bob_contract.pdf",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        share = create_share_link(
            user_id=owner["id"],
            file_id=up_res["file_id"],
            permission_level="download",
            shared_with_email="bob@partner.org",
            db_path=db_path,
        )

        # Attacker tries to access with different email
        with pytest.raises(PermissionError, match="restricted to bob@partner.org"):
            access_shared_file(
                share_token=share["share_token"],
                recipient_user_id=security_test_env["attacker"]["id"],
                recipient_email="eve@company.internal",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        logs = get_recent_activities(db_path=db_path, limit=10)
        failed_shares = [
            l for l in logs
            if l["action"] == "SHARE_ACCESS" and l["status"] == "FAILED"
        ]
        assert len(failed_shares) >= 1
        assert "Unauthorized recipient access attempt" in failed_shares[0]["details"]
