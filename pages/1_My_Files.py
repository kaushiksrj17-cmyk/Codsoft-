"""My Files page - Personal Cloud Storage Explorer."""

from __future__ import annotations

import streamlit as st
from components.file_table import render_empty_file_state
from components.sidebar import render_sidebar
from components.upload_panel import render_upload_panel_placeholder
from src.config import get_config

st.set_page_config(
    page_title="My Files - Cloud File Storage System",
    page_icon="📁",
    layout="wide",
)

render_sidebar()
config = get_config()

st.title("📁 My Files")
st.caption("Manage your private cloud documents, photos, and files stored in Amazon S3.")

# Upload panel placeholder
render_upload_panel_placeholder()

st.divider()

# Toolbar preview (Filter, Search, Actions)
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    st.text_input(
        "Search files",
        placeholder="Search by filename or tag... (Phase 2)",
        disabled=True,
        label_visibility="collapsed",
    )
with col2:
    st.selectbox(
        "Filter Type",
        options=["All Types", "Documents", "Images", "Archives", "Media"],
        disabled=True,
        label_visibility="collapsed",
    )
with col3:
    st.selectbox(
        "Sort By",
        options=["Date (Newest)", "Name (A-Z)", "Size (Largest)"],
        disabled=True,
        label_visibility="collapsed",
    )

# File Table Empty State
render_empty_file_state(
    "Your private S3 file repository is ready. "
    "File listing, upload streaming, and presigned download URL generation will be active in Phase 2."
)
