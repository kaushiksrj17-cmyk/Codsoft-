"""Upload panel UI component with enterprise-grade aesthetics."""

from __future__ import annotations

from typing import Any
import streamlit as st
from src.config import get_config


def render_upload_panel_placeholder() -> None:
    """Render the upload panel placeholder with file constraints."""
    config = get_config()

    html = f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(139, 92, 246, 0.25); border-radius: 16px; padding: 1.6rem 1.8rem; margin-bottom: 1.6rem; box-shadow: 0 4px 25px rgba(0, 0, 0, 0.5), 0 0 15px rgba(99, 102, 241, 0.12); backdrop-filter: blur(12px);">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.6rem; flex-wrap: wrap; gap: 8px;">
<h4 style="margin: 0; color: #F8FAFC; font-weight: 800; font-size: 1.15rem; display: flex; align-items: center; gap: 10px;">
<span>📤</span> Upload Files to Cloud Storage
</h4>
<span style="font-size: 0.72rem; font-weight: 700; color: #C4B5FD; background: rgba(139, 92, 246, 0.2); border: 1px solid rgba(139, 92, 246, 0.4); padding: 3px 10px; border-radius: 9999px;">
AMAZON S3 INGESTION
</span>
</div>
<p style="color: #94A3B8; font-size: 0.88rem; margin-bottom: 1.2rem; line-height: 1.5;">
Secure file ingestion with SHA-256 integrity verification, automatic MIME detection,
and direct AES-256 encrypted storage in your private Amazon S3 bucket.
</p>
<div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
<div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 0.45rem 0.85rem; font-size: 0.76rem; color: #CBD5E1;">
📏 <strong>Max Size:</strong> {config.max_file_size_mb} MB
</div>
<div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 0.45rem 0.85rem; font-size: 0.76rem; color: #CBD5E1;">
🔒 <strong>Encryption:</strong> Server-Side AES-256
</div>
<div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 0.45rem 0.85rem; font-size: 0.76rem; color: #CBD5E1;">
🛡️ <strong>Access:</strong> Tenant-Isolated Prefix
</div>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_upload_panel(user: dict[str, Any]) -> None:
    """Render the active, functional file upload panel with pre-flight checks and S3 ingestion."""
    from src.file_service import get_file_category, upload_file
    from src.file_validation import (
        get_content_type,
        validate_file_extension,
        validate_file_size,
        validate_filename,
    )
    from src.storage_quota import check_quota_availability, format_bytes

    config = get_config()

    panel_html = f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(139, 92, 246, 0.25); border-radius: 16px; padding: 1.6rem 1.8rem; margin-bottom: 1.6rem; box-shadow: 0 4px 25px rgba(0, 0, 0, 0.5), 0 0 15px rgba(99, 102, 241, 0.12); backdrop-filter: blur(12px);">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.6rem; flex-wrap: wrap; gap: 8px;">
<h4 style="margin: 0; color: #F8FAFC; font-weight: 800; font-size: 1.15rem; display: flex; align-items: center; gap: 10px;">
<span>📤</span> Upload Files to Amazon S3
</h4>
<span style="font-size: 0.72rem; font-weight: 700; color: #34D399; background: rgba(16, 185, 129, 0.2); border: 1px solid rgba(52, 211, 153, 0.35); padding: 3px 10px; border-radius: 9999px;">
● ACTIVE INGESTION
</span>
</div>
<p style="color: #94A3B8; font-size: 0.88rem; margin-bottom: 1.2rem; line-height: 1.5;">
Files are cryptographically verified via SHA-256 before transfer, categorized by MIME type,
and securely written to your private tenant S3 partition with AES-256 server-side encryption.
</p>
<div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
<div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 0.45rem 0.85rem; font-size: 0.76rem; color: #CBD5E1;">
📏 <strong>Limit:</strong> {config.max_file_size_mb} MB
</div>
<div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 0.45rem 0.85rem; font-size: 0.76rem; color: #CBD5E1;">
🔒 <strong>Cipher:</strong> SSE-S3 (AES-256)
</div>
<div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 0.45rem 0.85rem; font-size: 0.76rem; color: #CBD5E1;">
🛡️ <strong>Integrity:</strong> SHA-256 Checksum
</div>
<div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 0.45rem 0.85rem; font-size: 0.76rem; color: #CBD5E1;">
📁 <strong>Prefix:</strong> <code>users/{user['id']}/files/</code>
</div>
</div>
</div>"""
    st.markdown(panel_html, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a file to upload",
        accept_multiple_files=False,
        key="s3_active_file_uploader",
        help=f"Allowed files up to {config.max_file_size_mb} MB. Executable binaries (.exe, .bat, etc.) are strictly prohibited.",
    )

    if uploaded_file is not None:
        filename = uploaded_file.name
        size_bytes = uploaded_file.size
        content_type = get_content_type(filename)
        category = get_file_category(filename)
        formatted_sz = format_bytes(size_bytes)

        # Pre-flight Validation
        fn_ok, fn_msg = validate_filename(filename)
        ext_ok, ext_msg = validate_file_extension(filename)
        sz_ok, sz_msg = validate_file_size(size_bytes, config.max_file_size_bytes)
        quota_ok, quota_msg = check_quota_availability(
            user["used_storage_bytes"], user["storage_quota_bytes"], size_bytes
        )

        preview_html = f"""<div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1rem; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4); backdrop-filter: blur(8px);">
<div style="font-weight: 700; color: #F8FAFC; font-size: 0.98rem; display: flex; align-items: center; justify-content: space-between;">
<span>📄 {filename}</span>
<span style="font-size: 0.72rem; background: rgba(99, 102, 241, 0.25); color: #C4B5FD; border: 1px solid rgba(139, 92, 246, 0.35); font-weight: 700; padding: 3px 8px; border-radius: 6px;">
{category}
</span>
</div>
<div style="font-size: 0.8rem; color: #94A3B8; margin-top: 6px; display: flex; gap: 18px; flex-wrap: wrap;">
<span>Size: <strong style="color: #F8FAFC;">{formatted_sz}</strong></span>
<span>MIME: <code>{content_type}</code></span>
<span>Tenant: <code>users/{user['id']}</code></span>
</div>
</div>"""
        st.markdown(preview_html, unsafe_allow_html=True)

        if not fn_ok:
            st.error(f"❌ Invalid Filename: {fn_msg}")
        elif not ext_ok:
            st.error(f"🛑 Prohibited File Type: {ext_msg}")
        elif not sz_ok:
            st.error(f"⚠️ Size Limit Exceeded: {sz_msg}")
        elif not quota_ok:
            st.error(f"📦 Quota Exceeded: {quota_msg}")
        else:
            if st.button("🚀 Confirm & Upload to Amazon S3", type="primary", use_container_width=True):
                with st.spinner("Encrypting payload and transferring to Amazon S3..."):
                    try:
                        file_bytes = uploaded_file.getvalue()
                        res = upload_file(
                            user_id=user["id"],
                            file_bytes=file_bytes,
                            filename=filename,
                            config=config,
                        )
                        st.success(
                            f"✅ Successfully uploaded **{res['filename']}** ({res['formatted_size']})! "
                            f"Version: `v{res['version']}` • SHA-256 Checksum: `[{res['checksum'][:16]}...]`"
                        )
                        st.rerun()
                    except Exception as err:
                        st.error(f"❌ Upload Failed: {err}")
