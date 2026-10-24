"""File upload, storage coordination, metadata persistence, and file retrieval services.

Integrates S3 object storage with SQLite metadata, enforcing strict input validation,
storage quota limits, tenant isolation, audit logging, and transactional compensation.
"""

from __future__ import annotations

import logging
from typing import Any, BinaryIO, Dict, List, Optional

from src.activity_logger import log_activity
from src.auth import get_user_by_id
from src.aws_storage import S3StorageManager
from src.config import AppConfig, get_config
from src.database import get_db_cursor
from src.file_validation import (
    compute_sha256,
    get_content_type,
    sanitize_filename,
    validate_file_extension,
    validate_file_size,
    validate_filename,
)
from src.file_versions import get_next_version_number, list_file_versions, record_file_version
from src.permissions import can_delete_file, can_download_file, can_view_file
from src.storage_quota import (
    bytes_to_mb,
    calculate_usage_percentage,
    check_quota_availability,
    format_bytes,
    get_remaining_quota_bytes,
)

logger = logging.getLogger(__name__)

# File extension categorization mapping for UI filters
CATEGORY_EXTENSIONS: Dict[str, set[str]] = {
    "Documents": {".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt", ".xlsx", ".xls", ".pptx", ".csv", ".json", ".xml", ".md"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff"},
    "Archives": {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz"},
    "Media": {".mp3", ".wav", ".ogg", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4a"},
}


def get_file_category(filename: str) -> str:
    """Classify a filename into a UI category (Documents, Images, Archives, Media, or Other)."""
    import os
    ext = os.path.splitext(filename.lower())[1]
    for category, extensions in CATEGORY_EXTENSIONS.items():
        if ext in extensions:
            return category
    return "Other"


def upload_file(
    user_id: int,
    file_bytes: bytes | BinaryIO,
    filename: str,
    storage_manager: Optional[S3StorageManager] = None,
    config: Optional[AppConfig] = None,
    db_path: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the end-to-end file upload workflow with pre-flight checks and rollback.

    Workflow:
      1. Filename validation and sanitization.
      2. File extension blacklist / whitelist validation.
      3. Size limit boundary check.
      4. User account status & quota availability check.
      5. SHA-256 data integrity checksum calculation.
      6. Duplicate / existing version resolution.
      7. Amazon S3 encrypted upload (AES-256).
      8. Metadata insertion in SQLite and quota deduction.
      9. Audit trail logging.
      10. Compensating S3 object cleanup if database persistence fails.
    """
    cfg = config or get_config()
    mgr = storage_manager or S3StorageManager(cfg)

    # 1. Filename validation
    is_valid_fn, fn_msg = validate_filename(filename)
    if not is_valid_fn:
        raise ValueError(f"Invalid filename: {fn_msg}")

    clean_filename = sanitize_filename(filename)

    # 2. File extension validation
    is_valid_ext, ext_msg = validate_file_extension(clean_filename)
    if not is_valid_ext:
        raise ValueError(f"Security Policy: {ext_msg}")

    # Read binary bytes if stream
    if isinstance(file_bytes, bytes):
        raw_bytes = file_bytes
    else:
        raw_bytes = file_bytes.read()

    size_bytes = len(raw_bytes)

    # 3. Size boundary check
    is_valid_sz, sz_msg = validate_file_size(size_bytes, cfg.max_file_size_bytes)
    if not is_valid_sz:
        raise ValueError(sz_msg)

    # 4. Check user existence and available quota
    user = get_user_by_id(user_id, db_path=db_path)
    if not user:
        raise ValueError(f"User account with ID {user_id} does not exist.")

    if not user.get("is_active", True):
        raise ValueError("User account is suspended or inactive.")

    is_quota_ok, quota_msg = check_quota_availability(
        user["used_storage_bytes"], user["storage_quota_bytes"], size_bytes
    )
    if not is_quota_ok:
        raise ValueError(quota_msg)

    # 5. Integrity checksum
    checksum = compute_sha256(raw_bytes)

    # 6. Check for duplicate filename or existing versions
    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, original_name, s3_key, file_size_bytes, checksum_sha256
            FROM files
            WHERE user_id = ? AND original_name = ? AND is_deleted = 0
            """,
            (user_id, clean_filename),
        )
        existing_file = cursor.fetchone()

    is_new_version = False
    parent_file_id: Optional[int] = None
    next_ver = 1

    if existing_file:
        if existing_file["checksum_sha256"] == checksum:
            raise ValueError(
                f"File '{clean_filename}' with identical SHA-256 checksum is already stored in your cloud files."
            )

        # Existing file with different content -> create new version
        is_new_version = True
        parent_file_id = existing_file["id"]
        with get_db_cursor(db_path) as cursor:
            cursor.execute(
                "SELECT version_number FROM file_versions WHERE file_id = ?",
                (parent_file_id,),
            )
            version_numbers = [row["version_number"] for row in cursor.fetchall()]

        next_ver = get_next_version_number(version_numbers)
        s3_key = mgr.build_s3_key(user_id, clean_filename, version=next_ver)
    else:
        # Initial version of a new file
        s3_key = mgr.build_s3_key(user_id, clean_filename)

    # 7. S3 Ingestion
    content_type = get_content_type(clean_filename)
    metadata = {
        "user_id": str(user_id),
        "original_name": clean_filename,
        "sha256": checksum,
        "version": str(next_ver),
    }

    try:
        mgr.upload_file_bytes(
            file_bytes=raw_bytes,
            s3_key=s3_key,
            content_type=content_type,
            metadata=metadata,
        )
    except Exception as s3_err:
        logger.error(f"S3 upload failed for key {s3_key}: {s3_err}")
        try:
            log_activity(
                action="FILE_UPLOAD",
                resource_type="file",
                user_id=user_id,
                resource_id=clean_filename,
                details=f"S3 upload failed: {type(s3_err).__name__}",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise RuntimeError(f"Cloud storage upload error: {s3_err}")

    # 8. Database Persistence with compensating rollback
    try:
        with get_db_cursor(db_path) as cursor:
            if not is_new_version:
                cursor.execute(
                    """
                    INSERT INTO files (user_id, original_name, s3_key, s3_bucket, file_size_bytes, content_type, checksum_sha256)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, clean_filename, s3_key, cfg.s3_bucket_name, size_bytes, content_type, checksum),
                )
                file_id = cursor.lastrowid
                if not file_id:
                    raise RuntimeError("Failed to retrieve file record ID.")
            else:
                file_id = parent_file_id
                cursor.execute(
                    """
                    UPDATE files
                    SET s3_key = ?, file_size_bytes = ?, content_type = ?, checksum_sha256 = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (s3_key, size_bytes, content_type, checksum, file_id),
                )

            # Record version history within active transaction
            cursor.execute(
                """
                INSERT INTO file_versions (file_id, version_number, s3_version_id, s3_key, file_size_bytes, checksum_sha256)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_id, next_ver, None, s3_key, size_bytes, checksum),
            )

            # Update tenant storage usage
            cursor.execute(
                """
                UPDATE users
                SET used_storage_bytes = used_storage_bytes + ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (size_bytes, user_id),
            )

        # 9. Log successful activity
        log_activity(
            action="FILE_UPLOAD",
            resource_type="file",
            user_id=user_id,
            resource_id=str(file_id),
            details=f"Uploaded '{clean_filename}' (v{next_ver}, {format_bytes(size_bytes)})",
            ip_address=client_ip,
            status="SUCCESS",
            db_path=db_path,
        )

    except Exception as db_err:
        logger.error(f"Metadata persistence failed after S3 upload. Rolling back S3 object {s3_key}: {db_err}")
        # Compensating cleanup: delete newly created S3 object
        try:
            mgr.delete_object(s3_key)
        except Exception as clean_err:
            logger.critical(f"Failed to clean up orphaned S3 object {s3_key}: {clean_err}")

        try:
            log_activity(
                action="FILE_UPLOAD",
                resource_type="file",
                user_id=user_id,
                resource_id=clean_filename,
                details=f"Database metadata failure. S3 rollback executed: {type(db_err).__name__}",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass

        raise RuntimeError(f"Database error during metadata recording: {db_err}")

    return {
        "file_id": file_id,
        "filename": clean_filename,
        "s3_key": s3_key,
        "size_bytes": size_bytes,
        "formatted_size": format_bytes(size_bytes),
        "version": next_ver,
        "checksum": checksum,
        "content_type": content_type,
        "category": get_file_category(clean_filename),
    }


def list_user_files(
    user_id: int,
    user_role: str = "user",
    search_query: Optional[str] = None,
    filter_category: Optional[str] = None,
    sort_by: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve file metadata records for a user with strict tenant isolation and filtering."""
    from src.permissions import is_admin

    sql = """
        SELECT f.id, f.user_id, f.original_name, f.s3_key, f.s3_bucket, f.file_size_bytes,
               f.content_type, f.checksum_sha256, f.created_at, f.updated_at,
               u.username as owner_username,
               COALESCE((SELECT MAX(fv.version_number) FROM file_versions fv WHERE fv.file_id = f.id), 1) as current_version
        FROM files f
        JOIN users u ON f.user_id = u.id
        WHERE f.is_deleted = 0
    """
    params: List[Any] = []

    # Ownership enforcement: Non-admins can strictly only see their own files
    if not is_admin(user_role):
        sql += " AND f.user_id = ?"
        params.append(user_id)

    # Search filter
    if search_query and search_query.strip():
        sql += " AND f.original_name LIKE ?"
        params.append(f"%{search_query.strip()}%")

    # Ordering
    if sort_by == "Name (A-Z)":
        sql += " ORDER BY f.original_name ASC"
    elif sort_by == "Name (Z-A)":
        sql += " ORDER BY f.original_name DESC"
    elif sort_by == "Size (Largest)":
        sql += " ORDER BY f.file_size_bytes DESC"
    elif sort_by == "Size (Smallest)":
        sql += " ORDER BY f.file_size_bytes ASC"
    elif sort_by == "Date (Oldest)":
        sql += " ORDER BY f.created_at ASC"
    else:
        # Default: Date (Newest)
        sql += " ORDER BY f.created_at DESC, f.id DESC"

    with get_db_cursor(db_path) as cursor:
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

    files = []
    for row in rows:
        item = dict(row)
        item["formatted_size"] = format_bytes(item["file_size_bytes"])
        item["category"] = get_file_category(item["original_name"])
        item["version_label"] = f"v{item['current_version']}"

        # Category filtering post-query to maintain flexibility
        if filter_category and filter_category != "All Types":
            if item["category"] != filter_category:
                continue

        files.append(item)

    return files


def get_user_quota_info(user_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve authoritative storage quota details and calculation metrics for a user."""
    user = get_user_by_id(user_id, db_path=db_path)
    if not user:
        return {
            "used_bytes": 0,
            "quota_bytes": 0,
            "remaining_bytes": 0,
            "used_mb": 0.0,
            "quota_mb": 0.0,
            "remaining_mb": 0.0,
            "usage_percentage": 0.0,
            "formatted_used": "0 B",
            "formatted_quota": "0 B",
            "formatted_remaining": "0 B",
        }

    used_bytes = user["used_storage_bytes"]
    quota_bytes = user["storage_quota_bytes"]
    remaining_bytes = get_remaining_quota_bytes(used_bytes, quota_bytes)

    return {
        "used_bytes": used_bytes,
        "quota_bytes": quota_bytes,
        "remaining_bytes": remaining_bytes,
        "used_mb": round(bytes_to_mb(used_bytes), 2),
        "quota_mb": round(bytes_to_mb(quota_bytes), 2),
        "remaining_mb": round(bytes_to_mb(remaining_bytes), 2),
        "usage_percentage": calculate_usage_percentage(used_bytes, quota_bytes),
        "formatted_used": format_bytes(used_bytes),
        "formatted_quota": format_bytes(quota_bytes),
        "formatted_remaining": format_bytes(remaining_bytes),
    }


def download_file(
    user_id: int,
    file_id: int,
    user_role: str = "user",
    expires_in_seconds: int = 300,
    storage_manager: Optional[S3StorageManager] = None,
    config: Optional[AppConfig] = None,
    db_path: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a secure, time-limited presigned S3 download URL for an active file.

    Enforces authentication, ownership/RBAC permissions, deletion status, and storage presence.
    """
    if not user_id or user_id <= 0:
        raise ValueError("User must be authenticated to download files.")

    cfg = config or get_config()
    mgr = storage_manager or S3StorageManager(cfg)

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, user_id, original_name, s3_key, s3_bucket, file_size_bytes, content_type, checksum_sha256, is_deleted
            FROM files
            WHERE id = ?
            """,
            (file_id,),
        )
        row = cursor.fetchone()

    if not row:
        raise ValueError(f"File with ID {file_id} not found.")

    file_rec = dict(row)

    if file_rec["is_deleted"] == 1:
        raise ValueError(f"File '{file_rec['original_name']}' has been deleted and cannot be downloaded.")

    if not can_download_file(user_id=user_id, user_role=user_role, owner_id=file_rec["user_id"]):
        try:
            log_activity(
                action="FILE_DOWNLOAD",
                resource_type="file",
                user_id=user_id,
                resource_id=str(file_id),
                details=f"Unauthorized download attempt for '{file_rec['original_name']}'. Permission denied.",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise PermissionError(f"User {user_id} does not have download permissions for file {file_id}.")

    s3_key = file_rec["s3_key"]

    if hasattr(mgr, "object_exists") and not mgr.object_exists(s3_key):
        raise FileNotFoundError(f"Storage object for file '{file_rec['original_name']}' not found in S3 bucket.")

    try:
        url = mgr.generate_presigned_download_url(s3_key, expires_in_seconds=expires_in_seconds)
    except Exception as presign_err:
        logger.error(f"Failed to generate presigned download URL for file_id {file_id}: {type(presign_err).__name__}")
        raise RuntimeError(f"Failed to generate download URL: {presign_err}")

    # Audit log (safe: never logs presigned URL or credentials)
    try:
        log_activity(
            action="FILE_DOWNLOAD",
            resource_type="file",
            user_id=user_id,
            resource_id=str(file_id),
            details=f"Generated download link for '{file_rec['original_name']}'",
            ip_address=client_ip,
            status="SUCCESS",
            db_path=db_path,
        )
    except Exception:
        pass

    return {
        "file_id": file_id,
        "filename": file_rec["original_name"],
        "s3_key": s3_key,
        "download_url": url,
        "expires_in_seconds": expires_in_seconds,
        "file_size_bytes": file_rec["file_size_bytes"],
        "formatted_size": format_bytes(file_rec["file_size_bytes"]),
        "content_type": file_rec["content_type"],
        "checksum_sha256": file_rec["checksum_sha256"],
    }


def delete_file(
    user_id: int,
    file_id: int,
    user_role: str = "user",
    storage_manager: Optional[S3StorageManager] = None,
    config: Optional[AppConfig] = None,
    db_path: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute safe soft-deletion of a file with storage quota recovery and audit logging.

    Prevents deleted files from appearing in active views or being downloaded.
    Idempotent: repeating deletion does not deduct storage quota twice.
    """
    if not user_id or user_id <= 0:
        raise ValueError("User must be authenticated to delete files.")

    cfg = config or get_config()
    mgr = storage_manager or S3StorageManager(cfg)

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, user_id, original_name, s3_key, file_size_bytes, is_deleted
            FROM files
            WHERE id = ?
            """,
            (file_id,),
        )
        row = cursor.fetchone()

    if not row:
        raise ValueError(f"File with ID {file_id} not found.")

    file_rec = dict(row)

    if not can_delete_file(user_id=user_id, user_role=user_role, owner_id=file_rec["user_id"]):
        try:
            log_activity(
                action="FILE_DELETE",
                resource_type="file",
                user_id=user_id,
                resource_id=str(file_id),
                details=f"Unauthorized deletion attempt for '{file_rec['original_name']}'. Permission denied.",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise PermissionError(f"User {user_id} is not authorized to delete file {file_id}.")

    # Idempotent: already deleted
    if file_rec["is_deleted"] == 1:
        return {
            "success": True,
            "file_id": file_id,
            "filename": file_rec["original_name"],
            "already_deleted": True,
            "freed_bytes": 0,
            "formatted_freed": "0 B",
            "message": f"File '{file_rec['original_name']}' is already deleted.",
        }

    # Calculate total storage bytes used by this file across versions
    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            "SELECT COALESCE(SUM(file_size_bytes), 0) FROM file_versions WHERE file_id = ?",
            (file_id,),
        )
        sum_row = cursor.fetchone()
        ver_total = sum_row[0] if sum_row else 0

    freed_bytes = ver_total if ver_total > 0 else file_rec["file_size_bytes"]

    # Delete the active S3 object (preserve historical version objects for retention compliance)
    active_s3_key = file_rec["s3_key"]
    try:
        mgr.delete_object(active_s3_key)
    except Exception as s3_err:
        logger.error(f"S3 deletion failed for {active_s3_key}: {type(s3_err).__name__}")
        try:
            log_activity(
                action="FILE_DELETE",
                resource_type="file",
                user_id=user_id,
                resource_id=str(file_id),
                details=f"S3 object deletion failed: {type(s3_err).__name__}",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise RuntimeError(f"Cloud storage deletion error: {s3_err}")

    # Mark soft-deleted and update user quota in a single atomic transaction
    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            UPDATE files
            SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (file_id,),
        )
        cursor.execute(
            """
            UPDATE users
            SET used_storage_bytes = MAX(0, used_storage_bytes - ?), updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (freed_bytes, file_rec["user_id"]),
        )

    # Log successful audit trail
    try:
        log_activity(
            action="FILE_DELETE",
            resource_type="file",
            user_id=user_id,
            resource_id=str(file_id),
            details=f"Soft-deleted file '{file_rec['original_name']}' (freed {format_bytes(freed_bytes)})",
            ip_address=client_ip,
            status="SUCCESS",
            db_path=db_path,
        )
    except Exception:
        pass

    return {
        "success": True,
        "file_id": file_id,
        "filename": file_rec["original_name"],
        "already_deleted": False,
        "freed_bytes": freed_bytes,
        "formatted_freed": format_bytes(freed_bytes),
        "message": f"Successfully deleted '{file_rec['original_name']}'.",
    }


def get_file_version_history(
    user_id: int,
    file_id: int,
    user_role: str = "user",
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve full version history metadata for a file, enforcing access control."""
    if not user_id or user_id <= 0:
        raise ValueError("User must be authenticated to view version history.")

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, user_id, original_name, s3_key, file_size_bytes, checksum_sha256, is_deleted, created_at
            FROM files
            WHERE id = ?
            """,
            (file_id,),
        )
        row = cursor.fetchone()

    if not row:
        raise ValueError(f"File with ID {file_id} not found.")

    file_rec = dict(row)

    if not can_view_file(user_id=user_id, user_role=user_role, owner_id=file_rec["user_id"]):
        try:
            log_activity(
                action="FILE_VIEW_VERSIONS",
                resource_type="file",
                user_id=user_id,
                resource_id=str(file_id),
                details=f"Unauthorized version history request for '{file_rec['original_name']}'. Permission denied.",
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise PermissionError(f"User {user_id} does not have permission to view file {file_id}.")

    raw_versions = list_file_versions(file_id, db_path=db_path)

    if not raw_versions:
        # Fallback if file_versions was empty: return the base record as v1
        return [
            {
                "id": 0,
                "file_id": file_id,
                "version_number": 1,
                "version_label": "v1",
                "s3_key": file_rec["s3_key"],
                "file_size_bytes": file_rec["file_size_bytes"],
                "formatted_size": format_bytes(file_rec["file_size_bytes"]),
                "checksum_sha256": file_rec["checksum_sha256"],
                "created_at": file_rec["created_at"],
                "is_current": True,
            }
        ]

    max_version = max(v["version_number"] for v in raw_versions)
    enriched = []
    for v in raw_versions:
        item = dict(v)
        item["version_label"] = f"v{item['version_number']}"
        item["formatted_size"] = format_bytes(item["file_size_bytes"])
        item["is_current"] = item["version_number"] == max_version
        enriched.append(item)

    return enriched


def download_historical_version(
    user_id: int,
    file_id: int,
    version_number: int,
    user_role: str = "user",
    expires_in_seconds: int = 300,
    storage_manager: Optional[S3StorageManager] = None,
    config: Optional[AppConfig] = None,
    db_path: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve and generate a presigned download URL for a specific historical file version.

    Looks up the authoritative S3 key from the database rather than trusting client parameters.
    """
    if not user_id or user_id <= 0:
        raise ValueError("User must be authenticated to download file versions.")

    cfg = config or get_config()
    mgr = storage_manager or S3StorageManager(cfg)

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

    file_rec = dict(file_row)

    if file_rec["is_deleted"] == 1:
        raise ValueError(f"File '{file_rec['original_name']}' has been deleted and cannot be downloaded.")

    if not can_download_file(user_id=user_id, user_role=user_role, owner_id=file_rec["user_id"]):
        try:
            log_activity(
                action="FILE_DOWNLOAD",
                resource_type="file_version",
                user_id=user_id,
                resource_id=f"{file_id}:v{version_number}",
                details=f"Unauthorized historical download attempt for '{file_rec['original_name']}' (v{version_number}). Permission denied.",
                ip_address=client_ip,
                status="FAILED",
                db_path=db_path,
            )
        except Exception:
            pass
        raise PermissionError(f"User {user_id} does not have download permissions for file {file_id}.")

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, file_id, version_number, s3_key, file_size_bytes, checksum_sha256, created_at
            FROM file_versions
            WHERE file_id = ? AND version_number = ?
            """,
            (file_id, version_number),
        )
        ver_row = cursor.fetchone()

    if not ver_row:
        raise ValueError(f"Version {version_number} does not exist for file {file_id}.")

    version_rec = dict(ver_row)
    s3_key = version_rec["s3_key"]

    if hasattr(mgr, "object_exists") and not mgr.object_exists(s3_key):
        raise FileNotFoundError(
            f"Historical version {version_number} storage object for '{file_rec['original_name']}' not found in S3 bucket."
        )

    try:
        url = mgr.generate_presigned_download_url(s3_key, expires_in_seconds=expires_in_seconds)
    except Exception as presign_err:
        logger.error(
            f"Failed to generate presigned download URL for historical version {version_number} of file_id {file_id}: {type(presign_err).__name__}"
        )
        raise RuntimeError(f"Failed to generate download URL: {presign_err}")

    # Audit log
    try:
        log_activity(
            action="FILE_DOWNLOAD",
            resource_type="file_version",
            user_id=user_id,
            resource_id=f"{file_id}:v{version_number}",
            details=f"Generated historical download link for '{file_rec['original_name']}' (v{version_number})",
            ip_address=client_ip,
            status="SUCCESS",
            db_path=db_path,
        )
    except Exception:
        pass

    return {
        "file_id": file_id,
        "filename": file_rec["original_name"],
        "version_number": version_number,
        "version_label": f"v{version_number}",
        "s3_key": s3_key,
        "download_url": url,
        "expires_in_seconds": expires_in_seconds,
        "file_size_bytes": version_rec["file_size_bytes"],
        "formatted_size": format_bytes(version_rec["file_size_bytes"]),
        "checksum_sha256": version_rec["checksum_sha256"],
    }
