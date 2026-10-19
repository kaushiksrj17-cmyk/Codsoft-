"""Reusable metric cards and styled UI containers for the Streamlit dashboard."""

from __future__ import annotations

import streamlit as st


def render_metric_card(
    title: str,
    value: str,
    subtitle: str = "",
    icon: str = "📊",
    border_color: str = "#E2E8F0",
    bg_gradient: str = "linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%)",
) -> None:
    """Render a styled modern dashboard metric card."""
    st.markdown(
        f"""
        <div style="
            background: {bg_gradient};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 1.1rem 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            height: 100%;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="font-size: 0.85rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em;">
                    {title}
                </span>
                <span style="font-size: 1.35rem;">{icon}</span>
            </div>
            <div style="font-size: 1.65rem; font-weight: 700; color: #0F172A; line-height: 1.2;">
                {value}
            </div>
            {f'<div style="font-size: 0.78rem; color: #64748B; margin-top: 0.4rem;">{subtitle}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_card(
    title: str,
    description: str,
    status: str = "Planned (Phase 2)",
    icon: str = "⚡",
) -> None:
    """Render a card explaining a planned or implemented system feature."""
    is_live = "Active" in status or "Implemented" in status
    badge_bg = "#ECFDF5" if is_live else "#F1F5F9"
    badge_color = "#047857" if is_live else "#475569"
    badge_border = "#A7F3D0" if is_live else "#CBD5E1"

    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 1rem 1.15rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.4rem;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.2rem;">{icon}</span>
                    <strong style="font-size: 0.95rem; color: #1E293B;">{title}</strong>
                </div>
                <span style="
                    background: {badge_bg};
                    color: {badge_color};
                    border: 1px solid {badge_border};
                    font-size: 0.7rem;
                    font-weight: 600;
                    padding: 2px 8px;
                    border-radius: 9999px;
                    text-transform: uppercase;
                    letter-spacing: 0.04em;
                ">
                    {status}
                </span>
            </div>
            <p style="font-size: 0.82rem; color: #64748B; margin: 0; line-height: 1.45;">
                {description}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
