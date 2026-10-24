"""Unit tests for role-based access control and file permissions."""

from __future__ import annotations

import pytest
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


@pytest.mark.unit
class TestRoleAndOwnershipChecks:
    """Tests for role and owner identity checking."""

    def test_is_admin(self) -> None:
        assert is_admin(UserRole.ADMIN.value) is True
        assert is_admin("admin") is True
        assert is_admin("user") is False
        assert is_admin("guest") is False

    def test_is_owner(self) -> None:
        assert is_owner(user_id=1, owner_id=1) is True
        assert is_owner(user_id=1, owner_id=2) is False


@pytest.mark.unit
class TestFilePermissions:
    """Tests for object-level view, download, edit, and deletion permissions."""

    def test_owner_has_full_permissions(self) -> None:
        owner_id = 10
        role = UserRole.USER.value

        assert can_view_file(user_id=10, user_role=role, owner_id=owner_id) is True
        assert can_download_file(user_id=10, user_role=role, owner_id=owner_id) is True
        assert can_edit_file(user_id=10, user_role=role, owner_id=owner_id) is True
        assert can_delete_file(user_id=10, user_role=role, owner_id=owner_id) is True
        assert can_manage_shares(user_id=10, user_role=role, owner_id=owner_id) is True

    def test_unauthorized_user_denied_all(self) -> None:
        owner_id = 10
        stranger_id = 20
        role = UserRole.USER.value

        assert can_view_file(user_id=stranger_id, user_role=role, owner_id=owner_id) is False
        assert can_download_file(user_id=stranger_id, user_role=role, owner_id=owner_id) is False
        assert can_edit_file(user_id=stranger_id, user_role=role, owner_id=owner_id) is False
        assert can_delete_file(user_id=stranger_id, user_role=role, owner_id=owner_id) is False
        assert can_manage_shares(user_id=stranger_id, user_role=role, owner_id=owner_id) is False

    def test_view_share_permission(self) -> None:
        owner_id = 10
        collaborator_id = 20
        role = UserRole.USER.value

        # With 'view' share permission
        assert can_view_file(collaborator_id, role, owner_id, share_permission=SharePermission.VIEW.value) is True
        assert can_download_file(collaborator_id, role, owner_id, share_permission=SharePermission.VIEW.value) is False
        assert can_edit_file(collaborator_id, role, owner_id, share_permission=SharePermission.VIEW.value) is False
        assert can_delete_file(collaborator_id, role, owner_id) is False

    def test_download_share_permission(self) -> None:
        owner_id = 10
        collaborator_id = 20
        role = UserRole.USER.value

        # With 'download' share permission
        assert can_view_file(collaborator_id, role, owner_id, share_permission=SharePermission.DOWNLOAD.value) is True
        assert can_download_file(collaborator_id, role, owner_id, share_permission=SharePermission.DOWNLOAD.value) is True
        assert can_edit_file(collaborator_id, role, owner_id, share_permission=SharePermission.DOWNLOAD.value) is False
        assert can_delete_file(collaborator_id, role, owner_id) is False

    def test_edit_share_permission(self) -> None:
        owner_id = 10
        collaborator_id = 20
        role = UserRole.USER.value

        # With 'edit' share permission
        assert can_view_file(collaborator_id, role, owner_id, share_permission=SharePermission.EDIT.value) is True
        assert can_download_file(collaborator_id, role, owner_id, share_permission=SharePermission.EDIT.value) is True
        assert can_edit_file(collaborator_id, role, owner_id, share_permission=SharePermission.EDIT.value) is True
        # Shared editor still CANNOT delete someone else's file
        assert can_delete_file(collaborator_id, role, owner_id) is False

    def test_admin_has_universal_permissions(self) -> None:
        owner_id = 10
        admin_id = 99
        admin_role = UserRole.ADMIN.value

        assert can_view_file(admin_id, admin_role, owner_id) is True
        assert can_download_file(admin_id, admin_role, owner_id) is True
        assert can_edit_file(admin_id, admin_role, owner_id) is True
        assert can_delete_file(admin_id, admin_role, owner_id) is True
        assert can_manage_shares(admin_id, admin_role, owner_id) is True
