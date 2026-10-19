"""Cloud File Storage System - Main Application Entry Point.

CODSOFT Cloud Computing Internship - Task 1.
Architecture: Streamlit UI + Amazon S3 Object Storage + SQLite/PostgreSQL Metadata Store.
"""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_feature_card, render_metric_card
from components.sidebar import render_sidebar
from src.config import get_config

# 1. Page Configuration
st.set_page_config(
    page_title="Cloud File Storage System",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Modern Custom Styling
st.markdown(
    """
    <style>
        /* Modern font hierarchy & color tokens */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        /* Hero banner container */
        .hero-banner {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #2563EB 100%);
            border-radius: 16px;
            padding: 2.2rem 2.5rem;
            color: #FFFFFF;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        }

        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(8px);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 0.8rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .hero-title {
            font-size: 2.3rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin: 0 0 0.5rem 0;
            line-height: 1.15;
            color: #FFFFFF;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            color: #CBD5E1;
            margin: 0;
            max-width: 720px;
            line-height: 1.5;
        }

        /* Status Pills */
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 600;
        }

        .status-pill-ok {
            background-color: #ECFDF5;
            color: #065F46;
            border: 1px solid #A7F3D0;
        }

        .status-pill-pending {
            background-color: #FFFBEB;
            color: #92400E;
            border: 1px solid #FDE68A;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Standard Navigation Sidebar
render_sidebar()
config = get_config()
aws_status = config.get_safe_aws_status()

# 4. Hero Banner with Project Title
st.markdown(
    """
    <div class="hero-banner">
        <div class="hero-badge">
            <span>🛡️</span> CODSOFT Cloud Computing Internship • Task 1
        </div>
        <h1 class="hero-title">Cloud File Storage System</h1>
        <p class="hero-subtitle">
            Enterprise-grade secure cloud file storage engine built on Amazon S3 object storage,
            fast metadata indexing, role-based access control, and time-expiring share link distribution.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# 5. Cloud Storage Status Indicator Banner
if aws_status["is_configured"]:
    st.markdown(
        f"""
        <div style="background: #ECFDF5; border: 1px solid #6EE7B7; border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 2rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.4rem;">☁️</span>
                <div>
                    <strong style="color: #065F46; font-size: 0.95rem;">Amazon S3 Connected & Operational</strong>
                    <div style="color: #047857; font-size: 0.82rem;">Target Region: <code>{aws_status['region']}</code> • Bucket: <code>{aws_status['bucket_display']}</code></div>
                </div>
            </div>
            <span class="status-pill status-pill-ok">● Live Cloud Active</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"""
        <div style="background: #FFFBEB; border: 1px solid #FCD34D; border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 2rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.4rem;">⚠️</span>
                <div>
                    <strong style="color: #92400E; font-size: 0.95rem;">Development Mode Active (S3 Setup Pending)</strong>
                    <div style="color: #B45309; font-size: 0.82rem;">
                        AWS credentials or bucket name are currently placeholder values. Zero cloud charges are incurred.
                        Follow the checklist in <code>docs/AWS_SETUP.md</code> to connect your private S3 bucket.
                    </div>
                </div>
            </div>
            <span class="status-pill status-pill-pending">● Dev Environment</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        status="Planned (Phase 2)",
        icon="📤",
    )
    render_feature_card(
        title="Presigned Download URLs",
        description="Direct-from-S3 authenticated download URLs with short expiration periods, eliminating server bottlenecks.",
        status="Planned (Phase 2)",
        icon="⚡",
    )
    render_feature_card(
        title="Cryptographic File Sharing Links",
        description="Time-limited URL sharing with token validation, access counter tracking, and instant owner revocation.",
        status="Planned (Phase 2)",
        icon="🔗",
    )
    render_feature_card(
        title="Multi-Version File Management",
        description="Automated version archiving when overwriting existing filenames with restore capabilities.",
        status="Planned (Phase 3)",
        icon="🕒",
    )

st.divider()

# Navigation Quick Links
st.markdown("#### 🧭 Dashboard Navigation Guide")
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.info("📁 **1_My_Files.py**\nPersonal file manager, drag-and-drop upload zone, and file catalog.")
with nav_col2:
    st.info("📊 **2_Storage_Analytics.py**\nStorage quota consumption breakdown, file categories, and analytics.")
with nav_col3:
    st.info("🔗 **3_Shared_Files.py**\nActive share tokens, incoming shared documents, and expiry rules.")

nav_col4, nav_col5, nav_col6 = st.columns(3)
with nav_col4:
    st.info("📜 **4_Activity_History.py**\nAudit logs, mutation trails, and access compliance records.")
with nav_col5:
    st.info("⚙️ **5_Settings.py**\nAWS S3 connectivity tester, system thresholds, and policy diagnostics.")
with nav_col6:
    st.info("👑 **6_Admin.py**\nMulti-tenant oversight, quota adjustment console, and system metrics.")
