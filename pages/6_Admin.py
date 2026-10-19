"""System Administration and User Management dashboard."""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_feature_card, render_metric_card
from components.sidebar import render_sidebar
from src.config import get_config

st.set_page_config(
    page_title="Admin - Cloud File Storage System",
    page_icon="👑",
    layout="wide",
)

render_sidebar()
config = get_config()

st.title("👑 System Administration")
st.caption("Central administrative console for tenant management, quota allocations, and system telemetry.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card(
        title="Total Tenants",
        value="1",
        subtitle="Active user profiles",
        icon="👥",
    )
with col2:
    render_metric_card(
        title="Aggregated Storage",
        value="0.00 MB",
        subtitle="Stored across all users",
        icon="💾",
    )
with col3:
    render_metric_card(
        title="Access Violations",
        value="0",
        subtitle="Past 30 days",
        icon="🛡️",
    )
with col4:
    render_metric_card(
        title="Engine Mode",
        value="SQLite",
        subtitle="Migration target: PostgreSQL",
        icon="⚙️",
    )

st.write("")
st.subheader("Administrative Capabilities (Planned)")

c1, c2 = st.columns(2)
with c1:
    render_feature_card(
        title="Dynamic Quota Allocation",
        description="Override default storage quotas per-user or tenant tier without restarting application services.",
        status="Planned (Phase 3)",
        icon="📊",
    )
    render_feature_card(
        title="Global Security Audit",
        description="Search access logs across all tenants, inspect IP geolocations, and filter failed authentication events.",
        status="Planned (Phase 3)",
        icon="🔍",
    )
with c2:
    render_feature_card(
        title="User Lifecycle & Deactivation",
        description="Suspend abusive accounts, trigger bulk file exports, or schedule GDPR-compliant data purge jobs.",
        status="Planned (Phase 3)",
        icon="👤",
    )
    render_feature_card(
        title="PostgreSQL Migration Bridge",
        description="Export SQLite metadata dumps directly into managed Amazon RDS / PostgreSQL databases.",
        status="Planned (Phase 4)",
        icon="🐘",
    )
