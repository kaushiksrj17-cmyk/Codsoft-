"""Cloud File Storage System - Main Application Entry Point.

CODSOFT Cloud Computing Internship - Task 1.
Architecture: Streamlit UI + Amazon S3 Object Storage + SQLite/PostgreSQL Metadata Store.
"""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_feature_card, render_metric_card
from components.sidebar import render_sidebar
try:
    from components.styles import inject_custom_styles
except (ImportError, ModuleNotFoundError):
    from components import inject_custom_styles
from src.config import get_config

# 1. Page Configuration
st.set_page_config(
    page_title="Cloud File Storage System",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Inject Modern Design System
inject_custom_styles()

# 3. Standard Navigation Sidebar
render_sidebar()
config = get_config()
aws_status = config.get_safe_aws_status()

# Query param routing for share links
if st.query_params.get("share"):
    st.switch_page("pages/3_Shared_Files.py")

# 4. Premium Hero Banner (Zero-indent HTML)
hero_html = """<div class="hero-banner">
<div class="hero-badge">
<span>🛡️</span> CODSOFT Cloud Computing Internship • Task 1
</div>
<h1 class="hero-title">Cloud File Storage System</h1>
<p class="hero-subtitle">
Enterprise-grade secure cloud file storage engine built on Amazon S3 object storage,
fast relational metadata indexing, role-based access control (RBAC), and cryptographically signed sharing links.
</p>
<div class="hero-tags">
<span class="hero-tag">☁️ Amazon S3 (ap-south-1)</span>
<span class="hero-tag">🔒 AES-256 Server-Side Encryption</span>
<span class="hero-tag">🛡️ SHA-256 Integrity Verification</span>
<span class="hero-tag">⚡ Presigned SigV4 Direct Transfers</span>
<span class="hero-tag">👥 Multi-Tenant Isolation</span>
</div>
</div>"""
st.markdown(hero_html, unsafe_allow_html=True)

# 5. Cloud Storage Status Indicator Banner (Zero-indent HTML)
if aws_status["is_configured"]:
    status_html = f"""<div style="background: linear-gradient(135deg, rgba(6, 78, 59, 0.4) 0%, rgba(15, 23, 42, 0.8) 100%); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 14px; padding: 1.1rem 1.4rem; margin-bottom: 2rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 15px rgba(16, 185, 129, 0.15); backdrop-filter: blur(12px);">
<div style="display: flex; align-items: center; gap: 14px;">
<div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(6, 78, 59, 0.6); border: 1px solid rgba(52, 211, 153, 0.3); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; box-shadow: 0 0 12px rgba(16, 185, 129, 0.2);">☁️</div>
<div>
<div style="display: flex; align-items: center; gap: 8px;">
<span class="beacon-live"></span>
<strong style="color: #34D399; font-size: 0.98rem; font-weight: 800;">Amazon S3 Connected & Operational</strong>
</div>
<div style="color: #94A3B8; font-size: 0.82rem; margin-top: 3px;">
Target Region: <code>{aws_status['region']}</code> • Bucket: <code>{aws_status['bucket_display']}</code> • Encryption: <strong style="color: #F8FAFC;">SSE-S3 (AES-256)</strong>
</div>
</div>
</div>
<span class="status-pill status-pill-ok">
<span class="beacon-live"></span> Live Cloud Active
</span>
</div>"""
    st.markdown(status_html, unsafe_allow_html=True)
else:
    status_html = f"""<div style="background: linear-gradient(135deg, rgba(120, 53, 15, 0.35) 0%, rgba(15, 23, 42, 0.8) 100%); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 14px; padding: 1.1rem 1.4rem; margin-bottom: 2rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 15px rgba(245, 158, 11, 0.15); backdrop-filter: blur(12px);">
<div style="display: flex; align-items: center; gap: 14px;">
<div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(120, 53, 15, 0.5); border: 1px solid rgba(245, 158, 11, 0.3); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; box-shadow: 0 0 12px rgba(245, 158, 11, 0.2);">⚠️</div>
<div>
<div style="display: flex; align-items: center; gap: 8px;">
<span class="beacon-pending"></span>
<strong style="color: #FBBF24; font-size: 0.98rem; font-weight: 800;">Development Sandbox Mode Active (S3 Setup Pending)</strong>
</div>
<div style="color: #94A3B8; font-size: 0.82rem; margin-top: 3px;">
AWS credentials or bucket name are currently placeholder values. Zero cloud charges are incurred.<br>
Follow the checklist in <code>docs/AWS_SETUP.md</code> to connect your private S3 bucket.
</div>
</div>
</div>
<span class="status-pill status-pill-pending">
<span class="beacon-pending"></span> Dev Environment
</span>
</div>"""
    st.markdown(status_html, unsafe_allow_html=True)

# 6. High-Level System Telemetry Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card(
        title="Storage Backend",
        value="Amazon S3",
        subtitle=f"Region: {aws_status['region']}",
        icon="☁️",
    )
with col2:
    render_metric_card(
        title="Metadata Store",
        value="SQLite",
        subtitle="Ready for PostgreSQL",
        icon="🗄️",
    )
with col3:
    render_metric_card(
        title="Upload Ceiling",
        value=f"{config.max_file_size_mb} MB",
        subtitle="Per single file upload",
        icon="📏",
    )
with col4:
    render_metric_card(
        title="User Base Quota",
        value=f"{config.default_storage_quota_mb} MB",
        subtitle="Enforced on tenant accounts",
        icon="📦",
    )

st.write("")
st.subheader("System Architecture & Implementation Roadmap")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 🚀 Phase 1 Foundation Status")
    render_feature_card(
        title="Central Configuration & Environment Validation",
        description="Type-safe configuration loader with safe dummy credential detection and zero secret exposure.",
        status="Active (Phase 1)",
        icon="⚙️",
    )
    render_feature_card(
        title="SQLite & PostgreSQL Metadata Schema",
        description="Normalized relational schema covering users, file metadata, multi-versions, share links, and activity logs.",
        status="Active (Phase 1)",
        icon="🗄️",
    )
    render_feature_card(
        title="Input Validation & Path Traversal Defense",
        description="Strict filename sanitization, Windows reserved character prevention, and executable extension blocking.",
        status="Active (Phase 1)",
        icon="🛡️",
    )
    render_feature_card(
        title="Role-Based Access Control (RBAC)",
        description="Permission matrix for file viewing, downloading, editing, and deletion with owner-tenant isolation.",
        status="Active (Phase 1)",
        icon="🔒",
    )

with col_right:
    st.markdown("#### 🗺️ Next Milestones (Phase 2+)")
    render_feature_card(
        title="Direct Amazon S3 File Ingestion",
        description="Multi-part streaming upload to private S3 bucket with SHA-256 integrity checks and quota deduction.",
        status="Active (Phase 2)",
        icon="📤",
    )
    render_feature_card(
        title="Presigned Download URLs",
        description="Direct-from-S3 authenticated download URLs with short expiration periods, eliminating server bottlenecks.",
        status="Active (Phase 2)",
        icon="⚡",
    )
    render_feature_card(
        title="Cryptographic File Sharing Links",
        description="Time-limited URL sharing with token validation, access counter tracking, and instant owner revocation.",
        status="Active (Phase 2)",
        icon="🔗",
    )
    render_feature_card(
        title="Multi-Version File Management",
        description="Automated version archiving when overwriting existing filenames with restore capabilities.",
        status="Active (Phase 3)",
        icon="🕒",
    )

st.divider()

# Navigation Quick Links - Modern Interactive Card Grid
st.markdown("#### 🧭 Dashboard Quick Navigation")
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.markdown("""<div class="nav-card">
<div>
<div style="font-size: 1.5rem; margin-bottom: 0.4rem;">📁</div>
<strong style="color: #0F172A; font-size: 1rem;">1. My Files (Cloud Catalog)</strong>
<p style="color: #64748B; font-size: 0.82rem; margin: 0.35rem 0 0 0; line-height: 1.45;">
Personal cloud explorer, drag-and-drop file ingestion, SHA-256 checksum tags, and file catalog.
</p>
</div>
<div style="margin-top: 0.8rem; font-size: 0.75rem; color: #A78BFA; font-weight: 700;">Open Explorer →</div>
</div>""", unsafe_allow_html=True)

with nav_col2:
    st.markdown("""<div class="nav-card">
<div>
<div style="font-size: 1.5rem; margin-bottom: 0.4rem;">📊</div>
<strong style="color: #0F172A; font-size: 1rem;">2. Storage Analytics</strong>
<p style="color: #64748B; font-size: 0.82rem; margin: 0.35rem 0 0 0; line-height: 1.45;">
Storage quota consumption breakdown, file categories, capacity metering, and analytics.
</p>
</div>
<div style="margin-top: 0.8rem; font-size: 0.75rem; color: #A78BFA; font-weight: 700;">View Analytics →</div>
</div>""", unsafe_allow_html=True)

with nav_col3:
    st.markdown("""<div class="nav-card">
<div>
<div style="font-size: 1.5rem; margin-bottom: 0.4rem;">🔗</div>
<strong style="color: #0F172A; font-size: 1rem;">3. Shared Files & Links</strong>
<p style="color: #64748B; font-size: 0.82rem; margin: 0.35rem 0 0 0; line-height: 1.45;">
Cryptographic share tokens, time-expiring links, permission enforcement, and access metrics.
</p>
</div>
<div style="margin-top: 0.8rem; font-size: 0.75rem; color: #A78BFA; font-weight: 700;">Manage Shares →</div>
</div>""", unsafe_allow_html=True)

st.write("")
nav_col4, nav_col5, nav_col6 = st.columns(3)
with nav_col4:
    st.markdown("""<div class="nav-card">
<div>
<div style="font-size: 1.5rem; margin-bottom: 0.4rem;">📜</div>
<strong style="color: #0F172A; font-size: 1rem;">4. Security Audit History</strong>
<p style="color: #64748B; font-size: 0.82rem; margin: 0.35rem 0 0 0; line-height: 1.45;">
Comprehensive immutable audit logs, mutation trails, and access compliance records.
</p>
</div>
<div style="margin-top: 0.8rem; font-size: 0.75rem; color: #A78BFA; font-weight: 700;">Audit Trails →</div>
</div>""", unsafe_allow_html=True)

with nav_col5:
    st.markdown("""<div class="nav-card">
<div>
<div style="font-size: 1.5rem; margin-bottom: 0.4rem;">⚙️</div>
<strong style="color: #0F172A; font-size: 1rem;">5. S3 Settings & Diagnostics</strong>
<p style="color: #64748B; font-size: 0.82rem; margin: 0.35rem 0 0 0; line-height: 1.45;">
Amazon S3 live connectivity tester, system thresholds, and runtime policy diagnostics.
</p>
</div>
<div style="margin-top: 0.8rem; font-size: 0.75rem; color: #A78BFA; font-weight: 700;">Open Diagnostics →</div>
</div>""", unsafe_allow_html=True)

with nav_col6:
    st.markdown("""<div class="nav-card">
<div>
<div style="font-size: 1.5rem; margin-bottom: 0.4rem;">👑</div>
<strong style="color: #0F172A; font-size: 1rem;">6. Admin Management Console</strong>
<p style="color: #64748B; font-size: 0.82rem; margin: 0.35rem 0 0 0; line-height: 1.45;">
Multi-tenant oversight, quota adjustment console, system telemetry, and user management.
</p>
</div>
<div style="margin-top: 0.8rem; font-size: 0.75rem; color: #A78BFA; font-weight: 700;">Admin Portal →</div>
</div>""", unsafe_allow_html=True)
