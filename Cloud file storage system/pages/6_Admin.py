"""System Administration and User Management dashboard."""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_feature_card, render_metric_card
from components.sidebar import render_sidebar
from src.auth import get_all_users
from src.config import get_config
from src.permissions import is_admin
from src.storage_quota import format_bytes

st.set_page_config(
    page_title="Admin - Cloud File Storage System",
    page_icon="👑",
    layout="wide",
)

render_sidebar()
config = get_config()

current_user = st.session_state.get("current_user")

if not current_user:
    st.title("👑 System Administration Console")
    st.info("🔒 **Sign In Required:** Please sign in with an administrator account using the sidebar to access this console.")
    st.stop()

if not is_admin(current_user.get("role", "user")):
    st.title("👑 System Administration Console")
    st.error("🚫 **Access Denied:** Administrator privileges are required to access this console.")
    st.stop()

st.title("👑 System Administration Console")
st.caption("Central administrative console for multi-tenant oversight, quota allocations, and system telemetry.")

all_users = get_all_users()
total_tenants = len(all_users)
total_storage_bytes = sum(u.get("used_storage_bytes", 0) for u in all_users)
formatted_total = format_bytes(total_storage_bytes)

# 1. Telemetry Metric Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card(
        title="Total Tenants",
        value=str(total_tenants),
        subtitle="Active user profiles",
        icon="👥",
    )
with col2:
    render_metric_card(
        title="Aggregated Storage",
        value=formatted_total,
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
        subtitle="Target: Amazon RDS/Postgres",
        icon="⚙️",
    )

st.write("")

# 2. Registered Tenants Overview Table
if all_users:
    st.subheader("👥 Registered Tenant Profiles")
    tenant_data = []
    for u in all_users:
        tenant_data.append({
            "ID": u["id"],
            "Username": u["username"],
            "Email": u["email"],
            "Role": u.get("role", "user").upper(),
            "Used Storage": format_bytes(u.get("used_storage_bytes", 0)),
            "Quota": format_bytes(u.get("storage_quota_bytes", 0)),
            "Created": u.get("created_at", "")[:10],
        })
    st.dataframe(tenant_data, use_container_width=True, hide_index=True)

st.divider()

# 3. Administrative Capabilities Roadmap
st.subheader("🗺️ Enterprise Admin Capabilities (Roadmap)")

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
