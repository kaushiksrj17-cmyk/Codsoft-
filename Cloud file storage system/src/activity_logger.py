"""Audit trail and activity logging service.

Records system events, user actions (uploads, downloads, shares, deletions),
and security alerts to the metadata database.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.database import get_db_cursor


def log_activity(
    action: str,
    resource_type: str,
    user_id: Optional[int] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    status: str = "SUCCESS",
    db_path: Optional[str] = None,
) -> int:
    """Record an audit entry into the activity_logs table using safe parameterized queries."""
    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            INSERT INTO activity_logs (user_id, action, resource_type, resource_id, details, ip_address, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, action, resource_type, resource_id, details, ip_address, status),
        )
        return cursor.lastrowid or 0


def get_recent_activities(
    user_id: Optional[int] = None,
    limit: int = 50,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve recent activity logs, optionally filtered by user ID."""
    with get_db_cursor(db_path) as cursor:
        if user_id is not None:
            cursor.execute(
                """
                SELECT id, user_id, action, resource_type, resource_id, details, ip_address, status, created_at
                FROM activity_logs
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT id, user_id, action, resource_type, resource_id, details, ip_address, status, created_at
                FROM activity_logs
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
