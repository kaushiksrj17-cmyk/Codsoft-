"""Upload panel UI component."""

from __future__ import annotations

import streamlit as st
from src.config import get_config


def render_upload_panel_placeholder() -> None:
    """Render the upload panel placeholder with file constraints and Phase 1 notice."""
    config = get_config()

    st.markdown(
        f"""
        <div style="
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        ">
            <h4 style="margin-top: 0; color: #1E293B; display: flex; align-items: center; gap: 8px;">
                <span>📤</span> Upload Files to Cloud Storage
            </h4>
            <p style="color: #64748B; font-size: 0.88rem; margin-bottom: 1rem;">
                Secure file ingestion with SHA-256 integrity verification, automatic MIME detection,
                and direct AES-256 encrypted storage in your private Amazon S3 bucket.
            </p>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;">
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 0.4rem 0.8rem; font-size: 0.78rem;">
                    <strong>Max File Size:</strong> {config.max_file_size_mb} MB
                </div>
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 0.4rem 0.8rem; font-size: 0.78rem;">
                    <strong>Encryption:</strong> Server-Side AES-256
                </div>
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 0.4rem 0.8rem; font-size: 0.78rem;">
                    <strong>Access:</strong> Private & User-Scoped
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "ℹ️ **Phase 1 Status:** File upload controls and live S3 streaming will be enabled in Phase 2 "
        "once database and cloud permissions are reviewed. To prepare your bucket, review `docs/AWS_SETUP.md`."
    )
