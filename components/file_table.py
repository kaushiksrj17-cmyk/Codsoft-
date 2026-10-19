"""File list and table rendering component."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st


def render_empty_file_state(message: Optional[str] = None) -> None:
    """Render an informative empty state when no files exist."""
    msg = message or "No files uploaded yet. Files stored will appear here in Phase 2."
    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 3rem 1.5rem;
            background: #F8FAFC;
            border: 2px dashed #CBD5E1;
            border-radius: 12px;
            margin: 1.5rem 0;
        ">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📂</div>
            <h4 style="color: #334155; margin-bottom: 0.3rem;">No Files Available</h4>
            <p style="color: #64748B; font-size: 0.88rem; max-width: 420px; margin: 0 auto;">
                {msg}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_file_table(files: List[Dict[str, Any]]) -> None:
    """Render structured file metadata table."""
    if not files:
        render_empty_file_state()
        return

    # In Phase 2, this will display interactive file action rows (download, share, delete, versions)
    st.dataframe(
        files,
        use_container_width=True,
        hide_index=True,
    )
