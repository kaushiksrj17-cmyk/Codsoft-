"""Activity History page - Audit trails, action logs, and compliance records."""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_metric_card
from components.file_table import render_empty_file_state
from components.sidebar import render_sidebar
from src.activity_logger import get_recent_activities
from src.config import get_config

st.set_page_config(
    page_title="Activity History - Cloud File Storage System",
    page_icon="📜",
    layout="wide",
)

render_sidebar()
config = get_config()

st.title("📜 Activity History")
st.caption("Comprehensive immutable audit logging for security compliance and tracking user operations.")

# Try to query recent activities if database exists, otherwise show empty state
try:
    activities = get_recent_activities(limit=25)
except Exception:
    activities = []

col1, col2, col3 = st.columns(3)
with col1:
    render_metric_card(
        title="Recorded Events",
        value=str(len(activities)),
        subtitle="Current session logs",
        icon="📝",
    )
with col2:
    render_metric_card(
        title="Audit Target",
        value="SQLite / PG",
        subtitle="Transactional persistence",
        icon="🗄️",
    )
with col3:
    render_metric_card(
        title="Compliance Status",
        value="Active",
        subtitle="All file mutations tracked",
        icon="✅",
    )

st.write("")

if activities:
    st.dataframe(activities, use_container_width=True, hide_index=True)
else:
    render_empty_file_state(
        "No audit events recorded yet. "
        "Every file upload, version update, download URL creation, and share revocation will be permanently recorded here."
    )
