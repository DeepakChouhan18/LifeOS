"""
LifeOS — Personal Productivity, Health & Finance Analytics Platform.

App Entry Point: Authentication guard, Login/Signup screens, and Application Shell.

Architecture:
  1. Tables are created/migrated on startup.
  2. If the user is not authenticated → show Login or Signup.
  3. If authenticated → render the full application shell with sidebar navigation.
  4. Each page module receives the authenticated user_id so it can't accidentally
     read or write another user's data.
"""

import streamlit as st

st.set_page_config(
    page_title="LifeOS — Personal Analytics Platform",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

from database.connection import get_session
from database import init_db
from utils import ui_components, date_helpers, auth as auth_utils
from config import DEFAULT_USER_ID, APP_NAME

# ---- Bootstrap: create/migrate DB tables once per container startup ----
@st.cache_resource
def _bootstrap_database():
    init_db.ensure_tables()
    return True

_bootstrap_database()

# Inject global design system CSS
ui_components.inject_custom_css()



# ---------------------------------------------------------------------------
# Navigation config
# ---------------------------------------------------------------------------

NAV_ITEMS = [
    ("Dashboard", "Dashboard"),
    ("Study",     "Study"),
    ("Health",    "Health"),
    ("Finance",   "Finance"),
    ("Insights",  "Insights"),
    ("Settings",  "Settings"),
]


# ---------------------------------------------------------------------------
# Login / Signup screens
# ---------------------------------------------------------------------------

def _render_login():
    """Premium login screen."""
    # Check if this is first-time (legacy single-user DB exists with data)
    db = get_session()
    try:
        from database.models import User
        legacy_user = db.get(User, DEFAULT_USER_ID)
        has_legacy_data = legacy_user and not legacy_user.email
    finally:
        db.close()

    st.markdown("<div style='height:3rem;'></div>", unsafe_allow_html=True)
    # Center the auth card
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(
            """
            <div style="text-align:center; margin-bottom:2rem;">
                <div style="font-size:1.6rem; font-weight:800; letter-spacing:-0.03em; color:#f8fafc; margin-bottom:0.3rem;">LifeOS</div>
                <div style="font-size:0.875rem; color:#475569;">Personal Analytics Platform</div>
            </div>
            <div style="font-size:1.2rem; font-weight:700; color:#f8fafc; margin-bottom:1.5rem; letter-spacing:-0.02em;">Sign In</div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="you@example.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please enter your email and password.")
                else:
                    db = get_session()
                    try:
                        user = auth_utils.authenticate_user(db, email, password)
                        if user:
                            auth_utils.login_user(user)
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                    except Exception:
                        st.error("Something went wrong. Please try again.")
                    finally:
                        db.close()

        st.markdown(
            "<p style='text-align:center; font-size:0.82rem; color:#475569; margin-top:1rem;'>"
            "Don't have an account?</p>",
            unsafe_allow_html=True,
        )
        if st.button("Create an account", key="goto_signup", use_container_width=True):
            st.session_state["auth_mode"] = "signup"
            st.rerun()

        # Migration hint for users with existing data
        if has_legacy_data:
            st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
            ui_components.info_banner(
                "Existing LifeOS data detected. When you create an account, "
                "you'll have the option to link it to your new account.",
                banner_type="info",
            )


def _render_signup():
    """Premium signup screen."""
    # Check for existing legacy data
    db = get_session()
    try:
        from database.models import User
        legacy_user = db.get(User, DEFAULT_USER_ID)
        has_legacy_data = legacy_user and not legacy_user.email
        from modules.settings import crud as settings_crud
        legacy_profile = settings_crud.get_user_profile(db, DEFAULT_USER_ID) if has_legacy_data else None
    finally:
        db.close()

    st.markdown("<div style='height:3rem;'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(
            """
            <div style="text-align:center; margin-bottom:2rem;">
                <div style="font-size:1.6rem; font-weight:800; letter-spacing:-0.03em; color:#f8fafc; margin-bottom:0.3rem;">LifeOS</div>
                <div style="font-size:0.875rem; color:#475569;">Personal Analytics Platform</div>
            </div>
            <div style="font-size:1.2rem; font-weight:700; color:#f8fafc; margin-bottom:1.5rem; letter-spacing:-0.02em;">Create your account</div>
            """,
            unsafe_allow_html=True,
        )

        claim_legacy = False
        if has_legacy_data and legacy_profile:
            claim_legacy = st.checkbox(
                f"Link existing LifeOS data (recorded as \"{legacy_profile.name}\") to my new account",
                value=True,
                help="Your existing study, health, and finance records will be attached to your new account.",
            )

        with st.form("signup_form", clear_on_submit=False):
            name = st.text_input("Name", placeholder="Your full name", key="signup_name")
            email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
            password = st.text_input("Password", type="password", placeholder="Min. 8 characters", key="signup_password")
            confirm = st.text_input("Confirm password", type="password", placeholder="••••••••", key="signup_confirm")
            submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)

            if submitted:
                if not name or not email or not password or not confirm:
                    st.error("All fields are required.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif "@" not in email:
                    st.error("Please enter a valid email address.")
                else:
                    db = get_session()
                    try:
                        success, message, user = auth_utils.signup_user(
                            db, email=email, password=password, display_name=name,
                            claim_legacy_data=claim_legacy,
                        )
                        if success and user:
                            # For fresh users, run onboarding via Settings
                            auth_utils.login_user(user)
                            # If they didn't claim legacy data, they need profile setup
                            from modules.settings import crud as settings_crud
                            profile = settings_crud.get_user_profile(db, user.id)
                            if not profile:
                                st.session_state["needs_onboarding"] = True
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    except Exception as e:
                        st.error("Something went wrong. Please try again.")
                    finally:
                        db.close()

        st.markdown(
            "<p style='text-align:center; font-size:0.82rem; color:#475569; margin-top:1rem;'>"
            "Already have an account?</p>",
            unsafe_allow_html=True,
        )
        if st.button("Sign in", key="goto_login", use_container_width=True):
            st.session_state["auth_mode"] = "login"
            st.rerun()


# ---------------------------------------------------------------------------
# Authenticated Application Shell
# ---------------------------------------------------------------------------

def _render_sidebar(user_id: int) -> str:
    """Renders the primary sidebar navigation. Returns current page name."""

    # Brand mark & Navigation section header
    st.sidebar.markdown(
        """
        <div style="padding:1.25rem 1rem 0.75rem 1rem; border-bottom:1px solid #1a2540; margin-bottom:0.75rem;">
            <div style="font-size:1.15rem; font-weight:800; letter-spacing:-0.03em; color:#f8fafc;">LifeOS</div>
            <div style="font-size:0.7rem; color:#475569; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; margin-top:0.15rem;">Analytics Platform</div>
        </div>
        <div style="font-size:0.7rem; font-weight:700; color:#475569; text-transform:uppercase; letter-spacing:0.08em; padding:0.2rem 0.5rem 0.4rem 0.5rem;">Navigation</div>
        """,
        unsafe_allow_html=True,
    )

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    # Primary navigation items ONLY
    for name, label in NAV_ITEMS:
        is_active = st.session_state.page == name
        btn_type = "primary" if is_active else "secondary"
        if st.sidebar.button(label, key=f"nav_{name}", type=btn_type, use_container_width=True):
            st.session_state.page = name
            st.rerun()

    # User profile footer pill
    display_name = auth_utils.get_current_display_name()
    email = auth_utils.get_current_email()
    initials = "".join(p[0].upper() for p in display_name.split()[:2]) if display_name else "U"
    
    st.sidebar.markdown(
        f"""
        <div style="margin-top:auto; padding-top:1.5rem;">
            <div class="los-sidebar-profile">
                <div class="los-sidebar-avatar">{initials}</div>
                <div style="min-width:0;">
                    <div class="los-sidebar-name">{display_name}</div>
                    <div class="los-sidebar-email">{email}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return st.session_state.page



def _route_page(page: str, user_id: int):
    """Routes to the correct page module, passing user_id."""

    if page == "Dashboard":
        from modules.dashboard import page as dashboard_page
        dashboard_page.render(user_id)

    elif page == "Study":
        from modules.study import page as study_page
        study_page.render(user_id)

    elif page == "Health":
        from modules.health import page as health_page
        health_page.render(user_id)

    elif page == "Finance":
        from modules.finance import page as finance_page
        finance_page.render(user_id)

    elif page == "Insights":
        from modules.insights import page as insights_page
        insights_page.render(user_id)

    elif page == "Settings":
        from modules.settings import page as settings_page
        settings_page.render(user_id)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    # --- Not authenticated: show login or signup ---
    if not auth_utils.is_authenticated():
        mode = st.session_state.get("auth_mode", "login")
        if mode == "signup":
            _render_signup()
        else:
            _render_login()
        return

    # --- Authenticated ---
    user_id = auth_utils.get_current_user_id()

    # Onboarding: new user without a profile → redirect to Settings for setup
    if st.session_state.get("needs_onboarding"):
        db = get_session()
        try:
            from modules.settings import crud as settings_crud
            profile = settings_crud.get_user_profile(db, user_id)
        finally:
            db.close()

        if not profile:
            from modules.settings import page as settings_page
            db = get_session()
            try:
                settings_page.render_onboarding(db, user_id)
            finally:
                db.close()
            return
        else:
            st.session_state.pop("needs_onboarding", None)

    # Application shell
    page = _render_sidebar(user_id)
    _route_page(page, user_id)


main()
