"""File versioning logic and metadata tracking.

Supports tracking multiple iterations of uploaded files, retaining previous
versions in S3, and managing version numbers in the metadata store.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.database import get_db_cursor


def get_next_version_number(existing_versions: List[int]) -> int:
    """Determine the next sequential version number given a list of existing version numbers."""
    if not existing_versions:
        return 1
    return max(existing_versions) + 1


def format_version_label(version_number: int) -> str:
    """Format an integer version number as a display label (e.g., 'v1', 'v2')."""
    return f"v{max(1, version_number)}"


def record_file_version(
    file_id: int,
    version_number: int,
    s3_key: str,
    file_size_bytes: int,
    s3_version_id: Optional[str] = None,
    checksum_sha256: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a record of a file version into the file_versions table."""
    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            INSERT INTO file_versions (file_id, version_number, s3_version_id, s3_key, file_size_bytes, checksum_sha256)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (file_id, version_number, s3_version_id, s3_key, file_size_bytes, checksum_sha256),
        )
        return cursor.lastrowid or 0


def list_file_versions(file_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all recorded versions for a given file ID in descending chronological order."""
    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, file_id, version_number, s3_version_id, s3_key, file_size_bytes, checksum_sha256, created_at
            FROM file_versions
            WHERE file_id = ?
            ORDER BY version_number DESC
            """,
            (file_id,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
