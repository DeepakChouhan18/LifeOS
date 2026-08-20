"""
Reusable UI components and CSS injection for LifeOS.

Complete design system with:
  - Neutral-first dark palette (90% neutral, 10% meaningful accent)
  - Strong typographic hierarchy using Inter
  - Consistent spacing, radii, and shadows
  - Premium metric cards, section headers, badges, banners, empty states
  - Auth screens (login, signup) styled as premium product pages
  - Sidebar navigation shell with user profile pill
  - Progressive disclosure via clean tab styling

Color semantics (used ONLY where they communicate meaning):
  Study accent  : #6366f1 (indigo)
  Health accent : #10b981 (emerald)
  Finance accent: #f59e0b (amber)
  Success       : #22c55e
  Warning       : #f59e0b
  Danger        : #ef4444
  Info          : #6366f1
  Neutral text  : #64748b (muted), #94a3b8 (caption), #e2e8f0 (body), #f8fafc (heading)
  Surfaces      : #090d16 (page bg), #111827 (sidebar), #1a2233 (card), #243049 (card hover)
  Borders       : #1e293b (subtle), #334155 (card), #475569 (interactive hover)
"""

import streamlit as st


# ---------------------------------------------------------------------------
# Global CSS injection
# ---------------------------------------------------------------------------

def inject_custom_css():
    """Call once in app.py to inject the global LifeOS stylesheet."""
    st.markdown("""
    <style>
    /* ---- Import Google Fonts ---- */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

    /* ---- Global reset & base typography ---- */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        color: #e2e8f0;
    }

    /* ---- Custom Scrollbar ---- */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #080c14;
    }
    ::-webkit-scrollbar-thumb {
        background: #1e293b;
        border-radius: 999px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #334155;
    }

    /* ---- App background with subtle atmospheric mesh gradient ---- */
    .stApp {
        background-color: #080c14 !important;
        background-image: 
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.08) 0%, transparent 60%),
            radial-gradient(ellipse 60% 40% at 90% 10%, rgba(16, 185, 129, 0.03) 0%, transparent 50%) !important;
        background-attachment: fixed !important;
    }

    /* ---- Anti-dimming reset & smooth state transitions ---- */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    div[data-testid="stVerticalBlock"],
    .element-container,
    [data-testid="stMetric"],
    [data-testid="stPlotlyChart"],
    div[data-testid="stTabs"] {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }

    .stApp[data-test-script-state="running"] [data-testid="stVerticalBlock"],
    .stApp[data-test-script-state="running"] .element-container {
        opacity: 1 !important;
    }

    /* Hide top status widget */
    div[data-testid="stStatusWidget"] {
        visibility: hidden !important;
    }

    /* ---- Main content container ---- */
    .main .block-container {
        padding: 2rem 2.5rem 4rem 2.5rem !important;
        max-width: 1240px !important;
    }

    /* ====================================================================
       SIDEBAR — Modern SaaS Navigation
    ==================================================================== */

    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"][aria-expanded="false"],
    section[data-testid="stSidebar"][data-collapsed="true"],
    div[data-testid="stSidebar"] {
        background-color: #090e1a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
        margin-left: 0 !important;
        transform: none !important;
        visibility: visible !important;
        display: flex !important;
        min-width: 255px !important;
        width: 255px !important;
        max-width: 255px !important;
        opacity: 1 !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.25) !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem !important;
    }
    [data-testid="stSidebarUserContent"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Close sidebar"],
    button[aria-label="Expand sidebar"] {
        display: none !important;
    }

    /* Sidebar nav buttons */
    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        text-align: left !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 9px !important;
        color: #94a3b8 !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        padding: 0.58rem 0.9rem !important;
        margin-bottom: 3px !important;
        transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
        letter-spacing: -0.01em !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.05) !important;
        color: #f8fafc !important;
        border-color: rgba(255, 255, 255, 0.05) !important;
        transform: translateX(2px) !important;
    }

    /* Active nav button */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.16) 0%, rgba(99, 102, 241, 0.04) 100%) !important;
        color: #c7d2fe !important;
        font-weight: 600 !important;
        border-left: 3px solid #6366f1 !important;
        border-top: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-bottom: 1px solid rgba(99, 102, 241, 0.1) !important;
        border-right: 1px solid rgba(99, 102, 241, 0.1) !important;
        border-radius: 9px !important;
        padding-left: calc(0.9rem - 3px) !important;
        box-shadow: 0 2px 10px rgba(99, 102, 241, 0.15) !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.22) 0%, rgba(99, 102, 241, 0.08) 100%) !important;
        color: #e0e7ff !important;
    }

    /* Sidebar divider */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.06) !important;
        margin: 0.75rem 0 !important;
    }

    /* ====================================================================
       TABS — Modern Segment / Underline
    ==================================================================== */

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 0;
        padding: 0 0 0.1rem 0;
        margin-bottom: 1.75rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 0.65rem 1.15rem;
        font-weight: 500;
        font-size: 0.88rem;
        color: #64748b;
        transition: all 0.15s ease;
        border-bottom: 2px solid transparent;
        margin-bottom: -1px;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #cbd5e1;
        background: rgba(255, 255, 255, 0.03) !important;
    }
    .stTabs [aria-selected="true"] {
        background: transparent !important;
        color: #f8fafc !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #6366f1 !important;
        box-shadow: 0 2px 10px rgba(99, 102, 241, 0.2) !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding: 0 !important;
    }

    /* ====================================================================
       STREAMLIT METRICS (Native st.metric)
    ==================================================================== */

    [data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.75) 0%, rgba(13, 19, 32, 0.75) 100%) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 12px !important;
        padding: 1.1rem 1.25rem !important;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    [data-testid="stMetric"]:hover {
        border-color: rgba(99, 102, 241, 0.3) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.5), 0 0 16px -4px rgba(99, 102, 241, 0.15) !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: #64748b !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        letter-spacing: -0.03em !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
    }

    /* ====================================================================
       FORMS & CONTAINERS
    ==================================================================== */

    .stForm {
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.7) 0%, rgba(13, 19, 32, 0.75) 100%) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 1.75rem !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
    }
    .stForm [data-testid="stFormSubmitButton"] > button {
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 0.65rem 1.75rem !important;
    }

    /* ====================================================================
       BUTTONS
    ==================================================================== */

    .stButton > button {
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        letter-spacing: -0.01em !important;
        transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
        padding: 0.55rem 1.15rem !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #ffffff !important;
        box-shadow: 0 2px 10px rgba(99, 102, 241, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%) !important;
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        color: #cbd5e1 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.18) !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
    }

    /* ====================================================================
       PROGRESS BARS
    ==================================================================== */

    .stProgress > div > div > div {
        background: linear-gradient(90deg, #6366f1 0%, #818cf8 100%) !important;
        border-radius: 999px !important;
        transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stProgress > div > div {
        background: rgba(255, 255, 255, 0.06) !important;
        border-radius: 999px !important;
        height: 6px !important;
    }

    /* ====================================================================
       INPUTS / SELECTS / TEXTAREAS
    ==================================================================== */

    div[data-baseweb="input"],
    .stTextArea > div > div > textarea,
    div[data-baseweb="select"] > div {
        background: rgba(12, 18, 32, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 9px !important;
        color: #f1f5f9 !important;
        font-size: 0.875rem !important;
        transition: all 0.15s ease !important;
    }

    div[data-baseweb="select"] div {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }

    div[data-baseweb="select"] svg {
        fill: #94a3b8 !important;
        color: #94a3b8 !important;
    }

    div[data-baseweb="input"] > input {
        background: transparent !important;
        border: none !important;
        color: #f1f5f9 !important;
        font-size: 0.875rem !important;
        box-shadow: none !important;
    }

    div[data-baseweb="input"]:focus-within,
    .stTextArea > div > div > textarea:focus,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25) !important;
    }

    /* Popovers / Select Menus */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"] {
        background-color: #0f172a !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6) !important;
    }

    li[role="option"] {
        background-color: #0f172a !important;
        color: #cbd5e1 !important;
        font-size: 0.875rem !important;
        padding: 0.55rem 0.85rem !important;
        border-radius: 6px !important;
        margin: 2px 4px !important;
    }

    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }

    div[data-baseweb="input"] button {
        background: transparent !important;
        border: none !important;
        color: #94a3b8 !important;
        box-shadow: none !important;
    }
    div[data-baseweb="input"] button:hover {
        color: #f8fafc !important;
    }

    /* ====================================================================
       DATAFRAMES / TABLES
    ==================================================================== */

    .stDataFrame {
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        background: rgba(13, 19, 32, 0.6) !important;
    }

    /* ====================================================================
       EXPANDERS
    ==================================================================== */

    .streamlit-expanderHeader {
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        color: #e2e8f0 !important;
        background: rgba(18, 26, 43, 0.6) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        transition: all 0.15s ease !important;
    }
    .streamlit-expanderHeader:hover {
        background: rgba(25, 36, 60, 0.7) !important;
        border-color: rgba(255, 255, 255, 0.14) !important;
    }
    .streamlit-expanderContent {
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
        background: rgba(9, 14, 26, 0.7) !important;
    }

    /* ====================================================================
       ALERTS
    ==================================================================== */

    [data-testid="stAlert"] {
        border-radius: 10px !important;
        border-left-width: 3px !important;
        font-size: 0.875rem !important;
        backdrop-filter: blur(8px) !important;
    }

    /* ====================================================================
       DIVIDERS
    ==================================================================== */

    hr {
        border: none !important;
        border-top: 1px solid rgba(255, 255, 255, 0.07) !important;
        margin: 1.75rem 0 !important;
    }

    /* ====================================================================
       HIDE STREAMLIT CHROME
    ==================================================================== */

    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    [data-testid="stToolbar"] { display: none !important; }
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    header[data-testid="stHeader"] button {
        color: #f8fafc !important;
    }

    /* ====================================================================
       LIFEOS DESIGN SYSTEM CLASSES
    ==================================================================== */

    /* ---- Page header ---- */
    .los-page-title {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.035em;
        color: #ffffff;
        margin: 0 0 0.25rem 0;
        line-height: 1.2;
    }
    .los-page-subtitle {
        font-size: 0.88rem;
        color: #64748b;
        font-weight: 400;
        margin: 0 0 1.75rem 0;
    }

    /* ---- Section header ---- */
    .los-section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        color: #64748b;
        margin: 0 0 0.85rem 0;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* ---- Custom metric card with glassmorphism & accent glow ---- */
    .los-metric {
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.75) 0%, rgba(13, 19, 32, 0.75) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 1.15rem 1.25rem;
        border-left: 3px solid transparent;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .los-metric:hover {
        border-color: rgba(99, 102, 241, 0.35);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.5), 0 0 16px -4px rgba(99, 102, 241, 0.15);
    }
    .los-metric-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin: 0 0 0.4rem 0;
    }
    .los-metric-value {
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #ffffff;
        line-height: 1.1;
        margin: 0 0 0.35rem 0;
    }
    .los-metric-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin: 0;
        line-height: 1.4;
    }
    .los-metric-delta-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.18rem 0.5rem;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
        width: fit-content;
    }
    .los-metric-delta-up {
        background: rgba(34, 197, 94, 0.12);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.2);
    }
    .los-metric-delta-down {
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }
    .los-metric-delta-neu {
        background: rgba(148, 163, 184, 0.1);
        color: #94a3b8;
        border: 1px solid rgba(148, 163, 184, 0.15);
    }

    /* ---- Status badge ---- */
    .los-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        white-space: nowrap;
        line-height: 1.4;
    }
    .los-badge-success  { background: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.25); }
    .los-badge-warning  { background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25); }
    .los-badge-danger   { background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.25); }
    .los-badge-info     { background: rgba(99, 102, 241, 0.12); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.25); }
    .los-badge-neutral  { background: rgba(148, 163, 184, 0.1); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2); }
    .los-badge-study    { background: rgba(99, 102, 241, 0.12); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.25); }
    .los-badge-health   { background: rgba(16, 185, 129, 0.12); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.25); }
    .los-badge-finance  { background: rgba(245, 158, 11, 0.12); color: #fde68a; border: 1px solid rgba(245, 158, 11, 0.25); }

    /* ---- Info banner / alert ---- */
    .los-banner {
        border-radius: 10px;
        padding: 0.85rem 1.15rem;
        margin-bottom: 1.25rem;
        font-size: 0.875rem;
        line-height: 1.5;
        border-left: 3px solid;
        display: flex;
        gap: 0.75rem;
        align-items: center;
        backdrop-filter: blur(8px);
    }
    .los-banner-info    { background: rgba(15, 23, 42, 0.75); color: #c7d2fe; border-color: #6366f1; border-top: 1px solid rgba(99, 102, 241, 0.15); border-right: 1px solid rgba(99, 102, 241, 0.15); border-bottom: 1px solid rgba(99, 102, 241, 0.15); }
    .los-banner-success { background: rgba(5, 46, 22, 0.75); color: #86efac; border-color: #16a34a; border-top: 1px solid rgba(34, 197, 94, 0.15); border-right: 1px solid rgba(34, 197, 94, 0.15); border-bottom: 1px solid rgba(34, 197, 94, 0.15); }
    .los-banner-warning { background: rgba(28, 20, 7, 0.75); color: #fde68a; border-color: #d97706; border-top: 1px solid rgba(245, 158, 11, 0.15); border-right: 1px solid rgba(245, 158, 11, 0.15); border-bottom: 1px solid rgba(245, 158, 11, 0.15); }
    .los-banner-danger  { background: rgba(31, 7, 7, 0.75); color: #fca5a5; border-color: #dc2626; border-top: 1px solid rgba(239, 68, 68, 0.15); border-right: 1px solid rgba(239, 68, 68, 0.15); border-bottom: 1px solid rgba(239, 68, 68, 0.15); }

    /* ---- Empty state ---- */
    .los-empty {
        text-align: center;
        padding: 3.5rem 2rem;
        border: 1px dashed rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        margin: 0.75rem 0;
        background: rgba(15, 23, 42, 0.3);
    }
    .los-empty-icon { font-size: 2.2rem; margin-bottom: 0.75rem; display: block; opacity: 0.6; }
    .los-empty-title { font-size: 0.95rem; font-weight: 600; color: #94a3b8; margin: 0 0 0.35rem 0; }
    .los-empty-hint  { font-size: 0.82rem; color: #64748b; margin: 0; line-height: 1.5; }

    /* ---- Insight card ---- */
    .los-insight {
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.7) 0%, rgba(13, 19, 32, 0.75) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-left: 3px solid #10b981;
        border-radius: 10px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.6rem;
        color: #cbd5e1;
        font-size: 0.875rem;
        line-height: 1.5;
        transition: all 0.15s ease;
    }
    .los-insight:hover {
        border-color: rgba(16, 185, 129, 0.4);
        transform: translateX(2px);
    }

    /* ---- Consistency score display ---- */
    .los-score-ring {
        text-align: center;
        padding: 2rem 1.25rem;
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.8) 0%, rgba(13, 19, 32, 0.85) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.06);
    }
    .los-score-label  { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; }
    .los-score-number { font-size: 3.2rem; font-weight: 800; letter-spacing: -0.04em; line-height: 1; margin: 0.5rem 0 0.15rem 0; text-shadow: 0 0 24px rgba(99, 102, 241, 0.2); }
    .los-score-denom  { font-size: 0.8rem; color: #64748b; }
    .los-score-bar-row   { display: flex; align-items: center; gap: 0.85rem; margin-bottom: 0.7rem; font-size: 0.85rem; }
    .los-score-bar-label { width: 4.2rem; color: #94a3b8; font-weight: 600; text-align: right; flex-shrink: 0; font-size: 0.82rem; }
    .los-score-bar-track { flex: 1; height: 7px; background: rgba(255, 255, 255, 0.06); border-radius: 999px; overflow: hidden; }
    .los-score-bar-fill  { height: 100%; border-radius: 999px; transition: width 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
    .los-score-bar-val   { width: 2.6rem; color: #ffffff; font-weight: 700; text-align: right; flex-shrink: 0; }

    /* ---- Timer display ---- */
    .los-timer {
        text-align: center;
        padding: 2rem 1.25rem;
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.8) 0%, rgba(13, 19, 32, 0.85) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.06);
    }
    .los-timer-face    { font-size: 3.4rem; font-weight: 800; letter-spacing: 0.04em; color: #ffffff; font-variant-numeric: tabular-nums; text-shadow: 0 0 30px rgba(99, 102, 241, 0.3); }
    .los-timer-subject { font-size: 0.88rem; color: #a5b4fc; font-weight: 600; margin-top: 0.4rem; }

    /* ---- Budget progress row ---- */
    .los-budget-row {
        padding: 0.95rem 1.15rem;
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.6) 0%, rgba(13, 19, 32, 0.65) 100%);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 10px;
        margin-bottom: 0.6rem;
        transition: all 0.15s ease;
    }
    .los-budget-row:hover {
        border-color: rgba(255, 255, 255, 0.14);
        transform: translateY(-1px);
    }
    .los-budget-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem; font-size: 0.88rem; }
    .los-budget-name   { font-weight: 600; color: #f1f5f9; }
    .los-budget-spent  { color: #64748b; font-size: 0.78rem; }
    .los-budget-track  { height: 5px; background: rgba(255, 255, 255, 0.06); border-radius: 999px; overflow: hidden; margin-top: 0.45rem; }
    .los-budget-fill   { height: 100%; border-radius: 999px; transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1); }

    /* ---- Priority task row ---- */
    .los-task-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.7rem 0.9rem;
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.5) 0%, rgba(13, 19, 32, 0.55) 100%);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 9px;
        margin-bottom: 0.45rem;
        transition: all 0.15s ease;
    }
    .los-task-row:hover {
        background: rgba(25, 36, 60, 0.6);
        border-color: rgba(255, 255, 255, 0.12);
    }
    .los-task-label { flex: 1; font-size: 0.875rem; color: #f1f5f9; font-weight: 500; }
    .los-task-done  { color: #64748b; text-decoration: line-through; }

    /* ---- Transaction row ---- */
    .los-tx-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 0.25rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .los-tx-row:last-child { border-bottom: none; }
    .los-tx-left  { display: flex; flex-direction: column; gap: 0.15rem; }
    .los-tx-title { font-size: 0.88rem; font-weight: 600; color: #f1f5f9; }
    .los-tx-meta  { font-size: 0.75rem; color: #64748b; }
    .los-tx-amount { font-size: 0.98rem; font-weight: 700; color: #ffffff; letter-spacing: -0.01em; }

    /* ---- Choice cards (onboarding) ---- */
    .los-choice-card {
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.75) 0%, rgba(13, 19, 32, 0.75) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 2.25rem 1.75rem;
        text-align: center;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .los-choice-card:hover { 
        border-color: rgba(99, 102, 241, 0.4);
        transform: translateY(-3px);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(99, 102, 241, 0.15);
    }
    .los-choice-icon  { font-size: 2.75rem; display: block; margin-bottom: 0.85rem; }
    .los-choice-title { font-size: 1.15rem; font-weight: 700; color: #ffffff; margin: 0 0 0.45rem 0; letter-spacing: -0.02em; }
    .los-choice-desc  { font-size: 0.84rem; color: #94a3b8; line-height: 1.55; margin: 0; }

    /* ---- Auth screen ---- */
    .los-auth-card {
        max-width: 440px;
        margin: 0 auto;
        padding: 2.5rem;
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.85) 0%, rgba(13, 19, 32, 0.9) 100%);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 16px;
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }

    /* ---- User profile pill (sidebar) ---- */
    .los-sidebar-profile {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.7rem 0.85rem;
        background: linear-gradient(180deg, rgba(18, 26, 43, 0.6) 0%, rgba(13, 19, 32, 0.65) 100%);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 11px;
        margin-top: 0.75rem;
        margin-bottom: 0.5rem;
        transition: all 0.15s ease;
    }
    .los-sidebar-profile:hover {
        background: rgba(25, 36, 60, 0.7);
        border-color: rgba(255, 255, 255, 0.12);
    }
    .los-sidebar-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4338ca 0%, #312e81 100%);
        border: 1.5px solid rgba(99, 102, 241, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.88rem;
        font-weight: 700;
        color: #c7d2fe;
        flex-shrink: 0;
        box-shadow: 0 0 12px rgba(99, 102, 241, 0.2);
    }
    .los-sidebar-name {
        font-size: 0.85rem;
        font-weight: 600;
        color: #ffffff;
        line-height: 1.25;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .los-sidebar-email {
        font-size: 0.72rem;
        color: #64748b;
        line-height: 1.25;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = ""):
    """Renders a styled page title with optional subtitle."""
    sub_html = f'<p class="los-page-subtitle">{subtitle}</p>' if subtitle else '<div style="margin-bottom:1.5rem;"></div>'
    st.markdown(
        f'<h1 class="los-page-title">{title}</h1>{sub_html}',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------

def section_header(title: str, subtitle: str = "", icon: str = ""):
    """Renders a compact all-caps section label. Used for major sections within a page."""
    label = f"{icon} {title}" if icon else title
    sub_html = ""
    if subtitle:
        sub_html = f'<p style="font-size:0.78rem;color:#475569;margin:0 0 0.75rem 0;">{subtitle}</p>'
    st.markdown(
        f'<p class="los-section-title">{label}</p>{sub_html}',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Metric card
# ---------------------------------------------------------------------------

def metric_card(label: str, value: str, subtitle: str = "", accent_color: str = "#6366f1",
                delta: str = "", delta_type: str = "neutral"):
    """
    Renders a custom metric card with left accent border.
    delta_type: 'up' (green), 'down' (red), 'neutral' (muted)
    """
    delta_html = ""
    if delta:
        cls = f"los-metric-delta-{delta_type}"
        arrow = "↑ " if delta_type == "up" else ("↓ " if delta_type == "down" else "")
        delta_html = f'<div class="los-metric-delta-pill {cls}"><span>{arrow}{delta}</span></div>'
    sub_html = f'<p class="los-metric-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="los-metric" style="border-left: 3px solid {accent_color};">'
        f'<div>'
        f'<p class="los-metric-label">{label}</p>'
        f'<p class="los-metric-value">{value}</p>'
        f'</div>'
        f'{delta_html}'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Status badge
# ---------------------------------------------------------------------------

_BADGE_CLASS_MAP = {
    "success":    "los-badge-success",
    "warning":    "los-badge-warning",
    "danger":     "los-badge-danger",
    "info":       "los-badge-info",
    "neutral":    "los-badge-neutral",
    "completed":  "los-badge-success",
    "pending":    "los-badge-neutral",
    "overdue":    "los-badge-danger",
    "on_track":   "los-badge-success",
    "near_limit": "los-badge-warning",
    "over_budget":"los-badge-danger",
    "study":      "los-badge-study",
    "health":     "los-badge-health",
    "finance":    "los-badge-finance",
}


def status_badge(text: str, variant: str = "neutral") -> str:
    """Returns HTML string for an inline status badge."""
    cls = _BADGE_CLASS_MAP.get(variant, "los-badge-neutral")
    return f'<span class="los-badge {cls}">{text}</span>'


# ---------------------------------------------------------------------------
# Info / alert banner
# ---------------------------------------------------------------------------

def info_banner(text: str, banner_type: str = "info"):
    """Renders a styled horizontal banner. banner_type: info | success | warning | danger."""
    labels = {"info": "INFO", "success": "SUCCESS", "warning": "WARNING", "danger": "ERROR"}
    lbl = labels.get(banner_type, "INFO")
    st.markdown(
        f'<div class="los-banner los-banner-{banner_type}">'
        f'<span style="font-size:0.68rem; font-weight:700; letter-spacing:0.06em; flex-shrink:0; padding:0.1rem 0.35rem; border-radius:4px; background:rgba(255,255,255,0.08);">{lbl}</span>'
        f'<span>{text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

def empty_state(message: str, icon: str = "", hint: str = ""):
    """Shows a professional empty state with message and optional hint."""
    hint_html = f'<p class="los-empty-hint">{hint}</p>' if hint else ""
    st.markdown(
        f'<div class="los-empty">'
        f'<p class="los-empty-title">{message}</p>'
        f'{hint_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Insight card
# ---------------------------------------------------------------------------

def insight_card(text: str, icon: str = "→"):
    """Renders a styled insight card with an emerald left border."""
    prefix = f"{icon} " if icon else ""
    st.markdown(
        f'<div class="los-insight">{prefix}{text}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Info card (blue accent, backward compat)
# ---------------------------------------------------------------------------

def info_card(text: str):
    """Renders a styled info card (indigo accent)."""
    st.markdown(
        f'<div class="los-banner los-banner-info">{text}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Consistency score display
# ---------------------------------------------------------------------------

def consistency_score_display(
    overall: float,
    study: float, health: float, finance: float,
    study_w: float = 0.4, health_w: float = 0.35, finance_w: float = 0.25,
):
    """Renders the visual consistency score block."""
    col1, col2 = st.columns([1, 2])

    with col1:
        if overall >= 70:
            score_color = "#22c55e"
        elif overall >= 45:
            score_color = "#f59e0b"
        else:
            score_color = "#ef4444"

        st.markdown(
            f'<div class="los-score-ring">'
            f'<p class="los-score-label">Consistency Score</p>'
            f'<p class="los-score-number" style="color:{score_color};">{overall:.0f}</p>'
            f'<p class="los-score-denom">out of 100</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            '<div style="padding:0.25rem 0 0 0.5rem;">'
            + _score_bar("Study", study, "#6366f1")
            + _score_bar("Health", health, "#10b981")
            + _score_bar("Finance", finance, "#f59e0b")
            + f'<p style="font-size:0.75rem;color:#475569;margin-top:0.75rem;">'
            f'Weights — Study {study_w*100:.0f}% · Health {health_w*100:.0f}% · Finance {finance_w*100:.0f}%.'
            f' Adjust in Settings.</p>'
            '</div>',
            unsafe_allow_html=True,
        )


def _score_bar(label: str, value: float, color: str) -> str:
    pct = min(max(value, 0), 100)
    return (
        f'<div class="los-score-bar-row">'
        f'<span class="los-score-bar-label">{label}</span>'
        f'<div class="los-score-bar-track">'
        f'<div class="los-score-bar-fill" style="width:{pct:.0f}%;background:{color};"></div>'
        f'</div>'
        f'<span class="los-score-bar-val">{value:.0f}</span>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Timer display
# ---------------------------------------------------------------------------

def timer_display(elapsed_minutes: int, elapsed_seconds: int, subject: str):
    """Renders a prominent centered study timer."""
    st.markdown(
        f'<div class="los-timer">'
        f'<div class="los-timer-face">{elapsed_minutes:02d}:{elapsed_seconds:02d}</div>'
        f'<div class="los-timer-subject">{subject}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Budget progress bar row
# ---------------------------------------------------------------------------

def budget_progress_row(name: str, budget: float, spent: float):
    """Renders a styled budget row with progress bar and status badge."""
    if budget > 0:
        pct = min(spent / budget * 100, 100)
    else:
        pct = 0

    if pct >= 100:
        bar_color = "#ef4444"
        badge_html = status_badge("Over Budget", "over_budget")
    elif pct >= 80:
        bar_color = "#f59e0b"
        badge_html = status_badge("Near Limit", "near_limit")
    else:
        bar_color = "#22c55e"
        badge_html = status_badge("On Track", "on_track")

    remaining = budget - spent
    rem_str = f"₹{abs(remaining):.0f} {'over' if remaining < 0 else 'left'}"

    st.markdown(
        f'<div class="los-budget-row">'
        f'<div class="los-budget-header">'
        f'<span class="los-budget-name">{name}</span>'
        f'{badge_html}'
        f'</div>'
        f'<span class="los-budget-spent">₹{spent:.0f} of ₹{budget:.0f} — {rem_str}</span>'
        f'<div class="los-budget-track">'
        f'<div class="los-budget-fill" style="width:{pct:.1f}%;background:{bar_color};"></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Progress metric (keeps backward compat)
# ---------------------------------------------------------------------------

def progress_metric(label: str, current: float, target: float, unit: str = "", inverse: bool = False):
    """Shows a label, value, and progress bar. Falls back gracefully if target is 0."""
    if target > 0:
        pct = min(current / target, 1.0)
        remaining = target - current
    else:
        pct = 0.0
        remaining = 0

    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(label)
        st.progress(pct)
    with col2:
        if unit:
            st.metric(
                label=label,
                value=f"{current:.0f}",
                delta=f"{remaining:+.0f} {unit}",
                label_visibility="collapsed",
            )
        else:
            st.metric(
                label=label,
                value=f"{current:.0f}/{target:.0f}",
                label_visibility="collapsed",
            )


# ---------------------------------------------------------------------------
# Transaction row (for Finance page recent expenses)
# ---------------------------------------------------------------------------

def transaction_row(title: str, amount: str, meta: str):
    """Renders a clean transaction list row."""
    st.markdown(
        f'<div class="los-tx-row">'
        f'<div class="los-tx-left">'
        f'<span class="los-tx-title">{title}</span>'
        f'<span class="los-tx-meta">{meta}</span>'
        f'</div>'
        f'<span class="los-tx-amount">{amount}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
