"""Shared Files page - Manage shared links and collaborative access."""

from __future__ import annotations

import streamlit as st
from components.dashboard_cards import render_feature_card, render_metric_card
from components.file_table import render_empty_file_state
from components.sidebar import render_sidebar
from src.config import get_config

st.set_page_config(
    page_title="Shared Files - Cloud File Storage System",
    page_icon="🔗",
    layout="wide",
)

render_sidebar()
config = get_config()

st.title("🔗 Shared Files")
st.caption("Generate time-limited secure share links with cryptographic token validation and role restrictions.")

col1, col2, col3 = st.columns(3)
with col1:
    render_metric_card(
        title="Active Share Links",
        value="0",
        subtitle="Unexpired share tokens",
        icon="🌐",
    )
with col2:
    render_metric_card(
        title="Files Shared with Me",
        value="0",
        subtitle="From team members",
        icon="📥",
    )
with col3:
    render_metric_card(
        title="Max Expiry Policy",
        value=f"{config.share_link_max_expiry_hours}h",
        subtitle="Configured token lifespan",
        icon="⏱️",
    )

st.write("")
tab1, tab2 = st.tabs(["📤 Shared by Me", "📥 Shared with Me"])

with tab1:
    render_empty_file_state(
        "You have not created any share links yet. "
        "In Phase 2, select any uploaded file to generate a time-limited shareable URL with access control."
    )

with tab2:
    render_empty_file_state(
        "No files have been shared with your account yet. "
        "Incoming shared documents will appear here once collaborative sharing is activated."
    )

st.divider()

st.subheader("Security Architecture for Sharing")
c1, c2 = st.columns(2)
with c1:
    render_feature_card(
        title="Cryptographic Token Authorization",
        description="Every share link utilizes a 256-bit entropy random URL token, never exposing direct S3 object paths.",
        status="Architecture Ready",
        icon="🔐",
    )
with c2:
    render_feature_card(
        title="Instant Link Revocation",
        description="File owners and administrators can revoke access instantly, invalidating active access tokens.",
        status="Planned (Phase 2)",
        icon="🚫",
    )
