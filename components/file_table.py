"""File list and table rendering component with modern cloud storage aesthetics."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import streamlit as st


def render_empty_file_state(message: Optional[str] = None) -> None:
    """Render an informative, beautifully styled empty state when no files exist."""
    msg = message or "No files uploaded yet. Files stored in your private S3 bucket will appear here."
    html = f"""<div style="text-align: center; padding: 3.5rem 2rem; background: rgba(15, 23, 42, 0.75); border: 2px dashed rgba(139, 92, 246, 0.35); border-radius: 18px; margin: 1.8rem 0; box-shadow: 0 4px 25px rgba(0, 0, 0, 0.45); backdrop-filter: blur(12px);">
<div style="display: inline-flex; align-items: center; justify-content: center; width: 64px; height: 64px; border-radius: 18px; background: rgba(99, 102, 241, 0.2); color: #C4B5FD; font-size: 2rem; margin-bottom: 1rem; border: 1px solid rgba(139, 92, 246, 0.35); box-shadow: 0 0 15px rgba(139, 92, 246, 0.3);">
📂
</div>
<h4 style="color: #F8FAFC; margin: 0 0 0.4rem 0; font-weight: 800; font-size: 1.2rem;">
No Files in Bucket
</h4>
<p style="color: #94A3B8; font-size: 0.9rem; max-width: 440px; margin: 0 auto; line-height: 1.5;">
{msg}
</p>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_share_form(f: Dict[str, Any], user: Dict[str, Any]) -> None:
    """Render form controls to create a secure share link for a file."""
    from src.sharing import create_share_link

    file_id = f["id"]
    filename = f["original_name"]
    st.markdown(
        f"Generate a cryptographically secure, time-limited share link for **{filename}**."
    )

    perm = st.selectbox(
        "Permission Level",
        options=["view", "download"],
        format_func=lambda x: (
            "👁️ View Only (Preview & Metadata)"
            if x == "view"
            else "⚡ Download (Permits S3 file download)"
        ),
        key=f"share_perm_select_{file_id}",
    )
    exp = st.selectbox(
        "Expiration Duration",
        options=[1, 24, 72, 168],
        index=1,
        format_func=lambda h: f"{h} Hour" if h == 1 else f"{h // 24} Days ({h}h)",
        key=f"share_exp_select_{file_id}",
    )
    email = st.text_input(
        "Recipient Email (Optional)",
        placeholder="collaborator@example.com",
        help="Leave blank to allow anyone with the secure token to access.",
        key=f"share_email_input_{file_id}",
    )

    if st.button(
        "✨ Generate Share Link",
        key=f"btn_gen_link_{file_id}",
        type="primary",
        use_container_width=True,
    ):
        try:
            res = create_share_link(
                user_id=user["id"],
                file_id=file_id,
                user_role=user.get("role", "user"),
                permission_level=perm,
                expires_in_hours=exp,
                shared_with_email=email,
            )
            st.session_state[f"share_res_{file_id}"] = res
            st.success("✅ Secure share link generated!")
        except Exception as share_err:
            st.error(f"Failed to generate share link: {share_err}")

    if st.session_state.get(f"share_res_{file_id}"):
        res = st.session_state[f"share_res_{file_id}"]
        st.markdown("#### 🔗 Your Share Link")
        st.code(res["share_url"], language=None)
        st.caption("Copy the link above to share with your recipient.")
        st.info(
            f"**Security Policy:** Token lifespan: `{exp}h` • Permission: `{perm.upper()}`"
            + (f" • Restricted to: `{email}`" if email else " • Token-authorized")
        )


if hasattr(st, "dialog"):

    @st.dialog("🔗 Share File")
    def _open_share_dialog(f: Dict[str, Any], user: Dict[str, Any]) -> None:
        render_share_form(f, user)

else:

    def _open_share_dialog(f: Dict[str, Any], user: Dict[str, Any]) -> None:
        st.session_state[f"show_inline_share_{f['id']}"] = True


def render_file_table(
    files: List[Dict[str, Any]],
    current_user: Optional[Dict[str, Any]] = None,
    storage_manager: Optional[Any] = None,
) -> None:
    """Render interactive file metadata table with download, share, delete, and version history actions."""
    if not files:
        render_empty_file_state(
            "No files found matching your search. Upload a file above to get started."
        )
        return

    from src.aws_storage import S3StorageManager
    from src.config import get_config
    from src.file_service import (
        delete_file,
        download_file,
        download_historical_version,
        get_file_version_history,
    )

    user = current_user or st.session_state.get("current_user")
    cfg = get_config()
    mgr = storage_manager or S3StorageManager(cfg)

    catalog_header_html = f"""<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.8rem;">
<span style="font-size: 0.95rem; font-weight: 700; color: #F8FAFC;">
Catalog Results: <strong style="color: #A78BFA;">{len(files)}</strong> file{'s' if len(files) != 1 else ''}
</span>
<span style="font-size: 0.74rem; color: #34D399; font-weight: 600; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(52, 211, 153, 0.3); padding: 3px 8px; border-radius: 6px;">
🔒 SSE-S3 AES-256 Protected
</span>
</div>"""
    st.markdown(catalog_header_html, unsafe_allow_html=True)

    category_icons = {
        "Documents": "📄",
        "Images": "🖼️",
        "Archives": "📦",
        "Media": "🎬",
        "Other": "📁",
    }

    for f in files:
        file_id = f["id"]
        filename = f["original_name"]
        size_str = f.get("formatted_size", f"{f['file_size_bytes']} B")
        version_lbl = f.get("version_label", f"v{f.get('current_version', 1)}")
        category = f.get("category", "Document")
        checksum = f.get("checksum_sha256", "N/A")
        created_at = f.get("created_at", "")[:19]
        icon = category_icons.get(category, "📄")

        sha_html = f'<div style="font-size: 0.72rem; color: #94A3B8; font-family: monospace; margin-top: 2px;">SHA-256: {checksum[:16]}...</div>' if checksum and checksum != 'N/A' else ''

        row_html = f"""<div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 0.9rem 1.15rem; margin-bottom: 0.5rem; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); backdrop-filter: blur(8px);">
<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
<div style="display: flex; align-items: center; gap: 10px;">
<span style="font-size: 1.3rem;">{icon}</span>
<div>
<strong style="color: #F8FAFC; font-size: 0.95rem;">{filename}</strong>
<span style="font-size: 0.68rem; background: rgba(99, 102, 241, 0.2); color: #C4B5FD; border: 1px solid rgba(139, 92, 246, 0.3); font-weight: 700; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">
{version_lbl}
</span>
{sha_html}
</div>
</div>
<div style="display: flex; align-items: center; gap: 16px; font-size: 0.78rem; color: #94A3B8;">
<span>📦 <strong style="color: #F8FAFC;">{size_str}</strong></span>
<span>🏷️ {category}</span>
<span>📅 {created_at}</span>
</div>
</div>
</div>"""
        st.markdown(row_html, unsafe_allow_html=True)

        # Action Toolbar
        act_col1, act_col2, act_col3 = st.columns([1, 1, 1])
        with act_col1:
            if st.button(
                "⚡ Download",
                key=f"btn_dl_{file_id}",
                use_container_width=True,
            ):
                if not user:
                    st.error("Please sign in to download files.")
                else:
                    try:
                        dl_res = download_file(
                            user_id=user["id"],
                            file_id=file_id,
                            user_role=user.get("role", "user"),
                            expires_in_seconds=300,
                            storage_manager=mgr,
                            config=cfg,
                        )
                        st.session_state[f"dl_url_{file_id}"] = dl_res[
                            "download_url"
                        ]
                    except Exception as dl_err:
                        st.error(f"Download failed: {dl_err}")

        with act_col2:
            if st.button(
                "🔗 Share",
                key=f"btn_share_{file_id}",
                use_container_width=True,
            ):
                if not user:
                    st.error("Please sign in to share files.")
                else:
                    _open_share_dialog(f, user)

        with act_col3:
            if st.button(
                "🗑️ Delete",
                key=f"btn_del_init_{file_id}",
                use_container_width=True,
            ):
                st.session_state[f"confirm_delete_{file_id}"] = True

        # If download URL generated, display direct download link banner
        if st.session_state.get(f"dl_url_{file_id}"):
            url = st.session_state[f"dl_url_{file_id}"]
            dl_banner_html = f"""<div style="background: linear-gradient(135deg, rgba(30, 27, 75, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%); border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 10px; padding: 10px 14px; margin: 6px 0 10px 0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; box-shadow: 0 0 15px rgba(139, 92, 246, 0.25);">
<span style="color: #C4B5FD; font-size: 0.85rem; font-weight: 600;">
✅ Presigned S3 URL generated for <strong style="color: #FFFFFF;">{filename}</strong> (Valid 5m)
</span>
<a href="{url}" target="_blank" style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #EC4899 100%); color: #FFFFFF; padding: 6px 16px; border-radius: 8px; text-decoration: none; font-size: 0.82rem; font-weight: 700; box-shadow: 0 0 14px rgba(124, 58, 237, 0.5);">
⬇️ Direct Download
</a>
</div>"""
            st.markdown(dl_banner_html, unsafe_allow_html=True)

        # If share link generated in active session, display share banner
        if st.session_state.get(f"share_res_{file_id}"):
            s_res = st.session_state[f"share_res_{file_id}"]
            share_banner_html = f"""<div style="background: linear-gradient(135deg, rgba(6, 78, 59, 0.5) 0%, rgba(15, 23, 42, 0.9) 100%); border: 1px solid rgba(52, 211, 153, 0.4); border-radius: 10px; padding: 10px 14px; margin: 6px 0 10px 0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);">
<span style="color: #34D399; font-size: 0.84rem; font-weight: 600;">
🔗 Active Share Link: <code>{s_res['share_url']}</code> ({s_res['permission_level'].upper()})
</span>
</div>"""
            st.markdown(share_banner_html, unsafe_allow_html=True)

        # Inline fallback sharing panel if st.dialog is not used
        if st.session_state.get(f"show_inline_share_{file_id}"):
            with st.container():
                st.info(f"🔗 Sharing **{filename}**")
                render_share_form(f, user)
                if st.button(
                    "Close Sharing Panel", key=f"btn_close_share_{file_id}"
                ):
                    st.session_state[f"show_inline_share_{file_id}"] = False
                    st.rerun()

        # Deletion confirmation banner
        if st.session_state.get(f"confirm_delete_{file_id}"):
            with st.container():
                st.warning(
                    f"⚠️ Are you sure you want to delete **{filename}**? Storage quota will be recovered."
                )
                c_yes, c_no = st.columns([1, 1])
                with c_yes:
                    if st.button(
                        "🔴 Confirm Delete",
                        key=f"btn_del_confirm_{file_id}",
                        use_container_width=True,
                    ):
                        if not user:
                            st.error("Please sign in to delete files.")
                        else:
                            try:
                                res = delete_file(
                                    user_id=user["id"],
                                    file_id=file_id,
                                    user_role=user.get("role", "user"),
                                    storage_manager=mgr,
                                    config=cfg,
                                    )
                                st.session_state[
                                    f"confirm_delete_{file_id}"
                                ] = False
                                st.session_state.pop(f"dl_url_{file_id}", None)
                                st.success(
                                    f"Deleted '{filename}'. Freed {res['formatted_freed']} storage."
                                )
                                st.rerun()
                            except Exception as del_err:
                                st.error(f"Deletion failed: {del_err}")
                with c_no:
                    if st.button(
                        "Cancel",
                        key=f"btn_del_cancel_{file_id}",
                        use_container_width=True,
                    ):
                        st.session_state[f"confirm_delete_{file_id}"] = False
                        st.rerun()

        # Version History expander
        with st.expander(f"🕒 Version History ({version_lbl})", expanded=False):
            if not user:
                st.caption("Sign in to view version history.")
            else:
                try:
                    history = get_file_version_history(
                        user_id=user["id"],
                        file_id=file_id,
                        user_role=user.get("role", "user"),
                    )
                    if history:
                        for v in history:
                            v_num = v["version_number"]
                            v_size = v["formatted_size"]
                            v_date = v.get("created_at", "")[:19]
                            v_sha = v.get("checksum_sha256", "N/A")
                            is_curr = v.get("is_current", False)

                            badge = (
                                "🟢 **Current Version**"
                                if is_curr
                                else "⚪ Archived Version"
                            )
                            v_col1, v_col2, v_col3, v_col4 = st.columns(
                                [2, 2, 3, 2]
                            )
                            with v_col1:
                                st.markdown(f"**v{v_num}** {badge}")
                            with v_col2:
                                st.caption(f"📦 {v_size} • 📅 {v_date}")
                            with v_col3:
                                if v_sha and v_sha != "N/A":
                                    st.caption(f"SHA-256: `{v_sha[:16]}...`")
                            with v_col4:
                                if st.button(
                                    f"⬇️ v{v_num}",
                                    key=f"btn_hdl_{file_id}_{v_num}",
                                    use_container_width=True,
                                ):
                                    try:
                                        h_res = download_historical_version(
                                            user_id=user["id"],
                                            file_id=file_id,
                                            version_number=v_num,
                                            user_role=user.get("role", "user"),
                                            storage_manager=mgr,
                                            config=cfg,
                                        )
                                        st.session_state[
                                            f"hdl_url_{file_id}_{v_num}"
                                        ] = h_res["download_url"]
                                    except Exception as h_err:
                                        st.error(
                                            f"Historical download failed: {h_err}"
                                        )

                            if st.session_state.get(
                                f"hdl_url_{file_id}_{v_num}"
                            ):
                                h_url = st.session_state[
                                    f"hdl_url_{file_id}_{v_num}"
                                ]
                                st.markdown(
                                    f"<a href='{h_url}' target='_blank' style='font-size:0.8rem; color:#2563EB;'>🔗 Click to download version {v_num}</a>",
                                    unsafe_allow_html=True,
                                )
                            st.markdown(
                                "<hr style='margin: 0.3rem 0; border: none; border-top: 1px dashed #E2E8F0;' />",
                                unsafe_allow_html=True,
                            )
                    else:
                        st.caption("No historical versions recorded.")
                except Exception as hist_err:
                    st.caption(f"Could not load version history: {hist_err}")

        st.markdown(
            "<hr style='margin: 0.6rem 0; border: none; border-top: 1px solid #F1F5F9;' />",
            unsafe_allow_html=True,
        )
