"""Shared Files page - Manage shared links and collaborative access."""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_feature_card, render_metric_card
from components.file_table import render_empty_file_state
from components.sidebar import render_sidebar
from src.aws_storage import S3StorageManager
from src.config import get_config
from src.file_service import list_user_files
from src.sharing import (
    access_shared_file,
    create_share_link,
    get_share_by_token,
    get_sharing_metrics,
    list_shares_by_user,
    list_shares_shared_with_email,
    revoke_share_link,
)

st.set_page_config(
    page_title="Shared Files - Cloud File Storage System",
    page_icon="🔗",
    layout="wide",
)

render_sidebar()
config = get_config()
mgr = S3StorageManager(config)

current_user = st.session_state.get("current_user")
share_token = st.query_params.get("share")

# -------------------------------------------------------------------------
# VIEW 1: Direct Shared Link Access via ?share=<token>
# -------------------------------------------------------------------------
if share_token:
    st.title("🔗 Shared File Access")
    st.caption("Accessing private cloud document via secure cryptographic token verification.")

    recipient_user_id = current_user["id"] if current_user else None
    recipient_email = current_user["email"] if current_user else None

    try:
        access_res = access_shared_file(
            share_token=share_token,
            recipient_user_id=recipient_user_id,
            recipient_email=recipient_email,
            storage_manager=mgr,
            config=config,
        )

        filename = access_res["filename"]
        formatted_size = access_res["formatted_size"]
        owner = access_res["owner_username"]
        permission = access_res["permission_level"]
        created_at = access_res["created_at"][:19]
        expires_at = access_res["expires_at"][:19] if access_res["expires_at"] else "Permanent (No Expiry)"
        access_count = access_res["access_count"]
        checksum = access_res["checksum_sha256"] or "N/A"
        content_type = access_res["content_type"]

        st.success("✅ **Access Authorized:** Secure token verified and file record retrieved.")

        # File Presentation Card
        perm_bg = "rgba(6, 78, 59, 0.45)" if permission == "download" else "rgba(99, 102, 241, 0.25)"
        perm_color = "#34D399" if permission == "download" else "#C4B5FD"
        perm_border = "rgba(52, 211, 153, 0.4)" if permission == "download" else "rgba(139, 92, 246, 0.4)"
        perm_text = "⚡ Download Allowed" if permission == "download" else "👁️ View Only Access"

        file_card_html = f"""<div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 1.4rem 1.6rem; margin: 1rem 0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); backdrop-filter: blur(12px);">
<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
<div>
<h3 style="margin: 0; color: #F8FAFC; font-size: 1.25rem; font-weight: 800;">📄 {filename}</h3>
<p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.88rem;">
Shared by <strong style="color: #F8FAFC;">{owner}</strong> • Size: <strong style="color: #F8FAFC;">{formatted_size}</strong> • Type: <code>{content_type}</code>
</p>
</div>
<div>
<span style="background: {perm_bg}; color: {perm_color}; border: 1px solid {perm_border}; padding: 6px 14px; border-radius: 9999px; font-size: 0.82rem; font-weight: 700; display: inline-flex; align-items: center;">
{perm_text}
</span>
</div>
</div>
</div>"""
        st.markdown(file_card_html, unsafe_allow_html=True)

        # Download / View Actions
        if access_res["can_download"] and access_res["download_url"]:
            dl_url = access_res["download_url"]
            dl_card_html = f"""<div style="background: linear-gradient(135deg, rgba(30, 27, 75, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%); border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 14px; padding: 1.5rem; text-align: center; margin: 1.2rem 0; box-shadow: 0 0 20px rgba(139, 92, 246, 0.25);">
<h4 style="color: #C4B5FD; margin: 0 0 6px 0; font-size: 1.1rem; font-weight: 800;">📥 Ready for Secure Download</h4>
<p style="color: #94A3B8; font-size: 0.88rem; margin: 0 0 16px 0;">
A short-lived Amazon S3 presigned download URL has been generated. Valid for 5 minutes.
</p>
<a href="{dl_url}" target="_blank" style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #EC4899 100%); color: #FFFFFF; padding: 10px 28px; border-radius: 10px; text-decoration: none; font-size: 0.95rem; font-weight: 700; display: inline-block; box-shadow: 0 0 16px rgba(124, 58, 237, 0.5);">
⬇️ Click to Download ({formatted_size})
</a>
</div>"""
            st.markdown(dl_card_html, unsafe_allow_html=True)
        else:
            view_card_html = """<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 1.5rem; text-align: center; margin: 1.2rem 0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);">
<div style="font-size: 2.2rem; margin-bottom: 6px;">👁️</div>
<h4 style="color: #F8FAFC; margin: 0 0 4px 0; font-weight: 800; font-size: 1.05rem;">View-Only Access Enforced</h4>
<p style="color: #94A3B8; font-size: 0.88rem; max-width: 480px; margin: 0 auto; line-height: 1.5;">
The owner shared this file with view permissions only. Direct file download and S3 object retrieval are restricted by policy.
</p>
</div>"""
            st.markdown(view_card_html, unsafe_allow_html=True)

        # Metadata Telemetry
        st.subheader("📋 Security & Verification Details")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("Expires At")
            st.markdown(f"**{expires_at}**")
        with c2:
            st.caption("Access Counter")
            st.markdown(f"**{access_count} access event{'s' if access_count != 1 else ''}**")
        with c3:
            st.caption("SHA-256 Checksum")
            st.markdown(f"`{checksum[:16]}...`" if checksum != "N/A" else "N/A")

    except PermissionError as p_err:
        err_msg = str(p_err)
        if "revoked" in err_msg.lower():
            st.warning("🚫 **Access Denied:** This share link has been revoked by the owner.")
        elif "restricted to" in err_msg.lower():
            if not current_user:
                st.info(f"🔒 **Authentication Required:** {err_msg} Please sign in using the sidebar to verify your identity.")
            else:
                st.error(f"🔒 **Unauthorized Account:** {err_msg} (You are signed in as `{current_user['email']}`).")
        else:
            st.error(f"🔒 **Permission Denied:** {err_msg}")

    except ValueError as v_err:
        err_msg = str(v_err)
        if "expired" in err_msg.lower():
            st.warning("⏱️ **Link Expired:** This share link has expired and is no longer accessible. Please request a new link from the owner.")
        else:
            st.error("❌ **Invalid Link:** The requested share token is unknown, invalid, or has been removed.")

    except FileNotFoundError:
        st.info("📂 **File Unavailable:** The underlying file has been deleted by its owner and is no longer available.")

    except Exception as err:
        st.error(f"⚠️ **Access Error:** Could not retrieve shared file. {err}")

    st.write("")
    if st.button("← Back to Shared Files Dashboard", key="btn_back_to_shares"):
        st.query_params.clear()
        st.rerun()

# -------------------------------------------------------------------------
# VIEW 2: Shared Files Management Dashboard
# -------------------------------------------------------------------------
else:
    st.title("🔗 Shared Files")
    st.caption("Generate time-limited secure share links with cryptographic token validation and role restrictions.")

    if not current_user:
        st.info("🔒 **Sign In Required:** Please sign in using the sidebar to view and manage your share links.")
        st.stop()
    else:
        # 1. Telemetry Metrics
        metrics = get_sharing_metrics(
            user_id=current_user["id"],
            user_role=current_user.get("role", "user"),
            email=current_user.get("email"),
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            render_metric_card(
                title="Active Share Links",
                value=str(metrics["active_shares_count"]),
                subtitle="Unexpired share tokens",
                icon="🌐",
            )
        with col2:
            render_metric_card(
                title="Files Shared with Me",
                value=str(metrics["received_shares_count"]),
                subtitle="From team members",
                icon="📥",
            )
        with col3:
            render_metric_card(
                title="Max Expiry Policy",
                value=f"{config.share_link_max_expiry_hours}h",
                subtitle="Configured token lifespan",
                icon="⏱️",
            )

        st.write("")

        # 2. Quick Share Creator Expander
        user_files = list_user_files(
            user_id=current_user["id"],
            user_role=current_user.get("role", "user"),
        )

        with st.expander("➕ Create a New Share Link", expanded=False):
            if not user_files:
                st.caption("You have no uploaded files to share. Upload a file in 'My Files' first.")
            else:
                f_options = {f"{f['original_name']} ({f['formatted_size']})": f for f in user_files}
                selected_label = st.selectbox("Select File to Share", options=list(f_options.keys()), key="select_share_file")
                selected_f = f_options[selected_label]

                c_perm, c_exp = st.columns(2)
                with c_perm:
                    q_perm = st.selectbox(
                        "Permission",
                        options=["view", "download"],
                        format_func=lambda x: "👁️ View Only" if x == "view" else "⚡ Download Allowed",
                        key="quick_share_perm",
                    )
                with c_exp:
                    q_exp = st.selectbox(
                        "Expiration",
                        options=[1, 24, 72, 168],
                        index=1,
                        format_func=lambda h: f"{h} Hour" if h == 1 else f"{h // 24} Days ({h}h)",
                        key="quick_share_exp",
                    )

                q_email = st.text_input(
                    "Recipient Email (Optional)",
                    placeholder="peer@example.com (Leave blank for open link sharing)",
                    key="quick_share_email",
                )

                if st.button("✨ Generate Link", key="btn_quick_gen_share", type="primary", use_container_width=True):
                    try:
                        new_share = create_share_link(
                            user_id=current_user["id"],
                            file_id=selected_f["id"],
                            user_role=current_user.get("role", "user"),
                            permission_level=q_perm,
                            expires_in_hours=q_exp,
                            shared_with_email=q_email,
                        )
                        st.session_state["recent_share_link"] = new_share
                        st.success("✅ Secure share link created!")
                        st.rerun()
                    except Exception as q_err:
                        st.error(f"Failed to create share link: {q_err}")

                if st.session_state.get("recent_share_link"):
                    r_share = st.session_state["recent_share_link"]
                    st.markdown("#### 🔗 Generated Share URL")
                    st.code(r_share["share_url"], language=None)
                    st.caption("Copy this URL and share it with your recipient.")

        st.write("")

        # 3. Two-tab Management View
        tab1, tab2 = st.tabs(["📤 Shared by Me", "📥 Shared with Me"])

        with tab1:
            my_shares = list_shares_by_user(
                user_id=current_user["id"],
                user_role=current_user.get("role", "user"),
            )

            if not my_shares:
                render_empty_file_state(
                    "You have not created any share links yet. "
                    "Use the expander above or click 'Share' in the file explorer to create one."
                )
            else:
                st.markdown(f"**Total links created: {len(my_shares)}**")
                for s in my_shares:
                    share_id = s["id"]
                    fn = s["filename"]
                    token_snippet = s["share_token"][:12] + "..."
                    perm_str = "⚡ Download" if s["permission_level"] == "download" else "👁️ View Only"
                    status = s["status"]
                    created = s["created_at"][:16]
                    expires = s["expires_at"][:16] if s["expires_at"] else "Never"
                    recip = s["shared_with_email"] or "Open Link"

                    with st.container():
                        col_info, col_perm, col_stat, col_act = st.columns([2.8, 1.4, 1.4, 2.2])

                        with col_info:
                            st.markdown(f"📄 **{fn}** (`{s['formatted_size']}`)")
                            st.caption(f"Token: `{token_snippet}` • Visits: `{s['access_count']}`")

                        with col_perm:
                            st.markdown(f"**{perm_str}**")
                            st.caption(f"To: `{recip}`")

                        with col_stat:
                            if status == "Active":
                                st.markdown("🟢 **Active**")
                            elif status == "Expired":
                                st.markdown("🟡 **Expired**")
                            elif status == "Revoked":
                                st.markdown("🔴 **Revoked**")
                            else:
                                st.markdown("⚪ **File Deleted**")
                            st.caption(f"Exp: {expires}")

                        with col_act:
                            b_c1, b_c2 = st.columns([1, 1])
                            with b_c1:
                                if st.button("📋 Link", key=f"btn_my_link_{share_id}", use_container_width=True):
                                    st.session_state[f"show_my_link_{share_id}"] = not st.session_state.get(f"show_my_link_{share_id}", False)
                            with b_c2:
                                if status == "Active":
                                    if st.button("🚫 Revoke", key=f"btn_my_revoke_{share_id}", use_container_width=True):
                                        try:
                                            revoke_share_link(
                                                user_id=current_user["id"],
                                                share_id=share_id,
                                                user_role=current_user.get("role", "user"),
                                            )
                                            st.success("Share link revoked.")
                                            st.rerun()
                                        except Exception as rev_err:
                                            st.error(f"Revoke failed: {rev_err}")
                                else:
                                    st.caption(f"Status: {status}")

                        if st.session_state.get(f"show_my_link_{share_id}"):
                            st.code(s["share_url"], language=None)

                        st.markdown("<hr style='margin: 0.4rem 0; border: none; border-top: 1px dashed #E2E8F0;' />", unsafe_allow_html=True)

        with tab2:
            shared_with_me = list_shares_shared_with_email(current_user.get("email"))

            if not shared_with_me:
                render_empty_file_state(
                    f"No files have been shared directly with '{current_user.get('email')}' yet. "
                    "When another user specifies your email address when creating a share link, it will appear here."
                )
            else:
                st.markdown(f"**Files shared with your account: {len(shared_with_me)}**")
                for s in shared_with_me:
                    s_id = s["id"]
                    fn = s["filename"]
                    owner_name = s["owner_username"]
                    perm_str = "⚡ Download" if s["permission_level"] == "download" else "👁️ View Only"
                    status = s["status"]

                    with st.container():
                        c_info, c_owner, c_stat, c_open = st.columns([3, 1.8, 1.4, 1.8])
                        with c_info:
                            st.markdown(f"📄 **{fn}** (`{s['formatted_size']}`)")
                            st.caption(f"Permission: {perm_str}")
                        with c_owner:
                            st.markdown(f"👤 **{owner_name}**")
                            st.caption(f"Shared: {s['created_at'][:10]}")
                        with c_stat:
                            if status == "Active":
                                st.markdown("🟢 **Active**")
                            elif status == "Expired":
                                st.markdown("🟡 **Expired**")
                            elif status == "Revoked":
                                st.markdown("🔴 **Revoked**")
                            else:
                                st.markdown("⚪ **File Deleted**")
                            st.caption(f"Exp: {s['expires_at'][:16] if s['expires_at'] else 'Never'}")
                        with c_open:
                            if status == "Active":
                                if st.button("📂 Open File", key=f"btn_open_shared_{s_id}", use_container_width=True):
                                    st.query_params["share"] = s["share_token"]
                                    st.rerun()
                            else:
                                st.caption("Unavailable")

                        st.markdown("<hr style='margin: 0.4rem 0; border: none; border-top: 1px dashed #E2E8F0;' />", unsafe_allow_html=True)

    st.divider()

    st.subheader("Security Architecture for Sharing")
    c1, c2 = st.columns(2)
    with c1:
        render_feature_card(
            title="Cryptographic Token Authorization",
            description="Every share link utilizes a 256-bit entropy random URL token, never exposing direct S3 object paths.",
            status="Active (Phase 4C)",
            icon="🔐",
        )
    with c2:
        render_feature_card(
            title="Instant Link Revocation",
            description="File owners and administrators can revoke access instantly, invalidating active access tokens.",
            status="Active (Phase 4C)",
            icon="🚫",
        )
