"""Reusable metric cards and styled UI containers for the Streamlit dashboard - AI Theme."""

from __future__ import annotations

import streamlit as st


def render_metric_card(
    title: str,
    value: str,
    subtitle: str = "",
    icon: str = "📊",
    border_color: str = "rgba(139, 92, 246, 0.25)",
    bg_gradient: str = "linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 27, 75, 0.35) 100%)",
) -> None:
    """Render a styled modern AI-themed dashboard metric card with zero-indent HTML."""
    sub_html = f'<div style="font-size: 0.78rem; color: #94A3B8; font-weight: 500; margin-top: 6px;">{subtitle}</div>' if subtitle else ""

    html = f"""<div style="background: {bg_gradient}; border: 1px solid {border_color}; border-radius: 14px; padding: 1.15rem 1.35rem; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 15px -3px rgba(99, 102, 241, 0.15); height: 100%; display: flex; flex-direction: column; justify-content: space-between; backdrop-filter: blur(12px);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.55rem;">
<span style="font-size: 0.76rem; font-weight: 700; color: #A5B4FC; text-transform: uppercase; letter-spacing: 0.05em;">{title}</span>
<div style="width: 36px; height: 36px; border-radius: 10px; background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.35); box-shadow: 0 0 12px rgba(139, 92, 246, 0.2); display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">{icon}</div>
</div>
<div>
<div style="font-size: 1.75rem; font-weight: 800; color: #F8FAFC; line-height: 1.15; letter-spacing: -0.02em;">{value}</div>
{sub_html}
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_feature_card(
    title: str,
    description: str,
    status: str = "Planned (Phase 2)",
    icon: str = "⚡",
) -> None:
    """Render a card explaining a planned or implemented system feature with zero-indent HTML."""
    is_live = "Active" in status or "Implemented" in status
    badge_bg = "rgba(6, 78, 59, 0.45)" if is_live else "rgba(30, 41, 59, 0.6)"
    badge_color = "#34D399" if is_live else "#94A3B8"
    badge_border = "rgba(52, 211, 153, 0.4)" if is_live else "rgba(255, 255, 255, 0.1)"
    left_accent = "#10B981" if is_live else "#8B5CF6"
    beacon_html = '<span style="display:inline-block; width:6px; height:6px; background:#10B981; border-radius:50%; margin-right:5px; box-shadow: 0 0 6px #10B981;"></span>' if is_live else ""

    html = f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid {left_accent}; border-radius: 12px; padding: 1.05rem 1.25rem; margin-bottom: 0.85rem; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.35); backdrop-filter: blur(8px);">
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.45rem; gap: 10px;">
<div style="display: flex; align-items: center; gap: 10px;">
<div style="width: 32px; height: 32px; border-radius: 8px; background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); display: flex; align-items: center; justify-content: center; font-size: 1.1rem;">{icon}</div>
<strong style="font-size: 0.93rem; color: #F8FAFC; font-weight: 700;">{title}</strong>
</div>
<span style="display: inline-flex; align-items: center; background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; font-size: 0.69rem; font-weight: 700; padding: 3px 9px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap;">
{beacon_html}{status}
</span>
</div>
<p style="font-size: 0.82rem; color: #94A3B8; margin: 0; line-height: 1.5; padding-left: 42px;">
{description}
</p>
</div>"""
    st.markdown(html, unsafe_allow_html=True)
