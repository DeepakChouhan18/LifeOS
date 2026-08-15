"""
Streamlit UI for onboarding and Settings.

Features:
- Professional Account & Profile card with avatar, email, and security settings
- Activity level dropdown with proper placeholder and submit-only validation
- Consistency score weights manager with exact 1.00 (100%) total validation
- Data export & privacy management
"""

import streamlit as st
from datetime import date

from database.connection import get_session
from database import init_db
from modules.settings import crud as settings_crud
from utils import health_calc, export, validation, ui_components, auth as auth_utils


# =======================================================================
# ONBOARDING (new user without a profile)
# =======================================================================

def render_onboarding(db, user_id: int):
    """
    Called for newly registered users who have no profile yet.
    Offers Fresh Start or Demo Data, then collects profile info.
    """
    display_name = auth_utils.get_current_display_name()

    st.markdown(
        f"""
        <div style="text-align:center; padding:2rem 0 1rem 0;">
            <div style="font-size:2rem; font-weight:800; letter-spacing:-0.04em; color:#f8fafc; margin:0 0 0.4rem 0;">
                Welcome, {display_name}
            </div>
            <p style="font-size:1rem; color:#475569; margin:0;">
                Let's set up your LifeOS profile and preferences.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "onboarding_choice" not in st.session_state:
        st.session_state.onboarding_choice = None

    if st.session_state.onboarding_choice is None:
        st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2, gap="large")

        with col1:
            st.markdown(
                """
                <div class="los-choice-card">
                    <p class="los-choice-title">Start Fresh</p>
                    <p class="los-choice-desc">Begin with a clean database. Configure your profile and immediately start logging your own data.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)
            if st.button("Configure My Profile", use_container_width=True, type="primary", key="onboard_fresh"):
                st.session_state.onboarding_choice = "fresh"
                st.rerun()

        with col2:
            st.markdown(
                """
                <div class="los-choice-card">
                    <p class="los-choice-title">Explore Demo Data</p>
                    <p class="los-choice-desc">Seed ~5 weeks of simulated productivity, health, and expense data to explore all charts and ML insights first.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)
            if st.button("Load Sample Data", use_container_width=True, key="onboard_demo"):
                st.session_state.onboarding_choice = "demo"
                st.rerun()
        return

    if st.session_state.onboarding_choice == "demo":
        with st.spinner("Populating simulated dataset..."):
            init_db.seed_all_demo_data(db, user_id)
        st.success("Demo data ready. Reloading...")
        st.session_state.pop("onboarding_choice", None)
        st.session_state.pop("needs_onboarding", None)
        st.rerun()
        return

    # "fresh" path → show profile form
    ui_components.section_header("YOUR PROFILE")
    _render_profile_form(db, user_id, is_demo=False, on_first_launch=True)


# =======================================================================
# NORMAL SETTINGS PAGE
# =======================================================================

def render(user_id: int):
    ui_components.page_header(
        "Settings",
        "Manage your profile details, consistency weights, data exports, and account security.",
    )

    db = get_session()
    try:
        profile = settings_crud.get_user_profile(db, user_id)

        if profile and profile.is_demo:
            ui_components.info_banner(
                "Demo Mode Active: You are exploring simulated data. "
                "Reset or start fresh in Data & Privacy whenever you're ready.",
                banner_type="warning",
            )

        tab_account, tab_weights, tab_privacy = st.tabs([
            "Account & Profile", "Consistency Score", "Data & Privacy"
        ])

        with tab_account:
            _render_account_and_profile(db, user_id, profile)

        with tab_weights:
            _render_score_weights(db, user_id, profile)

        with tab_privacy:
            _render_data_and_privacy(db, user_id, profile)

    finally:
        db.close()


# =======================================================================
# ACCOUNT & PROFILE TAB
# =======================================================================

def _render_account_and_profile(db, user_id: int, profile):
    display_name = auth_utils.get_current_display_name()
    email = auth_utils.get_current_email()
    initials = "".join(p[0].upper() for p in display_name.split()[:2]) if display_name else "U"

    # ---- 1. Compact Account Profile Card ----
    st.markdown(
        f"""
        <div style="background:#111927; border:1px solid #1e293b; border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1.5rem; display:flex; align-items:center; gap:1.25rem;">
            <div style="width:48px; height:48px; border-radius:50%; background:#1e1b4b; border:2px solid #3730a3; display:flex; align-items:center; justify-content:center; font-size:1.15rem; font-weight:800; color:#a5b4fc; flex-shrink:0;">
                {initials}
            </div>
            <div>
                <div style="font-size:1.1rem; font-weight:700; color:#f8fafc; margin-bottom:0.15rem;">
                    {display_name}
                </div>
                <div style="font-size:0.83rem; color:#64748b;">
                    {email}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- 2. Profile Information Form ----
    _render_profile_form(db, user_id, is_demo=profile.is_demo if profile else False)

    st.markdown("<hr style='border-color:#1e293b; margin:2rem 0;'>", unsafe_allow_html=True)

    # ---- 3. Security / Change Password ----
    _render_security_section(user_id)


def _render_profile_form(db, user_id: int, is_demo: bool = False, on_first_launch: bool = False):
    profile = settings_crud.get_user_profile(db, user_id)

    activity_options = ["sedentary", "light", "moderate", "active", "very_active"]

    if profile and profile.activity_level in activity_options:
        act_idx = activity_options.index(profile.activity_level)
    else:
        act_idx = 2  # Default to moderate

    with st.form("profile_form"):
        col1, col2 = st.columns(2, gap="large")
        with col1:
            ui_components.section_header("PERSONAL DETAILS")
            name = st.text_input("Name", value=profile.name if profile else auth_utils.get_current_display_name())
            age = st.number_input("Age", min_value=5, max_value=119, value=profile.age if profile else 22)
            sex = st.selectbox("Biological sex", ["male", "female"], index=0 if not profile or profile.sex == "male" else 1,
                               help="Used for Mifflin-St Jeor BMR calculation.")
            height_cm = st.number_input("Height (cm)", min_value=50.0, max_value=272.0, value=float(profile.height_cm) if profile else 170.0)
            weight_kg = st.number_input("Current weight (kg)", min_value=20.0, max_value=300.0, value=float(profile.weight_kg) if profile else 70.0, step=0.1, format="%.1f")

        with col2:
            ui_components.section_header("GOALS & TARGETS")
            activity_level = st.selectbox(
                "Activity level",
                activity_options,
                index=act_idx,
                format_func=lambda x: health_calc.ACTIVITY_LABELS.get(x, x.title()),
                help="Select your exercise frequency for TDEE calorie target calculations.",
            )
            goal = st.selectbox(
                "Weight goal",
                ["lose", "maintain", "gain"],
                index=["lose", "maintain", "gain"].index(profile.goal) if profile else 0,
                format_func=lambda x: {"lose": "Lose weight", "maintain": "Maintain weight", "gain": "Gain weight"}[x],
            )
            target_weight_kg = st.number_input(
                "Target weight (kg, optional)", min_value=0.0, max_value=300.0,
                value=float(profile.target_weight_kg) if profile and profile.target_weight_kg else 0.0,
                step=0.1, format="%.1f",
                help="Leave as 0 to maintain current weight.",
            )
            weekly_goal_kg = st.number_input(
                "Weekly change speed (kg/week)", min_value=0.0, max_value=1.5, step=0.1,
                value=float(profile.weekly_goal_kg) if profile and profile.weekly_goal_kg else 0.5,
            )
            daily_study_goal_minutes = st.number_input(
                "Daily study target (minutes)", min_value=0, max_value=1440,
                value=profile.daily_study_goal_minutes if profile else 60,
            )
            monthly_budget = st.number_input(
                "Monthly financial budget (₹, optional)", min_value=0.0,
                value=float(profile.monthly_budget) if profile and profile.monthly_budget else 0.0,
            )

        st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Save Profile", type="primary", use_container_width=True)

        if submitted:
            if not activity_level:
                st.error("Please select your activity level.")
            else:
                try:
                    settings_crud.save_user_profile(
                        db, user_id, name, int(age), sex, height_cm, weight_kg,
                        activity_level, goal,
                        target_weight_kg if target_weight_kg > 0 else None,
                        weekly_goal_kg, int(daily_study_goal_minutes),
                        monthly_budget if monthly_budget > 0 else None,
                        is_demo=is_demo,
                    )
                    if on_first_launch:
                        init_db.ensure_default_categories_and_subjects(db, user_id)
                        st.session_state.pop("onboarding_choice", None)
                        st.session_state.pop("needs_onboarding", None)
                    st.success("Profile saved successfully.")
                    st.rerun()
                except (ValueError, validation.ValidationError) as e:
                    st.error(str(e))

    # Target preview
    if profile:
        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        ui_components.section_header("ESTIMATED TARGETS", subtitle="Based on your profile using the Mifflin-St Jeor formula.")
        _render_calculated_preview(profile)


def _render_calculated_preview(profile):
    targets = health_calc.get_full_health_targets(
        age=profile.age, sex=profile.sex, height_cm=profile.height_cm,
        weight_kg=profile.weight_kg, activity_level=profile.activity_level,
        goal=profile.goal, target_weight_kg=profile.target_weight_kg,
        weekly_goal_kg=profile.weekly_goal_kg or 0.5,
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        ui_components.metric_card("BMR", f"{targets['bmr']:.0f} kcal", accent_color="#10b981")
    with c2:
        ui_components.metric_card("TDEE", f"{targets['tdee']:.0f} kcal", accent_color="#10b981")
    with c3:
        ui_components.metric_card("Calorie Target", f"{targets['calorie_target']:.0f} kcal", accent_color="#10b981")
    with c4:
        ui_components.metric_card("Protein Target", f"{targets['protein_target']:.0f} g", accent_color="#10b981")
    with c5:
        ui_components.metric_card("BMI", f"{targets['bmi']:.1f}", subtitle=targets['bmi_category'], accent_color="#10b981")

    if targets["calorie_warning"]:
        st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
        ui_components.info_banner(targets["calorie_warning"], banner_type="warning")

    st.caption(
        "These are estimates. BMR: Mifflin-St Jeor equation. TDEE = BMR × activity multiplier. "
        "Not clinical guidance — consult a healthcare professional for personalized advice."
    )


def _render_security_section(user_id: int):
    col_pw, col_so = st.columns([2, 1], gap="large")

    with col_pw:
        ui_components.section_header("CHANGE PASSWORD")
        with st.form("change_password_form", clear_on_submit=True):
            current_pw = st.text_input("Current password", type="password")
            new_pw = st.text_input("New password (min 8 chars)", type="password")
            confirm_pw = st.text_input("Confirm new password", type="password")
            submitted = st.form_submit_button("Update Password", type="primary")

            if submitted:
                if not current_pw or not new_pw or not confirm_pw:
                    st.error("All fields are required.")
                elif new_pw != confirm_pw:
                    st.error("New passwords do not match.")
                elif len(new_pw) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    db = get_session()
                    try:
                        user = db.get(__import__("database.models", fromlist=["User"]).User, user_id)
                        if user and user.password_hash and auth_utils.verify_password(current_pw, user.password_hash):
                            user.password_hash = auth_utils.hash_password(new_pw)
                            db.commit()
                            st.success("Password updated successfully.")
                        else:
                            st.error("Current password is incorrect.")
                    finally:
                        db.close()

    with col_so:
        ui_components.section_header("ACCOUNT ACTIONS")
        st.markdown(
            '<div style="font-size:0.83rem; color:#64748b; margin-bottom:0.75rem;">'
            'End your current LifeOS session on this device.'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign out", key="settings_signout", type="secondary", use_container_width=True):
            auth_utils.logout_user()
            st.rerun()


# =======================================================================
# SCORE WEIGHTS TAB
# =======================================================================

def _render_score_weights(db, user_id: int, profile):
    ui_components.section_header(
        "CONSISTENCY SCORE WEIGHTS",
        subtitle="Controls the proportion each domain contributes to your overall Consistency Score. Must sum to 1.00 (100%).",
    )

    if not profile:
        ui_components.empty_state("Complete your profile setup first.")
        return

    col_sld, col_preview = st.columns([2, 1], gap="large")
    with col_sld:
        study_w = st.slider("Study Weight", 0.0, 1.0, float(profile.score_weight_study or 0.4), 0.05,
                            format="%.2f", help="Contribution of study sessions to your score")
        health_w = st.slider("Health Weight", 0.0, 1.0, float(profile.score_weight_health or 0.35), 0.05,
                             format="%.2f", help="Contribution of nutrition and workouts")
        finance_w = st.slider("Finance Weight", 0.0, 1.0, float(profile.score_weight_finance or 0.25), 0.05,
                              format="%.2f", help="Contribution of budget adherence")

        total = round(study_w + health_w + finance_w, 2)
        is_valid = abs(total - 1.0) < 0.01

        if is_valid:
            st.markdown(
                '<p style="font-weight:700; font-size:0.9rem; color:#22c55e; margin-top:0.5rem;">'
                'Total: 1.00</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<p style="font-weight:700; font-size:0.9rem; color:#ef4444; margin-top:0.5rem;">'
                f'Total: {total:.2f} — Weights must add up to 1.00.</p>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("Save Weights", disabled=not is_valid, type="primary"):
            try:
                settings_crud.update_score_weights(db, user_id, study_w, health_w, finance_w)
                st.success("Weights saved successfully.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    with col_preview:
        st.markdown(
            f'<div style="padding:1.25rem;background:#111927;border:1px solid #1e293b;border-radius:10px;">'
            f'<p style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#475569;margin:0 0 0.75rem 0;">Weight Distribution</p>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:0.5rem;font-size:0.85rem;">'
            f'<span style="color:#a5b4fc;">Study</span><b style="color:#e2e8f0;">{study_w*100:.0f}%</b></div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:0.5rem;font-size:0.85rem;">'
            f'<span style="color:#6ee7b7;">Health</span><b style="color:#e2e8f0;">{health_w*100:.0f}%</b></div>'
            f'<div style="display:flex;justify-content:space-between;font-size:0.85rem;">'
            f'<span style="color:#fde68a;">Finance</span><b style="color:#e2e8f0;">{finance_w*100:.0f}%</b></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# =======================================================================
# DATA & PRIVACY TAB
# =======================================================================

def _render_data_and_privacy(db, user_id: int, profile):
    ui_components.section_header("DATA EXPORT", subtitle="Download your logged activity records as CSV files.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button(
            "Study CSV", export.export_study_csv(db, user_id),
            file_name="lifeos_study.csv", mime="text/csv", use_container_width=True,
        )
    with col2:
        st.download_button(
            "Health CSV", export.export_health_csv(db, user_id),
            file_name="lifeos_health.csv", mime="text/csv", use_container_width=True,
        )
    with col3:
        st.download_button(
            "Finance CSV", export.export_finance_csv(db, user_id),
            file_name="lifeos_finance.csv", mime="text/csv", use_container_width=True,
        )
    with col4:
        st.download_button(
            "Combined CSV", export.export_all_csv(db, user_id),
            file_name="lifeos_combined.csv", mime="text/csv", use_container_width=True,
        )

    st.markdown("<hr style='border-color:#1e293b; margin:2rem 0;'>", unsafe_allow_html=True)

    ui_components.section_header("DATA MANAGEMENT")
    ui_components.info_banner(
        "These operations modify or delete your logged data. They cannot be undone.",
        banner_type="warning",
    )

    if profile and profile.is_demo:
        ui_components.section_header("DEMO DATA ACTIONS")
        st.caption("Your account is currently using simulated demo data.")
        if st.button("Reset & Reload Demo Data", use_container_width=True):
            init_db.reset_demo_data(db, user_id)
            st.success("Demo data reloaded.")
            st.rerun()

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        st.caption("Wipe all demo data and start entering your own records.")
        if st.button("Delete Demo Data & Start Fresh", type="secondary", use_container_width=True):
            settings_crud.delete_all_user_data(db, user_id)
            st.success("Demo data cleared. Return to Dashboard to begin.")
            st.rerun()
    else:
        ui_components.section_header("RESET ACTIVITY LOGS")
        st.caption(
            "Deletes all your logged study sessions, meals, water, workouts, and expenses. "
            "Your profile and settings remain unchanged."
        )
        confirm = st.checkbox("I understand this action is permanent and cannot be undone.")
        if st.button("Reset Logged Activity", disabled=not confirm, type="secondary", use_container_width=True):
            settings_crud.reset_logged_data_keep_profile(db, user_id)
            st.success("Activity logs cleared. Profile preserved.")
            st.rerun()
