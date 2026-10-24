"""Global CSS design system and typography tokens for Cloud File Storage System - AI Theme."""

from __future__ import annotations

import streamlit as st


def inject_custom_styles() -> None:
    """Inject ultra-premium modern AI-themed CSS design system into the Streamlit app with zero-indent markup."""
    css = """<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

* {
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
box-sizing: border-box;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
color: #F8FAFC !important;
letter-spacing: -0.01em;
background-color: #080B11 !important;
background: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.04) 35%, rgba(8, 11, 17, 1) 75%), #080B11 !important;
}

h1, h2, h3, h4, h5, h6,
.stHeading,
[data-testid="stHeadingWithActionElements"] h1,
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3,
[data-testid="stHeadingWithActionElements"] h4 {
font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
color: #F8FAFC !important;
font-weight: 800 !important;
letter-spacing: -0.025em !important;
}

p, span, li,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span {
font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
color: #CBD5E1;
line-height: 1.55;
}

[data-testid="stMarkdownContainer"] strong {
color: #F8FAFC !important;
font-weight: 700 !important;
}

[data-testid="stCaptionContainer"] p,
.stCaption {
font-family: 'Plus Jakarta Sans', sans-serif !important;
color: #94A3B8 !important;
font-size: 0.82rem !important;
font-weight: 500 !important;
}

code, pre, .mono-chip {
font-family: 'JetBrains Mono', 'Courier New', monospace !important;
font-size: 0.85em !important;
background-color: rgba(30, 41, 59, 0.7) !important;
color: #38BDF8 !important;
padding: 0.18em 0.5em !important;
border-radius: 6px !important;
border: 1px solid rgba(56, 189, 248, 0.25) !important;
}

.main .block-container {
padding-top: 1.8rem;
padding-bottom: 3.5rem;
max-width: 1220px;
}

::-webkit-scrollbar {
width: 7px;
height: 7px;
}
::-webkit-scrollbar-track {
background: #0B0F19;
}
::-webkit-scrollbar-thumb {
background: #334155;
border-radius: 4px;
border: 1px solid rgba(139, 92, 246, 0.2);
}
::-webkit-scrollbar-thumb:hover {
background: #475569;
}

.stButton > button {
font-family: 'Plus Jakarta Sans', sans-serif !important;
font-weight: 600 !important;
font-size: 0.88rem !important;
border-radius: 10px !important;
padding: 0.55rem 1.25rem !important;
transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
border: 1px solid rgba(255, 255, 255, 0.12) !important;
background: rgba(30, 41, 59, 0.75) !important;
color: #F1F5F9 !important;
backdrop-filter: blur(8px) !important;
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
}

.stButton > button:hover {
transform: translateY(-2px) !important;
box-shadow: 0 0 15px rgba(139, 92, 246, 0.35), 0 8px 18px -4px rgba(0, 0, 0, 0.5) !important;
border-color: rgba(139, 92, 246, 0.45) !important;
color: #FFFFFF !important;
background: rgba(51, 65, 85, 0.9) !important;
}

.stButton > button:active {
transform: translateY(0px) !important;
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #C026D3 100%) !important;
color: #FFFFFF !important;
border: 1px solid rgba(192, 132, 252, 0.45) !important;
box-shadow: 0 0 20px rgba(124, 58, 237, 0.45) !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%) !important;
box-shadow: 0 0 28px rgba(139, 92, 246, 0.7) !important;
border-color: rgba(236, 72, 153, 0.6) !important;
transform: translateY(-2px) !important;
}

.stTextInput > div > div > input,
.stSelectbox > div > div,
div[data-baseweb="select"] {
border-radius: 10px !important;
font-family: 'Plus Jakarta Sans', sans-serif !important;
font-size: 0.9rem !important;
border-color: rgba(255, 255, 255, 0.12) !important;
background-color: rgba(15, 23, 42, 0.85) !important;
color: #F8FAFC !important;
}

.stTextInput > div > div > input:focus {
border-color: #8B5CF6 !important;
box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.3) !important;
}

[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] p {
font-family: 'Plus Jakarta Sans', sans-serif !important;
font-size: 0.82rem !important;
font-weight: 700 !important;
color: #C4B5FD !important;
letter-spacing: 0.01em !important;
}

.stProgress > div > div > div > div {
background: linear-gradient(90deg, #06B6D4 0%, #6366F1 50%, #EC4899 100%) !important;
border-radius: 9999px !important;
box-shadow: 0 0 14px rgba(99, 102, 241, 0.6) !important;
}

.stProgress > div > div {
background-color: rgba(30, 41, 59, 0.7) !important;
border-radius: 9999px !important;
height: 8px !important;
}

div[data-testid="stFileUploader"] {
border-radius: 14px !important;
border: 2px dashed rgba(139, 92, 246, 0.4) !important;
background: linear-gradient(180deg, rgba(15, 23, 42, 0.6) 0%, rgba(30, 27, 75, 0.25) 100%) !important;
padding: 1.2rem !important;
transition: all 0.25s ease !important;
}

div[data-testid="stFileUploader"]:hover {
border-color: #C084FC !important;
background: rgba(30, 27, 75, 0.4) !important;
box-shadow: 0 0 20px rgba(139, 92, 246, 0.25) !important;
}

@keyframes beacon-pulse {
0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.75); }
70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

@keyframes beacon-amber {
0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.75); }
70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}

.beacon-live {
display: inline-block;
width: 9px;
height: 9px;
background-color: #10B981;
border-radius: 50%;
animation: beacon-pulse 2s infinite;
vertical-align: middle;
box-shadow: 0 0 8px #10B981;
}

.beacon-pending {
display: inline-block;
width: 9px;
height: 9px;
background-color: #F59E0B;
border-radius: 50%;
animation: beacon-amber 2s infinite;
vertical-align: middle;
box-shadow: 0 0 8px #F59E0B;
}

.hero-banner {
position: relative;
background: linear-gradient(135deg, #090D16 0%, #0F172A 45%, #1E1B4B 80%, #2E1065 100%);
border: 1px solid rgba(139, 92, 246, 0.3);
border-radius: 18px;
padding: 2.4rem 2.8rem;
color: #FFFFFF !important;
margin-bottom: 2rem;
box-shadow: 0 20px 45px -10px rgba(0, 0, 0, 0.8), 0 0 25px -5px rgba(99, 102, 241, 0.25);
}

.hero-badge {
display: inline-flex;
align-items: center;
gap: 7px;
background: rgba(139, 92, 246, 0.15);
padding: 5px 14px;
border-radius: 9999px;
font-size: 0.78rem;
font-weight: 700;
letter-spacing: 0.04em;
color: #C4B5FD !important;
margin-bottom: 1rem;
border: 1px solid rgba(139, 92, 246, 0.35);
box-shadow: 0 0 12px rgba(139, 92, 246, 0.25);
}

.hero-title {
font-size: 2.4rem;
font-weight: 800;
letter-spacing: -0.03em;
margin: 0 0 0.6rem 0;
line-height: 1.15;
background: linear-gradient(135deg, #FFFFFF 0%, #F1F5F9 40%, #A5B4FC 75%, #F472B6 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
}

.hero-subtitle {
font-size: 1.05rem;
color: #CBD5E1 !important;
margin: 0 0 1.4rem 0;
max-width: 760px;
line-height: 1.55;
}

.hero-tags {
display: flex;
flex-wrap: wrap;
gap: 8px;
}

.hero-tag {
background: rgba(15, 23, 42, 0.7) !important;
border: 1px solid rgba(255, 255, 255, 0.12) !important;
color: #E2E8F0 !important;
font-size: 0.76rem;
font-weight: 600;
padding: 4px 11px;
border-radius: 6px;
box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.status-pill {
display: inline-flex;
align-items: center;
gap: 7px;
padding: 6px 14px;
border-radius: 9999px;
font-size: 0.8rem;
font-weight: 700;
letter-spacing: 0.02em;
}

.status-pill-ok {
background-color: rgba(6, 78, 59, 0.45);
color: #34D399;
border: 1px solid rgba(52, 211, 153, 0.4);
box-shadow: 0 0 12px rgba(16, 185, 129, 0.25);
}

.status-pill-pending {
background-color: rgba(120, 53, 15, 0.45);
color: #FBBF24;
border: 1px solid rgba(251, 191, 36, 0.4);
box-shadow: 0 0 12px rgba(245, 158, 11, 0.25);
}

.nav-card {
background: rgba(15, 23, 42, 0.75);
border: 1px solid rgba(255, 255, 255, 0.08);
border-radius: 14px;
padding: 1.25rem 1.35rem;
height: 100%;
box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
backdrop-filter: blur(12px);
display: flex;
flex-direction: column;
justify-content: space-between;
transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.nav-card:hover {
transform: translateY(-3px);
border-color: rgba(139, 92, 246, 0.5);
box-shadow: 0 12px 30px -8px rgba(99, 102, 241, 0.35), 0 0 18px rgba(139, 92, 246, 0.25);
}

section[data-testid="stSidebar"] {
background-color: #070A10 !important;
border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

[data-testid="stSidebarNav"] a {
font-family: 'Plus Jakarta Sans', sans-serif !important;
font-weight: 600 !important;
font-size: 0.88rem !important;
color: #94A3B8 !important;
border-radius: 8px !important;
padding: 0.45rem 0.75rem !important;
transition: all 0.15s ease !important;
}

[data-testid="stSidebarNav"] a:hover {
background-color: rgba(30, 41, 59, 0.6) !important;
color: #F8FAFC !important;
}

[data-testid="stSidebarNav"] a[aria-current="page"] {
background-color: rgba(99, 102, 241, 0.16) !important;
color: #C4B5FD !important;
font-weight: 700 !important;
border-left: 3px solid #8B5CF6 !important;
}

[data-testid="stDataFrame"] {
border-radius: 12px !important;
border: 1px solid rgba(255, 255, 255, 0.1) !important;
box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
overflow: hidden !important;
background: rgba(15, 23, 42, 0.85) !important;
}

[data-testid="stAlert"] {
border-radius: 12px !important;
background-color: rgba(15, 23, 42, 0.85) !important;
border-width: 1px !important;
}
</style>"""
    st.markdown(css, unsafe_allow_html=True)
