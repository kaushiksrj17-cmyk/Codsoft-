"""Unit and integration tests for SQLite metadata database layer."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import pytest
from src.database import get_connection, get_db_cursor, init_db


@pytest.mark.integration
class TestDatabaseSchemaAndInitialization:
    """Tests verifying database creation, schema tables, and constraints."""

    def test_schema_initialization_in_memory(self) -> None:
        """Verify init_db initializes all expected tables in an in-memory database."""
        conn = get_connection(":memory:")
        try:
            # Run schema initialization
            with conn:
                from src.database import SCHEMA_SQL
                conn.executescript(SCHEMA_SQL)

            # Query list of created tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row["name"] for row in cursor.fetchall()}

            expected_tables = {"users", "files", "file_versions", "file_shares", "activity_logs"}
            for table in expected_tables:
                assert table in tables, f"Expected table '{table}' was not created."
        finally:
            conn.close()

    def test_foreign_key_enforcement(self) -> None:
        """Verify that SQLite foreign keys reject inserting files for non-existent users."""
        conn = get_connection(":memory:")
        try:
            from src.database import SCHEMA_SQL
            with conn:
                conn.executescript(SCHEMA_SQL)

            cursor = conn.cursor()
            # Attempt to insert file with non-existent user_id = 9999
            with pytest.raises(sqlite3.IntegrityError):
                with conn:
                    cursor.execute(
                        """
                        INSERT INTO files (user_id, original_name, s3_key, s3_bucket, file_size_bytes)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (9999, "orphan.txt", "users/9999/files/orphan.txt", "test-bucket", 1024),
                    )
        finally:
            conn.close()

    def test_user_creation_and_retrieval(self) -> None:
        """Verify user creation with parameterized query and retrieval."""
        conn = get_connection(":memory:")
        try:
            from src.database import SCHEMA_SQL
            with conn:
                conn.executescript(SCHEMA_SQL)

            cursor = conn.cursor()
            with conn:
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role, storage_quota_bytes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("alex_cloud", "alex@example.com", "fake_hash", "user", 524288000),
                )
                user_id = cursor.lastrowid

            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            assert user is not None
            assert user["username"] == "alex_cloud"
            assert user["email"] == "alex@example.com"
            assert user["storage_quota_bytes"] == 524288000
            assert user["used_storage_bytes"] == 0
        finally:
            conn.close()

    def test_transaction_rollback_on_error(self) -> None:
        """Verify that an error inside a transaction rolls back uncommitted changes."""
        conn = get_connection(":memory:")
        try:
            from src.database import SCHEMA_SQL
            with conn:
                conn.executescript(SCHEMA_SQL)

            cursor = conn.cursor()
            with conn:
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, storage_quota_bytes) VALUES (?, ?, ?, ?)",
                    ("valid_user", "valid@example.com", "hash", 1000),
                )

            # Now attempt a block where an error occurs after an insert
            try:
                with conn:
                    cursor.execute(
                        "INSERT INTO users (username, email, password_hash, storage_quota_bytes) VALUES (?, ?, ?, ?)",
                        ("temporary_user", "temp@example.com", "hash", 1000),
                    )
                    # Trigger an error: duplicate email / syntax error
                    raise ValueError("Simulated operational failure")
            except ValueError:
                pass

            # Verify temporary_user was rolled back
            cursor.execute("SELECT * FROM users WHERE username = 'temporary_user'")
            assert cursor.fetchone() is None
            # Valid user should still exist
            cursor.execute("SELECT * FROM users WHERE username = 'valid_user'")
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_activity_logging_and_retrieval(self, tmp_path: Path) -> None:
        """Verify recording and querying audit logs through activity_logger."""
        from src.activity_logger import get_recent_activities, log_activity

        db_file = str(tmp_path / "activity_test.db")
        init_db(db_file)

        conn = get_connection(db_file)
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users (username, email, password_hash, storage_quota_bytes) VALUES (?, ?, ?, ?)",
                    ("audit_user", "audit@example.com", "hash", 1000000),
                )
                user_id = cur.lastrowid
        finally:
            conn.close()

        log_id = log_activity(
            action="FILE_UPLOAD",
            resource_type="file",
            user_id=user_id,
            resource_id="doc_101",
            details="Uploaded quarterly_report.pdf",
            ip_address="127.0.0.1",
            status="SUCCESS",
            db_path=db_file,
        )
        assert log_id > 0

        activities = get_recent_activities(user_id=user_id, limit=10, db_path=db_file)
        assert len(activities) == 1
        entry = activities[0]
        assert entry["action"] == "FILE_UPLOAD"
        assert entry["resource_id"] == "doc_101"
        assert entry["status"] == "SUCCESS"

    def test_file_versioning_lifecycle(self, tmp_path: Path) -> None:
        """Verify sequential versioning and listing through file_versions module."""
        from src.file_versions import (
            format_version_label,
            get_next_version_number,
            list_file_versions,
            record_file_version,
        )

        assert get_next_version_number([]) == 1
        assert get_next_version_number([1, 2, 3]) == 4
        assert format_version_label(1) == "v1"
        assert format_version_label(3) == "v3"

        db_file = str(tmp_path / "version_test.db")
        init_db(db_file)

        # Create parent user and file
        conn = get_connection(db_file)
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users (username, email, password_hash, storage_quota_bytes) VALUES (?, ?, ?, ?)",
                    ("version_user", "vu@example.com", "hash", 1000000),
                )
                user_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO files (user_id, original_name, s3_key, s3_bucket, file_size_bytes) VALUES (?, ?, ?, ?, ?)",
                    (user_id, "doc.pdf", "users/1/files/doc.pdf", "test-bucket", 1024),
                )
                file_id = cur.lastrowid
        finally:
            conn.close()

        v1_id = record_file_version(
            file_id=file_id,
            version_number=1,
            s3_key="users/1/files/v1/doc.pdf",
            file_size_bytes=1024,
            checksum_sha256="abc123sha",
            db_path=db_file,
        )
        assert v1_id > 0

        v2_id = record_file_version(
            file_id=file_id,
            version_number=2,
            s3_key="users/1/files/v2/doc.pdf",
            file_size_bytes=2048,
            checksum_sha256="def456sha",
            db_path=db_file,
        )
        assert v2_id > 0

        versions = list_file_versions(file_id=file_id, db_path=db_file)
        assert len(versions) == 2
        assert versions[0]["version_number"] == 2
        assert versions[1]["version_number"] == 1

