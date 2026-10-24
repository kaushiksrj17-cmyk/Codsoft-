"""Authentication, password hashing, and user credential validation.

Utilizes bcrypt for adaptive, salted one-way password hashing.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import bcrypt

    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password complexity.

    Requires at least 8 characters, an uppercase letter, a lowercase letter,
    and a digit.
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit (0-9)."

    return True, "Password meets strength criteria."


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    if not _BCRYPT_AVAILABLE:
        raise RuntimeError(
            "bcrypt package is not installed. Please install requirements via setup script."
        )

    # Encode to bytes and generate salt
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an existing bcrypt hash."""
    if not _BCRYPT_AVAILABLE:
        raise RuntimeError(
            "bcrypt package is not installed. Please install requirements via setup script."
        )

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve an active user record by ID, omitting the raw password hash."""
    from src.database import get_db_cursor

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, username, email, role, storage_quota_bytes, used_storage_bytes, is_active, created_at, updated_at
            FROM users
            WHERE id = ? AND is_active = 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_users(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all active users for administrative oversight or account selection."""
    from src.database import get_db_cursor

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, username, email, role, storage_quota_bytes, used_storage_bytes, is_active, created_at, updated_at
            FROM users
            ORDER BY id ASC
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


import sqlite3

ALLOWED_ROLES = {"user", "admin"}
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def create_user(
    username: str,
    email: str,
    plain_password: str,
    role: str = "user",
    quota_bytes: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new user with bcrypt-hashed credentials and default storage quota."""
    from src.config import get_config
    from src.database import get_db_cursor

    clean_username = username.strip() if username else ""
    clean_email = email.strip().lower() if email else ""
    clean_role = role.strip().lower() if role else "user"

    if clean_role not in ALLOWED_ROLES:
        raise ValueError(
            f"Invalid role '{role}'. Allowed roles are: {', '.join(sorted(ALLOWED_ROLES))}."
        )

    if not USERNAME_REGEX.match(clean_username):
        raise ValueError(
            "Username must be between 3 and 32 characters and contain only letters, numbers, dots, underscores, or hyphens."
        )

    if not EMAIL_REGEX.match(clean_email):
        raise ValueError("A valid email address is required.")

    is_strong, msg = validate_password_strength(plain_password)
    if not is_strong:
        raise ValueError(msg)

    hashed = hash_password(plain_password)
    quota = quota_bytes if quota_bytes is not None else get_config().default_storage_quota_bytes

    try:
        with get_db_cursor(db_path) as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, role, storage_quota_bytes, used_storage_bytes, is_active)
                VALUES (?, ?, ?, ?, ?, 0, 1)
                """,
                (clean_username, clean_email, hashed, clean_role, quota),
            )
            user_id = cursor.lastrowid
            if not user_id:
                raise RuntimeError("Failed to insert user record.")
    except sqlite3.IntegrityError:
        raise ValueError("Username or email already registered.")

    user = get_user_by_id(user_id, db_path=db_path)
    if not user:
        raise RuntimeError("Failed to retrieve created user.")
    return user


def authenticate_user(
    username_or_email: str,
    plain_password: str,
    client_ip: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Authenticate a user by username or email and return the user profile dict if valid."""
    from src.activity_logger import log_activity
    from src.database import get_db_cursor

    identifier = username_or_email.strip() if username_or_email else ""
    if not identifier or not plain_password:
        return None

    with get_db_cursor(db_path) as cursor:
        cursor.execute(
            """
            SELECT id, username, email, password_hash, role, storage_quota_bytes, used_storage_bytes, is_active, created_at, updated_at
            FROM users
            WHERE (username = ? OR LOWER(email) = LOWER(?)) AND is_active = 1
            """,
            (identifier, identifier),
        )
        row = cursor.fetchone()

        if not row:
            try:
                log_activity(
                    action="AUTH_LOGIN",
                    resource_type="USER",
                    user_id=None,
                    resource_id=None,
                    details=f"Failed login attempt: user '{identifier}' not found.",
                    ip_address=client_ip,
                    status="FAILED",
                    db_path=db_path,
                )
            except Exception:
                pass
            return None

        if verify_password(plain_password, row["password_hash"]):
            user_data = dict(row)
            del user_data["password_hash"]
            try:
                log_activity(
                    action="AUTH_LOGIN",
                    resource_type="USER",
                    user_id=user_data["id"],
                    resource_id=str(user_data["id"]),
                    details=f"User {user_data['username']} logged in successfully.",
                    ip_address=client_ip,
                    status="SUCCESS",
                    db_path=db_path,
                )
            except Exception:
                pass
            return user_data
        else:
            try:
                log_activity(
                    action="AUTH_LOGIN",
                    resource_type="USER",
                    user_id=row["id"],
                    resource_id=str(row["id"]),
                    details=f"Failed login attempt for user '{row['username']}': invalid credentials.",
                    ip_address=client_ip,
                    status="FAILED",
                    db_path=db_path,
                )
            except Exception:
                pass

    return None

