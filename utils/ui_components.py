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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ---- Global reset & base typography ---- */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* ---- App background ---- */
    .stApp {
        background-color: #090d16 !important;
    }

    /* ---- Smooth interaction & Anti-dimming reset ---- */
    /* Streamlit by default fades/dims widgets and containers to 0.4 opacity on every rerun */
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

    /* Prevent top status widget from causing header flicker */
    div[data-testid="stStatusWidget"] {
        visibility: hidden !important;
    }

    /* ---- Main content container ---- */
    .main .block-container {
        padding: 1.75rem 2.5rem 4rem 2.5rem !important;
        max-width: 1200px !important;
    }


    /* ====================================================================
       SIDEBAR — persistent application navigation
    ==================================================================== */

    /* Force section[data-testid="stSidebar"] to ALWAYS remain expanded, visible, and 250px wide */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"][aria-expanded="false"],
    section[data-testid="stSidebar"][data-collapsed="true"],
    div[data-testid="stSidebar"] {
        background-color: #0d1424 !important;
        border-right: 1px solid #1a2540 !important;
        margin-left: 0 !important;
        transform: none !important;
        visibility: visible !important;
        display: flex !important;
        min-width: 250px !important;
        width: 250px !important;
        max-width: 250px !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem !important;
    }
    [data-testid="stSidebarUserContent"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    /* Hide Streamlit collapse buttons so sidebar remains permanently fixed open */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Close sidebar"],
    button[aria-label="Expand sidebar"] {
        display: none !important;
    }

    /* Sidebar nav buttons — default (inactive) state */
    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        text-align: left !important;
        background: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        color: #94a3b8 !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        padding: 0.55rem 0.85rem !important;
        margin-bottom: 2px !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #1a2540 !important;
        color: #f8fafc !important;
    }

    /* Active nav button */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: #1e1b4b !important;
        color: #818cf8 !important;
        font-weight: 600 !important;
        border-left: 3px solid #6366f1 !important;
        border-radius: 8px !important;
        padding-left: calc(0.85rem - 3px) !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: #2e2a72 !important;
        color: #a5b4fc !important;
    }

    /* Sidebar divider */
    section[data-testid="stSidebar"] hr {
        border-color: #1a2540 !important;
        margin: 0.5rem 0 !important;
    }

    /* ====================================================================
       TABS
    ==================================================================== */

    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: transparent;
        border-bottom: 1px solid #1e293b;
        border-radius: 0;
        padding: 0;
        margin-bottom: 1.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 0;
        padding: 0.6rem 1rem;
        font-weight: 500;
        font-size: 0.85rem;
        color: #64748b;
        transition: color 0.12s ease;
        border-bottom: 2px solid transparent;
        margin-bottom: -1px;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #cbd5e1;
        background: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        background: transparent !important;
        color: #e2e8f0 !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #6366f1 !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding: 0 !important;
    }

    /* ====================================================================
       STREAMLIT METRIC (native st.metric)
    ==================================================================== */

    [data-testid="stMetric"] {
        background: #111927;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 1rem 1.25rem;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: #64748b !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #f1f5f9 !important;
        letter-spacing: -0.02em !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.78rem !important;
        font-weight: 500 !important;
    }

    /* ====================================================================
       FORMS
    ==================================================================== */

    .stForm {
        background: #111927 !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
    }
    .stForm [data-testid="stFormSubmitButton"] > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.6rem 1.6rem !important;
    }

    /* ====================================================================
       BUTTONS (general)
    ==================================================================== */

    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        transition: all 0.12s ease !important;
        letter-spacing: 0 !important;
    }
    .stButton > button[kind="primary"] {
        background: #6366f1 !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 1px 4px rgba(99,102,241,0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #4f46e5 !important;
        box-shadow: 0 2px 10px rgba(99,102,241,0.35) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid #334155 !important;
        color: #94a3b8 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #1a2233 !important;
        border-color: #475569 !important;
        color: #e2e8f0 !important;
    }

    /* ====================================================================
       PROGRESS BARS
    ==================================================================== */

    .stProgress > div > div > div {
        background: #6366f1;
        border-radius: 999px;
        transition: width 0.4s ease;
    }
    .stProgress > div > div {
        background: #1e293b;
        border-radius: 999px;
    }

    /* ====================================================================
       INPUTS / SELECTS / TEXTAREAS
    ==================================================================== */

    div[data-baseweb="input"],
    .stTextArea > div > div > textarea,
    div[data-baseweb="select"] > div {
        background: #111927 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
        font-size: 0.875rem !important;
    }

    /* Remove nested borders inside BaseWeb selectbox control */
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
        color: #e2e8f0 !important;
        font-size: 0.875rem !important;
        box-shadow: none !important;
    }

    div[data-baseweb="input"]:focus-within,
    .stTextArea > div > div > textarea:focus,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99,102,241,0.15) !important;
    }

    /* BaseWeb Select Popover Menu */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"] {
        background-color: #111927 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
    }

    li[role="option"] {
        background-color: #111927 !important;
        color: #cbd5e1 !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 0.75rem !important;
        border-radius: 4px !important;
    }

    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background-color: #1e293b !important;
        color: #f8fafc !important;
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
        border: 1px solid #1e293b !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }

    /* ====================================================================
       EXPANDERS
    ==================================================================== */

    .streamlit-expanderHeader {
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        color: #e2e8f0 !important;
        background: #111927 !important;
        border-radius: 8px !important;
        border: 1px solid #1e293b !important;
    }
    .streamlit-expanderContent {
        border: 1px solid #1e293b !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        background: #0d1424 !important;
    }

    /* ====================================================================
       ALERTS
    ==================================================================== */

    [data-testid="stAlert"] {
        border-radius: 8px !important;
        border-left-width: 3px !important;
        font-size: 0.875rem !important;
    }

    /* ====================================================================
       DIVIDERS
    ==================================================================== */

    hr {
        border: none !important;
        border-top: 1px solid #1e293b !important;
        margin: 1.5rem 0 !important;
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
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        color: #f8fafc;
        margin: 0 0 0.2rem 0;
        line-height: 1.2;
    }
    .los-page-subtitle {
        font-size: 0.875rem;
        color: #64748b;
        font-weight: 400;
        margin: 0 0 1.5rem 0;
    }

    /* ---- Section header ---- */
    .los-section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #475569;
        margin: 0 0 0.75rem 0;
    }

    /* ---- Custom metric card ---- */
    .los-metric {
        background: #111927;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 1.1rem 1.2rem;
        border-left: 3px solid transparent;
        transition: border-color 0.15s;
        height: 100%;
    }
    .los-metric:hover {
        border-color: #334155;
    }
    .los-metric-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b;
        margin: 0 0 0.4rem 0;
    }
    .los-metric-value {
        font-size: 1.55rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        color: #f8fafc;
        line-height: 1.1;
        margin: 0 0 0.25rem 0;
    }
    .los-metric-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin: 0;
        line-height: 1.4;
    }
    .los-metric-delta-up   { color: #22c55e; font-size: 0.78rem; font-weight: 500; }
    .los-metric-delta-down { color: #ef4444; font-size: 0.78rem; font-weight: 500; }
    .los-metric-delta-neu  { color: #64748b; font-size: 0.78rem; font-weight: 500; }

    /* ---- Status badge ---- */
    .los-badge {
        display: inline-block;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        white-space: nowrap;
        line-height: 1.6;
    }
    .los-badge-success  { background: #052e16; color: #4ade80; border: 1px solid #15803d; }
    .los-badge-warning  { background: #1c1407; color: #fbbf24; border: 1px solid #92400e; }
    .los-badge-danger   { background: #1f0707; color: #f87171; border: 1px solid #991b1b; }
    .los-badge-info     { background: #1e1b4b; color: #a5b4fc; border: 1px solid #3730a3; }
    .los-badge-neutral  { background: #0f172a; color: #94a3b8; border: 1px solid #334155; }
    .los-badge-study    { background: #1e1b4b; color: #a5b4fc; border: 1px solid #4f46e5; }
    .los-badge-health   { background: #052e16; color: #6ee7b7; border: 1px solid #065f46; }
    .los-badge-finance  { background: #1c1407; color: #fde68a; border: 1px solid #78350f; }

    /* ---- Info banner / alert ---- */
    .los-banner {
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.875rem;
        line-height: 1.5;
        border-left: 3px solid;
        display: flex;
        gap: 0.5rem;
        align-items: flex-start;
    }
    .los-banner-info    { background: #0f172a; color: #c7d2fe; border-color: #6366f1; }
    .los-banner-success { background: #052e16; color: #86efac; border-color: #16a34a; }
    .los-banner-warning { background: #1c1407; color: #fde68a; border-color: #d97706; }
    .los-banner-danger  { background: #1f0707; color: #fca5a5; border-color: #dc2626; }

    /* ---- Empty state ---- */
    .los-empty {
        text-align: center;
        padding: 3rem 2rem;
        border: 1px dashed #1e293b;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .los-empty-icon { font-size: 2rem; margin-bottom: 0.75rem; display: block; opacity: 0.5; }
    .los-empty-title { font-size: 0.95rem; font-weight: 600; color: #64748b; margin: 0 0 0.3rem 0; }
    .los-empty-hint  { font-size: 0.82rem; color: #475569; margin: 0; line-height: 1.5; }

    /* ---- Insight card ---- */
    .los-insight {
        background: #111927;
        border: 1px solid #1e293b;
        border-left: 2px solid #10b981;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        color: #cbd5e1;
        font-size: 0.875rem;
        line-height: 1.5;
    }

    /* ---- Consistency score ---- */
    .los-score-ring {
        text-align: center;
        padding: 1.75rem 1rem;
        background: #111927;
        border: 1px solid #1e293b;
        border-radius: 10px;
    }
    .los-score-label  { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #475569; }
    .los-score-number { font-size: 3rem; font-weight: 800; letter-spacing: -0.04em; color: #f8fafc; line-height: 1; margin: 0.4rem 0 0.1rem 0; }
    .los-score-denom  { font-size: 0.8rem; color: #475569; }
    .los-score-bar-row   { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.55rem; font-size: 0.82rem; }
    .los-score-bar-label { width: 4rem; color: #64748b; font-weight: 500; text-align: right; flex-shrink: 0; }
    .los-score-bar-track { flex: 1; height: 5px; background: #1e293b; border-radius: 999px; overflow: hidden; }
    .los-score-bar-fill  { height: 100%; border-radius: 999px; transition: width 0.5s ease; }
    .los-score-bar-val   { width: 2.5rem; color: #e2e8f0; font-weight: 600; text-align: right; flex-shrink: 0; }

    /* ---- Timer display ---- */
    .los-timer {
        text-align: center;
        padding: 1.75rem 1rem;
        background: #111927;
        border: 1px solid #1e293b;
        border-radius: 10px;
    }
    .los-timer-face    { font-size: 3rem; font-weight: 800; letter-spacing: 0.05em; color: #f8fafc; font-variant-numeric: tabular-nums; }
    .los-timer-subject { font-size: 0.82rem; color: #6366f1; font-weight: 600; margin-top: 0.25rem; }

    /* ---- Budget progress row ---- */
    .los-budget-row {
        padding: 0.85rem 1rem;
        background: #111927;
        border: 1px solid #1e293b;
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }
    .los-budget-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; font-size: 0.875rem; }
    .los-budget-name   { font-weight: 600; color: #e2e8f0; }
    .los-budget-spent  { color: #64748b; font-size: 0.78rem; }
    .los-budget-track  { height: 4px; background: #1e293b; border-radius: 999px; overflow: hidden; margin-top: 0.4rem; }
    .los-budget-fill   { height: 100%; border-radius: 999px; transition: width 0.4s ease; }

    /* ---- Priority task row ---- */
    .los-task-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.55rem 0.75rem;
        background: #111927;
        border: 1px solid #1e293b;
        border-radius: 8px;
        margin-bottom: 0.35rem;
    }
    .los-task-label { flex: 1; font-size: 0.875rem; color: #e2e8f0; font-weight: 500; }
    .los-task-done  { color: #64748b; text-decoration: line-through; }

    /* ---- Transaction row ---- */
    .los-tx-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.7rem 0;
        border-bottom: 1px solid #1e293b;
    }
    .los-tx-row:last-child { border-bottom: none; }
    .los-tx-left  { display: flex; flex-direction: column; gap: 0.1rem; }
    .los-tx-title { font-size: 0.875rem; font-weight: 500; color: #e2e8f0; }
    .los-tx-meta  { font-size: 0.75rem; color: #64748b; }
    .los-tx-amount { font-size: 0.95rem; font-weight: 600; color: #f8fafc; letter-spacing: -0.01em; }

    /* ---- Choice cards (onboarding) ---- */
    .los-choice-card {
        background: #111927;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 2rem 1.5rem;
        text-align: center;
        transition: border-color 0.15s;
    }
    .los-choice-card:hover { border-color: #334155; }
    .los-choice-icon  { font-size: 2.5rem; display: block; margin-bottom: 0.75rem; }
    .los-choice-title { font-size: 1.05rem; font-weight: 700; color: #f8fafc; margin: 0 0 0.4rem 0; }
    .los-choice-desc  { font-size: 0.82rem; color: #64748b; line-height: 1.55; margin: 0; }

    /* ---- Auth screen ---- */
    .los-auth-card {
        max-width: 420px;
        margin: 0 auto;
        padding: 2.5rem;
        background: #111927;
        border: 1px solid #1e293b;
        border-radius: 14px;
    }
    .los-auth-brand {
        text-align: center;
        margin-bottom: 2rem;
    }
    .los-auth-logo {
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #f8fafc;
    }
    .los-auth-tagline {
        font-size: 0.82rem;
        color: #475569;
        margin-top: 0.2rem;
    }
    .los-auth-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0 0 1.5rem 0;
        letter-spacing: -0.02em;
    }

    /* ---- User profile pill (sidebar) ---- */
    .los-user-pill {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.6rem 0.8rem;
        background: #0d1424;
        border: 1px solid #1a2540;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .los-user-avatar {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background: #1e1b4b;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: 700;
        color: #a5b4fc;
        flex-shrink: 0;
    }
    .los-user-name  { font-size: 0.82rem; font-weight: 600; color: #e2e8f0; line-height: 1.2; }
    .los-user-email { font-size: 0.72rem; color: #475569; line-height: 1.2; }

    /* Sidebar profile card at bottom */
    .los-sidebar-profile {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        padding: 0.6rem 0.75rem;
        background: #111927;
        border: 1px solid #1e293b;
        border-radius: 9px;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .los-sidebar-avatar {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: #1e1b4b;
        border: 1px solid #3730a3;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.82rem;
        font-weight: 700;
        color: #a5b4fc;
        flex-shrink: 0;
    }
    .los-sidebar-name {
        font-size: 0.83rem;
        font-weight: 600;
        color: #f8fafc;
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
        delta_html = f'<p class="{cls}">{arrow}{delta}</p>'
    sub_html = f'<p class="los-metric-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="los-metric" style="border-left-color:{accent_color};">'
        f'<p class="los-metric-label">{label}</p>'
        f'<p class="los-metric-value">{value}</p>'
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
