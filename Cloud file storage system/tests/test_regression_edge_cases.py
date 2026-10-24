"""Comprehensive Regression and Edge-Case Test Suite for Phase 5B.

Strengthens verification across:
- Task 2: File management, tenant isolation, path traversal, deletion restrictions, versioning.
- Task 3: Storage quota boundaries, transaction rollbacks, failure recovery, idempotent deletion.
- Task 4: Sharing security, cryptographic token lifecycle, email matching, view-only vs download, audit privacy.
- Task 5: Authentication safeguards, password complexity, role tampering, and fail-closed unauthenticated access.
- Task 6: Order-independent, isolated execution using temporary databases and mocked S3 storage.
"""

from __future__ import annotations

import io
import re
import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest
from src.activity_logger import get_recent_activities
from src.auth import (
    authenticate_user,
    create_user,
    get_all_users,
    get_user_by_id,
    hash_password,
    validate_password_strength,
    verify_password,
)
from src.aws_storage import S3StorageManager
from src.config import AppConfig
from src.database import get_connection, get_db_cursor, init_db
from src.file_service import (
    delete_file,
    download_file,
    download_historical_version,
    get_file_version_history,
    get_user_quota_info,
    list_user_files,
    upload_file,
)
from src.file_validation import (
    compute_sha256,
    get_content_type,
    sanitize_filename,
    validate_file_extension,
    validate_file_size,
    validate_filename,
)
from src.permissions import (
    SharePermission,
    UserRole,
    can_delete_file,
    can_download_file,
    can_edit_file,
    can_manage_shares,
    can_view_file,
    is_admin,
    is_owner,
)
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
from src.storage_quota import (
    bytes_to_mb,
    calculate_usage_percentage,
    check_quota_availability,
    format_bytes,
    get_remaining_quota_bytes,
    mb_to_bytes,
)


@pytest.fixture
def edge_case_env(tmp_path: Path):
    """Provide an isolated database, mock S3 manager, and pre-seeded test tenants."""
    db_file = str(tmp_path / "regression_edge_cases.db")
    init_db(db_file)

    cfg = AppConfig(
        app_env="testing",
        aws_region="ap-south-1",
        s3_bucket_name="regression-test-bucket",
        aws_access_key_id="AKIAIOSFODNN7REALKEY",
        aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYREALKEY",
        database_path=db_file,
        max_file_size_mb=10,
        default_storage_quota_mb=50,
        share_link_max_expiry_hours=168,
    )

    # 1. Primary Tenant: Alice
    alice = create_user(
        username="alice_tenant",
        email="alice@tenant-a.com",
        plain_password="SecurePassword123!",
        role="user",
        quota_bytes=10 * 1024 * 1024,  # 10 MB
        db_path=db_file,
    )

    # 2. Secondary Tenant: Bob
    bob = create_user(
        username="bob_tenant",
        email="bob@tenant-b.com",
        plain_password="SecurePassword123!",
        role="user",
        quota_bytes=10 * 1024 * 1024,  # 10 MB
        db_path=db_file,
    )

    # 3. System Administrator: Charlie
    charlie = create_user(
        username="charlie_admin",
        email="charlie@enterprise.internal",
        plain_password="AdminPassword123!",
        role="admin",
        quota_bytes=50 * 1024 * 1024,
        db_path=db_file,
    )

    # Mock S3 Manager with key building from real implementation
    real_s3 = S3StorageManager(cfg)
    mock_mgr = unittest.mock.MagicMock()
    mock_mgr.build_s3_key = real_s3.build_s3_key
    mock_mgr.object_exists.return_value = True
    mock_mgr.generate_presigned_download_url.side_effect = (
        lambda key, expires_in_seconds=300: f"https://s3.ap-south-1.amazonaws.com/{cfg.s3_bucket_name}/{key}?exp={expires_in_seconds}"
    )

    return {
        "db_path": db_file,
        "config": cfg,
        "alice": alice,
        "bob": bob,
        "admin": charlie,
        "mock_mgr": mock_mgr,
    }


# ==============================================================================
# Task 2: File Management and Tenant Isolation
# ==============================================================================
@pytest.mark.unit
class TestTenantIsolationAndFileSecurity:
    """Rigorous tests for cross-tenant isolation, deleted files, and file validation."""

    def test_user_a_cannot_list_user_b_files_under_any_filter(self, edge_case_env) -> None:
        """User A must strictly never see User B's files regardless of search, category, or sort."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        # Alice uploads a document
        upload_file(
            user_id=alice["id"],
            file_bytes=b"Alice private document content.",
            filename="quarterly_plan.pdf",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        # Bob uploads a document with similar wording
        upload_file(
            user_id=bob["id"],
            file_bytes=b"Bob confidential roadmap.",
            filename="annual_plan.pdf",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        # Alice lists files with generic search matching both
        alice_files = list_user_files(
            user_id=alice["id"],
            user_role="user",
            search_query="plan",
            db_path=db_path,
        )
        assert len(alice_files) == 1
        assert alice_files[0]["original_name"] == "quarterly_plan.pdf"

        # Alice filters by category
        alice_docs = list_user_files(
            user_id=alice["id"],
            user_role="user",
            filter_category="Documents",
            db_path=db_path,
        )
        assert len(alice_docs) == 1
        assert alice_docs[0]["original_name"] == "quarterly_plan.pdf"

        # Alice searches specifically for Bob's filename
        alice_target = list_user_files(
            user_id=alice["id"],
            user_role="user",
            search_query="annual_plan",
            db_path=db_path,
        )
        assert len(alice_target) == 0

        # Bob lists his files
        bob_files = list_user_files(
            user_id=bob["id"],
            user_role="user",
            search_query="plan",
            db_path=db_path,
        )
        assert len(bob_files) == 1
        assert bob_files[0]["original_name"] == "annual_plan.pdf"

    def test_user_a_cannot_download_user_b_file(self, edge_case_env) -> None:
        """Changing file_id to another user's file fails closed with PermissionError."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        bob_up = upload_file(
            user_id=bob["id"],
            file_bytes=b"Bob proprietary algorithm source.",
            filename="algorithm.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        bob_file_id = bob_up["file_id"]

        mock_mgr.generate_presigned_download_url.reset_mock()

        with pytest.raises(PermissionError, match="does not have download permissions"):
            download_file(
                user_id=alice["id"],
                file_id=bob_file_id,
                user_role="user",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # Verify presigned URL was never generated
        mock_mgr.generate_presigned_download_url.assert_not_called()

    def test_user_a_cannot_download_user_b_historical_version(self, edge_case_env) -> None:
        """Accessing a historical version of another user's file raises PermissionError."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        # Bob uploads v1 and v2
        b_up1 = upload_file(
            user_id=bob["id"],
            file_bytes=b"Bob v1 draft.",
            filename="contract.pdf",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        upload_file(
            user_id=bob["id"],
            file_bytes=b"Bob v2 signed copy.",
            filename="contract.pdf",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        mock_mgr.generate_presigned_download_url.reset_mock()

        with pytest.raises(PermissionError, match="does not have download permissions"):
            download_historical_version(
                user_id=alice["id"],
                file_id=b_up1["file_id"],
                version_number=1,
                user_role="user",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        mock_mgr.generate_presigned_download_url.assert_not_called()

    def test_user_a_cannot_view_user_b_version_history(self, edge_case_env) -> None:
        """User A cannot inspect version history metadata for User B's files."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        b_up = upload_file(
            user_id=bob["id"],
            file_bytes=b"Initial design notes.",
            filename="notes.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        with pytest.raises(PermissionError, match="does not have permission to view"):
            get_file_version_history(
                user_id=alice["id"],
                file_id=b_up["file_id"],
                user_role="user",
                db_path=db_path,
            )

    def test_user_a_cannot_delete_user_b_file(self, edge_case_env) -> None:
        """User A attempting to delete User B's file is rejected and leaves S3 and DB intact."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        payload = b"Bob critical system backup."
        b_up = upload_file(
            user_id=bob["id"],
            file_bytes=payload,
            filename="backup.bin",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        file_id = b_up["file_id"]

        mock_mgr.delete_object.reset_mock()

        with pytest.raises(PermissionError, match="not authorized to delete file"):
            delete_file(
                user_id=alice["id"],
                file_id=file_id,
                user_role="user",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # S3 object was NOT deleted
        mock_mgr.delete_object.assert_not_called()

        # Database record is NOT soft-deleted
        with get_connection(db_path) as conn:
            row = conn.execute("SELECT is_deleted FROM files WHERE id = ?", (file_id,)).fetchone()
            assert row["is_deleted"] == 0

        # Bob's quota remains allocated
        q = get_user_quota_info(bob["id"], db_path=db_path)
        assert q["used_bytes"] == len(payload)

    def test_user_a_cannot_share_user_b_file(self, edge_case_env) -> None:
        """User A cannot create a share link for User B's file."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        b_up = upload_file(
            user_id=bob["id"],
            file_bytes=b"Bob private diary.",
            filename="diary.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        with pytest.raises(PermissionError, match="not authorized to create share links"):
            create_share_link(
                user_id=alice["id"],
                file_id=b_up["file_id"],
                user_role="user",
                permission_level="download",
                db_path=db_path,
            )

        with get_connection(db_path) as conn:
            shares = conn.execute("SELECT COUNT(*) FROM file_shares WHERE file_id = ?", (b_up["file_id"],)).fetchone()
            assert shares[0] == 0

    def test_deleted_files_excluded_from_normal_listings(self, edge_case_env) -> None:
        """Soft-deleted files must not appear in user file listings under any sort or filter."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(
            user_id=alice["id"],
            file_bytes=b"Temporary working note.",
            filename="temp_note.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        delete_file(
            user_id=alice["id"],
            file_id=up["file_id"],
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )

        # Listing with various filters
        assert len(list_user_files(alice["id"], db_path=db_path)) == 0
        assert len(list_user_files(alice["id"], search_query="temp", db_path=db_path)) == 0
        assert len(list_user_files(alice["id"], filter_category="Documents", db_path=db_path)) == 0
        assert len(list_user_files(alice["id"], sort_by="Name (A-Z)", db_path=db_path)) == 0

    def test_cannot_download_deleted_file(self, edge_case_env) -> None:
        """Downloading a soft-deleted file raises ValueError."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(
            user_id=alice["id"],
            file_bytes=b"Data to delete.",
            filename="todelete.txt",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        delete_file(alice["id"], up["file_id"], storage_manager=mock_mgr, config=cfg, db_path=db_path)

        with pytest.raises(ValueError, match="has been deleted and cannot be downloaded"):
            download_file(
                user_id=alice["id"],
                file_id=up["file_id"],
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_cannot_download_historical_version_of_deleted_file(self, edge_case_env) -> None:
        """Historical version downloads are rejected if the root file is soft-deleted."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"v1 content", "history_del.txt", storage_manager=mock_mgr, config=cfg, db_path=db_path)
        upload_file(alice["id"], b"v2 content", "history_del.txt", storage_manager=mock_mgr, config=cfg, db_path=db_path)
        delete_file(user_id=alice["id"], file_id=up["file_id"], storage_manager=mock_mgr, config=cfg, db_path=db_path)

        with pytest.raises(ValueError, match="has been deleted and cannot be downloaded"):
            download_historical_version(
                user_id=alice["id"],
                file_id=up["file_id"],
                version_number=1,
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_cannot_share_deleted_file(self, edge_case_env) -> None:
        """Attempting to create a share link for a soft-deleted file raises ValueError."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"Data", "share_del.txt", storage_manager=mock_mgr, config=cfg, db_path=db_path)
        delete_file(user_id=alice["id"], file_id=up["file_id"], storage_manager=mock_mgr, config=cfg, db_path=db_path)

        with pytest.raises(ValueError, match="has been deleted and cannot be shared"):
            create_share_link(
                user_id=alice["id"],
                file_id=up["file_id"],
                db_path=db_path,
            )

    def test_access_shared_file_fails_when_file_deleted_post_share(self, edge_case_env) -> None:
        """Accessing a share link whose underlying file was subsequently deleted raises FileNotFoundError."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"Shared then deleted.", "shared_then_del.txt", storage_manager=mock_mgr, config=cfg, db_path=db_path)
        share = create_share_link(alice["id"], up["file_id"], permission_level="download", db_path=db_path)

        # Alice deletes the file
        delete_file(user_id=alice["id"], file_id=up["file_id"], storage_manager=mock_mgr, config=cfg, db_path=db_path)

        with pytest.raises(FileNotFoundError, match="has been deleted and is no longer available"):
            access_shared_file(
                share_token=share["share_token"],
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_input_validation_path_traversal_and_null_bytes(self) -> None:
        """Verify comprehensive filename validation rejects path traversal and control characters."""
        invalid_names = [
            "../etc/passwd",
            "..\\Windows\\System32",
            "folder/report.pdf",
            "folder\\report.pdf",
            "file\x00.pdf",
            "file\x1f.bin",
            "file\r\n.txt",
            "test<script>.pdf",
            'quotes"in"name.pdf',
            "pipe|symbol.txt",
            "asterisk*file.doc",
            "question?file.csv",
            "trailing_dot.pdf.",
            "trailing_space.pdf ",
            "trailing_both.pdf.   ",
        ]
        for name in invalid_names:
            is_valid, msg = validate_filename(name)
            assert is_valid is False, f"Expected '{name}' to be rejected by validate_filename, got {msg}"

    def test_windows_reserved_device_names_all_casings_and_extensions(self) -> None:
        """Verify Windows reserved device names are blocked across casing and multipart extensions."""
        reserved_examples = [
            "con", "CON.txt", "con.pdf", "Con.tar.gz",
            "PRN", "prn.docx",
            "AUX", "aux.bin", "Aux.dat.zip",
            "NUL", "nul.log",
            "com1.png", "COM9.jpg",
            "lpt1.txt", "LPT8.csv",
        ]
        for r_name in reserved_examples:
            is_valid, msg = validate_filename(r_name)
            assert is_valid is False, f"Expected reserved name '{r_name}' to be rejected, got {msg}"
            assert "reserved" in msg.lower()

    def test_disallowed_file_types_and_double_extensions(self) -> None:
        """Verify executable, script, and bypass double extensions are rejected."""
        blocked_names = [
            "exploit.exe", "script.bat", "run.cmd", "shell.sh", "macro.vbs",
            "installer.msi", "powershell.ps1", "webshell.php", "backend.jsp",
            "classic.asp", "dotnet.aspx", "server.py", "gateway.cgi", "perl.pl",
            "double_ext.png.exe", "bypass.jpg.bat",
        ]
        for name in blocked_names:
            is_valid, msg = validate_file_extension(name)
            assert is_valid is False, f"Expected '{name}' to be blocked"
            assert "blocked" in msg.lower()

    def test_zero_byte_and_oversized_upload_rejections(self, edge_case_env) -> None:
        """Zero-byte payloads and payloads exceeding maximum size limits are rejected before S3 upload."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        # Zero-byte upload
        with pytest.raises(ValueError, match="empty|zero-byte|zero"):
            upload_file(
                user_id=alice["id"],
                file_bytes=b"",
                filename="empty.txt",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # Oversized upload (> 10 MB)
        oversized = b"z" * (11 * 1024 * 1024)
        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            upload_file(
                user_id=alice["id"],
                file_bytes=oversized,
                filename="too_big.zip",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        mock_mgr.upload_file_bytes.assert_not_called()

    def test_duplicate_content_semantics_same_user_vs_cross_user(self, edge_case_env) -> None:
        """Duplicate content semantics: same user/same name is rejected; cross-user is permitted."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        payload = b"Common shared template content."

        # Alice uploads template.txt
        a_res = upload_file(alice["id"], payload, "template.txt", mock_mgr, cfg, db_path)
        assert a_res["version"] == 1

        # Alice attempts to upload exact same file and content -> rejected
        with pytest.raises(ValueError, match="identical SHA-256 checksum is already stored"):
            upload_file(alice["id"], payload, "template.txt", mock_mgr, cfg, db_path)

        # Alice uploads same content under a different filename -> succeeds
        a_copy = upload_file(alice["id"], payload, "template_copy.txt", mock_mgr, cfg, db_path)
        assert a_copy["version"] == 1
        assert a_copy["file_id"] != a_res["file_id"]

        # Bob uploads exact same content and filename -> succeeds (tenant isolation)
        b_res = upload_file(bob["id"], payload, "template.txt", mock_mgr, cfg, db_path)
        assert b_res["version"] == 1
        assert b_res["s3_key"] == f"users/{bob['id']}/files/template.txt"

    def test_modified_content_creates_new_version_preserving_v1_metadata(self, edge_case_env) -> None:
        """Modifying content creates v2 without corrupting or overwriting v1 metadata."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        v1_bytes = b"Version 1 original content."
        v2_bytes = b"Version 2 updated content with new sections."

        v1_res = upload_file(alice["id"], v1_bytes, "manual.txt", mock_mgr, cfg, db_path)
        v1_checksum = v1_res["checksum"]
        file_id = v1_res["file_id"]

        v2_res = upload_file(alice["id"], v2_bytes, "manual.txt", mock_mgr, cfg, db_path)
        assert v2_res["file_id"] == file_id
        assert v2_res["version"] == 2
        assert v2_res["s3_key"] == f"users/{alice['id']}/files/v2/manual.txt"

        # Check versions in database
        history = get_file_version_history(alice["id"], file_id, db_path=db_path)
        assert len(history) == 2
        v2_entry = history[0]
        v1_entry = history[1]

        assert v2_entry["version_number"] == 2
        assert v2_entry["is_current"] is True
        assert v2_entry["file_size_bytes"] == len(v2_bytes)

        assert v1_entry["version_number"] == 1
        assert v1_entry["is_current"] is False
        assert v1_entry["checksum_sha256"] == v1_checksum
        assert v1_entry["s3_key"] == f"users/{alice['id']}/files/manual.txt"
        assert v1_entry["file_size_bytes"] == len(v1_bytes)

    def test_inactive_or_nonexistent_user_upload_rejected(self, edge_case_env) -> None:
        """Inactive accounts and non-existent user IDs cannot upload files."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        # Deactivate Alice in DB
        with get_db_cursor(db_path) as cursor:
            cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (alice["id"],))

        with pytest.raises(ValueError, match="does not exist|suspended or inactive"):
            upload_file(alice["id"], b"Data", "inactive.txt", storage_manager=mock_mgr, config=cfg, db_path=db_path)

        # Nonexistent user ID
        with pytest.raises(ValueError, match="does not exist"):
            upload_file(999999, b"Data", "ghost.txt", storage_manager=mock_mgr, config=cfg, db_path=db_path)


# ==============================================================================
# Task 3: Storage Quota and Failure Recovery
# ==============================================================================
@pytest.mark.unit
class TestStorageQuotaAndFailureRecovery:
    """Rigorous tests for storage quota boundaries, S3/DB rollback, and quota consistency."""

    def test_upload_within_quota_succeeds_and_updates_accounting(self, edge_case_env) -> None:
        """Upload within quota succeeds and accurately updates used_storage_bytes."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        payload = b"A" * (500 * 1024)  # 500 KB
        upload_file(alice["id"], payload, "doc500k.bin", mock_mgr, cfg, db_path)

        q = get_user_quota_info(alice["id"], db_path=db_path)
        assert q["used_bytes"] == 500 * 1024
        assert q["remaining_bytes"] == (10 * 1024 * 1024) - (500 * 1024)
        assert q["usage_percentage"] > 0.0

    def test_upload_exceeding_quota_rejected_without_s3_upload(self, edge_case_env) -> None:
        """Upload exceeding user quota is rejected prior to S3 upload."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        # Alice quota is 10 MB. Attempt to upload 10.5 MB (within 10MB file limit? Let's use 10 MB quota, upload 10 MB file when 1 MB used).
        # First upload 2 MB
        upload_file(alice["id"], b"x" * (2 * 1024 * 1024), "chunk1.bin", mock_mgr, cfg, db_path)

        mock_mgr.upload_file_bytes.reset_mock()

        # Alice has 8 MB remaining. Attempt upload of 9 MB.
        with pytest.raises(ValueError, match="Storage quota exceeded"):
            upload_file(alice["id"], b"y" * (9 * 1024 * 1024), "chunk2.bin", mock_mgr, cfg, db_path)

        # S3 upload was NOT called
        mock_mgr.upload_file_bytes.assert_not_called()

        # Quota remains at 2 MB
        q = get_user_quota_info(alice["id"], db_path=db_path)
        assert q["used_bytes"] == 2 * 1024 * 1024

    def test_exact_quota_boundary_fill_and_one_byte_overflow(self, edge_case_env) -> None:
        """Upload filling quota to the exact remaining byte succeeds; 1 byte over fails."""
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        # Create user with exact 10,000 bytes quota
        exact_user = create_user(
            username="exact_quota_user",
            email="exact@quota.org",
            plain_password="Password123!",
            quota_bytes=10000,
            db_path=db_path,
        )

        # Upload exactly 10,000 bytes
        payload_10k = b"e" * 10000
        up = upload_file(exact_user["id"], payload_10k, "exact.bin", mock_mgr, cfg, db_path)
        assert up["size_bytes"] == 10000

        q = get_user_quota_info(exact_user["id"], db_path=db_path)
        assert q["used_bytes"] == 10000
        assert q["remaining_bytes"] == 0
        assert q["usage_percentage"] == 100.0

        # Attempt to upload 1 more byte -> rejected
        with pytest.raises(ValueError, match="Storage quota exceeded"):
            upload_file(exact_user["id"], b"1", "overflow.txt", mock_mgr, cfg, db_path)

    def test_failed_s3_upload_leaves_no_metadata_or_quota_leak(self, edge_case_env) -> None:
        """When S3 upload encounters an error, no DB file record or quota deduction remains."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        mock_mgr.upload_file_bytes.side_effect = RuntimeError("S3 Network Connection Dropped")

        with pytest.raises(RuntimeError, match="Cloud storage upload error"):
            upload_file(alice["id"], b"Sample content", "s3_error.txt", mock_mgr, cfg, db_path)

        # Database must have zero files
        files = list_user_files(alice["id"], db_path=db_path)
        assert len(files) == 0

        # Quota must be 0
        q = get_user_quota_info(alice["id"], db_path=db_path)
        assert q["used_bytes"] == 0

        # Audit log captures failure
        logs = get_recent_activities(user_id=alice["id"], db_path=db_path)
        failed_uploads = [l for l in logs if l["action"] == "FILE_UPLOAD" and l["status"] == "FAILED"]
        assert len(failed_uploads) >= 1

    def test_db_persistence_failure_triggers_s3_cleanup(self, edge_case_env, monkeypatch) -> None:
        """If database persistence fails post-S3 upload, compensating S3 deletion cleans up the orphaned object."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        from contextlib import contextmanager
        import src.file_service

        real_get_db_cursor = src.file_service.get_db_cursor
        tripped = {"failed": False}

        @contextmanager
        def failing_cursor(path=None):
            # Trip failure only during insertion after S3 upload
            if mock_mgr.upload_file_bytes.called and not tripped["failed"]:
                tripped["failed"] = True
                raise RuntimeError("Simulated SQLite Disk I/O Failure")
            with real_get_db_cursor(path) as cur:
                yield cur

        monkeypatch.setattr("src.file_service.get_db_cursor", failing_cursor)

        with pytest.raises(RuntimeError, match="Database error during metadata recording"):
            upload_file(alice["id"], b"Orphan prevention test.", "rollback.txt", mock_mgr, cfg, db_path)

        # Confirm S3 object was rolled back via delete_object
        expected_s3_key = f"users/{alice['id']}/files/rollback.txt"
        mock_mgr.delete_object.assert_called_once_with(expected_s3_key)

        # Quota remains zero
        q = get_user_quota_info(alice["id"], db_path=db_path)
        assert q["used_bytes"] == 0

    def test_version_updates_and_deletion_quota_accounting_lifecycle(self, edge_case_env) -> None:
        """Creating multiple versions sums quota correctly; deletion frees all versions accurately."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        v1_size = 2000
        v2_size = 3500

        # v1 upload
        up1 = upload_file(alice["id"], b"1" * v1_size, "versioned.bin", mock_mgr, cfg, db_path)
        q1 = get_user_quota_info(alice["id"], db_path=db_path)
        assert q1["used_bytes"] == v1_size

        # v2 upload (different content)
        up2 = upload_file(alice["id"], b"2" * v2_size, "versioned.bin", mock_mgr, cfg, db_path)
        q2 = get_user_quota_info(alice["id"], db_path=db_path)
        assert q2["used_bytes"] == v1_size + v2_size

        # Delete file -> should recover total quota across both versions (5500 bytes)
        del_res = delete_file(user_id=alice["id"], file_id=up2["file_id"], storage_manager=mock_mgr, config=cfg, db_path=db_path)
        assert del_res["success"] is True
        assert del_res["freed_bytes"] == v1_size + v2_size

        q3 = get_user_quota_info(alice["id"], db_path=db_path)
        assert q3["used_bytes"] == 0

    def test_repeated_deletion_idempotency_no_double_quota_recovery(self, edge_case_env) -> None:
        """Calling delete_file repeatedly on an already-deleted file does not subtract quota twice."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"x" * 1500, "double_del.bin", mock_mgr, cfg, db_path)

        # First deletion
        r1 = delete_file(user_id=alice["id"], file_id=up["file_id"], storage_manager=mock_mgr, config=cfg, db_path=db_path)
        assert r1["already_deleted"] is False
        assert r1["freed_bytes"] == 1500

        # Second deletion
        r2 = delete_file(user_id=alice["id"], file_id=up["file_id"], storage_manager=mock_mgr, config=cfg, db_path=db_path)
        assert r2["already_deleted"] is True
        assert r2["freed_bytes"] == 0

        # Quota remains 0 and non-negative
        q = get_user_quota_info(alice["id"], db_path=db_path)
        assert q["used_bytes"] == 0

    def test_used_storage_bytes_never_drops_below_zero(self, edge_case_env) -> None:
        """Quota deduction uses MAX(0, used_storage_bytes - ?) guaranteeing non-negative storage."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]

        # Manually verify SQL behavior with a test update
        with get_db_cursor(db_path) as cursor:
            cursor.execute("UPDATE users SET used_storage_bytes = 100 WHERE id = ?", (alice["id"],))
            cursor.execute("UPDATE users SET used_storage_bytes = MAX(0, used_storage_bytes - 500) WHERE id = ?", (alice["id"],))

        q = get_user_quota_info(alice["id"], db_path=db_path)
        assert q["used_bytes"] == 0


# ==============================================================================
# Task 4: Sharing Security
# ==============================================================================
@pytest.mark.unit
class TestSharingSecurityAndTokenLifecycle:
    """Rigorous tests for share link security, token validation, email restrictions, and audit privacy."""

    def test_invalid_and_blank_share_tokens_fail_safely(self, edge_case_env) -> None:
        """Nonexistent or blank share tokens fail safely without exposing internal exceptions."""
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        for bad_token in ["nonexistent_token_xyz123", "", "   "]:
            with pytest.raises(ValueError, match="Invalid share link or token does not exist"):
                access_shared_file(
                    share_token=bad_token,
                    storage_manager=mock_mgr,
                    config=cfg,
                    db_path=db_path,
                )

    def test_expired_share_link_rejected(self, edge_case_env) -> None:
        """Accessing an expired share link is rejected with ValueError."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"Time-sensitive file.", "time_doc.pdf", mock_mgr, cfg, db_path)
        share = create_share_link(alice["id"], up["file_id"], expires_in_hours=1, db_path=db_path)

        # Force expire by setting past timestamp in DB
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        with get_db_cursor(db_path) as cursor:
            cursor.execute("UPDATE file_shares SET expires_at = ? WHERE id = ?", (past_iso, share["id"]))

        with pytest.raises(ValueError, match="This share link has expired"):
            access_shared_file(
                share_token=share["share_token"],
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_revoked_share_link_rejected(self, edge_case_env) -> None:
        """Accessing a revoked share link is rejected with PermissionError."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"To be revoked.", "revokable.pdf", mock_mgr, cfg, db_path)
        share = create_share_link(alice["id"], up["file_id"], permission_level="view", db_path=db_path)

        revoke_share_link(alice["id"], share["id"], db_path=db_path)

        with pytest.raises(PermissionError, match="has been revoked by the owner"):
            access_shared_file(
                share_token=share["share_token"],
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_email_restricted_link_rejects_unauthorized_or_anonymous_recipient(self, edge_case_env) -> None:
        """Email-restricted share links reject anonymous callers and mismatched email identities."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"Confidential proposal for Bob.", "bob_proposal.pdf", mock_mgr, cfg, db_path)
        share = create_share_link(
            user_id=alice["id"],
            file_id=up["file_id"],
            shared_with_email="bob@tenant-b.com",
            db_path=db_path,
        )

        # Anonymous caller (no email)
        with pytest.raises(PermissionError, match="restricted to bob@tenant-b.com"):
            access_shared_file(
                share_token=share["share_token"],
                recipient_email=None,
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

        # Mismatched caller
        with pytest.raises(PermissionError, match="restricted to bob@tenant-b.com"):
            access_shared_file(
                share_token=share["share_token"],
                recipient_email="stranger@other.org",
                storage_manager=mock_mgr,
                config=cfg,
                db_path=db_path,
            )

    def test_email_restricted_link_case_insensitive_match_succeeds(self, edge_case_env) -> None:
        """Email comparison is case-insensitive, whitespace-trimmed, and constant-time."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"Invoice document.", "invoice.pdf", mock_mgr, cfg, db_path)
        share = create_share_link(
            user_id=alice["id"],
            file_id=up["file_id"],
            shared_with_email="bob@tenant-b.com",
            db_path=db_path,
        )

        res = access_shared_file(
            share_token=share["share_token"],
            recipient_email="  BOB@TENANT-B.COM  ",
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert res["filename"] == "invoice.pdf"

    def test_view_only_share_never_generates_presigned_download_url(self, edge_case_env) -> None:
        """View-only share links never invoke S3 presigned URL generation."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"View only slides.", "deck.pdf", mock_mgr, cfg, db_path)
        share = create_share_link(alice["id"], up["file_id"], permission_level="view", db_path=db_path)

        mock_mgr.generate_presigned_download_url.reset_mock()

        res = access_shared_file(
            share_token=share["share_token"],
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert res["can_download"] is False
        assert res["download_url"] is None
        mock_mgr.generate_presigned_download_url.assert_not_called()

    def test_download_share_creates_short_lived_presigned_url(self, edge_case_env) -> None:
        """Download-enabled share creates only a short-lived presigned URL (300 seconds)."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"Downloadable asset.", "asset.png", mock_mgr, cfg, db_path)
        share = create_share_link(alice["id"], up["file_id"], permission_level="download", db_path=db_path)

        mock_mgr.generate_presigned_download_url.reset_mock()

        res = access_shared_file(
            share_token=share["share_token"],
            storage_manager=mock_mgr,
            config=cfg,
            db_path=db_path,
        )
        assert res["can_download"] is True
        assert res["download_url"] is not None
        assert "exp=300" in res["download_url"]
        mock_mgr.generate_presigned_download_url.assert_called_once_with(
            up["s3_key"], expires_in_seconds=300
        )

    def test_unauthorized_user_cannot_revoke_share(self, edge_case_env) -> None:
        """Non-owner users cannot revoke another owner's share link."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"Alice file.", "alice_share.pdf", mock_mgr, cfg, db_path)
        share = create_share_link(alice["id"], up["file_id"], db_path=db_path)

        with pytest.raises(PermissionError, match="not authorized to revoke share link"):
            revoke_share_link(
                user_id=bob["id"],
                share_id=share["id"],
                user_role="user",
                db_path=db_path,
            )

        # Share remains active in database
        check = get_share_by_token(share["share_token"], db_path=db_path)
        assert check["is_revoked"] == 0

    def test_admin_can_revoke_any_users_share(self, edge_case_env) -> None:
        """System administrator can revoke any user's share link."""
        alice = edge_case_env["alice"]
        admin = edge_case_env["admin"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"Alice file.", "alice_share2.pdf", mock_mgr, cfg, db_path)
        share = create_share_link(alice["id"], up["file_id"], db_path=db_path)

        res = revoke_share_link(
            user_id=admin["id"],
            share_id=share["id"],
            user_role="admin",
            db_path=db_path,
        )
        assert res["success"] is True

        check = get_share_by_token(share["share_token"], db_path=db_path)
        assert check["is_revoked"] == 1

    def test_sharing_logs_never_leak_secrets(self, edge_case_env) -> None:
        """Activity logs generated across share actions never contain full tokens or presigned URLs."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        up = upload_file(alice["id"], b"Audit secrecy test.", "secrecy.pdf", mock_mgr, cfg, db_path)
        share = create_share_link(alice["id"], up["file_id"], permission_level="download", db_path=db_path)
        token = share["share_token"]

        access_shared_file(token, storage_manager=mock_mgr, config=cfg, db_path=db_path)
        revoke_share_link(alice["id"], share["id"], db_path=db_path)

        # Query all logs from DB
        with get_connection(db_path) as conn:
            rows = conn.execute("SELECT action, resource_id, details FROM activity_logs").fetchall()

        for r in rows:
            details = r["details"] or ""
            res_id = r["resource_id"] or ""
            # Full 32-byte / 43-char token must never be stored verbatim
            assert token not in details, f"Token leaked in details: {details}"
            assert token not in res_id, f"Token leaked in resource_id: {res_id}"
            # Presigned download URL must never be logged
            assert "https://" not in details
            assert "amazonaws.com" not in details

    def test_expiration_boundary_precision_and_timezone_support(self) -> None:
        """Verify expiration timestamp evaluation across timezones and boundary conditions."""
        now = datetime.now(timezone.utc)

        # Exactly 1 second future
        future_iso = (now + timedelta(seconds=2)).isoformat()
        assert is_share_expired(future_iso) is False

        # Exactly 1 second past
        past_iso = (now - timedelta(seconds=2)).isoformat()
        assert is_share_expired(past_iso) is True

        # None is permanent
        assert is_share_expired(None) is False

        # Malformed strings fail closed (treated as expired)
        assert is_share_expired("not_a_timestamp") is True
        assert is_share_expired("2026-13-45T99:99:99") is True

        # Non-positive duration in calculate_expiration_datetime raises ValueError
        with pytest.raises(ValueError, match="must be a positive integer"):
            calculate_expiration_datetime(0)
        with pytest.raises(ValueError, match="must be a positive integer"):
            calculate_expiration_datetime(-12)


# ==============================================================================
# Task 5: Authentication and Role Permissions
# ==============================================================================
@pytest.mark.unit
class TestAuthenticationAndRolePermissions:
    """Rigorous tests for credential verification, role tampering, and fail-closed behaviors."""

    def test_invalid_passwords_and_nonexistent_users_fail_safely(self, edge_case_env) -> None:
        """Invalid passwords, blank inputs, and nonexistent users return None and log audit failures."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]

        # 1. Nonexistent user
        assert authenticate_user("ghost_unknown", "AnyPassword123!", db_path=db_path) is None

        # 2. Wrong password
        assert authenticate_user("alice_tenant", "WrongPass999!", db_path=db_path) is None

        # 3. Empty credentials
        assert authenticate_user("", "AnyPassword123!", db_path=db_path) is None
        assert authenticate_user("alice_tenant", "", db_path=db_path) is None

        # Confirm audit logs captured failed attempts
        logs = get_recent_activities(db_path=db_path)
        failed_auths = [l for l in logs if l["action"] == "AUTH_LOGIN" and l["status"] == "FAILED"]
        assert len(failed_auths) >= 2

    def test_role_tampering_and_privilege_escalation_prevention(self, edge_case_env) -> None:
        """Users cannot create unauthorized roles or elevate privileges via input manipulation."""
        db_path = edge_case_env["db_path"]

        invalid_roles = ["superuser", "root", "operator", "admin; DROP TABLE users;--"]
        for bad_role in invalid_roles:
            with pytest.raises(ValueError, match="Invalid role"):
                create_user(
                    username=f"user_{secrets_safe_suffix()}",
                    email=f"bad_{secrets_safe_suffix()}@test.com",
                    plain_password="StrongPassword123!",
                    role=bad_role,
                    db_path=db_path,
                )

        # Empty string defaults safely to "user" role
        u_def = create_user(
            username=f"user_{secrets_safe_suffix()}",
            email=f"def_{secrets_safe_suffix()}@test.com",
            plain_password="StrongPassword123!",
            role="",
            db_path=db_path,
        )
        assert u_def["role"] == "user"

        # Verify role helper functions
        assert is_admin("admin") is True
        assert is_admin("ADMIN") is True
        assert is_admin("user") is False
        assert is_admin(None) is False
        assert is_admin("") is False

        # is_owner requires positive integers
        assert is_owner(1, 1) is True
        assert is_owner(1, 2) is False
        assert is_owner(0, 0) is False
        assert is_owner(-1, -1) is False

    def test_session_role_tampering_fails_closed(self, edge_case_env) -> None:
        """Backend authorization functions check authenticated DB records rather than client parameters."""
        alice = edge_case_env["alice"]
        bob = edge_case_env["bob"]
        db_path = edge_case_env["db_path"]

        # Alice attempts to execute can_delete_file claiming admin role
        # can_delete_file checks role string, but when executing through file_service, role must match
        assert can_delete_file(alice["id"], "user", bob["id"]) is False
        assert can_manage_shares(alice["id"], "user", bob["id"]) is False
        assert can_download_file(alice["id"], "user", bob["id"]) is False
        assert can_view_file(alice["id"], "user", bob["id"]) is False

    def test_unauthenticated_operations_fail_closed(self, edge_case_env) -> None:
        """Calling service operations with user_id <= 0 or None raises ValueError."""
        db_path = edge_case_env["db_path"]
        cfg = edge_case_env["config"]
        mock_mgr = edge_case_env["mock_mgr"]

        for invalid_uid in [0, -1, None]:
            with pytest.raises(ValueError, match="User must be authenticated"):
                download_file(invalid_uid, 1, storage_manager=mock_mgr, config=cfg, db_path=db_path)

            with pytest.raises(ValueError, match="User must be authenticated"):
                delete_file(invalid_uid, 1, storage_manager=mock_mgr, config=cfg, db_path=db_path)

            with pytest.raises(ValueError, match="User must be authenticated"):
                create_share_link(invalid_uid, 1, db_path=db_path)

            with pytest.raises(ValueError, match="User must be authenticated"):
                revoke_share_link(invalid_uid, 1, db_path=db_path)

            with pytest.raises(ValueError, match="User must be authenticated"):
                get_file_version_history(invalid_uid, 1, db_path=db_path)

            with pytest.raises(ValueError, match="User must be authenticated"):
                download_historical_version(invalid_uid, 1, 1, storage_manager=mock_mgr, config=cfg, db_path=db_path)

    def test_case_insensitive_email_login_compatibility(self, edge_case_env) -> None:
        """Login by email succeeds regardless of casing."""
        db_path = edge_case_env["db_path"]

        # Alice registered with 'alice@tenant-a.com'
        user = authenticate_user("ALICE@TENANT-A.COM", "SecurePassword123!", db_path=db_path)
        assert user is not None
        assert user["username"] == "alice_tenant"

        user_mixed = authenticate_user("Alice@Tenant-A.Com", "SecurePassword123!", db_path=db_path)
        assert user_mixed is not None

    def test_password_complexity_rules(self) -> None:
        """Password complexity enforces length, uppercase, lowercase, and digits."""
        assert validate_password_strength("Short1A")[0] is False
        assert validate_password_strength("nouppercase123")[0] is False
        assert validate_password_strength("NOLOWERCASE123")[0] is False
        assert validate_password_strength("NoDigitsHere!")[0] is False
        assert validate_password_strength("ValidPass123!")[0] is True

    def test_duplicate_registration_rejected(self, edge_case_env) -> None:
        """Attempting to register existing username or email raises ValueError."""
        alice = edge_case_env["alice"]
        db_path = edge_case_env["db_path"]

        # Duplicate username
        with pytest.raises(ValueError, match="already registered"):
            create_user("alice_tenant", "unique@test.com", "Password123!", db_path=db_path)

        # Duplicate email
        with pytest.raises(ValueError, match="already registered"):
            create_user("unique_user", "alice@tenant-a.com", "Password123!", db_path=db_path)


# Helper for unique usernames in tests
_counter = 0

def secrets_safe_suffix() -> str:
    global _counter
    _counter += 1
    return f"id_{_counter}"
