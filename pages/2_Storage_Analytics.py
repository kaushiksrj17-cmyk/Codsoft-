"""Storage Analytics page - Quota consumption, file type distribution, and capacity."""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_feature_card, render_metric_card
from components.sidebar import render_sidebar
from src.config import get_config
from src.storage_quota import format_bytes

st.set_page_config(
    page_title="Storage Analytics - Cloud File Storage System",
    page_icon="📊",
    layout="wide",
)

render_sidebar()
config = get_config()

st.title("📊 Storage Analytics")
st.caption("Inspect quota consumption, storage distribution, and cloud utilization.")

# Metric row
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card(
        title="Used Storage",
        value="0.00 MB",
        subtitle=f"of {config.default_storage_quota_mb} MB total quota",
        icon="💾",
    )
with col2:
    render_metric_card(
        title="Remaining Quota",
        value=f"{config.default_storage_quota_mb} MB",
        subtitle="100% capacity free",
        icon="🛡️",
    )
with col3:
    render_metric_card(
        title="Total Files",
        value="0",
        subtitle="Across all buckets",
        icon="📄",
    )
with col4:
    render_metric_card(
        title="Active Shares",
        value="0",
        subtitle="Expiring & public links",
        icon="🔗",
    )

st.write("")
st.subheader("Quota Allocation Overview")
st.progress(0.0)
st.caption(f"Currently consuming 0 bytes of {format_bytes(config.default_storage_quota_bytes)}.")

st.divider()

st.subheader("Planned Analytics Modules (Phase 2 & 3)")
c1, c2 = st.columns(2)
with c1:
    render_feature_card(
        title="File Format Distribution",
        description="Interactive breakdown of PDF, images, video, documents, and archives stored in your S3 prefix.",
        status="Planned (Phase 2)",
        icon="🥧",
    )
    render_feature_card(
        title="Upload Frequency Velocity",
        description="Time-series chart showing daily and weekly upload bandwidth consumption and object counts.",
        status="Planned (Phase 3)",
        icon="📈",
    )
with c2:
    render_feature_card(
        title="Storage Class Optimization",
        description="Recommendations for S3 Intelligent-Tiering and S3 Glacier lifecycle transitions for cold data.",
        status="Planned (Phase 3)",
        icon="💡",
    )
    render_feature_card(
        title="Quota Usage Alerts",
        description="Configurable threshold warnings when storage usage approaches 80% and 90% of capacity.",
        status="Planned (Phase 2)",
        icon="🔔",
    )
