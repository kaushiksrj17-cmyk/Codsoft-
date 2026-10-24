"""Secure file sharing, access token generation, and expiration checking.

Implements cryptographically random token generation and expiration validation
for time-limited, role-restricted public and peer share links.
Coordinates share link persistence, access verification, presigned URL distribution,
and owner revocation with audit logging.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.activity_logger import log_activity
from src.aws_storage import S3StorageManager
from src.config import AppConfig, get_config
from src.database import get_db_cursor
from src.permissions import SharePermission, can_manage_shares
from src.storage_quota import format_bytes

logger = logging.getLogger(__name__)


def generate_share_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure URL-safe random token."""
    return secrets.token_urlsafe(nbytes)


def calculate_expiration_datetime(hours: int) -> str:
    """Calculate future ISO-8601 UTC timestamp based on an expiry duration in hours."""
    if hours <= 0:
        raise ValueError("Expiration duration must be a positive integer.")
    expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
    return expiry.isoformat()


def is_share_expired(expires_at_iso: Optional[str]) -> bool:
    """Check whether a share link's expiration timestamp has passed.

    If expires_at_iso is None, the share has no expiration and is permanent until revoked.
    """
    if not expires_at_iso:
        return False

    try:
        # Support ISO 8601 with or without Z/offset
        exp_dt = datetime.fromisoformat(expires_at_iso)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        return now >= exp_dt
    except (ValueError, TypeError):
        # Malformed expiration timestamps fail closed (treated as expired)
        return True


def validate_share_access(share_record: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate whether a share link is currently valid and active."""
    if not share_record:
        return False, "Share link does not exist."

    if bool(share_record.get("is_revoked", False)):
        return False, "This share link has been revoked by the owner."

    expires_at = share_record.get("expires_at")
    if is_share_expired(expires_at):
        return False, "This share link has expired."

    return True, "Share link is valid and active."


def build_share_url(token: str, base_url: str = "http://localhost:8501") -> str:
    """Construct user-facing share URL."""
    return f"{base_url.rstrip('/')}/Shared_Files?share={token}"


def create_share_link(
    user_id: int,
    file_id: int,
    user_role: str = "user",
    permission_level: str = "view",
    expires_in_hours: Optional[int] = 24,
    shared_with_email: Optional[str] = None,
    client_ip: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a secure, time-limited share link for an active file.

    Enforces ownership/RBAC permissions, validates input, inserts a new record
    in file_shares using parameterized SQL, and records the audit log.
    """
    if not user_id or user_id <= 0:
        raise ValueError("User must be authenticated to create a share link.")

    normalized_perm = permission_level.strip().lower()
    valid_perms = {SharePermission.VIEW.value, SharePermission.DOWNLOAD.value}
    if normalized_perm not in valid_perms:
        raise ValueError(
            f"Invalid permission level '{permission_level}'. Supported: 'view', 'download'."
        )

    # Validate file existence and deletion status
    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, user_id, original_name, is_deleted
            FROM files
            WHERE id = ?
            """,
            (file_id,),
        )
        file_row = cursor.fetchone()

    if not file_row:
        raise ValueError(f"File with ID {file_id} not found.")

    if file_row["is_deleted"] == 1:
        raise ValueError(
            f"File '{file_row['original_name']}' has been deleted and cannot be shared."
        )

    # Verify authorization
    if not can_manage_shares(
        user_id=user_id, user_role=user_role, owner_id=file_row["user_id"]
    ):
        try:
            log_activity(
                action="SHARE_CREATE",
                resource_type="file_share",
                user_id=user_id,
                resource_id=str(file_id),
                details=f"Unauthorized share creation attempt for file {file_id}",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise PermissionError(
            f"User {user_id} is not authorized to create share links for file {file_id}."
        )

    # Compute expiration timestamp
    if expires_in_hours is not None:
        expires_at = calculate_expiration_datetime(expires_in_hours)
    else:
        expires_at = None

    clean_email = (
        shared_with_email.strip().lower()
        if shared_with_email and shared_with_email.strip()
        else None
    )

    token = generate_share_token(32)

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            INSERT INTO file_shares (file_id, shared_by_user_id, shared_with_email, share_token, permission_level, expires_at, access_count, is_revoked)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (file_id, user_id, clean_email, token, normalized_perm, expires_at),
        )
        share_id = cursor.lastrowid
        if not share_id:
            raise RuntimeError("Failed to retrieve share record ID.")

    expiry_desc = f"expires in {expires_in_hours}h" if expires_in_hours else "permanent"
    recipient_desc = f" with {clean_email}" if clean_email else ""
    try:
        log_activity(
            action="SHARE_CREATE",
            resource_type="file_share",
            user_id=user_id,
            resource_id=str(file_id),
            details=f"Created {normalized_perm} share link for '{file_row['original_name']}' ({expiry_desc}{recipient_desc})",
            ip_address=client_ip,
            status="SUCCESS",
            db_path=db_path,
        )
    except Exception:
        pass

    return {
        "id": share_id,
        "file_id": file_id,
        "filename": file_row["original_name"],
        "shared_by_user_id": user_id,
        "shared_with_email": clean_email,
        "share_token": token,
        "permission_level": normalized_perm,
        "expires_at": expires_at,
        "access_count": 0,
        "is_revoked": 0,
        "share_url": build_share_url(token),
    }


def get_share_by_token(
    share_token: str, db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve full share details joined with file and owner information by token."""
    if not share_token or not isinstance(share_token, str):
        return None

    cleaned_token = share_token.strip()
    if not cleaned_token:
        return None

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT s.id, s.file_id, s.shared_by_user_id, s.shared_with_email, s.share_token,
                   s.permission_level, s.expires_at, s.access_count, s.is_revoked, s.created_at,
                   f.original_name as filename, f.file_size_bytes, f.content_type, f.checksum_sha256,
                   f.s3_key, f.s3_bucket, f.is_deleted as file_is_deleted,
                   u.username as owner_username, u.email as owner_email
            FROM file_shares s
            JOIN files f ON s.file_id = f.id
            JOIN users u ON s.shared_by_user_id = u.id
            WHERE s.share_token = ?
            """,
            (cleaned_token,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def access_shared_file(
    share_token: str,
    recipient_user_id: Optional[int] = None,
    recipient_email: Optional[str] = None,
    storage_manager: Optional[Any] = None,
    config: Optional[AppConfig] = None,
    client_ip: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Access and validate a shared file link, enforcing permissions and recording access.

    If permission level is 'download', generates a short-lived presigned S3 download URL.
    Does not expose internal S3 keys or credentials.
    """
    share = get_share_by_token(share_token, db_path=db_path)
    if not share:
        try:
            log_activity(
                action="SHARE_ACCESS",
                resource_type="file_share",
                user_id=recipient_user_id,
                resource_id=(share_token[:8] + "...") if share_token else "none",
                details="Access attempt with invalid or nonexistent share token",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise ValueError("Invalid share link or token does not exist.")

    file_id = share["file_id"]
    filename = share["filename"]

    if bool(share["is_revoked"]):
        try:
            log_activity(
                action="SHARE_ACCESS",
                resource_type="file_share",
                user_id=recipient_user_id,
                resource_id=str(file_id),
                details=f"Access attempt to revoked share link for '{filename}'",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise PermissionError("This share link has been revoked by the owner.")

    if is_share_expired(share["expires_at"]):
        try:
            log_activity(
                action="SHARE_ACCESS",
                resource_type="file_share",
                user_id=recipient_user_id,
                resource_id=str(file_id),
                details=f"Access attempt to expired share link for '{filename}'",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise ValueError("This share link has expired.")

    if share["file_is_deleted"] == 1:
        try:
            log_activity(
                action="SHARE_ACCESS",
                resource_type="file_share",
                user_id=recipient_user_id,
                resource_id=str(file_id),
                details=f"Access attempt to deleted file '{filename}'",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise FileNotFoundError("The shared file has been deleted and is no longer available.")

    # Verify recipient restriction if share was targeted to a specific email
    if share["shared_with_email"]:
        req_email = recipient_email.strip().lower() if recipient_email else None
        target_email = share["shared_with_email"].strip().lower()
        if not req_email or not secrets.compare_digest(req_email, target_email):
            try:
                log_activity(
                    action="SHARE_ACCESS",
                    resource_type="file_share",
                    user_id=recipient_user_id,
                    resource_id=str(file_id),
                    details=f"Unauthorized recipient access attempt for '{filename}' (restricted to {target_email})",
                    ip_address=client_ip,
                    status="FAILED",
                    db_path=db_path,
                )
            except Exception:
                pass
            raise PermissionError(f"This share link is restricted to {target_email}.")

    # Atomically increment access counter
    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            "UPDATE file_shares SET access_count = access_count + 1 WHERE id = ?",
            (share["id"],),
        )

    download_url: Optional[str] = None
    can_download = share["permission_level"] in (
        SharePermission.DOWNLOAD.value,
        SharePermission.EDIT.value,
    )

    if can_download:
        cfg = config or get_config()
        mgr = storage_manager or S3StorageManager(cfg)
        download_url = mgr.generate_presigned_download_url(
            share["s3_key"], expires_in_seconds=300
        )

    try:
        log_activity(
            action="SHARE_ACCESS",
            resource_type="file_share",
            user_id=recipient_user_id,
            resource_id=str(file_id),
            details=f"Accessed shared file '{filename}' ({share['permission_level']} access)",
            ip_address=client_ip,
            status="SUCCESS",
            db_path=db_path,
        )
    except Exception:
        pass

    return {
        "share_id": share["id"],
        "file_id": file_id,
        "filename": filename,
        "file_size_bytes": share["file_size_bytes"],
        "formatted_size": format_bytes(share["file_size_bytes"]),
        "content_type": share["content_type"],
        "checksum_sha256": share["checksum_sha256"],
        "owner_username": share["owner_username"],
        "permission_level": share["permission_level"],
        "can_download": can_download,
        "download_url": download_url,
        "expires_at": share["expires_at"],
        "access_count": share["access_count"] + 1,
        "shared_with_email": share["shared_with_email"],
        "created_at": share["created_at"],
    }


def revoke_share_link(
    user_id: int,
    share_id: int,
    user_role: str = "user",
    client_ip: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Revoke an active share link immediately.

    Only the file owner or an administrator can revoke a share.
    Does not delete audit history.
    """
    if not user_id or user_id <= 0:
        raise ValueError("User must be authenticated to revoke a share link.")

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, file_id, shared_by_user_id, is_revoked
            FROM file_shares
            WHERE id = ?
            """,
            (share_id,),
        )
        share_row = cursor.fetchone()

    if not share_row:
        raise ValueError(f"Share link with ID {share_id} not found.")

    share = dict(share_row)

    if not can_manage_shares(
        user_id=user_id, user_role=user_role, owner_id=share["shared_by_user_id"]
    ):
        try:
            log_activity(
                action="SHARE_REVOKE",
                resource_type="file_share",
                user_id=user_id,
                resource_id=str(share_id),
                details=f"Unauthorized revocation attempt for share {share_id}",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise PermissionError(
            f"User {user_id} is not authorized to revoke share link {share_id}."
        )

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            "UPDATE file_shares SET is_revoked = 1 WHERE id = ?",
            (share_id,),
        )

    try:
        log_activity(
            action="SHARE_REVOKE",
            resource_type="file_share",
            user_id=user_id,
            resource_id=str(share_id),
            details=f"Revoked share link {share_id} for file ID {share['file_id']}",
            ip_address=client_ip,
            status="SUCCESS",
            db_path=db_path,
        )
    except Exception:
        pass

    return {
        "success": True,
        "share_id": share_id,
        "file_id": share["file_id"],
        "message": "Share link revoked successfully.",
    }


def list_shares_by_user(
    user_id: int,
    user_role: str = "user",
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all file share records created by the given user (or all if admin)."""
    from src.permissions import is_admin

    sql = """
        SELECT s.id, s.file_id, s.shared_by_user_id, s.shared_with_email, s.share_token,
               s.permission_level, s.expires_at, s.access_count, s.is_revoked, s.created_at,
               f.original_name as filename, f.file_size_bytes, f.is_deleted as file_is_deleted,
               u.username as owner_username
        FROM file_shares s
        JOIN files f ON s.file_id = f.id
        JOIN users u ON s.shared_by_user_id = u.id
    """
    params: List[Any] = []
    if not is_admin(user_role):
        sql += " WHERE s.shared_by_user_id = ?"
        params.append(user_id)

    sql += " ORDER BY s.created_at DESC, s.id DESC"

    with get_db_cursor(db_path) as cursor:
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

    results: List[Dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["formatted_size"] = format_bytes(item["file_size_bytes"])
        item["share_url"] = build_share_url(item["share_token"])

        if item["is_revoked"] == 1:
            item["status"] = "Revoked"
        elif is_share_expired(item["expires_at"]):
            item["status"] = "Expired"
        elif item["file_is_deleted"] == 1:
            item["status"] = "File Deleted"
        else:
            item["status"] = "Active"

        results.append(item)

    return results


def list_shares_shared_with_email(
    email: Optional[str],
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List share records specifically targeted to the given user email."""
    if not email or not isinstance(email, str) or not email.strip():
        return []

    sql = """
        SELECT s.id, s.file_id, s.shared_by_user_id, s.shared_with_email, s.share_token,
               s.permission_level, s.expires_at, s.access_count, s.is_revoked, s.created_at,
               f.original_name as filename, f.file_size_bytes, f.is_deleted as file_is_deleted,
               u.username as owner_username
        FROM file_shares s
        JOIN files f ON s.file_id = f.id
        JOIN users u ON s.shared_by_user_id = u.id
        WHERE LOWER(s.shared_with_email) = LOWER(?)
        ORDER BY s.created_at DESC, s.id DESC
    """
    with get_db_cursor(db_path) as cursor:
        cursor.execute(sql, (email.strip().lower(),))
        rows = cursor.fetchall()

    results: List[Dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["formatted_size"] = format_bytes(item["file_size_bytes"])
        item["share_url"] = build_share_url(item["share_token"])

        if item["is_revoked"] == 1:
            item["status"] = "Revoked"
        elif is_share_expired(item["expires_at"]):
            item["status"] = "Expired"
        elif item["file_is_deleted"] == 1:
            item["status"] = "File Deleted"
        else:
            item["status"] = "Active"

        results.append(item)

    return results


def get_sharing_metrics(
    user_id: int,
    user_role: str = "user",
    email: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate aggregate telemetry metrics for the sharing dashboard."""
    shares_created = list_shares_by_user(user_id, user_role=user_role, db_path=db_path)
    shares_received = (
        list_shares_shared_with_email(email, db_path=db_path) if email else []
    )

    active_created = sum(1 for s in shares_created if s["status"] == "Active")
    active_received = sum(1 for s in shares_received if s["status"] == "Active")
    revoked_or_expired = sum(
        1 for s in shares_created if s["status"] in ("Revoked", "Expired")
    )

    return {
        "active_shares_count": active_created,
        "received_shares_count": active_received,
        "total_created_count": len(shares_created),
        "revoked_or_expired_count": revoked_or_expired,
    }
