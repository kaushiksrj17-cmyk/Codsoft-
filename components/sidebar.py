"""Standardized navigation sidebar component for Streamlit."""

from __future__ import annotations

import streamlit as st
from src.config import get_config


def render_sidebar() -> None:
    """Render the standard application sidebar across all pages."""
    config = get_config()
    aws_status = config.get_safe_aws_status()

    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
                <div style="font-size: 2.2rem; line-height: 1;">☁️</div>
                <h2 style="margin: 0.2rem 0 0 0; font-size: 1.15rem; font-weight: 700; color: #1E293B;">
                    Cloud Storage
                </h2>
                <span style="font-size: 0.75rem; color: #64748B; letter-spacing: 0.05em; text-transform: uppercase;">
                    CODSOFT Task 1 • S3 Storage
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Cloud Status Badge
        if aws_status["is_configured"]:
            st.markdown(
                f"""
                <div style="background-color: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 0.6rem 0.8rem; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="color: #059669; font-size: 0.85rem;">●</span>
                        <strong style="color: #065F46; font-size: 0.82rem;">Amazon S3 Connected</strong>
                    </div>
                    <div style="font-size: 0.74rem; color: #047857; margin-top: 3px;">
                        Region: <code>{aws_status['region']}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="background-color: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 0.6rem 0.8rem; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="color: #D97706; font-size: 0.85rem;">●</span>
                        <strong style="color: #92400E; font-size: 0.82rem;">Dev Mode (Local)</strong>
                    </div>
                    <div style="font-size: 0.74rem; color: #B45309; margin-top: 3px;">
                        S3 setup pending • Zero cloud charges
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Quota Quick Summary
        st.caption("Storage Allocation")
        st.progress(0.0)
        st.caption(f"0 MB used of {config.default_storage_quota_mb} MB")

        st.divider()

        st.markdown(
            """
            <div style="font-size: 0.75rem; color: #94A3B8; text-align: center;">
                Phase 1 Foundation • Python 3.11<br>
                Amazon S3 + Boto3 + SQLite
            </div>
            """,
            unsafe_allow_html=True,
        )
