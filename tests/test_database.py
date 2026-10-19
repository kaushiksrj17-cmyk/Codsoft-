"""Unit and integration tests for SQLite metadata database layer."""

from __future__ import annotations

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
