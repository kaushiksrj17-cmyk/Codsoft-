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

st.title("📊 Storage Analytics & Quota Intelligence")
st.caption("Inspect quota consumption, file type distribution, and cloud resource allocation.")

current_user = st.session_state.get("current_user")
if not current_user:
    st.info("🔒 **Sign In Required:** Please sign in via the sidebar to view your storage analytics.")
    st.stop()

from src.file_service import get_user_quota_info, list_user_files
from src.sharing import list_shares_by_user

quota_info = get_user_quota_info(current_user["id"])
user_files = list_user_files(current_user["id"], user_role=current_user.get("role", "user"))

try:
    user_shares = list_shares_by_user(current_user["id"], user_role=current_user.get("role", "user"))
    active_shares_count = str(sum(1 for s in user_shares if s.get("status") == "Active"))
except Exception:
    active_shares_count = "0"

used_display = f"{quota_info['used_mb']} MB"
rem_display = f"{quota_info['remaining_mb']} MB"
file_count = str(len(user_files))
pct = quota_info["usage_percentage"]
total_quota_str = quota_info["formatted_quota"]
used_str = quota_info["formatted_used"]
free_pct = round(100.0 - pct, 1)
subtitle_rem = f"{free_pct}% capacity free"

# 1. Telemetry Metric Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card(
        title="Used Storage",
        value=used_display,
        subtitle=f"of {total_quota_str} total quota",
        icon="💾",
    )
with col2:
    render_metric_card(
        title="Remaining Quota",
        value=rem_display,
        subtitle=subtitle_rem,
        icon="🛡️",
    )
with col3:
    render_metric_card(
        title="Total Files",
        value=file_count,
        subtitle="Stored in private S3 bucket",
        icon="📄",
    )
with col4:
    render_metric_card(
        title="Active Shares",
        value=active_shares_count,
        subtitle="Expiring & public links",
        icon="🔗",
    )

st.write("")

# 2. Quota Health Meter Card (Zero-indent HTML)
health_badge = "🟢 Optimal Capacity" if pct < 80 else ("🟡 Warning (80%+)" if pct < 90 else "🔴 Critical (>90%)")
health_bg = "rgba(6, 78, 59, 0.45)" if pct < 80 else ("rgba(120, 53, 15, 0.45)" if pct < 90 else "rgba(153, 27, 27, 0.45)")
health_color = "#34D399" if pct < 80 else ("#FBBF24" if pct < 90 else "#F87171")
health_border = "rgba(52, 211, 153, 0.4)" if pct < 80 else ("rgba(245, 158, 11, 0.4)" if pct < 90 else "rgba(248, 113, 113, 0.4)")

meter_html = f"""<div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 1.3rem 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); backdrop-filter: blur(12px);">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.8rem; flex-wrap: wrap; gap: 8px;">
<div>
<strong style="color: #F8FAFC; font-size: 1rem;">Storage Quota Consumption</strong>
<div style="color: #94A3B8; font-size: 0.82rem; margin-top: 2px;">
Consuming <strong style="color: #F8FAFC;">{used_str}</strong> of <strong style="color: #F8FAFC;">{total_quota_str}</strong> ({pct}% utilized)
</div>
</div>
<span style="background: {health_bg}; color: {health_color}; border: 1px solid {health_border}; font-size: 0.72rem; font-weight: 700; padding: 4px 10px; border-radius: 9999px;">
{health_badge}
</span>
</div>
</div>"""
st.markdown(meter_html, unsafe_allow_html=True)

st.progress(min(pct / 100.0, 1.0))
st.caption(f"Tenant isolation enforces hard ceiling at {total_quota_str}. Excess uploads are rejected pre-flight.")

st.divider()

# 3. File Category Distribution
st.subheader("📦 Storage Category Distribution")
if user_files:
    category_counts = {}
    for f in user_files:
        cat = f.get("category", "Other")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    cat_cols = st.columns(len(category_counts))
    for idx, (cat_name, count) in enumerate(category_counts.items()):
        with cat_cols[idx]:
            pct_of_files = round((count / len(user_files)) * 100, 1)
            st.metric(
                label=cat_name,
                value=f"{count} file{'s' if count != 1 else ''}",
                delta=f"{pct_of_files}% of total",
            )
else:
    st.info("ℹ️ No files stored yet. Once files are ingested, distribution by MIME type and category will appear here.")

st.divider()

# 4. Planned Analytics Modules
st.subheader("🗺️ Advanced Analytics Modules (Roadmap)")
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
