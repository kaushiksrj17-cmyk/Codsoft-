"""Settings and System Diagnostics page."""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_feature_card
from components.sidebar import render_sidebar
from src.aws_storage import S3StorageManager
from src.config import get_config
from src.permissions import is_admin

st.set_page_config(
    page_title="Settings - Cloud File Storage System",
    page_icon="⚙️",
    layout="wide",
)

render_sidebar()
config = get_config()

current_user = st.session_state.get("current_user")
if not current_user:
    st.title("⚙️ Settings & System Diagnostics")
    st.info("🔒 **Sign In Required:** Please sign in via the sidebar to view system settings and diagnostics.")
    st.stop()

aws_status = config.get_safe_aws_status()

st.title("⚙️ Settings & System Diagnostics")
st.caption("Inspect runtime configurations, cloud connection status, and system security policies.")

st.subheader("Cloud Storage Backend (Amazon S3)")

col1, col2 = st.columns(2)
with col1:
    telemetry_html = f"""<div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 1.4rem 1.6rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); backdrop-filter: blur(12px);">
<h4 style="margin: 0 0 1rem 0; color: #F8FAFC; font-weight: 800; font-size: 1.05rem;">
AWS S3 Configuration Telemetry
</h4>
<table style="width: 100%; font-size: 0.85rem; border-collapse: collapse;">
<tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
<td style="padding: 8px 0; color: #94A3B8;">Operating Mode</td>
<td style="padding: 8px 0; font-weight: 700; text-align: right; color: #F8FAFC;">{aws_status['mode']}</td>
</tr>
<tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
<td style="padding: 8px 0; color: #94A3B8;">Target AWS Region</td>
<td style="padding: 8px 0; font-weight: 700; text-align: right;"><code>{aws_status['region']}</code></td>
</tr>
<tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
<td style="padding: 8px 0; color: #94A3B8;">Configured S3 Bucket</td>
<td style="padding: 8px 0; font-weight: 700; text-align: right;"><code>{aws_status['bucket_display']}</code></td>
</tr>
<tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
<td style="padding: 8px 0; color: #94A3B8;">Access Credentials</td>
<td style="padding: 8px 0; font-weight: 700; text-align: right; color: #34D399;">{aws_status['credentials_status']}</td>
</tr>
<tr>
<td style="padding: 8px 0; color: #94A3B8;">Environment Tier</td>
<td style="padding: 8px 0; font-weight: 700; text-align: right;">
<span style="background: rgba(99, 102, 241, 0.2); color: #C4B5FD; border: 1px solid rgba(139, 92, 246, 0.35); font-size: 0.72rem; padding: 2px 8px; border-radius: 9999px;">
{aws_status['environment'].upper()}
</span>
</td>
</tr>
</table>
</div>"""
    st.markdown(telemetry_html, unsafe_allow_html=True)

with col2:
    probe_html = """<div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 1.4rem 1.6rem; margin-bottom: 1rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); backdrop-filter: blur(12px);">
<h4 style="margin: 0 0 0.5rem 0; color: #F8FAFC; font-weight: 800; font-size: 1.05rem;">
Cloud Connectivity Probe
</h4>
<p style="font-size: 0.83rem; color: #94A3B8; margin-bottom: 0.6rem; line-height: 1.5;">
Validates that configured IAM credentials have active <code>head_bucket</code>,
<code>put_object</code>, and <code>get_object</code> permissions against the target S3 bucket.
</p>
</div>"""
    st.markdown(probe_html, unsafe_allow_html=True)
    if st.button("🔍 Test AWS S3 Connectivity", use_container_width=True, type="primary"):
        if not is_admin(current_user.get("role", "user")):
            st.error("🚫 Administrative privileges required to run cloud connectivity tests.")
        else:
            with st.spinner("Probing Amazon S3 bucket permissions..."):
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
