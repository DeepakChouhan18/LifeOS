"""
LifeOS — Personal Productivity, Health & Finance Analytics Platform.

App Entry Point & Top-Level Navigation Router.
"""

import streamlit as st
from database.connection import get_session
from database import init_db
from modules.settings import crud as settings_crud
from utils import ui_components
from config import DEFAULT_USER_ID

# Initialize DB tables on startup
init_db.ensure_tables()

st.set_page_config(
    page_title="LifeOS — Personal Analytics Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom modern styling
ui_components.inject_custom_css()

PAGES = {
    "📊 Overview": "overview",
    "📚 Study": "study",
    "💪 Health": "health",
    "💰 Finance": "finance",
    "🔍 Insights": "insights",
    "⚙️ Settings": "settings",
}

st.sidebar.title("🧠 LIFEOS")
st.sidebar.caption("Personal Productivity & Analytics")

# Check onboarding status
db = get_session()
try:
    profile = settings_crud.get_user_profile(db, DEFAULT_USER_ID)
finally:
    db.close()

if not profile:
    # Force onboarding view until profile is created
    from modules.settings import page as settings_page
    db = get_session()
    try:
        settings_page.render_onboarding(db)
    finally:
        db.close()
else:
    selection = st.sidebar.radio("Navigation", list(PAGES.keys()))

    if selection == "📊 Overview":
        from modules.dashboard import page as dashboard_page
        dashboard_page.render()

    elif selection == "📚 Study":
        from modules.study import page as study_page
        study_page.render()

    elif selection == "💪 Health":
        from modules.health import page as health_page
        health_page.render()

    elif selection == "💰 Finance":
        from modules.finance import page as finance_page
        finance_page.render()

    elif selection == "🔍 Insights":
        from modules.insights import page as insights_page
        insights_page.render()

    elif selection == "⚙️ Settings":
        from modules.settings import page as settings_page
        settings_page.render()
