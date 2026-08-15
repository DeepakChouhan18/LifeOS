"""
Streamlit UI for the Health & Fitness module.

Modern health tracking interface with:
- Overview: weight, target, calorie progress, TDEE/BMR from profile
- Nutrition & Water: meal logging with recent foods quick-fill
- Workouts: session logger and history
- Weight & Sleep: daily body metric logging
- Analytics: trends, calorie averages, consistency
"""

import streamlit as st
from datetime import date

from database.connection import get_session
from modules.health import crud, analytics
from modules.settings import crud as settings_crud
from utils.charts import weight_trend_line, workout_consistency_bar, weekly_calories_line, macro_breakdown_donut
from utils.ui_components import empty_state, progress_metric
from utils import ui_components, validation


def render(user_id: int):
    ui_components.page_header(
        "Health",
        "Track nutrition, weight, workouts, and monitor your daily targets.",
    )

    db = get_session()
    try:
        profile = settings_crud.get_user_profile(db, user_id)
        if not profile:
            ui_components.empty_state(
                "Complete your profile in Settings to unlock health targets.",
                icon="",
                hint="Your height, weight, activity level, and goal are used to estimate daily targets.",
            )
            return

        tab_overview, tab_nutrition, tab_workout, tab_weight, tab_analytics = st.tabs([
            "Overview", "Nutrition & Water", "Workouts", "Weight & Sleep", "Analytics"
        ])

        with tab_overview:
            _render_overview(db, profile, user_id)
        with tab_nutrition:
            _render_nutrition(db, user_id)
        with tab_workout:
            _render_workout(db, user_id)
        with tab_weight:
            _render_weight(db, user_id)
        with tab_analytics:
            _render_analytics(db, user_id)
    finally:
        db.close()


# =======================================================================
# OVERVIEW TAB
# =======================================================================

def _render_overview(db, profile, user_id: int):
    summary = analytics.get_full_summary(db, user_id)

    if summary["calorie_warning"]:
        ui_components.info_banner(summary["calorie_warning"], banner_type="warning")

    # Metrics Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        weight_val = f"{summary['latest_weight']:.1f} kg" if summary["latest_weight"] else "—"
        ui_components.metric_card("Current Weight", weight_val, accent_color="#10b981")
    with c2:
        target_val = f"{summary['target_weight']:.1f} kg" if summary["target_weight"] else "—"
        ui_components.metric_card("Target Weight", target_val, accent_color="#10b981")
    with c3:
        tdee_val = f"{summary['tdee']:.0f} kcal" if summary['tdee'] else "—"
        ui_components.metric_card("Maintenance (TDEE)", tdee_val, subtitle="Formula estimate", accent_color="#10b981")
    with c4:
        cal_val = f"{summary['calorie_target']:.0f} kcal" if summary['calorie_target'] else "—"
        ui_components.metric_card("Daily Target", cal_val, subtitle="Goal-adjusted", accent_color="#10b981")

    # Weight goal progress bar
    if summary["weight_progress_pct"] is not None:
        st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)
        col_lbl, col_bar = st.columns([1, 4])
        col_lbl.markdown(
            f'<span style="font-size:0.82rem;font-weight:600;color:#64748b;">Goal {summary["weight_progress_pct"]:.0f}%</span>',
            unsafe_allow_html=True,
        )
        col_bar.progress(min(1.0, max(0.0, summary["weight_progress_pct"] / 100)))

    st.markdown("<hr style='border-color:#1a2540;margin:1.25rem 0;'>", unsafe_allow_html=True)

    # Today targets & daily intake
    col_targets, col_today = st.columns([1, 1], gap="large")

    with col_targets:
        ui_components.section_header("TODAY'S TARGETS")
        if summary["calorie_target"]:
            progress_metric("Calories", summary["calories_today"], summary["calorie_target"], "kcal")
        if summary["protein_target_g"]:
            st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)
            progress_metric("Protein", summary["protein_today"], summary["protein_target_g"], "g")
        if summary["water_target_ml"]:
            st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)
            progress_metric("Water", summary["water_today"], summary["water_target_ml"], "ml")

        # Macronutrient summary today
        st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)
        todays_logs = crud.list_nutrition_logs(db, user_id, log_date=date.today())
        total_p = sum(l.protein_g or 0.0 for l in todays_logs)
        total_c = sum(l.carbs_g or 0.0 for l in todays_logs)
        total_f = sum(l.fats_g or 0.0 for l in todays_logs)
        st.markdown(
            f'<div style="font-size:0.78rem;color:#64748b;line-height:1.8;">'
            f'Protein: <b style="color:#94a3b8;">{total_p:.0f} g</b> &nbsp;·&nbsp; '
            f'Carbs: <b style="color:#94a3b8;">{total_c:.0f} g</b> &nbsp;·&nbsp; '
            f'Fat: <b style="color:#94a3b8;">{total_f:.0f} g</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_today:
        ui_components.section_header("TODAY'S ACTIVITY")
        w_completed = summary["workout_completed_today"]
        status_lbl = "Done" if w_completed else "Not yet"
        status_variant = "success" if w_completed else "neutral"

        st.markdown(
            f'<div style="padding:1rem;background:#111927;border-radius:8px;border:1px solid #1e293b;margin-bottom:0.75rem;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-weight:600;color:#e2e8f0;font-size:0.875rem;">Daily Workout</span>'
            f'{ui_components.status_badge(status_lbl, status_variant)}'
            f'</div>'
            f'<p style="font-size:0.78rem;color:#475569;margin:0.4rem 0 0 0;">'
            f'Logging workouts helps keep your consistency score accurate.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Quick actions
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("+ Log Food", key="hlth_quick_food", use_container_width=True):
                st.session_state["health_tab_override"] = "Nutrition & Water"
                st.rerun()
        with col_b:
            if st.button("+ Log Workout", key="hlth_quick_workout", use_container_width=True):
                st.session_state["health_tab_override"] = "Workouts"
                st.rerun()

    # Calorie calculator explainer
    with st.expander("Calorie Calculator — how your target is calculated"):
        from utils import health_calc
        bmr = summary.get("bmr")
        tdee = summary.get("tdee")
        cal_target = summary.get("calorie_target")
        goal = profile.goal or "maintain"
        if bmr and tdee:
            st.markdown(
                f"""
                **Formula**: Mifflin-St Jeor equation (1990)

                | Component | Value |
                |---|---|
                | BMR (Basal Metabolic Rate) | **{bmr:.0f} kcal/day** |
                | Activity Multiplier ({health_calc.ACTIVITY_LABELS.get(profile.activity_level, profile.activity_level)}) | × {health_calc.ACTIVITY_MULTIPLIERS.get(profile.activity_level, 1.55):.3f} |
                | TDEE (Maintenance) | **{tdee:.0f} kcal/day** |
                | Goal Adjustment ({goal}) | {'-' if goal == 'lose' else '+' if goal == 'gain' else '±'}{abs(tdee - (cal_target or tdee)):.0f} kcal |
                | **Daily Target** | **{cal_target:.0f} kcal/day** |

                *These are estimates. Consult a healthcare professional before making dietary changes.*
                """,
                unsafe_allow_html=False,
            )
        else:
            st.caption("Complete your profile in Settings to see your calorie calculation breakdown.")


# =======================================================================
# NUTRITION TAB
# =======================================================================

def _render_nutrition(db, user_id: int):
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        ui_components.section_header("LOG FOOD")
        recent_foods = crud.get_recent_foods(db, user_id)
        if recent_foods:
            st.caption("Quick-fill from recent foods:")
            cols = st.columns(min(4, len(recent_foods)))
            for i, food in enumerate(recent_foods[:8]):
                col = cols[i % len(cols)]
                with col:
                    if st.button(food['meal_name'], key=f"recent_{i}", use_container_width=True):
                        st.session_state["quick_food"] = food
                        st.rerun()

        quick = st.session_state.get("quick_food", {})

        with st.form("add_food_form", clear_on_submit=True):
            col_name, col_type = st.columns([2, 1])
            with col_name:
                meal_name = st.text_input("Food name", value=quick.get("meal_name", ""))
            with col_type:
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

            submitted = st.form_submit_button("+ Add Food", type="primary", use_container_width=True)
            if submitted and meal_name:
                try:
                    crud.log_nutrition(db, user_id, meal_name, date.today(), meal_type,
                                        int(calories), protein, carbs, fats)
                    st.session_state.pop("quick_food", None)
                    st.success(f"Added {meal_name}.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
            elif submitted:
                st.error("Please enter a food name.")

        st.markdown("<hr style='border-color:#1a2540;margin:1rem 0;'>", unsafe_allow_html=True)
        ui_components.section_header("WATER INTAKE")
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        water_amounts = [250, 500, 750, 1000]
        for col, amt in zip([col_w1, col_w2, col_w3, col_w4], water_amounts):
            with col:
                if st.button(f"+{amt} ml", key=f"water_{amt}", use_container_width=True):
                    crud.log_water(db, user_id, amt)
                    st.rerun()

    with col_right:
        ui_components.section_header("TODAY'S MEALS")
        todays_logs = crud.list_nutrition_logs(db, user_id, log_date=date.today())

        fig = macro_breakdown_donut(
            sum(l.protein_g or 0.0 for l in todays_logs),
            sum(l.carbs_g or 0.0 for l in todays_logs),
            sum(l.fats_g or 0.0 for l in todays_logs),
        )
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="health_macro_donut")
        else:
            ui_components.empty_state("No foods logged today", icon="", hint="Add meals using the form.")

        if todays_logs:
            st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
            for log in todays_logs:
                l_col1, l_col2, l_col3 = st.columns([3, 1.2, 1.0])
                with l_col1:
                    st.markdown(
                        f'<div style="font-weight:600;font-size:0.875rem;color:#e2e8f0;">{log.meal_name}</div>'
                        f'<div style="font-size:0.75rem;color:#64748b;">{log.meal_type or "Meal"} · '
                        f'P:{log.protein_g or 0:.0f}g C:{log.carbs_g or 0:.0f}g F:{log.fats_g or 0:.0f}g</div>',
                        unsafe_allow_html=True,
                    )
                with l_col2:
                    st.markdown(
                        f'<div style="text-align:right;font-weight:600;color:#f8fafc;font-size:0.875rem;">{log.calories or 0} kcal</div>',
                        unsafe_allow_html=True,
                    )
                with l_col3:
                    sub_c1, sub_c2 = st.columns(2)
                    if sub_c1.button("Copy", key=f"dup_{log.id}", help="Duplicate"):
                        crud.duplicate_nutrition_log(db, log.id)
                        st.rerun()
                    if sub_c2.button("Delete", key=f"del_food_{log.id}", help="Delete"):
                        crud.delete_nutrition_log(db, log.id)
                        st.rerun()
                st.markdown('<hr style="border-color:#1a2540;margin:0.25rem 0;">', unsafe_allow_html=True)


# =======================================================================
# WORKOUT TAB
# =======================================================================

def _render_workout(db, user_id: int):
    col_log, col_hist = st.columns([1, 2], gap="large")

    with col_log:
        ui_components.section_header("LOG WORKOUT")
        with st.form("log_workout_form", clear_on_submit=True):
            col_date, col_type = st.columns(2)
            with col_date:
                workout_date = st.date_input("Date", value=date.today())
            with col_type:
                workout_type = st.selectbox("Type", ["Strength", "Cardio", "Yoga", "Sports", "Other"])

            exercise = st.text_input("Exercise (optional)", placeholder="e.g. Bench Press, 5k Run")
            duration = st.number_input("Duration (minutes)", min_value=5, max_value=300, value=30, step=5)
            notes = st.text_input("Notes (optional)")

            submitted = st.form_submit_button("+ Add Workout", type="primary", use_container_width=True)
            if submitted:
                try:
                    crud.log_workout(db, user_id, workout_date, workout_type,
                                      exercise or None, int(duration), notes or None)
                    st.success("Workout logged.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    with col_hist:
        ui_components.section_header("RECENT WORKOUTS")
        workouts = crud.list_workouts(db, user_id, limit=15)
        if not workouts:
            ui_components.empty_state(
                "No workouts logged yet",
                icon="",
                hint="Use the form to log your first workout session.",
            )
        else:
            for w in workouts:
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    type_str = w.type or "Workout"
                    exercise_str = f" — {w.exercise}" if w.exercise else ""
                    date_lbl = w.workout_date.strftime("%b %d") if hasattr(w.workout_date, "strftime") else str(w.workout_date)
                    dur_str = f"{w.duration_minutes} min" if w.duration_minutes else "—"
                    st.markdown(
                        f'<div style="padding:0.6rem 0.75rem;background:#111927;border-radius:8px;'
                        f'margin-bottom:0.35rem;border:1px solid #1e293b;">'
                        f'<div style="font-size:0.875rem;font-weight:500;color:#e2e8f0;">{type_str}{exercise_str}</div>'
                        f'<div style="font-size:0.75rem;color:#64748b;margin-top:0.1rem;">{date_lbl} · {dur_str}'
                        + (f' · {w.notes}' if w.notes else '') +
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                with col_del:
                    st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)
                    if st.button("✕", key=f"del_workout_{w.id}", use_container_width=True):
                        crud.delete_workout(db, w.id)
                        st.rerun()


# =======================================================================
# WEIGHT & SLEEP TAB
# =======================================================================

def _render_weight(db, user_id: int):
    col_log, col_trend = st.columns([1, 2], gap="large")

    with col_log:
        ui_components.section_header("LOG DAILY METRICS")
        with st.form("log_weight_form"):
            weight = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, step=0.1, format="%.1f")
            sleep = st.number_input("Sleep last night (hours)", min_value=0.0, max_value=24.0, value=0.0, step=0.5)

            submitted = st.form_submit_button("Save Metrics", type="primary", use_container_width=True)
            if submitted:
                try:
                    crud.log_body_metric(db, user_id, date.today(), weight,
                                          sleep if sleep > 0 else None)
                    st.success("Metrics saved.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        st.markdown("<hr style='border-color:#1a2540;margin:1rem 0;'>", unsafe_allow_html=True)
        ui_components.section_header("WEIGHT PROGRESS")
        progress = analytics.get_weight_progress(db, user_id)
        if progress["starting"] is not None:
            c1, c2, c3 = st.columns(3)
            c1.metric("Starting", f"{progress['starting']:.1f} kg")
            c2.metric("Current", f"{progress['current']:.1f} kg")
            c3.metric("Target", f"{progress['target']:.1f} kg" if progress["target"] else "—")
            if progress["change"] is not None:
                st.caption(f"Net change: {progress['change']:+.1f} kg")
        else:
            empty_state("No weight data yet", icon="", hint="Log your weight to track your journey.")

    with col_trend:
        ui_components.section_header("WEIGHT TREND")
        weight_df = analytics.get_weight_trend_df(db, user_id)
        fig = weight_trend_line(weight_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="health_weight_trend_chart")
        else:
            empty_state("No weight logs yet", icon="", hint="Log your weight over several days to build a trend.")


# =======================================================================
# ANALYTICS TAB
# =======================================================================

def _render_analytics(db, user_id: int):
    averages = analytics.get_calorie_averages(db, user_id)
    consistency = analytics.get_target_consistency(db, user_id, days=7)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        v1 = f"{averages['avg_7day']:.0f} kcal" if averages["avg_7day"] else "—"
        ui_components.metric_card("7-Day Avg Calories", v1, accent_color="#10b981")
    with c2:
        v2 = f"{averages['avg_30day']:.0f} kcal" if averages["avg_30day"] else "—"
        ui_components.metric_card("30-Day Avg Calories", v2, accent_color="#10b981")
    with c3:
        v3 = f"{consistency['calorie_consistency_pct']:.0f}%" if consistency["calorie_consistency_pct"] is not None else "—"
        ui_components.metric_card("Calorie Consistency", v3, subtitle="Past 7 days", accent_color="#10b981")
    with c4:
        v4 = f"{consistency['protein_consistency_pct']:.0f}%" if consistency["protein_consistency_pct"] is not None else "—"
        ui_components.metric_card("Protein Consistency", v4, subtitle="Past 7 days", accent_color="#10b981")

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        nutrition_df = analytics.get_weekly_nutrition_df(db, user_id)
        fig = weekly_calories_line(nutrition_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="health_weekly_calorie_chart")
        else:
            empty_state("Not enough nutrition logs", icon="")
    with col2:
        workout_df = analytics.get_workout_consistency_df(db, user_id)
        fig = workout_consistency_bar(workout_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="health_workouts_weekly_chart")
        else:
            empty_state("No workouts logged yet", icon="")

    st.markdown("<hr style='border-color:#1a2540;margin:1.25rem 0;'>", unsafe_allow_html=True)

    ui_components.section_header("ADAPTIVE MAINTENANCE ESTIMATE")
    st.caption(
        "Compares your formula-based TDEE to an estimate inferred from your actual logged "
        "calories and weight change. Requires consistent daily logs."
    )
    observed = analytics.estimate_observed_maintenance(db, user_id)
    if observed["available"]:
        targets = analytics.get_user_health_targets(db, user_id)
        col_f, col_o = st.columns(2)
        with col_f:
            ui_components.metric_card("Formula TDEE", f"{targets['tdee']:.0f} kcal", accent_color="#10b981")
        with col_o:
            ui_components.metric_card(
                "Observed TDEE",
                f"~{observed['observed_maintenance']:.0f} kcal",
                subtitle=f"Span: {observed['days_span']} days logged",
                accent_color="#10b981",
            )
        st.caption(
            f"Avg intake {observed['avg_daily_calories']:.0f} kcal/day · "
            f"Net weight change {observed['weight_change_kg']:+.2f} kg"
        )
    else:
        empty_state(
            "Observed estimate not available yet",
            icon="",
            hint=observed["message"],
        )
