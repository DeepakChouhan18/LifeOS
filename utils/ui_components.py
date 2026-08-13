"""
Reusable UI components and CSS injection for a clean, professional SaaS aesthetic.

Provides consistent styling across all pages — metric cards, section
headers, empty states, and a base CSS layer that makes the app feel
like a modern product (clean dark theme with crisp typography and subtle borders).
"""

import streamlit as st


def inject_custom_css():
    """Call once in app.py to inject the global stylesheet."""
    st.markdown("""
    <style>
    /* ---- Import Google Font ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ---- Global typography ---- */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* ---- Sidebar styling ---- */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B;
    }
    section[data-testid="stSidebar"] .stRadio label {
        font-size: 0.92rem;
        font-weight: 500;
        padding: 0.4rem 0.6rem;
        border-radius: 6px;
        color: #94A3B8;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        color: #F8FAFC;
    }

    /* ---- Metric cards ---- */
    [data-testid="stMetric"] {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        transition: border-color 0.15s ease;
    }
    [data-testid="stMetric"]:hover {
        border-color: #475569;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700;
        color: #F8FAFC !important;
    }

    /* ---- Tab styling ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.3rem;
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 0.25rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 0.45rem 1rem;
        font-weight: 500;
        font-size: 0.88rem;
        color: #94A3B8;
    }
    .stTabs [aria-selected="true"] {
        background: #1E293B !important;
        color: #38BDF8 !important;
        font-weight: 600;
    }

    /* ---- Form styling ---- */
    .stForm {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 1.2rem;
    }

    /* ---- Dividers ---- */
    hr {
        border-color: #1E293B !important;
        margin: 1.5rem 0 !important;
    }

    /* ---- Dataframe styling ---- */
    .stDataFrame {
        border: 1px solid #1E293B;
        border-radius: 8px;
        overflow: hidden;
    }

    /* ---- Expander ---- */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 0.92rem;
        color: #E2E8F0;
    }

    /* ---- Progress bar ---- */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #38BDF8, #818CF8);
        border-radius: 6px;
    }

    /* ---- Hide hamburger menu ---- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ---- Page header styling ---- */
    .page-header {
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #F8FAFC;
        margin-bottom: 0.2rem;
    }
    .page-subtitle {
        font-size: 0.9rem;
        color: #94A3B8;
        margin-bottom: 1.5rem;
    }

    /* ---- Info & Insight cards ---- */
    .info-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-left: 3px solid #38BDF8;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        color: #CBD5E1;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .insight-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-left: 3px solid #10B981;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
        color: #E2E8F0;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    """Renders a styled page header with optional subtitle."""
    st.markdown(f'<div class="page-header">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def empty_state(message: str, icon: str = "📝"):
    """Shows a friendly empty state with an icon."""
    st.markdown(
        f"""<div style="text-align:center; padding:2rem 1rem; color:#64748B;">
            <div style="font-size:2.2rem; margin-bottom:0.4rem;">{icon}</div>
            <div style="font-size:0.9rem;">{message}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def insight_card(text: str, icon: str = "💡"):
    """Renders a styled insight card."""
    st.markdown(
        f'<div class="insight-card">{icon} {text}</div>',
        unsafe_allow_html=True,
    )


def progress_metric(label: str, current: float, target: float, unit: str = "", inverse: bool = False):
    """
    Shows a metric with a progress bar underneath.
    
    If inverse=True, lower current is better (e.g. spending vs budget).
    """
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
            st.metric(label=label, value=f"{current:.0f}", delta=f"{remaining:+.0f} {unit} left",
                      label_visibility="collapsed")
        else:
            st.metric(label=label, value=f"{current:.0f}/{target:.0f}", label_visibility="collapsed")
