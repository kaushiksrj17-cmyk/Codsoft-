"""Standardized navigation sidebar component for Streamlit."""

from __future__ import annotations

import streamlit as st
try:
    from components.styles import inject_custom_styles
except (ImportError, ModuleNotFoundError):
    from components import inject_custom_styles
from src.config import get_config


def render_sidebar() -> None:
    """Render the standard application sidebar across all pages with global styles."""
    inject_custom_styles()

    config = get_config()
    aws_status = config.get_safe_aws_status()

    with st.sidebar:
        # 1. Brand Logo & Header
        brand_html = """<div style="text-align: center; padding: 0.8rem 0 1.2rem 0;">
<div style="display: inline-flex; align-items: center; justify-content: center; width: 50px; height: 50px; border-radius: 14px; background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #EC4899 100%); box-shadow: 0 0 20px rgba(139, 92, 246, 0.45); margin-bottom: 0.6rem; font-size: 1.5rem;">
☁️
</div>
<h2 style="margin: 0; font-size: 1.2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.02em;">
Cloud Storage Engine
</h2>
<div style="font-size: 0.72rem; color: #A5B4FC; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; margin-top: 3px;">
CODSOFT Task 1 • Enterprise S3
</div>
</div>"""
        st.markdown(brand_html, unsafe_allow_html=True)

        st.divider()

        # 2. Cloud Infrastructure Status Badge
        if aws_status["is_configured"]:
            s3_badge_html = f"""<div style="background: linear-gradient(135deg, rgba(6, 78, 59, 0.45) 0%, rgba(15, 23, 42, 0.8) 100%); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 12px; padding: 0.75rem 0.9rem; margin-bottom: 1.2rem; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4), 0 0 12px rgba(16, 185, 129, 0.15);">
<div style="display: flex; align-items: center; justify-content: space-between;">
<div style="display: flex; align-items: center; gap: 8px;">
<span class="beacon-live"></span>
<strong style="color: #34D399; font-size: 0.82rem; font-weight: 700;">Amazon S3 Connected</strong>
</div>
<span style="font-size: 0.68rem; background: rgba(16, 185, 129, 0.25); color: #34D399; font-weight: 700; padding: 2px 6px; border-radius: 9999px; border: 1px solid rgba(52, 211, 153, 0.3);">
LIVE
</span>
</div>
<div style="font-size: 0.73rem; color: #94A3B8; margin-top: 5px; line-height: 1.4;">
Region: <code>{aws_status['region']}</code><br>
Bucket: <code>{aws_status['bucket_display']}</code>
</div>
</div>"""
            st.markdown(s3_badge_html, unsafe_allow_html=True)
        else:
            s3_badge_html = f"""<div style="background: linear-gradient(135deg, rgba(120, 53, 15, 0.45) 0%, rgba(15, 23, 42, 0.8) 100%); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 12px; padding: 0.75rem 0.9rem; margin-bottom: 1.2rem; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4), 0 0 12px rgba(245, 158, 11, 0.15);">
<div style="display: flex; align-items: center; justify-content: space-between;">
<div style="display: flex; align-items: center; gap: 8px;">
<span class="beacon-pending"></span>
<strong style="color: #FBBF24; font-size: 0.82rem; font-weight: 700;">Dev Sandbox Mode</strong>
</div>
<span style="font-size: 0.68rem; background: rgba(245, 158, 11, 0.25); color: #FBBF24; font-weight: 700; padding: 2px 6px; border-radius: 9999px; border: 1px solid rgba(245, 158, 11, 0.3);">
MOCK
</span>
</div>
<div style="font-size: 0.72rem; color: #94A3B8; margin-top: 5px;">
S3 setup pending • Zero cloud charges<br>
See <code>docs/AWS_SETUP.md</code> to connect.
</div>
</div>"""
            st.markdown(s3_badge_html, unsafe_allow_html=True)

        # 3. User Session Management
        st.subheader("Account Session")
        from src.auth import authenticate_user, create_user, get_all_users, get_user_by_id
        from src.file_service import get_user_quota_info

        current_user = st.session_state.get("current_user")

        if current_user:
            fresh_user = get_user_by_id(current_user["id"])
            if fresh_user:
                current_user = fresh_user
                st.session_state["current_user"] = fresh_user
            else:
                st.session_state.clear()
                st.rerun()

            quota_info = get_user_quota_info(current_user["id"])
            role_label = current_user.get("role", "user").upper()
            role_bg = "rgba(245, 158, 11, 0.25)" if role_label == "ADMIN" else "rgba(99, 102, 241, 0.25)"
            role_color = "#FBBF24" if role_label == "ADMIN" else "#C4B5FD"
            initial = current_user["username"][0].upper() if current_user.get("username") else "U"

            session_html = f"""<div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 0.85rem 0.95rem; margin-bottom: 0.9rem; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4); backdrop-filter: blur(8px);">
<div style="display: flex; align-items: center; gap: 10px;">
<div style="width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%); color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.95rem; box-shadow: 0 0 12px rgba(139, 92, 246, 0.45);">
{initial}
</div>
<div style="flex-grow: 1; min-width: 0;">
<div style="display: flex; align-items: center; justify-content: space-between; gap: 6px;">
<strong style="color: #F8FAFC; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
{current_user['username']}
</strong>
<span style="font-size: 0.65rem; font-weight: 800; background: {role_bg}; color: {role_color}; padding: 2px 6px; border-radius: 4px; letter-spacing: 0.04em;">
{role_label}
</span>
</div>
<div style="color: #94A3B8; font-size: 0.73rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
{current_user['email']}
</div>
</div>
</div>
</div>"""
            st.markdown(session_html, unsafe_allow_html=True)

            # Quota Summary with Progress Bar
            st.caption(f"**Storage Quota:** {quota_info['formatted_used']} / {quota_info['formatted_quota']}")
            progress_val = min(quota_info["usage_percentage"] / 100.0, 1.0)
            st.progress(progress_val)
            st.caption(f"{quota_info['formatted_remaining']} remaining ({100.0 - quota_info['usage_percentage']:.1f}% free)")

            if st.button("🚪 Sign Out", use_container_width=True, key="sidebar_sign_out"):
                try:
                    from src.activity_logger import log_activity
                    log_activity(
                        action="AUTH_LOGOUT",
                        resource_type="USER",
                        user_id=current_user["id"],
                        resource_id=str(current_user["id"]),
                        details=f"User {current_user['username']} logged out.",
                        status="SUCCESS",
                    )
                except Exception:
                    pass
                st.session_state.clear()
                st.rerun()

        else:
            all_users = get_all_users()
            if not all_users:
                st.info("No user accounts found in database. Create your profile below:")
                with st.expander("✨ Create Initial Profile", expanded=True):
                    init_user = st.text_input("Username", value="kaushik", key="init_user_input")
                    init_email = st.text_input("Email", value="kaushik@example.com", key="init_email_input")
                    init_pass = st.text_input("Password", value="CloudStorage2026!", type="password", key="init_pass_input")
                    if st.button("Create & Sign In", use_container_width=True, key="btn_init_user", type="primary"):
                        try:
                            new_u = create_user(init_user, init_email, init_pass, role="admin")
                            st.session_state["current_user"] = new_u
                            st.success(f"Welcome, {new_u['username']}!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            else:
                user_options = {u["username"]: u for u in all_users}
                selected_username = st.selectbox(
                    "Select Account to Sign In",
                    options=list(user_options.keys()),
                    key="sidebar_user_select",
                )
                sidebar_password = st.text_input(
                    "Password",
                    type="password",
                    key="sidebar_signin_pass",
                    placeholder="Enter account password",
                )
                if st.button("🔑 Sign In", use_container_width=True, key="btn_signin_selected", type="primary"):
                    authenticated = authenticate_user(selected_username, sidebar_password)
                    if authenticated:
                        st.session_state["current_user"] = authenticated
                        st.success(f"Welcome back, {authenticated['username']}!")
                        st.rerun()
                    else:
                        st.error("Invalid password. Please check your credentials.")

                with st.expander("➕ Register New Account"):
                    reg_user = st.text_input("New Username", key="reg_user_input")
                    reg_email = st.text_input("New Email", key="reg_email_input")
                    reg_pass = st.text_input("New Password", type="password", key="reg_pass_input")
                    if st.button("Register Account", use_container_width=True, key="btn_register_submit"):
                        try:
                            created_u = create_user(reg_user, reg_email, reg_pass, role="user")
                            st.session_state["current_user"] = created_u
                            st.success(f"Account '{created_u['username']}' registered!")
                            st.rerun()
                        except Exception as reg_err:
                            st.error(str(reg_err))

        st.divider()

        footer_html = """<div style="font-size: 0.72rem; color: #94A3B8; text-align: center; line-height: 1.5;">
<span style="font-weight: 600; color: #64748B;">Cloud File Storage System</span><br>
Python 3.11 • Amazon S3 • SQLite/PG<br>
CODSOFT Cloud Internship
</div>"""
        st.markdown(footer_html, unsafe_allow_html=True)
