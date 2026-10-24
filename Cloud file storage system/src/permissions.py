"""User roles, file permissions, and authorization rules.

Implements role-based access control (RBAC) and object-level permissions
governing viewing, downloading, updating, and deleting files.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    """System user roles."""

    USER = "user"
    ADMIN = "admin"


class SharePermission(str, Enum):
    """Sharing permission tiers."""

    VIEW = "view"
    DOWNLOAD = "download"
    EDIT = "edit"


def is_admin(role: Optional[str]) -> bool:
    """Check if the given role string corresponds to an administrator."""
    if not role or not isinstance(role, str):
        return False
    return role.strip().lower() == UserRole.ADMIN.value


def is_owner(user_id: int, owner_id: int) -> bool:
    """Check if the requesting user is the owner of the resource."""
    if not isinstance(user_id, int) or not isinstance(owner_id, int) or user_id <= 0 or owner_id <= 0:
        return False
    return user_id == owner_id


def can_view_file(
    user_id: int,
    user_role: str,
    owner_id: int,
    share_permission: Optional[str] = None,
) -> bool:
    """Determine if a user has permission to view file metadata and previews."""
    if is_admin(user_role):
        return True
    if is_owner(user_id, owner_id):
        return True
    if share_permission in {
        SharePermission.VIEW.value,
        SharePermission.DOWNLOAD.value,
        SharePermission.EDIT.value,
    }:
        return True
    return False


def can_download_file(
    user_id: int,
    user_role: str,
    owner_id: int,
    share_permission: Optional[str] = None,
) -> bool:
    """Determine if a user has permission to download or generate presigned download URLs."""
    if is_admin(user_role):
        return True
    if is_owner(user_id, owner_id):
        return True
    if share_permission in {
        SharePermission.DOWNLOAD.value,
        SharePermission.EDIT.value,
    }:
        return True
    return False


def can_edit_file(
    user_id: int,
    user_role: str,
    owner_id: int,
    share_permission: Optional[str] = None,
) -> bool:
    """Determine if a user has permission to update file content or metadata."""
    if is_admin(user_role):
        return True
    if is_owner(user_id, owner_id):
        return True
    if share_permission == SharePermission.EDIT.value:
        return True
    return False


def can_delete_file(user_id: int, user_role: str, owner_id: int) -> bool:
    """Determine if a user has permission to soft-delete or permanently delete a file.

    File deletion is restricted strictly to the file owner or an administrator.
    Shared collaborators cannot delete a file.
    """
    if is_admin(user_role):
        return True
    return is_owner(user_id, owner_id)


def can_manage_shares(user_id: int, user_role: str, owner_id: int) -> bool:
    """Determine if a user can create or revoke share links for a file."""
    if is_admin(user_role):
        return True
    return is_owner(user_id, owner_id)
