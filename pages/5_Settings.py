"""Settings and System Diagnostics page."""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_feature_card
from components.sidebar import render_sidebar
from src.aws_storage import S3StorageManager
from src.config import get_config

st.set_page_config(
    page_title="Settings - Cloud File Storage System",
    page_icon="⚙️",
    layout="wide",
)

render_sidebar()
config = get_config()
aws_status = config.get_safe_aws_status()

st.title("⚙️ Settings & Diagnostics")
st.caption("Inspect runtime configurations, cloud connection status, and system policies.")

st.subheader("Cloud Storage Backend (Amazon S3)")

col1, col2 = st.columns(2)
with col1:
    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1.25rem;">
            <h4 style="margin: 0 0 1rem 0; color: #1E293B;">AWS S3 Configuration Status</h4>
            <table style="width: 100%; font-size: 0.85rem; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #F1F5F9;">
                    <td style="padding: 6px 0; color: #64748B;">Operating Mode</td>
                    <td style="padding: 6px 0; font-weight: 600; text-align: right;">{aws_status['mode']}</td>
                </tr>
                <tr style="border-bottom: 1px solid #F1F5F9;">
                    <td style="padding: 6px 0; color: #64748B;">Target AWS Region</td>
                    <td style="padding: 6px 0; font-weight: 600; text-align: right;"><code>{aws_status['region']}</code></td>
                </tr>
                <tr style="border-bottom: 1px solid #F1F5F9;">
                    <td style="padding: 6px 0; color: #64748B;">Configured S3 Bucket</td>
                    <td style="padding: 6px 0; font-weight: 600; text-align: right;"><code>{aws_status['bucket_display']}</code></td>
                </tr>
                <tr style="border-bottom: 1px solid #F1F5F9;">
                    <td style="padding: 6px 0; color: #64748B;">Access Credentials</td>
                    <td style="padding: 6px 0; font-weight: 600; text-align: right;">{aws_status['credentials_status']}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748B;">Environment Tier</td>
                    <td style="padding: 6px 0; font-weight: 600; text-align: right;">{aws_status['environment'].upper()}</td>
                </tr>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1.25rem;">
            <h4 style="margin: 0 0 0.5rem 0; color: #1E293B;">Cloud Connectivity Check</h4>
            <p style="font-size: 0.82rem; color: #64748B; margin-bottom: 1rem;">
                Validate that your IAM credentials have sufficient <code>head_bucket</code>,
                <code>put_object</code>, and <code>get_object</code> permissions against your S3 bucket.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🔍 Test AWS S3 Connectivity", use_container_width=True):
        manager = S3StorageManager(config)
        is_ok, msg = manager.check_bucket_accessibility()
        if is_ok:
            st.success(f"✅ Connection Succeeded: {msg}")
        else:
            st.warning(f"⚠️ Diagnostic Result: {msg}")

st.divider()

st.subheader("System Storage Policies")
c1, c2, c3 = st.columns(3)
with c1:
    render_feature_card(
        title="Upload File Ceiling",
        description=f"Single file payloads are bounded at <strong>{config.max_file_size_mb} MB</strong> to prevent server memory bloat.",
        status="Enforced",
        icon="📏",
    )
with c2:
    render_feature_card(
        title="Default User Quota",
        description=f"New user accounts are initialized with <strong>{config.default_storage_quota_mb} MB</strong> of cloud storage.",
        status="Enforced",
        icon="📦",
    )
with c3:
    render_feature_card(
        title="Share Link Lifetime",
        description=f"Share links cannot exceed <strong>{config.share_link_max_expiry_hours} hours</strong> (7 days) maximum validity.",
        status="Enforced",
        icon="⏳",
    )
