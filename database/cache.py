"""
Query-level caching for LifeOS — all @st.cache_data functions live here.

Design principles
─────────────────
1. Cached functions NEVER touch module-level analytics/crud imports at the top
   of this file; all imports are deferred inside each function body. This
   prevents circular-import issues at startup and keeps the module lightweight.

2. Each function owns its DB session: open → query → close → return plain data.
   No SQLAlchemy ORM objects are allowed in return values; they don't pickle
   cleanly across Streamlit reruns.

3. ``user_id: int`` is the first argument of every cached function so Streamlit
   scopes the cache correctly per user (two users never share a cached entry).

4. Tests are UNAFFECTED: they call analytics/crud functions directly with their
   own in-memory SQLite sessions.  These cache wrappers are only called from
   the page files.

TTL guidelines
──────────────
  30 s  — today-level data: dashboard summary, today's meals/spend, task lists
  60 s  — trend/chart data: weekly trends, calorie averages, insights
 120 s  — slow-changing data: user profile name, subjects, categories

Cache invalidation
──────────────────
After any write operation in a page file, call the targeted ``clear_after_*``
helper (or individual ``.clear()`` calls) BEFORE ``st.rerun()``.  Each
``my_func.clear()`` wipes only that one function's cache, not every user's
entire cache.  Do NOT call ``st.cache_data.clear()`` — that nukes everything.
"""

import streamlit as st
from database.connection import get_session


# =============================================================================
# DASHBOARD
# =============================================================================

@st.cache_data(ttl=30)
def get_dashboard_combined_summary(user_id: int) -> dict:
    """Full dashboard payload: study + health + finance summaries, scores, insights."""
    from modules.dashboard import aggregator
    db = get_session()
    try:
        return aggregator.get_combined_summary(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=120)
def get_user_display_name(user_id: int):
    """User's display name from their profile (None if profile not set up yet)."""
    from modules.settings import crud as settings_crud
    db = get_session()
    try:
        profile = settings_crud.get_user_profile(db, user_id)
        return profile.name if profile else None
    finally:
        db.close()


# =============================================================================
# STUDY MODULE
# =============================================================================

@st.cache_data(ttl=30)
def get_study_full_summary(user_id: int) -> dict:
    """Streaks, completion %, today's hours, total hours — everything the Study
    Analytics tab needs in a single dict."""
    from modules.study import analytics
    db = get_session()
    try:
        return analytics.get_full_summary(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_study_today_summary(user_id: int) -> dict:
    """Today's study minutes, session count, goal progress, tasks due today."""
    from modules.study import analytics
    db = get_session()
    try:
        return analytics.get_today_summary(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_study_streak_summary(user_id: int) -> dict:
    """``{"current_streak": int, "longest_streak": int}``."""
    from modules.study import analytics
    db = get_session()
    try:
        return analytics.get_streak_summary(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_study_subject_breakdown(user_id: int):
    """pandas DataFrame of per-subject session counts and total minutes."""
    from modules.study import analytics
    db = get_session()
    try:
        return analytics.get_subject_breakdown_df(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_study_weekly_trend(user_id: int):
    """pandas DataFrame with rolling 7-day study minutes per day."""
    from modules.study import analytics
    db = get_session()
    try:
        return analytics.get_weekly_trend_df(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_study_tasks(user_id: int, include_completed: bool = True) -> list:
    """Study tasks as plain dicts (no ORM objects)."""
    from modules.study import crud
    db = get_session()
    try:
        tasks = crud.list_tasks(db, user_id, include_completed=include_completed)
        return [
            {
                "id": t.id,
                "title": t.title,
                "subject_id": t.subject_id,
                "subject_name": t.subject.name if t.subject else None,
                "priority": t.priority,
                "topic": t.topic,
                "due_date": t.due_date,
                "is_completed": t.is_completed,
                "completed_at": t.completed_at,
            }
            for t in tasks
        ]
    finally:
        db.close()


@st.cache_data(ttl=120)
def get_study_subjects(user_id: int) -> list:
    """Subjects as plain dicts: ``[{"id": int, "name": str, "color": str}]``."""
    from modules.study import crud
    db = get_session()
    try:
        subjects = crud.list_subjects(db, user_id)
        return [{"id": s.id, "name": s.name, "color": s.color} for s in subjects]
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_study_sessions(user_id: int, limit: int = 50) -> list:
    """Recent study sessions as plain dicts."""
    from modules.study import crud
    db = get_session()
    try:
        sessions = crud.list_sessions(db, user_id, limit=limit)
        return [
            {
                "id": s.id,
                "subject_name": s.subject.name if s.subject else "General",
                "session_date": s.session_date,
                "duration_minutes": s.duration_minutes,
                "topic": s.topic,
                "notes": s.notes,
            }
            for s in sessions
        ]
    finally:
        db.close()


# =============================================================================
# HEALTH MODULE
# =============================================================================

@st.cache_data(ttl=30)
def get_health_full_summary(user_id: int) -> dict:
    """Everything the health overview / dashboard needs (calories, weight, workouts…)."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.get_full_summary(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_health_today_summary(user_id: int) -> dict:
    """Today's nutrition/water totals vs calculated targets."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.get_today_summary(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_health_weight_trend(user_id: int):
    """pandas DataFrame of weight readings with rolling 7-day average."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.get_weight_trend_df(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_health_weight_progress(user_id: int) -> dict:
    """Starting / current / target weight and % progress toward goal."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.get_weight_progress(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_health_workout_consistency(user_id: int):
    """pandas DataFrame of per-week workout counts and total minutes."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.get_workout_consistency_df(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_health_weekly_nutrition(user_id: int):
    """pandas DataFrame of weekly average calories and macros."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.get_weekly_nutrition_df(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_health_calorie_averages(user_id: int) -> dict:
    """``{"avg_7day": float|None, "avg_30day": float|None}``."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.get_calorie_averages(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_health_target_consistency(user_id: int, days: int = 7) -> dict:
    """Fraction of recent days within 10 % of calorie/protein targets."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.get_target_consistency(db, user_id, days=days)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_health_nutrition_logs_today(user_id: int) -> list:
    """Today's nutrition log entries as plain dicts."""
    from modules.health import crud
    from datetime import date
    db = get_session()
    try:
        logs = crud.list_nutrition_logs(db, user_id, log_date=date.today())
        return [
            {
                "id": lg.id,
                "meal_name": lg.meal_name,
                "meal_type": lg.meal_type,
                "calories": lg.calories,
                "protein_g": lg.protein_g,
                "carbs_g": lg.carbs_g,
                "fats_g": lg.fats_g,
                "log_date": lg.log_date,
            }
            for lg in logs
        ]
    finally:
        db.close()


@st.cache_data(ttl=120)
def get_health_recent_foods(user_id: int, limit: int = 8) -> list:
    """Recent unique food names with typical macros (for quick-fill UI)."""
    from modules.health import crud
    db = get_session()
    try:
        return crud.get_recent_foods(db, user_id, limit=limit)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_health_workouts(user_id: int, limit: int = 15) -> list:
    """Recent workout entries as plain dicts."""
    from modules.health import crud
    db = get_session()
    try:
        workouts = crud.list_workouts(db, user_id, limit=limit)
        return [
            {
                "id": w.id,
                "workout_date": w.workout_date,
                "type": w.type,
                "exercise": w.exercise,
                "duration_minutes": w.duration_minutes,
                "notes": w.notes,
            }
            for w in workouts
        ]
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_health_observed_maintenance(user_id: int) -> dict:
    """Adaptive maintenance estimate from logged history (requires 21+ days)."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.estimate_observed_maintenance(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_health_user_targets(user_id: int) -> dict:
    """Calculated BMR / TDEE / calorie & protein targets from user profile."""
    from modules.health import analytics
    db = get_session()
    try:
        return analytics.get_user_health_targets(db, user_id)
    finally:
        db.close()


# =============================================================================
# FINANCE MODULE
# =============================================================================

@st.cache_data(ttl=30)
def get_finance_full_summary(user_id: int) -> dict:
    """Today + month totals, budget remaining, daily budget — dashboard card data."""
    from modules.finance import analytics
    db = get_session()
    try:
        return analytics.get_full_summary(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_finance_current_month_summary(user_id: int) -> dict:
    """Full current-month finance summary including daily budget remaining."""
    from modules.finance import analytics
    db = get_session()
    try:
        return analytics.get_current_month_summary(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_finance_category_breakdown(user_id: int):
    """pandas DataFrame of per-category spend this month."""
    from modules.finance import analytics
    db = get_session()
    try:
        return analytics.get_category_breakdown_df(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_finance_budget_remaining(user_id: int):
    """pandas DataFrame of budget limit vs actual spend per category."""
    from modules.finance import analytics
    db = get_session()
    try:
        return analytics.get_budget_remaining_df(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_finance_spend_trend(user_id: int):
    """pandas DataFrame of rolling 7-day spend per day."""
    from modules.finance import analytics
    db = get_session()
    try:
        return analytics.get_spend_trend_df(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_finance_largest_expenses(user_id: int, limit: int = 5) -> list:
    """Top N expenses by amount (plain dicts)."""
    from modules.finance import analytics
    db = get_session()
    try:
        return analytics.get_largest_expenses(db, user_id, limit=limit)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_finance_over_budget(user_id: int) -> list:
    """Categories where spend has exceeded budget this month (plain dicts)."""
    from modules.finance import analytics
    db = get_session()
    try:
        return analytics.get_over_budget_categories(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_finance_insights(user_id: int) -> list:
    """Plain-language finance insights from real data (list of strings)."""
    from modules.finance import analytics
    db = get_session()
    try:
        return analytics.get_finance_insights(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_finance_expenses(user_id: int, limit: int = 50) -> list:
    """Expense history as plain dicts (no ORM objects)."""
    from modules.finance import crud
    db = get_session()
    try:
        expenses = crud.list_expenses(db, user_id, limit=limit)
        return [
            {
                "id": e.id,
                "amount": float(e.amount),
                "category_name": e.category.name if e.category else "General",
                "expense_date": e.expense_date,
                "description": e.description,
                "payment_method": e.payment_method,
            }
            for e in expenses
        ]
    finally:
        db.close()


@st.cache_data(ttl=120)
def get_finance_categories(user_id: int) -> list:
    """Expense categories as plain dicts: ``[{"id": int, "name": str}]``."""
    from modules.finance import crud
    db = get_session()
    try:
        cats = crud.list_categories(db, user_id)
        return [{"id": c.id, "name": c.name} for c in cats]
    finally:
        db.close()


# =============================================================================
# INSIGHTS MODULE
# =============================================================================

@st.cache_data(ttl=60)
def get_insights_cross_study_workout(user_id: int) -> list:
    """Cross-domain study-vs-workout consistency by ISO week (plain dicts)."""
    from database import raw_queries as rq
    db = get_session()
    try:
        return rq.get_cross_study_workout(db, user_id)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_insights_spending_by_weekday(user_id: int) -> list:
    """Aggregated spend by day-of-week (plain dicts)."""
    from database import raw_queries as rq
    db = get_session()
    try:
        return rq.get_spending_by_weekday(db, user_id)
    finally:
        db.close()


# =============================================================================
# TARGETED CACHE INVALIDATION HELPERS
# =============================================================================
# Call these BEFORE st.rerun() after the corresponding write operation.
# Each helper clears ONLY the functions whose data just became stale.
# Do NOT call st.cache_data.clear() — that wipes the cache for ALL users
# and ALL functions in one shot.

def clear_after_study_session_write():
    """Call after crud.log_session / crud.delete_session."""
    get_study_full_summary.clear()
    get_study_today_summary.clear()
    get_study_streak_summary.clear()
    get_study_weekly_trend.clear()
    get_study_sessions.clear()
    get_dashboard_combined_summary.clear()


def clear_after_study_task_write():
    """Call after crud.add_task / crud.complete_task / crud.uncomplete_task / crud.delete_task."""
    get_study_tasks.clear()
    get_study_full_summary.clear()
    get_dashboard_combined_summary.clear()


def clear_after_study_subject_write():
    """Call after crud.add_subject / crud.delete_subject."""
    get_study_subjects.clear()
    get_study_subject_breakdown.clear()


def clear_after_nutrition_write():
    """Call after any nutrition log write (add / delete / duplicate)."""
    get_health_full_summary.clear()
    get_health_today_summary.clear()
    get_health_nutrition_logs_today.clear()
    get_health_recent_foods.clear()
    get_health_calorie_averages.clear()
    get_health_target_consistency.clear()
    get_health_weekly_nutrition.clear()
    get_dashboard_combined_summary.clear()


def clear_after_water_write():
    """Call after crud.log_water / crud.delete_water_log."""
    get_health_today_summary.clear()
    get_health_full_summary.clear()
    get_dashboard_combined_summary.clear()


def clear_after_workout_write():
    """Call after crud.log_workout / crud.delete_workout."""
    get_health_full_summary.clear()
    get_health_workout_consistency.clear()
    get_health_workouts.clear()
    get_dashboard_combined_summary.clear()
    get_insights_cross_study_workout.clear()


def clear_after_body_metric_write():
    """Call after crud.log_body_metric / crud.delete_body_metric."""
    get_health_full_summary.clear()
    get_health_weight_trend.clear()
    get_health_weight_progress.clear()
    get_dashboard_combined_summary.clear()


def clear_after_expense_write():
    """Call after crud.add_expense / crud.update_expense / crud.delete_expense."""
    get_finance_full_summary.clear()
    get_finance_current_month_summary.clear()
    get_finance_category_breakdown.clear()
    get_finance_spend_trend.clear()
    get_finance_budget_remaining.clear()
    get_finance_over_budget.clear()
    get_finance_insights.clear()
    get_finance_expenses.clear()
    get_dashboard_combined_summary.clear()
    get_insights_spending_by_weekday.clear()


def clear_after_budget_write():
    """Call after crud.set_budget / crud.delete_budget."""
    get_finance_budget_remaining.clear()
    get_finance_over_budget.clear()
    get_finance_full_summary.clear()
    get_finance_current_month_summary.clear()
    get_finance_insights.clear()
    get_dashboard_combined_summary.clear()


def clear_after_profile_save():
    """Call after settings_crud.save_user_profile."""
    get_user_display_name.clear()
    get_health_full_summary.clear()
    get_health_today_summary.clear()
    get_health_user_targets.clear()
    get_health_observed_maintenance.clear()
    get_health_weight_progress.clear()
    get_dashboard_combined_summary.clear()


def clear_after_score_weights_save():
    """Call after settings_crud.update_score_weights."""
    get_user_display_name.clear()
    get_dashboard_combined_summary.clear()


def clear_all_module_caches():
    """
    Wipes every cached function in this module.
    Use ONLY after full data reset operations (delete_all_user_data,
    reset_logged_data_keep_profile) — never after routine writes.
    """
    get_dashboard_combined_summary.clear()
    get_user_display_name.clear()
    get_study_full_summary.clear()
    get_study_today_summary.clear()
    get_study_streak_summary.clear()
    get_study_subject_breakdown.clear()
    get_study_weekly_trend.clear()
    get_study_tasks.clear()
    get_study_subjects.clear()
    get_study_sessions.clear()
    get_health_full_summary.clear()
    get_health_today_summary.clear()
    get_health_weight_trend.clear()
    get_health_weight_progress.clear()
    get_health_workout_consistency.clear()
    get_health_weekly_nutrition.clear()
    get_health_calorie_averages.clear()
    get_health_target_consistency.clear()
    get_health_nutrition_logs_today.clear()
    get_health_recent_foods.clear()
    get_health_workouts.clear()
    get_health_observed_maintenance.clear()
    get_health_user_targets.clear()
    get_finance_full_summary.clear()
    get_finance_current_month_summary.clear()
    get_finance_category_breakdown.clear()
    get_finance_budget_remaining.clear()
    get_finance_spend_trend.clear()
    get_finance_largest_expenses.clear()
    get_finance_over_budget.clear()
    get_finance_insights.clear()
    get_finance_expenses.clear()
    get_finance_categories.clear()
    get_insights_cross_study_workout.clear()
    get_insights_spending_by_weekday.clear()
