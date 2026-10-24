"""My Files page - Personal Cloud Storage Explorer."""

from __future__ import annotations

import streamlit as st
from components.file_table import render_empty_file_state, render_file_table
from components.sidebar import render_sidebar
from components.upload_panel import render_upload_panel
from src.auth import authenticate_user, get_all_users, get_user_by_id
from src.config import get_config
from src.file_service import list_user_files

st.set_page_config(
    page_title="My Files - Cloud File Storage System",
    page_icon="📁",
    layout="wide",
)

render_sidebar()
config = get_config()

current_user = st.session_state.get("current_user")

if not current_user:
    st.title("📁 My Files & Cloud Catalog")
    unauth_html = """<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 16px; padding: 2rem 2.4rem; margin: 1.5rem 0; box-shadow: 0 4px 25px rgba(0, 0, 0, 0.5), 0 0 15px rgba(99, 102, 241, 0.15); text-align: center; backdrop-filter: blur(12px);">
<div style="display: inline-flex; align-items: center; justify-content: center; width: 58px; height: 58px; border-radius: 16px; background: rgba(99, 102, 241, 0.2); color: #C4B5FD; font-size: 1.8rem; margin-bottom: 0.8rem; border: 1px solid rgba(139, 92, 246, 0.35); box-shadow: 0 0 15px rgba(139, 92, 246, 0.3);">
🔒
</div>
<h3 style="margin: 0 0 0.5rem 0; color: #F8FAFC; font-weight: 800;">
Tenant Authentication Required
</h3>
<p style="color: #94A3B8; font-size: 0.92rem; max-width: 520px; margin: 0 auto 1.5rem auto; line-height: 1.5;">
To access your tenant-isolated Amazon S3 partition and view your private catalog,
please sign in or select an active account profile.
</p>
</div>"""
    st.markdown(unauth_html, unsafe_allow_html=True)

    # Inline quick sign in card
    users = get_all_users()
    if users:
        st.markdown("#### 👤 Select an Account to Access S3 Partition")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            u_choice = st.selectbox("Select Account", options=[u["username"] for u in users], key="inline_user_choice")
        with c2:
            inline_pass = st.text_input("Password", type="password", key="inline_user_pass", placeholder="Enter account password")
        with c3:
            st.write("")
            st.write("")
            if st.button("🔑 Sign In", use_container_width=True, key="btn_inline_continue", type="primary"):
                auth_user = authenticate_user(u_choice, inline_pass)
                if auth_user:
                    st.session_state["current_user"] = auth_user
                    st.rerun()
                else:
                    st.error("Invalid password. Please check your credentials.")
    else:
        st.warning("No users exist in the database yet. Please use the sidebar form to create your initial administrator profile.")

else:
    fresh = get_user_by_id(current_user["id"])
    if fresh:
        current_user = fresh
        st.session_state["current_user"] = fresh
    else:
        st.session_state.clear()
        st.warning("Your session has expired or the account was deactivated. Please sign in again.")
        st.rerun()

    st.title("📁 My Files & Cloud Catalog")
    st.caption(
        f"Manage your private cloud documents, photos, and files stored in Amazon S3 • Account: **{current_user['username']}** (`{current_user.get('role', 'user').upper()}`)"
    )

    # 1. Functional Upload Panel
    render_upload_panel(current_user)

    st.divider()

    # 2. Interactive Toolbar (Search, Filter, Sort)
    col1, col2, col3 = st.columns([3, 1.2, 1.2])
    with col1:
        search_query = st.text_input(
            "Search files",
            placeholder="🔍 Search files by name...",
            label_visibility="collapsed",
            key="file_search_input",
        )
    with col2:
        filter_cat = st.selectbox(
            "Filter Type",
            options=["All Types", "Documents", "Images", "Archives", "Media", "Other"],
            label_visibility="collapsed",
            key="file_filter_select",
        )
    with col3:
        sort_by = st.selectbox(
            "Sort By",
            options=["Date (Newest)", "Date (Oldest)", "Name (A-Z)", "Name (Z-A)", "Size (Largest)", "Size (Smallest)"],
            label_visibility="collapsed",
            key="file_sort_select",
        )

    # 3. File Listing Query
    files = list_user_files(
        user_id=current_user["id"],
        user_role=current_user.get("role", "user"),
        search_query=search_query,
        filter_category=filter_cat,
        sort_by=sort_by,
    )

    # 4. Render Table
    render_file_table(files, current_user=current_user)
