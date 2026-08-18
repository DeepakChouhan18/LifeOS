"""
Hand-written raw SQL — deliberately kept separate from ORM CRUD code.

This is where CTEs, window functions, and multi-table JOINs live, so
they're easy to point to directly as evidence of real SQL ability, not
just ORM usage.

All functions take a SQLAlchemy Session and return plain lists of dicts,
so callers (analytics.py, tests) don't need to know these are raw SQL.

Dialect note
────────────
Queries that involve date arithmetic or date formatting use small helper
functions (_week / _month / _date_sub / …) that emit the correct SQL
fragment for either PostgreSQL or SQLite, so the same Python code runs
correctly in both production (PostgreSQL via Neon/Supabase/Railway) and
the local dev/test environment (SQLite in-memory via pytest).
"""

import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────────────────
# Dialect detection
# ─────────────────────────────────────────────────────────────────────────────

def _is_pg() -> bool:
    """Return True when the configured DATABASE_URL targets PostgreSQL."""
    try:
        from config import DATABASE_URL
        return DATABASE_URL.startswith("postgresql")
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Dialect-aware SQL fragment helpers
# ─────────────────────────────────────────────────────────────────────────────

def _week(col: str, pg: bool) -> str:
    """Format a date column as an ISO-week string ('YYYY-Www')."""
    if pg:
        # IYYY = ISO year, IW = ISO week number (01-53, zero-padded)
        return f"TO_CHAR({col}, 'IYYY-\"W\"IW')"
    return f"strftime('%Y-W%W', {col})"


def _month(col: str, pg: bool) -> str:
    """Format a date column as 'YYYY-MM'."""
    if pg:
        return f"TO_CHAR({col}, 'YYYY-MM')"
    return f"strftime('%Y-%m', {col})"


def _date_sub(col: str, days: int, pg: bool) -> str:
    """Subtract `days` calendar days from a date column, returning a date."""
    if pg:
        # PostgreSQL: date - integer = date
        return f"({col} - {days})"
    return f"DATE({col}, '-{days} days')"


def _date_sub_col(date_col: str, n_col: str, pg: bool) -> str:
    """Subtract an integer column's day-count from a date column."""
    if pg:
        return f"({date_col} - {n_col})"
    return f"DATE({date_col}, '-' || {n_col} || ' days')"


def _weekday(col: str, pg: bool) -> str:
    """Return 0 (Sunday) … 6 (Saturday) — same semantics as SQLite strftime('%w')."""
    if pg:
        return f"EXTRACT(DOW FROM {col})::integer"
    return f"CAST(strftime('%w', {col}) AS INTEGER)"


def _now_week(offset_days: int, pg: bool) -> str:
    """ISO week string for today, optionally shifted back by `offset_days`."""
    if pg:
        if offset_days:
            return f"TO_CHAR(CURRENT_DATE - {offset_days}, 'IYYY-\"W\"IW')"
        return "TO_CHAR(CURRENT_DATE, 'IYYY-\"W\"IW')"
    if offset_days:
        return f"strftime('%Y-W%W', 'now', '-{offset_days} days')"
    return "strftime('%Y-W%W', 'now')"


def _round_float(expr: str, places: int) -> str:
    """
    ROUND(float_expr, places) compatible with both SQLite and PostgreSQL.

    PostgreSQL's ROUND(x, n) requires x to be NUMERIC, not double precision.
    Wrapping in CAST(… AS NUMERIC) is harmless in SQLite and necessary in
    PostgreSQL for Float columns (protein_g, weight_kg, etc.).
    """
    return f"ROUND(CAST(({expr}) AS NUMERIC), {places})"


# =============================================================================
# STUDY MODULE QUERIES
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# STUDY STREAKS — classic "gaps and islands" pattern using a CTE +
# window function (ROW_NUMBER). The trick: for consecutive dates,
# (date − ROW_NUMBER) is constant, which groups consecutive days into
# the same "island".
# ─────────────────────────────────────────────────────────────────────────────

def _build_streaks_query(pg: bool) -> str:
    island = _date_sub_col("session_date", "rn", pg)
    return f"""
    WITH study_days AS (
        SELECT DISTINCT session_date
        FROM study_sessions
        WHERE user_id = :user_id
    ),
    numbered AS (
        SELECT
            session_date,
            ROW_NUMBER() OVER (ORDER BY session_date) AS rn
        FROM study_days
    ),
    grouped AS (
        SELECT
            session_date,
            rn,
            {island} AS island
        FROM numbered
    )
    SELECT
        island,
        MIN(session_date) AS streak_start,
        MAX(session_date) AS streak_end,
        COUNT(*) AS streak_length
    FROM grouped
    GROUP BY island
    ORDER BY streak_end DESC
    """


def get_all_streaks(session, user_id: int):
    """Returns every streak (island of consecutive study days), most recent first."""
    rows = session.execute(
        text(_build_streaks_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# SUBJECT-WISE BREAKDOWN — JOIN + GROUP BY across subjects and sessions
# ─────────────────────────────────────────────────────────────────────────────
# Pure JOIN/GROUP BY — no dialect-specific functions needed.

SUBJECT_BREAKDOWN_QUERY = text("""
    SELECT
        s.name AS subject_name,
        s.color AS subject_color,
        COUNT(ss.id) AS session_count,
        COALESCE(SUM(ss.duration_minutes), 0) AS total_minutes,
        COALESCE(AVG(ss.duration_minutes), 0) AS avg_minutes_per_session
    FROM subjects s
    LEFT JOIN study_sessions ss
        ON ss.subject_id = s.id AND ss.user_id = :user_id
    WHERE s.user_id = :user_id
    GROUP BY s.id, s.name, s.color
    ORDER BY total_minutes DESC
""")


def get_subject_breakdown(session, user_id: int):
    rows = session.execute(SUBJECT_BREAKDOWN_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# WEEKLY STUDY MINUTES — TRUE calendar-day rolling 7-day total.
#
# Uses a correlated self-join with a date range rather than
# "ROWS BETWEEN 6 PRECEDING" — a row-based window is only a 7-CALENDAR-DAY
# window when there are no gaps, which this app cannot guarantee.
# ─────────────────────────────────────────────────────────────────────────────

def _build_rolling_weekly_minutes_query(pg: bool) -> str:
    date_minus_6 = _date_sub("d.session_date", 6, pg)
    return f"""
    WITH daily AS (
        SELECT
            session_date,
            SUM(duration_minutes) AS minutes_that_day
        FROM study_sessions
        WHERE user_id = :user_id
        GROUP BY session_date
    )
    SELECT
        d.session_date,
        d.minutes_that_day,
        (
            SELECT COALESCE(SUM(d2.minutes_that_day), 0)
            FROM daily d2
            WHERE d2.session_date BETWEEN {date_minus_6} AND d.session_date
        ) AS rolling_7day_minutes
    FROM daily d
    ORDER BY d.session_date
    """


def get_rolling_weekly_minutes(session, user_id: int):
    rows = session.execute(
        text(_build_rolling_weekly_minutes_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# TODAY'S STUDY METRICS
# ─────────────────────────────────────────────────────────────────────────────

TODAY_STUDY_QUERY = text("""
    SELECT
        COALESCE(SUM(duration_minutes), 0) AS today_minutes,
        COUNT(id) AS session_count
    FROM study_sessions
    WHERE user_id = :user_id AND session_date = :today
""")


def get_today_study_summary(session, user_id: int, today_date):
    row = session.execute(
        TODAY_STUDY_QUERY, {"user_id": user_id, "today": today_date}
    ).mappings().first()
    return dict(row) if row else {"today_minutes": 0, "session_count": 0}


# ─────────────────────────────────────────────────────────────────────────────
# TASK COMPLETION PERCENTAGE
#
# TRUE / FALSE are recognised as 1 / 0 by SQLite ≥ 3.23.0 (2018) and
# as genuine booleans by PostgreSQL, so this query runs on both without
# dialect branching.
# ─────────────────────────────────────────────────────────────────────────────

COMPLETION_QUERY = text("""
    SELECT
        COUNT(*) AS total_tasks,
        SUM(CASE WHEN is_completed = TRUE  THEN 1 ELSE 0 END) AS completed_tasks,
        SUM(CASE WHEN is_completed = FALSE AND (due_date < :today OR due_date IS NULL)
                 THEN 1 ELSE 0 END) AS pending_tasks,
        SUM(CASE WHEN is_completed = FALSE AND due_date = :today
                 THEN 1 ELSE 0 END) AS due_today_tasks
    FROM study_tasks
    WHERE user_id = :user_id
""")


def get_completion_stats(session, user_id: int, today_date=None):
    from datetime import date
    today_date = today_date or date.today()
    row = session.execute(
        COMPLETION_QUERY, {"user_id": user_id, "today": today_date}
    ).mappings().first()
    result = dict(row) if row else {
        "total_tasks": 0, "completed_tasks": 0,
        "pending_tasks": 0, "due_today_tasks": 0,
    }
    total     = result["total_tasks"]     or 0
    completed = result["completed_tasks"] or 0
    result["completion_pct"] = round((completed / total) * 100, 1) if total > 0 else 0.0
    return result


# =============================================================================
# HEALTH & FITNESS MODULE QUERIES
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# WEEKLY NUTRITION AVERAGES — GROUP BY ISO week
# ─────────────────────────────────────────────────────────────────────────────

def _build_weekly_nutrition_query(pg: bool) -> str:
    week_expr = _week("log_date", pg)
    # protein_g / carbs_g / fats_g are Float columns; AVG(float) in PostgreSQL
    # returns double precision, and ROUND(double precision, n) is not defined —
    # must cast to NUMERIC first.  _round_float handles this for both dialects.
    return f"""
    SELECT
        {week_expr} AS week,
        ROUND(AVG(daily_cal), 0) AS avg_calories,
        {_round_float("AVG(daily_prot)", 1)} AS avg_protein_g,
        {_round_float("AVG(daily_carbs)", 1)} AS avg_carbs_g,
        {_round_float("AVG(daily_fats)", 1)} AS avg_fats_g,
        COUNT(*) AS days_logged
    FROM (
        SELECT log_date,
               SUM(calories)  AS daily_cal,
               SUM(protein_g) AS daily_prot,
               SUM(carbs_g)   AS daily_carbs,
               SUM(fats_g)    AS daily_fats
        FROM nutrition_logs
        WHERE user_id = :user_id
        GROUP BY log_date
    ) daily
    GROUP BY week
    ORDER BY week
    """


def get_weekly_nutrition_averages(session, user_id: int):
    rows = session.execute(
        text(_build_weekly_nutrition_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# WEIGHT TREND — TRUE calendar-day rolling 7-day average.
# Same gap-safe approach as the study rolling-window query above.
# ─────────────────────────────────────────────────────────────────────────────

def _build_weight_trend_query(pg: bool) -> str:
    date_minus_6 = _date_sub("w.log_date", 6, pg)
    avg_sub = (
        f"(SELECT AVG(w2.weight_kg) FROM weights w2 "
        f"WHERE w2.log_date BETWEEN {date_minus_6} AND w.log_date)"
    )
    return f"""
    WITH weights AS (
        SELECT log_date, weight_kg
        FROM body_metrics
        WHERE user_id = :user_id AND weight_kg IS NOT NULL
        ORDER BY log_date
    )
    SELECT
        w.log_date,
        w.weight_kg,
        {_round_float(avg_sub, 2)} AS rolling_avg_weight
    FROM weights w
    ORDER BY w.log_date
    """


def get_weight_trend(session, user_id: int):
    rows = session.execute(
        text(_build_weight_trend_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# WORKOUT CONSISTENCY — workouts per ISO week
# ─────────────────────────────────────────────────────────────────────────────

def _build_workout_consistency_query(pg: bool) -> str:
    week_expr = _week("workout_date", pg)
    return f"""
    SELECT
        {week_expr} AS week,
        COUNT(*) AS workout_count,
        COALESCE(SUM(duration_minutes), 0) AS total_minutes
    FROM workouts
    WHERE user_id = :user_id
    GROUP BY week
    ORDER BY week
    """


def get_workout_consistency(session, user_id: int):
    rows = session.execute(
        text(_build_workout_consistency_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# TODAY'S NUTRITION TOTALS
# ─────────────────────────────────────────────────────────────────────────────

DAILY_NUTRITION_QUERY = text("""
    SELECT
        log_date,
        COALESCE(SUM(calories), 0) AS total_calories,
        COALESCE(SUM(protein_g), 0) AS total_protein_g,
        COALESCE(SUM(carbs_g), 0) AS total_carbs_g,
        COALESCE(SUM(fats_g), 0) AS total_fats_g,
        COUNT(id) AS meal_count
    FROM nutrition_logs
    WHERE user_id = :user_id AND log_date = :log_date
    GROUP BY log_date
""")


def get_daily_nutrition_totals(session, user_id: int, log_date):
    row = session.execute(
        DAILY_NUTRITION_QUERY, {"user_id": user_id, "log_date": log_date}
    ).mappings().first()
    return dict(row) if row else {
        "log_date": log_date, "total_calories": 0, "total_protein_g": 0,
        "total_carbs_g": 0, "total_fats_g": 0, "meal_count": 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TODAY'S WATER TOTAL
# ─────────────────────────────────────────────────────────────────────────────

DAILY_WATER_QUERY = text("""
    SELECT COALESCE(SUM(amount_ml), 0) AS total_water_ml
    FROM water_logs
    WHERE user_id = :user_id AND log_date = :log_date
""")


def get_daily_water_total(session, user_id: int, log_date):
    row = session.execute(
        DAILY_WATER_QUERY, {"user_id": user_id, "log_date": log_date}
    ).mappings().first()
    return row["total_water_ml"] if row else 0


# ─────────────────────────────────────────────────────────────────────────────
# RECENT FOODS — distinct meal names ordered by most recently logged.
# Uses GROUP BY + MAX() to find each food's most recent occurrence and
# its typical macros (AVG), so re-selecting "Rice" pre-fills sensible
# defaults.
# ─────────────────────────────────────────────────────────────────────────────
# CAST(… AS NUMERIC) before ROUND is safe in SQLite and required in
# PostgreSQL for Float-typed macro columns.

RECENT_FOODS_QUERY = text("""
    SELECT
        meal_name,
        MAX(log_date) AS last_logged,
        ROUND(AVG(calories), 0) AS typical_calories,
        ROUND(CAST(AVG(protein_g) AS NUMERIC), 1) AS typical_protein_g,
        ROUND(CAST(AVG(carbs_g)   AS NUMERIC), 1) AS typical_carbs_g,
        ROUND(CAST(AVG(fats_g)    AS NUMERIC), 1) AS typical_fats_g,
        COUNT(*) AS times_logged
    FROM nutrition_logs
    WHERE user_id = :user_id
    GROUP BY meal_name
    HAVING COUNT(*) >= 1
    ORDER BY last_logged DESC
    LIMIT :limit
""")


def get_recent_foods(session, user_id: int, limit: int = 8):
    rows = session.execute(
        RECENT_FOODS_QUERY, {"user_id": user_id, "limit": limit}
    ).mappings().all()
    return [dict(r) for r in rows]


# =============================================================================
# FINANCE MODULE QUERIES
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# MONTHLY SPEND — GROUP BY month
# ─────────────────────────────────────────────────────────────────────────────

def _build_monthly_spend_query(pg: bool) -> str:
    month_expr = _month("expense_date", pg)
    return f"""
    SELECT
        {month_expr} AS month,
        ROUND(SUM(amount), 2) AS total_spent,
        COUNT(*) AS transaction_count
    FROM expenses
    WHERE user_id = :user_id
    GROUP BY month
    ORDER BY month
    """


def get_monthly_spend(session, user_id: int):
    rows = session.execute(
        text(_build_monthly_spend_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# TODAY'S SPEND
# ─────────────────────────────────────────────────────────────────────────────

TODAY_SPEND_QUERY = text("""
    SELECT
        COALESCE(SUM(amount), 0) AS today_spent,
        COUNT(*) AS today_transactions
    FROM expenses
    WHERE user_id = :user_id AND expense_date = :today
""")


def get_today_spend(session, user_id: int, today_date):
    row = session.execute(
        TODAY_SPEND_QUERY, {"user_id": user_id, "today": today_date}
    ).mappings().first()
    return dict(row) if row else {"today_spent": 0.0, "today_transactions": 0}


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY BREAKDOWN — JOIN + GROUP BY, for a given month
# ─────────────────────────────────────────────────────────────────────────────

def _build_category_breakdown_query(pg: bool) -> str:
    month_expr = _month("e.expense_date", pg)
    return f"""
    SELECT
        c.name AS category_name,
        COALESCE(SUM(e.amount), 0) AS total_spent,
        COUNT(e.id) AS transaction_count
    FROM expense_categories c
    LEFT JOIN expenses e
        ON e.category_id = c.id
        AND e.user_id = :user_id
        AND {month_expr} = :month
    WHERE c.user_id = :user_id
    GROUP BY c.id, c.name
    ORDER BY total_spent DESC
    """


def get_category_breakdown(session, user_id: int, month: str):
    rows = session.execute(
        text(_build_category_breakdown_query(_is_pg())),
        {"user_id": user_id, "month": month},
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# BUDGET REMAINING — CTE joining budgeted amount vs actual spend
# ─────────────────────────────────────────────────────────────────────────────

def _build_budget_remaining_query(pg: bool) -> str:
    expense_month = _month("expense_date", pg)
    # Budget.month is a Date column — format it the same way as expense_date
    budget_month = _month("b.month", pg)
    return f"""
    WITH spend AS (
        SELECT
            category_id,
            SUM(amount) AS spent
        FROM expenses
        WHERE user_id = :user_id
          AND {expense_month} = :month
        GROUP BY category_id
    )
    SELECT
        c.name AS category_name,
        b.limit_amount AS budget_limit,
        COALESCE(s.spent, 0) AS spent,
        ROUND(b.limit_amount - COALESCE(s.spent, 0), 2) AS remaining
    FROM budgets b
    JOIN expense_categories c ON c.id = b.category_id
    LEFT JOIN spend s ON s.category_id = b.category_id
    WHERE b.user_id = :user_id
      AND {budget_month} = :month
    ORDER BY remaining ASC
    """


def get_budget_remaining(session, user_id: int, month: str):
    rows = session.execute(
        text(_build_budget_remaining_query(_is_pg())),
        {"user_id": user_id, "month": month},
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# ROLLING 7-DAY SPEND — TRUE calendar-day window (gap-safe; see note on
# rolling study query above).
# ─────────────────────────────────────────────────────────────────────────────

def _build_rolling_spend_query(pg: bool) -> str:
    date_minus_6 = _date_sub("d.expense_date", 6, pg)
    rolling_sum = (
        f"(SELECT COALESCE(SUM(d2.spent_that_day), 0) "
        f"FROM daily d2 "
        f"WHERE d2.expense_date BETWEEN {date_minus_6} AND d.expense_date)"
    )
    return f"""
    WITH daily AS (
        SELECT
            expense_date,
            SUM(amount) AS spent_that_day
        FROM expenses
        WHERE user_id = :user_id
        GROUP BY expense_date
    )
    SELECT
        d.expense_date,
        d.spent_that_day,
        ROUND(CAST({rolling_sum} AS NUMERIC), 2) AS rolling_7day_spend
    FROM daily d
    ORDER BY d.expense_date
    """


def get_rolling_spend(session, user_id: int):
    rows = session.execute(
        text(_build_rolling_spend_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# =============================================================================
# CROSS-DOMAIN ANALYTICS & SMART INSIGHTS QUERIES
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# STUDY VS WORKOUT CONSISTENCY BY WEEK — CTE + LEFT JOIN
# ─────────────────────────────────────────────────────────────────────────────

def _build_cross_study_workout_query(pg: bool) -> str:
    study_week   = _week("session_date", pg)
    workout_week = _week("workout_date", pg)
    return f"""
    WITH weekly_study AS (
        SELECT
            {study_week} AS week,
            SUM(duration_minutes) / 60.0 AS study_hours
        FROM study_sessions
        WHERE user_id = :user_id
        GROUP BY week
    ),
    weekly_workout AS (
        SELECT
            {workout_week} AS week,
            COUNT(*) AS workout_count,
            SUM(duration_minutes) AS workout_minutes
        FROM workouts
        WHERE user_id = :user_id
        GROUP BY week
    )
    SELECT
        COALESCE(s.week, w.week) AS week,
        COALESCE(s.study_hours, 0) AS study_hours,
        COALESCE(w.workout_count, 0) AS workout_count,
        COALESCE(w.workout_minutes, 0) AS workout_minutes
    FROM weekly_study s
    LEFT JOIN weekly_workout w ON s.week = w.week
    ORDER BY week
    """


def get_cross_study_workout(session, user_id: int):
    rows = session.execute(
        text(_build_cross_study_workout_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# WEEKLY COMPARISON (THIS WEEK VS LAST WEEK) FOR INSIGHTS GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _build_weekly_comparison_query(pg: bool) -> str:
    study_week     = _week("session_date", pg)
    expense_week   = _week("expense_date", pg)
    nutrition_week = _week("log_date", pg)
    this_week      = _now_week(0, pg)
    last_week      = _now_week(7, pg)
    return f"""
    WITH study_weeks AS (
        SELECT
            {study_week} AS week,
            SUM(duration_minutes) AS total_minutes
        FROM study_sessions
        WHERE user_id = :user_id
        GROUP BY week
    ),
    spend_weeks AS (
        SELECT
            {expense_week} AS week,
            SUM(amount) AS total_spend
        FROM expenses
        WHERE user_id = :user_id
        GROUP BY week
    ),
    nutrition_weeks AS (
        SELECT
            {nutrition_week} AS week,
            AVG(daily_cal)  AS avg_cal,
            AVG(daily_prot) AS avg_prot
        FROM (
            SELECT log_date,
                   SUM(calories)  AS daily_cal,
                   SUM(protein_g) AS daily_prot
            FROM nutrition_logs
            WHERE user_id = :user_id
            GROUP BY log_date
        ) daily
        GROUP BY week
    )
    SELECT
        w.week,
        COALESCE(s.total_minutes, 0) AS study_minutes,
        COALESCE(e.total_spend, 0)   AS total_spend,
        COALESCE(n.avg_cal, 0)       AS avg_calories,
        COALESCE(n.avg_prot, 0)      AS avg_protein
    FROM (
        SELECT {last_week} AS week
        UNION
        SELECT {this_week} AS week
    ) w
    LEFT JOIN study_weeks    s ON s.week = w.week
    LEFT JOIN spend_weeks    e ON e.week = w.week
    LEFT JOIN nutrition_weeks n ON n.week = w.week
    ORDER BY w.week ASC
    """


def get_weekly_comparison(session, user_id: int):
    rows = session.execute(
        text(_build_weekly_comparison_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES OVER BUDGET — JOIN + GROUP BY + HAVING.
# HAVING is used (rather than WHERE) because the filter condition
# (spent > limit) depends on an aggregate (SUM), not available until
# after grouping.
# ─────────────────────────────────────────────────────────────────────────────

def _build_over_budget_categories_query(pg: bool) -> str:
    expense_month = _month("e.expense_date", pg)
    budget_month  = _month("b.month", pg)
    return f"""
    SELECT
        c.name AS category_name,
        b.limit_amount AS budget_limit,
        SUM(e.amount) AS spent,
        ROUND(SUM(e.amount) - b.limit_amount, 2) AS overspend
    FROM expenses e
    JOIN expense_categories c ON c.id = e.category_id
    JOIN budgets b ON b.category_id = e.category_id AND b.user_id = e.user_id
    WHERE e.user_id = :user_id
      AND {expense_month} = :month
      AND {budget_month}  = :month
    GROUP BY c.id, c.name, b.limit_amount
    HAVING SUM(e.amount) > b.limit_amount
    ORDER BY overspend DESC
    """


def get_over_budget_categories(session, user_id: int, month: str):
    rows = session.execute(
        text(_build_over_budget_categories_query(_is_pg())),
        {"user_id": user_id, "month": month},
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# SPENDING BY WEEKDAY — for "your highest spending day was Saturday" style
# insights.  0 = Sunday … 6 = Saturday (same semantics in both dialects).
# ─────────────────────────────────────────────────────────────────────────────

def _build_spending_by_weekday_query(pg: bool) -> str:
    dow = _weekday("expense_date", pg)
    return f"""
    SELECT
        {dow} AS weekday_num,
        CASE {dow}
            WHEN 0 THEN 'Sunday'    WHEN 1 THEN 'Monday'
            WHEN 2 THEN 'Tuesday'   WHEN 3 THEN 'Wednesday'
            WHEN 4 THEN 'Thursday'  WHEN 5 THEN 'Friday'
            ELSE 'Saturday'
        END AS weekday_name,
        SUM(amount)  AS total_spent,
        COUNT(*)     AS transaction_count
    FROM expenses
    WHERE user_id = :user_id
    GROUP BY {dow}
    ORDER BY total_spent DESC
    """


def get_spending_by_weekday(session, user_id: int):
    rows = session.execute(
        text(_build_spending_by_weekday_query(_is_pg())), {"user_id": user_id}
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# MONTH-OVER-MONTH CATEGORY CHANGE — self-join comparing this month's
# spend against last month's.
# ─────────────────────────────────────────────────────────────────────────────

def _build_month_over_month_category_query(pg: bool) -> str:
    month_expr = _month("expense_date", pg)
    return f"""
    WITH this_month AS (
        SELECT category_id, SUM(amount) AS spent
        FROM expenses
        WHERE user_id = :user_id AND {month_expr} = :this_month
        GROUP BY category_id
    ),
    last_month AS (
        SELECT category_id, SUM(amount) AS spent
        FROM expenses
        WHERE user_id = :user_id AND {month_expr} = :last_month
        GROUP BY category_id
    )
    SELECT
        c.name AS category_name,
        COALESCE(t.spent, 0) AS this_month_spent,
        COALESCE(l.spent, 0) AS last_month_spent
    FROM expense_categories c
    LEFT JOIN this_month t ON t.category_id = c.id
    LEFT JOIN last_month  l ON l.category_id = c.id
    WHERE c.user_id = :user_id
      AND (t.spent IS NOT NULL OR l.spent IS NOT NULL)
    ORDER BY this_month_spent DESC
    """


def get_month_over_month_category(session, user_id: int, this_month: str, last_month: str):
    rows = session.execute(
        text(_build_month_over_month_category_query(_is_pg())),
        {"user_id": user_id, "this_month": this_month, "last_month": last_month},
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# LARGEST EXPENSES — simple ORDER BY + LIMIT (no dialect-specific SQL)
# ─────────────────────────────────────────────────────────────────────────────

LARGEST_EXPENSES_QUERY = text("""
    SELECT e.expense_date, e.amount, c.name AS category_name, e.description
    FROM expenses e
    LEFT JOIN expense_categories c ON c.id = e.category_id
    WHERE e.user_id = :user_id
    ORDER BY e.amount DESC
    LIMIT :limit
""")


def get_largest_expenses(session, user_id: int, limit: int = 5):
    rows = session.execute(
        LARGEST_EXPENSES_QUERY, {"user_id": user_id, "limit": limit}
    ).mappings().all()
    return [dict(r) for r in rows]
