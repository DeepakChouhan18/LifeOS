"""
Streamlit UI for the Health & Fitness module.

Structured as its own complete mini-application: Overview, Nutrition,
Workout, Weight, Analytics tabs — so opening Health feels like using a
dedicated health app, not one section of a bigger form.
"""

import streamlit as st
from datetime import date

from database.connection import get_session
from modules.health import crud, analytics
from modules.settings import crud as settings_crud
from utils.charts import weight_trend_line, workout_consistency_bar, weekly_calories_line
from utils.ui_components import empty_state, progress_metric
from utils import validation
from config import DEFAULT_USER_ID


def render():
    st.header("💪 Health")

    db = get_session()
    try:
        profile = settings_crud.get_user_profile(db, DEFAULT_USER_ID)
        if not profile:
            empty_state("Complete your profile in Settings to unlock automatic health targets.")
            return

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["Overview", "Nutrition", "Workout", "Weight", "Analytics"])

        with tab1:
            _render_overview(db, profile)
        with tab2:
            _render_nutrition(db)
        with tab3:
            _render_workout(db)
        with tab4:
            _render_weight(db)
        with tab5:
            _render_analytics(db)
    finally:
        db.close()


def _render_overview(db, profile):
    summary = analytics.get_full_summary(db, DEFAULT_USER_ID)

    if summary["calorie_warning"]:
        st.warning(summary["calorie_warning"])

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current Weight", f"{summary['latest_weight']:.1f} kg" if summary["latest_weight"] else "—")
    with col2:
        st.metric("Target Weight", f"{summary['target_weight']:.1f} kg" if summary["target_weight"] else "—")

    if summary["weight_progress_pct"] is not None:
        st.caption(f"Progress toward goal: {summary['weight_progress_pct']:.0f}%")
        st.progress(min(1.0, max(0.0, summary["weight_progress_pct"] / 100)))

    st.divider()

    c1, c2 = st.columns(2)
    c1.metric("Estimated Maintenance (TDEE)", f"{summary['tdee']:.0f} kcal" if summary['tdee'] else "—")
    c2.metric("Today's Calorie Target", f"{summary['calorie_target']:.0f} kcal" if summary['calorie_target'] else "—")

    st.divider()

    if summary["calorie_target"]:
        progress_metric("Calories", summary["calories_today"], summary["calorie_target"], "kcal")
    if summary["protein_target_g"]:
        progress_metric("Protein", summary["protein_today"], summary["protein_target_g"], "g")
    if summary["water_target_ml"]:
        progress_metric("Water", summary["water_today"], summary["water_target_ml"], "ml")

    st.divider()
    st.write(f"**Today's workout:** {'✅ Completed' if summary['workout_completed_today'] else '⬜ Not completed'}")


# =======================================================================
# NUTRITION TAB
# =======================================================================

def _render_nutrition(db):
    st.subheader("Quick Add Food")

    recent_foods = crud.get_recent_foods(db, DEFAULT_USER_ID)
    if recent_foods:
        st.caption("Recent Foods — click to quick-fill")
        cols = st.columns(min(4, len(recent_foods)))
        for i, food in enumerate(recent_foods[:8]):
            col = cols[i % len(cols)]
            with col:
                if st.button(f"🍽️ {food['meal_name']}", key=f"recent_{i}", use_container_width=True):
                    st.session_state["quick_food"] = food
                    st.rerun()

    quick = st.session_state.get("quick_food", {})

    with st.form("add_food_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            meal_name = st.text_input("Food", value=quick.get("meal_name", ""))
        with col2:
            meal_type = st.selectbox("Meal", ["Breakfast", "Lunch", "Dinner", "Snack"])

        col3, col4, col5, col6 = st.columns(4)
        with col3:
            calories = st.number_input("Calories", min_value=0, value=int(quick.get("typical_calories") or 0))
        with col4:
            protein = st.number_input("Protein (g)", min_value=0.0, value=float(quick.get("typical_protein_g") or 0))
        with col5:
            carbs = st.number_input("Carbs (g)", min_value=0.0, value=float(quick.get("typical_carbs_g") or 0))
        with col6:
            fats = st.number_input("Fats (g)", min_value=0.0, value=float(quick.get("typical_fats_g") or 0))

        submitted = st.form_submit_button("+ Add Food", type="primary")
        if submitted:
            try:
                crud.log_nutrition(db, DEFAULT_USER_ID, meal_name, date.today(), meal_type,
                                    int(calories), protein, carbs, fats)
                st.session_state.pop("quick_food", None)
                st.success(f"Added {meal_name}")
                st.rerun()
            except validation.ValidationError as e:
                st.error(str(e))

    st.divider()
    st.subheader("💧 Water")
    col1, col2, col3, col4 = st.columns(4)
    for i, amt in enumerate([250, 500, 750, 1000]):
        with [col1, col2, col3, col4][i]:
            if st.button(f"+{amt} ml", key=f"water_{amt}", use_container_width=True):
                crud.log_water(db, DEFAULT_USER_ID, amt)
                st.rerun()

    st.divider()
    st.subheader("Today's Log")
    todays_logs = crud.list_nutrition_logs(db, DEFAULT_USER_ID, log_date=date.today())
    if not todays_logs:
        empty_state("No meals logged today.")
    else:
        for log in todays_logs:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            col1.write(f"**{log.meal_name}** ({log.meal_type or 'Meal'})")
            col2.write(f"{log.calories or 0} kcal")
            if col3.button("Duplicate", key=f"dup_{log.id}"):
                crud.duplicate_nutrition_log(db, log.id)
                st.rerun()
            if col4.button("Delete", key=f"del_food_{log.id}"):
                crud.delete_nutrition_log(db, log.id)
                st.rerun()


# =======================================================================
# WORKOUT TAB
# =======================================================================

def _render_workout(db):
    st.subheader("Log Workout")
    with st.form("log_workout_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            workout_date = st.date_input("Date", value=date.today())
            workout_type = st.selectbox("Type", ["Strength", "Cardio", "Yoga", "Sports", "Other"])
        with col2:
            exercise = st.text_input("Exercise (optional)", placeholder="e.g. Bench Press, 5k Run")
            duration = st.number_input("Duration (minutes)", min_value=5, max_value=300, value=30, step=5)
        notes = st.text_input("Notes (optional)")

        if st.form_submit_button("+ Add Workout", type="primary"):
            try:
                crud.log_workout(db, DEFAULT_USER_ID, workout_date, workout_type,
                                  exercise or None, int(duration), notes or None)
                st.success("Workout logged")
                st.rerun()
            except validation.ValidationError as e:
                st.error(str(e))

    st.divider()
    st.subheader("Recent Workouts")
    workouts = crud.list_workouts(db, DEFAULT_USER_ID, limit=15)
    if not workouts:
        empty_state("No workouts logged yet.")
    else:
        for w in workouts:
            col1, col2, col3 = st.columns([3, 1, 1])
            label = f"**{w.type or 'Workout'}**"
            if w.exercise:
                label += f" — {w.exercise}"
            col1.write(f"{label} · {w.workout_date} · {w.duration_minutes or '—'} min")
            if col3.button("Delete", key=f"del_workout_{w.id}"):
                crud.delete_workout(db, w.id)
                st.rerun()


# =======================================================================
# WEIGHT TAB
# =======================================================================

def _render_weight(db):
    st.subheader("Today's Weight")
    with st.form("log_weight_form"):
        weight = st.number_input("Weight (kg)", min_value=20.0, max_value=400.0, value=70.0, step=0.1)
        sleep = st.number_input("Sleep last night (hours, optional)", min_value=0.0, max_value=24.0, value=0.0, step=0.5)
        if st.form_submit_button("Save Weight", type="primary"):
            try:
                crud.log_body_metric(db, DEFAULT_USER_ID, date.today(), weight,
                                      sleep if sleep > 0 else None)
                st.success("Weight saved")
                st.rerun()
            except validation.ValidationError as e:
                st.error(str(e))

    progress = analytics.get_weight_progress(db, DEFAULT_USER_ID)
    if progress["starting"] is not None:
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Starting", f"{progress['starting']:.1f} kg")
        c2.metric("Current", f"{progress['current']:.1f} kg")
        c3.metric("Target", f"{progress['target']:.1f} kg" if progress["target"] else "—")
        if progress["change"] is not None:
            st.caption(f"Change since start: {progress['change']:+.1f} kg")

    st.divider()
    st.subheader("Weight Trend")
    weight_df = analytics.get_weight_trend_df(db, DEFAULT_USER_ID)
    fig = weight_trend_line(weight_df)
    if fig:
        # Drop the chart's own title — the subheader above already covers it.
        fig.update_layout(title=None, margin=dict(l=20, r=20, t=20, b=70))
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_state("No weight data logged yet.")


# =======================================================================
# ANALYTICS TAB
# =======================================================================

def _render_analytics(db):
    st.subheader("Health Analytics")

    averages = analytics.get_calorie_averages(db, DEFAULT_USER_ID)
    consistency = analytics.get_target_consistency(db, DEFAULT_USER_ID, days=7)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("7-Day Avg Calories", f"{averages['avg_7day']:.0f}" if averages["avg_7day"] else "—")
    c2.metric("30-Day Avg Calories", f"{averages['avg_30day']:.0f}" if averages["avg_30day"] else "—")
    c3.metric("Calorie Target Consistency", f"{consistency['calorie_consistency_pct']:.0f}%"
              if consistency["calorie_consistency_pct"] is not None else "—")
    c4.metric("Protein Target Consistency", f"{consistency['protein_consistency_pct']:.0f}%"
              if consistency["protein_consistency_pct"] is not None else "—")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        nutrition_df = analytics.get_weekly_nutrition_df(db, DEFAULT_USER_ID)
        fig = weekly_calories_line(nutrition_df)
        st.plotly_chart(fig, use_container_width=True) if fig else empty_state("Not enough nutrition data yet.")
    with col2:
        workout_df = analytics.get_workout_consistency_df(db, DEFAULT_USER_ID)
        fig = workout_consistency_bar(workout_df)
        st.plotly_chart(fig, use_container_width=True) if fig else empty_state("No workouts logged yet.")

    st.divider()
    st.subheader("Adaptive Maintenance Estimate (Advanced)")
    st.caption(
        "Compares your formula-based TDEE estimate to an ESTIMATE observed from "
        "your actual logged calories and weight change. Only shown once enough "
        "consistent data exists — never a fabricated precision number."
    )
    observed = analytics.estimate_observed_maintenance(db, DEFAULT_USER_ID)
    if observed["available"]:
        targets = analytics.get_user_health_targets(db, DEFAULT_USER_ID)
        c1, c2 = st.columns(2)
        c1.metric("Formula Estimate (TDEE)", f"{targets['tdee']:.0f} kcal")
        c2.metric("Observed Estimate", f"~{observed['observed_maintenance']:.0f} kcal")
        st.caption(
            f"Based on {observed['days_span']} days: avg intake "
            f"{observed['avg_daily_calories']:.0f} kcal/day, weight change "
            f"{observed['weight_change_kg']:+.2f} kg."
        )
    else:
        empty_state(observed["message"])
