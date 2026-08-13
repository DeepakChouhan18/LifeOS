"""
Streamlit UI for onboarding and Settings.

render_onboarding() is shown once, before any profile exists. It offers
a genuine choice: start with an empty personal database, or explore the
app with clearly-labeled demo data. render() is the normal Settings page,
reachable any time afterward to edit the profile, adjust score weights,
export data, or reset demo data.
"""

import streamlit as st
from datetime import date

from database.connection import get_session
from database import init_db
from modules.settings import crud as settings_crud
from utils import health_calc, export, validation
from utils.ui_components import empty_state
from config import DEFAULT_USER_ID


# =======================================================================
# ONBOARDING (first launch — no profile exists yet)
# =======================================================================

def render_onboarding(db):
    st.title("Welcome to LifeOS")
    st.caption("Your personal study, health & finance analytics platform.")

    if "onboarding_choice" not in st.session_state:
        st.session_state.onboarding_choice = None

    if st.session_state.onboarding_choice is None:
        st.subheader("Choose how to start")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🌱 Start Fresh")
            st.write("An empty, personal database. You'll enter your own profile "
                     "and start logging your real data right away.")
            if st.button("Start Fresh", use_container_width=True, type="primary"):
                st.session_state.onboarding_choice = "fresh"
                st.rerun()
        with col2:
            st.markdown("### 🧪 Explore Demo Data")
            st.write("Loads ~5 weeks of clearly-labeled sample data so you can "
                     "see every feature in action before committing to daily use. "
                     "Resettable any time from Settings.")
            if st.button("Explore Demo Data", use_container_width=True):
                st.session_state.onboarding_choice = "demo"
                st.rerun()
        return

    if st.session_state.onboarding_choice == "demo":
        with st.spinner("Loading demo data..."):
            init_db.seed_all_demo_data(db, DEFAULT_USER_ID)
        st.success("Demo data loaded. Reloading...")
        st.session_state.pop("onboarding_choice")
        st.rerun()
        return

    # "fresh" path -> show the profile form
    st.subheader("Tell us about yourself")
    st.caption("This lets LifeOS calculate your personal health targets automatically. "
               "You can edit this any time from Settings.")
    _render_profile_form(db, DEFAULT_USER_ID, is_demo=False, on_first_launch=True)


# =======================================================================
# NORMAL SETTINGS PAGE
# =======================================================================

def render():
    st.header("⚙️ Settings")

    db = get_session()
    try:
        profile = settings_crud.get_user_profile(db, DEFAULT_USER_ID)

        if profile and profile.is_demo:
            st.info("🧪 You're currently using **demo data**. Feel free to explore — "
                    "you can reset it any time below, or wipe it to start fresh with your own data.")

        tab1, tab2, tab3, tab4 = st.tabs(["Profile", "Personal Consistency Score", "Data Export", "Data Management"])

        with tab1:
            _render_profile_form(db, DEFAULT_USER_ID, is_demo=profile.is_demo if profile else False)

        with tab2:
            _render_score_weights(db, profile)

        with tab3:
            _render_export(db)

        with tab4:
            _render_data_management(db, profile)
    finally:
        db.close()


def _render_profile_form(db, user_id, is_demo=False, on_first_launch=False):
    profile = settings_crud.get_user_profile(db, user_id)

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", value=profile.name if profile else "")
            age = st.number_input("Age", min_value=5, max_value=119,
                                   value=profile.age if profile else 22)
            sex = st.selectbox("Sex", ["male", "female"],
                                index=0 if not profile or profile.sex == "male" else 1)
            height_cm = st.number_input("Height (cm)", min_value=50.0, max_value=272.0,
                                         value=float(profile.height_cm) if profile else 170.0)
        with col2:
            weight_kg = st.number_input("Current weight (kg)", min_value=20.0, max_value=400.0,
                                         value=float(profile.weight_kg) if profile else 70.0)
            activity_level = st.selectbox(
                "Activity level",
                ["sedentary", "light", "moderate", "active", "very_active"],
                index=["sedentary", "light", "moderate", "active", "very_active"].index(
                    profile.activity_level) if profile else 2,
                format_func=lambda x: health_calc.ACTIVITY_LABELS.get(x, x),
            )
            goal = st.selectbox("Goal", ["lose", "maintain", "gain"],
                                 index=["lose", "maintain", "gain"].index(profile.goal) if profile else 0,
                                 format_func=lambda x: {"lose": "Lose Weight", "maintain": "Maintain Weight",
                                                          "gain": "Gain Weight"}[x])
            target_weight_kg = st.number_input(
                "Target weight (kg, optional)", min_value=0.0, max_value=400.0,
                value=float(profile.target_weight_kg) if profile and profile.target_weight_kg else 0.0)

        col3, col4 = st.columns(2)
        with col3:
            weekly_goal_kg = st.number_input(
                "Weekly weight change goal (kg/week)", min_value=0.0, max_value=1.5, step=0.1,
                value=float(profile.weekly_goal_kg) if profile and profile.weekly_goal_kg else 0.5)
            daily_study_goal_minutes = st.number_input(
                "Daily study goal (minutes)", min_value=0, max_value=1440,
                value=profile.daily_study_goal_minutes if profile else 60)
        with col4:
            monthly_budget = st.number_input(
                "Monthly budget (₹, optional)", min_value=0.0,
                value=float(profile.monthly_budget) if profile and profile.monthly_budget else 0.0)

        submitted = st.form_submit_button(
            "Save & Continue" if on_first_launch else "Save Profile", type="primary")

        if submitted:
            try:
                saved = settings_crud.save_user_profile(
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
                st.success("Profile saved.")
                st.rerun()
            except (ValueError, validation.ValidationError) as e:
                st.error(str(e))

    # Live preview of calculated targets, updates as soon as the form is submitted
    if profile:
        st.divider()
        st.subheader("Your calculated targets")
        _render_calculated_preview(profile)


def _render_calculated_preview(profile):
    targets = health_calc.get_full_health_targets(
        age=profile.age, sex=profile.sex, height_cm=profile.height_cm,
        weight_kg=profile.weight_kg, activity_level=profile.activity_level,
        goal=profile.goal, target_weight_kg=profile.target_weight_kg,
        weekly_goal_kg=profile.weekly_goal_kg or 0.5,
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("BMR", f"{targets['bmr']:.0f} kcal")
    c2.metric("Est. Maintenance (TDEE)", f"{targets['tdee']:.0f} kcal")
    c3.metric("Daily Calorie Target", f"{targets['calorie_target']:.0f} kcal")
    c4.metric("Protein Target", f"{targets['protein_target']:.0f} g")
    c5.metric("BMI", f"{targets['bmi']:.1f} ({targets['bmi_category']})")

    if targets["calorie_warning"]:
        st.warning(targets["calorie_warning"])

    st.caption(
        "BMR via Mifflin-St Jeor equation. TDEE = BMR × activity multiplier — "
        "labeled as an **estimate**, not your exact real-world maintenance. "
        "These recalculate automatically whenever you update your profile."
    )


def _render_score_weights(db, profile):
    st.subheader("Personal Consistency Score weights")
    st.caption(
        "This score is **not** an objective measure of your life — it's a "
        "simple weighted average you control, meant as a rough daily signal. "
        "Adjust how much each area counts."
    )

    if not profile:
        empty_state("Complete your profile first.")
        return

    study_w = st.slider("Study weight", 0.0, 1.0, float(profile.score_weight_study or 0.4), 0.05)
    health_w = st.slider("Health weight", 0.0, 1.0, float(profile.score_weight_health or 0.35), 0.05)
    finance_w = st.slider("Finance weight", 0.0, 1.0, float(profile.score_weight_finance or 0.25), 0.05)

    total = round(study_w + health_w + finance_w, 2)
    st.write(f"Total: **{total}** (must equal 1.0)")

    if st.button("Save Weights", disabled=(abs(total - 1.0) > 0.01)):
        try:
            settings_crud.update_score_weights(db, DEFAULT_USER_ID, study_w, health_w, finance_w)
            st.success("Weights updated.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))


def _render_export(db):
    st.subheader("Export your data")
    st.caption("Download clean CSV exports of your logged data.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button("📚 Study CSV", export.export_study_csv(db, DEFAULT_USER_ID),
                            file_name="lifeos_study.csv", mime="text/csv")
    with col2:
        st.download_button("💪 Health CSV", export.export_health_csv(db, DEFAULT_USER_ID),
                            file_name="lifeos_health.csv", mime="text/csv")
    with col3:
        st.download_button("💰 Finance CSV", export.export_finance_csv(db, DEFAULT_USER_ID),
                            file_name="lifeos_finance.csv", mime="text/csv")
    with col4:
        st.download_button("📦 Combined CSV", export.export_all_csv(db, DEFAULT_USER_ID),
                            file_name="lifeos_combined.csv", mime="text/csv")


def _render_data_management(db, profile):
    st.subheader("Data management")

    if profile and profile.is_demo:
        st.write("**Reset demo data** — wipes all demo records and reloads a fresh demo dataset.")
        if st.button("🔄 Reset Demo Data"):
            init_db.reset_demo_data(db, DEFAULT_USER_ID)
            st.success("Demo data reset.")
            st.rerun()

        st.divider()
        st.write("**Switch to your own data** — permanently deletes all demo data "
                 "and lets you start fresh with a real profile.")
        if st.button("🌱 Delete Demo Data & Start Fresh", type="secondary"):
            settings_crud.delete_all_user_data(db, DEFAULT_USER_ID)
            st.success("Demo data cleared. Reloading onboarding...")
            st.rerun()
    else:
        st.write("**Reset logged data** — clears all your study/health/finance "
                 "records but keeps your profile.")
        confirm = st.checkbox("I understand this cannot be undone")
        if st.button("🗑️ Reset My Logged Data", disabled=not confirm):
            settings_crud.reset_logged_data_keep_profile(db, DEFAULT_USER_ID)
            st.success("Logged data cleared. Your profile is unchanged.")
            st.rerun()
