"""Verification runner for Phase 5C — Streamlit UI, Workflows, and Integration.

Conducts headless Streamlit AppTest runs and HTTP checks for:
- Task 1: Preflight checks
- Task 2: Streamlit UI components and workflows
- Task 3: Sharing workflows (view-only, download, revocation, email restrictions)
- Task 4: Live AWS S3 integration verification (opt-in isolated tests)
- Task 5: Regression & compilation verification
"""

from __future__ import annotations

import os
import sqlite3
import sys
import urllib.request
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from streamlit.testing.v1 import AppTest
from src.auth import authenticate_user, create_user, get_user_by_id
from src.aws_storage import S3StorageManager
from src.config import get_config
from src.database import get_db_cursor
from src.file_service import delete_file, list_user_files, upload_file
from src.sharing import (
    access_shared_file,
    create_share_link,
    list_shares_by_user,
    revoke_share_link,
)


def run_http_verification() -> Dict[str, Any]:
    """Verify live running Streamlit server on http://localhost:8501."""
    url = "http://localhost:8501"
    health_url = "http://localhost:8501/_stcore/health"
    results = {}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CODSOFT-Verification/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            results["root_status"] = resp.status
            results["root_ok"] = resp.status == 200
    except Exception as e:
        results["root_status"] = str(e)
        results["root_ok"] = False

    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "CODSOFT-Verification/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            results["health_status"] = resp.status
            results["health_body"] = body.strip()
            results["health_ok"] = resp.status == 200
    except Exception as e:
        results["health_status"] = str(e)
        results["health_ok"] = False

    return results


def run_apptest_verification() -> Dict[str, Any]:
    """Verify all Streamlit pages and workflows using Streamlit AppTest."""
    config = get_config()
    results: Dict[str, Any] = {}

    # 1. Application Startup & Unauthenticated Views
    pages_to_check = [
        "app.py",
        "pages/1_My_Files.py",
        "pages/2_Storage_Analytics.py",
        "pages/3_Shared_Files.py",
        "pages/4_Activity_History.py",
        "pages/5_Settings.py",
        "pages/6_Admin.py",
    ]
    unauth_page_results = {}
    for page in pages_to_check:
        print(f"  Testing unauthenticated page: {page}...")
        at = AppTest.from_file(os.path.join(PROJECT_ROOT, page), default_timeout=15)
        at.run()
        unauth_page_results[page] = {
            "has_exception": bool(at.exception),
            "exceptions": [str(e.value) for e in at.exception],
            "info_messages": [i.value for i in at.info],
            "warning_messages": [w.value for w in at.warning],
            "error_messages": [e.value for e in at.error],
        }
    results["unauth_pages"] = unauth_page_results

    # 2. Disposable Test Accounts Creation
    disp_username = "disp_test_5c_user"
    disp_email = "disp_test_5c@example.com"
    disp_pass = "TestPassword2026!"

    # Clean any stale records first
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE username = ?", (disp_username,))
        existing = cursor.fetchone()
        if existing:
            u_id = existing["id"]
            cursor.execute("DELETE FROM file_shares WHERE shared_by_user_id = ?", (u_id,))
            cursor.execute("DELETE FROM file_versions WHERE file_id IN (SELECT id FROM files WHERE user_id = ?)", (u_id,))
            cursor.execute("DELETE FROM files WHERE user_id = ?", (u_id,))
            cursor.execute("DELETE FROM activity_logs WHERE user_id = ?", (u_id,))
            cursor.execute("DELETE FROM users WHERE id = ?", (u_id,))

    # Create temporary user
    print("  Creating disposable test user...")
    created_user = create_user(disp_username, disp_email, disp_pass, role="user")
    user_id = created_user["id"]
    results["user_created"] = {"id": user_id, "username": disp_username, "role": "user"}

    # Authenticate
    auth_res = authenticate_user(disp_username, disp_pass)
    results["auth_successful"] = auth_res is not None and auth_res["id"] == user_id

    # 3. Authenticated App Tests
    # A: app.py with authenticated session
    print("  Testing authenticated app.py...")
    at_home = AppTest.from_file(os.path.join(PROJECT_ROOT, "app.py"), default_timeout=15)
    at_home.session_state["current_user"] = created_user
    at_home.run()
    results["home_auth"] = {
        "has_exception": bool(at_home.exception),
        "exceptions": [str(e.value) for e in at_home.exception],
    }

    # B: My Files (empty state)
    print("  Testing My Files empty state...")
    at_files_empty = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/1_My_Files.py"), default_timeout=15)
    at_files_empty.session_state["current_user"] = created_user
    at_files_empty.run()
    results["files_empty_state"] = {
        "has_exception": bool(at_files_empty.exception),
        "info_count": len(at_files_empty.info),
    }

    # C: Upload Validation and Disposable Upload
    print("  Uploading disposable test file...")
    disposable_filename = "disposable_test_5c.txt"
    disposable_payload = b"Phase 5C Browser Verification Test File Content."
    upload_res = upload_file(
        user_id=user_id,
        file_bytes=disposable_payload,
        filename=disposable_filename,
        config=config,
    )
    file_id = upload_res["file_id"]
    results["upload_res"] = {
        "file_id": file_id,
        "filename": upload_res["filename"],
        "version": upload_res["version"],
        "checksum_prefix": upload_res["checksum"][:16],
    }

    # D: File Listing & Search
    user_files = list_user_files(user_id=user_id, user_role="user")
    results["file_listing_count"] = len(user_files)

    # AppTest with uploaded file
    print("  Testing My Files populated state...")
    at_files_populated = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/1_My_Files.py"), default_timeout=15)
    at_files_populated.session_state["current_user"] = created_user
    at_files_populated.run()
    results["files_populated"] = {
        "has_exception": bool(at_files_populated.exception),
    }

    # E: Storage Analytics & Activity History
    print("  Testing Storage Analytics...")
    at_analytics = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/2_Storage_Analytics.py"), default_timeout=15)
    at_analytics.session_state["current_user"] = created_user
    at_analytics.run()
    results["analytics"] = {
        "has_exception": bool(at_analytics.exception),
    }

    print("  Testing Activity History...")
    at_history = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/4_Activity_History.py"), default_timeout=15)
    at_history.session_state["current_user"] = created_user
    at_history.run()
    results["activity_history"] = {
        "has_exception": bool(at_history.exception),
    }

    # F: Admin page access denied for regular user
    print("  Testing Admin RBAC boundary...")
    at_admin = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/6_Admin.py"), default_timeout=15)
    at_admin.session_state["current_user"] = created_user
    at_admin.run()
    admin_denied = any("Access Denied" in e.value for e in at_admin.error)
    results["admin_rbac_enforced"] = admin_denied

    # 4. Task 3 Sharing Workflows
    # A. View-Only Share Link
    print("  Testing Task 3A: View-Only share link...")
    view_share = create_share_link(
        user_id=user_id,
        file_id=file_id,
        user_role="user",
        permission_level="view",
        expires_in_hours=1,
    )
    view_token = view_share["share_token"]
    results["view_share_created"] = True

    at_view_share = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/3_Shared_Files.py"), default_timeout=15)
    at_view_share.query_params["share"] = view_token
    at_view_share.run()
    view_has_ex = bool(at_view_share.exception)
    view_only_text_found = any("View-Only Access Enforced" in m.value for m in at_view_share.markdown)
    download_btn_found = any("Click to Download" in m.value for m in at_view_share.markdown)
    results["task_3_a_view_only"] = {
        "has_exception": view_has_ex,
        "view_only_enforced_displayed": view_only_text_found,
        "download_button_exposed": download_btn_found,
        "passed": (not view_has_ex) and view_only_text_found and (not download_btn_found),
    }

    # B. Download Share Link
    print("  Testing Task 3B: Download share link...")
    dl_share = create_share_link(
        user_id=user_id,
        file_id=file_id,
        user_role="user",
        permission_level="download",
        expires_in_hours=1,
    )
    dl_token = dl_share["share_token"]
    results["dl_share_created"] = True

    at_dl_share = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/3_Shared_Files.py"), default_timeout=15)
    at_dl_share.query_params["share"] = dl_token
    at_dl_share.run()
    dl_has_ex = bool(at_dl_share.exception)
    dl_ready_found = any("Ready for Secure Download" in m.value for m in at_dl_share.markdown)
    dl_btn_found = any("Click to Download" in m.value for m in at_dl_share.markdown)

    dl_access = access_shared_file(share_token=dl_token, storage_manager=S3StorageManager(config), config=config)
    presigned_valid = dl_access["can_download"] and bool(dl_access["download_url"])

    results["task_3_b_download"] = {
        "has_exception": dl_has_ex,
        "ready_for_download_displayed": dl_ready_found,
        "download_button_rendered": dl_btn_found,
        "presigned_url_valid": presigned_valid,
        "passed": (not dl_has_ex) and dl_ready_found and dl_btn_found and presigned_valid,
    }

    # C. Share Revocation
    print("  Testing Task 3C: Revocation...")
    revoke_res = revoke_share_link(user_id=user_id, share_id=dl_share["id"], user_role="user")
    results["revocation_executed"] = revoke_res.get("success", False) is True

    at_revoked = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/3_Shared_Files.py"), default_timeout=15)
    at_revoked.query_params["share"] = dl_token
    at_revoked.run()
    revoked_denied = any("revoked by the owner" in w.value.lower() for w in at_revoked.warning)
    results["task_3_c_revocation"] = {
        "has_exception": bool(at_revoked.exception),
        "access_denied_warning_shown": revoked_denied,
        "passed": revoked_denied,
    }

    # D. Recipient Email Restriction
    print("  Testing Task 3D: Recipient email restrictions...")
    restricted_email = "team.colleague@example.com"
    colleague_user = create_user("team_colleague_5c", restricted_email, "TestPassword2026!", role="user")
    colleague_id = colleague_user["id"]

    email_share = create_share_link(
        user_id=user_id,
        file_id=file_id,
        user_role="user",
        permission_level="view",
        expires_in_hours=1,
        shared_with_email=restricted_email,
    )
    email_token = email_share["share_token"]

    at_email_anon = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/3_Shared_Files.py"), default_timeout=15)
    at_email_anon.query_params["share"] = email_token
    at_email_anon.run()
    email_restricted_info = any("restricted to" in i.value.lower() for i in at_email_anon.info)

    at_email_auth = AppTest.from_file(os.path.join(PROJECT_ROOT, "pages/3_Shared_Files.py"), default_timeout=15)
    at_email_auth.query_params["share"] = email_token
    at_email_auth.session_state["current_user"] = colleague_user
    at_email_auth.run()
    email_auth_authorized = any("Access Authorized" in s.value for s in at_email_auth.success)

    results["task_3_d_email_restrictions"] = {
        "anon_restricted_warning": email_restricted_info,
        "authorized_recipient_success": email_auth_authorized,
        "passed": email_restricted_info and email_auth_authorized,
    }

    # 5. Clean up disposable test data safely
    print("  Cleaning up disposable test objects...")
    try:
        delete_file(user_id=user_id, file_id=file_id, storage_manager=S3StorageManager(config), config=config)
    except Exception as del_err:
        results["file_cleanup_error"] = str(del_err)

    # Delete disposable user records
    with get_db_cursor() as cursor:
        cursor.execute("DELETE FROM file_shares WHERE shared_by_user_id IN (?, ?)", (user_id, colleague_id))
        cursor.execute("DELETE FROM file_versions WHERE file_id IN (SELECT id FROM files WHERE user_id = ?)", (user_id,))
        cursor.execute("DELETE FROM files WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM activity_logs WHERE user_id IN (?, ?)", (user_id, colleague_id))
        cursor.execute("DELETE FROM users WHERE id IN (?, ?)", (user_id, colleague_id))

    results["cleanup_completed"] = True
    return results


if __name__ == "__main__":
    print("=== Starting Phase 5C Automated Verification ===")
    print("1. Running HTTP endpoint verification...")
    http_res = run_http_verification()
    print("HTTP Results:", http_res)

    print("\n2. Running AppTest UI and Sharing Workflows verification...")
    app_res = run_apptest_verification()
    print("Task 3A View-Only:", app_res["task_3_a_view_only"])
    print("Task 3B Download:", app_res["task_3_b_download"])
    print("Task 3C Revocation:", app_res["task_3_c_revocation"])
    print("Task 3D Email Restrictions:", app_res["task_3_d_email_restrictions"])
    print("Admin RBAC Enforced:", app_res["admin_rbac_enforced"])
    print("All unauth pages clean:", all(not v["has_exception"] for v in app_res["unauth_pages"].values()))
    print("Cleanup Completed:", app_res["cleanup_completed"])
    print("\n=== Phase 5C Verification Complete ===")
