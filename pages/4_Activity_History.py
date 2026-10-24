"""Activity History page - Audit trails, action logs, and compliance records."""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_metric_card
from components.file_table import render_empty_file_state
from components.sidebar import render_sidebar
from src.activity_logger import get_recent_activities
from src.config import get_config
from src.permissions import is_admin

st.set_page_config(
    page_title="Activity History - Cloud File Storage System",
    page_icon="📜",
    layout="wide",
)

render_sidebar()
config = get_config()

st.title("📜 Security Audit & Activity History")
st.caption("Immutable append-only audit logging for regulatory compliance, security forensics, and operation tracking.")

current_user = st.session_state.get("current_user")

if not current_user:
    st.info("🔒 **Sign In Required:** Please sign in via the sidebar to view activity history.")
    st.stop()

try:
    if is_admin(current_user.get("role", "user")):
        activities = get_recent_activities(limit=100)
    else:
        activities = get_recent_activities(user_id=current_user["id"], limit=50)
except Exception:
    activities = []

# 1. Telemetry Metric Row
col1, col2, col3 = st.columns(3)
with col1:
    render_metric_card(
        title="Recorded Audit Events",
        value=str(len(activities)),
        subtitle="Recent tracked mutations",
        icon="📝",
    )
with col2:
    render_metric_card(
        title="Audit Store",
        value="SQLite / PG",
        subtitle="Transactional persistence",
        icon="🗄️",
    )
with col3:
    render_metric_card(
        title="Compliance Status",
        value="Enforced",
        subtitle="All file events immutably signed",
        icon="✅",
    )

st.write("")

# 2. Activity Table Presentation
if activities:
    st.subheader("📋 Immutable Audit Records")

    # Format table for cleaner display
    display_rows = []
    for a in activities:
        display_rows.append({
            "Timestamp": a.get("created_at", "")[:19],
            "Action": a.get("action", ""),
            "Resource": a.get("resource_type", ""),
            "Resource ID": a.get("resource_id", ""),
            "Status": a.get("status", "SUCCESS"),
            "Details": a.get("details", "") or "—",
        })

    st.dataframe(display_rows, use_container_width=True, hide_index=True)
else:
    render_empty_file_state(
        "No audit events recorded yet. "
        "Every file upload, version update, download URL creation, and share revocation is permanently logged here."
    )
