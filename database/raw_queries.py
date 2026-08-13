"""
Hand-written raw SQL — deliberately kept separate from ORM CRUD code.

This is where CTEs, window functions, and multi-table JOINs live, so
they're easy to point to directly as evidence of real SQL ability, not
just ORM usage.

All functions take a SQLAlchemy Session and return plain lists of dicts,
so callers (analytics.py, tests) don't need to know these are raw SQL.
"""

from sqlalchemy import text


# ---------------------------------------------------------------------
# STUDY STREAKS — classic "gaps and islands" pattern using a CTE +
# window function (ROW_NUMBER). The trick: for consecutive dates,
# (date - ROW_NUMBER) is constant, which groups consecutive days into
# the same "island".
# ---------------------------------------------------------------------
STREAKS_QUERY = text("""
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
            DATE(session_date, '-' || rn || ' days') AS island
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
""")


def get_all_streaks(session, user_id: int):
    """Returns every streak (island of consecutive study days), most recent first."""
    rows = session.execute(STREAKS_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# SUBJECT-WISE BREAKDOWN — JOIN + GROUP BY across subjects and sessions
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# WEEKLY STUDY MINUTES — TRUE calendar-day rolling 7-day total.
#
# IMPORTANT: this uses a correlated self-join with a date range
# (BETWEEN d.session_date - 6 days AND d.session_date), NOT
# "ROWS BETWEEN 6 PRECEDING" — the latter is a 7-ROW window, which is
# only a 7-CALENDAR-DAY window if there are no gaps in the data. Since
# this app allows skipped days, a row-based window silently produces
# wrong "weekly" totals whenever a day was missed. This version is
# correct regardless of gaps.
# ---------------------------------------------------------------------
ROLLING_WEEKLY_MINUTES_QUERY = text("""
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
            WHERE d2.session_date BETWEEN DATE(d.session_date, '-6 days') AND d.session_date
        ) AS rolling_7day_minutes
    FROM daily d
    ORDER BY d.session_date
""")


def get_rolling_weekly_minutes(session, user_id: int):
    rows = session.execute(ROLLING_WEEKLY_MINUTES_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# TODAY'S STUDY METRICS
# ---------------------------------------------------------------------
TODAY_STUDY_QUERY = text("""
    SELECT
        COALESCE(SUM(duration_minutes), 0) AS today_minutes,
        COUNT(id) AS session_count
    FROM study_sessions
    WHERE user_id = :user_id AND session_date = :today
""")


def get_today_study_summary(session, user_id: int, today_date):
    row = session.execute(TODAY_STUDY_QUERY, {"user_id": user_id, "today": today_date}).mappings().first()
    return dict(row) if row else {"today_minutes": 0, "session_count": 0}


# ---------------------------------------------------------------------
# TASK COMPLETION PERCENTAGE
# ---------------------------------------------------------------------
COMPLETION_QUERY = text("""
    SELECT
        COUNT(*) AS total_tasks,
        SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) AS completed_tasks,
        SUM(CASE WHEN is_completed = 0 AND (due_date < :today OR due_date IS NULL) THEN 1 ELSE 0 END) AS pending_tasks,
        SUM(CASE WHEN is_completed = 0 AND due_date = :today THEN 1 ELSE 0 END) AS due_today_tasks
    FROM study_tasks
    WHERE user_id = :user_id
""")


def get_completion_stats(session, user_id: int, today_date=None):
    from datetime import date
    today_date = today_date or date.today()
    row = session.execute(COMPLETION_QUERY, {"user_id": user_id, "today": today_date}).mappings().first()
    result = dict(row) if row else {"total_tasks": 0, "completed_tasks": 0, "pending_tasks": 0, "due_today_tasks": 0}
    total = result["total_tasks"] or 0
    completed = result["completed_tasks"] or 0
    result["completion_pct"] = round((completed / total) * 100, 1) if total > 0 else 0.0
    return result


# =======================================================================
# HEALTH & FITNESS MODULE QUERIES
# =======================================================================

# ---------------------------------------------------------------------
# WEEKLY NUTRITION AVERAGES — GROUP BY ISO week using strftime
# ---------------------------------------------------------------------
WEEKLY_NUTRITION_QUERY = text("""
    SELECT
        strftime('%Y-W%W', log_date) AS week,
        ROUND(AVG(daily_cal), 0) AS avg_calories,
        ROUND(AVG(daily_prot), 1) AS avg_protein_g,
        ROUND(AVG(daily_carbs), 1) AS avg_carbs_g,
        ROUND(AVG(daily_fats), 1) AS avg_fats_g,
        COUNT(*) AS days_logged
    FROM (
        SELECT log_date, SUM(calories) AS daily_cal, SUM(protein_g) AS daily_prot,
               SUM(carbs_g) AS daily_carbs, SUM(fats_g) AS daily_fats
        FROM nutrition_logs
        WHERE user_id = :user_id
        GROUP BY log_date
    )
    GROUP BY week
    ORDER BY week
""")


def get_weekly_nutrition_averages(session, user_id: int):
    rows = session.execute(WEEKLY_NUTRITION_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# WEIGHT TREND with a TRUE calendar-day rolling 7-day average.
# Same gaps-and-islands concern as the study query above: weight isn't
# necessarily logged every single day, so a row-based window would
# silently average together entries that could span weeks. This
# correlated subquery instead only averages entries actually within
# the last 7 CALENDAR days of each row's date.
# ---------------------------------------------------------------------
WEIGHT_TREND_QUERY = text("""
    WITH weights AS (
        SELECT log_date, weight_kg
        FROM body_metrics
        WHERE user_id = :user_id AND weight_kg IS NOT NULL
        ORDER BY log_date
    )
    SELECT
        w.log_date,
        w.weight_kg,
        ROUND((
            SELECT AVG(w2.weight_kg)
            FROM weights w2
            WHERE w2.log_date BETWEEN DATE(w.log_date, '-6 days') AND w.log_date
        ), 2) AS rolling_avg_weight
    FROM weights w
    ORDER BY w.log_date
""")


def get_weight_trend(session, user_id: int):
    rows = session.execute(WEIGHT_TREND_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# WORKOUT CONSISTENCY — workouts per ISO week
# ---------------------------------------------------------------------
WORKOUT_CONSISTENCY_QUERY = text("""
    SELECT
        strftime('%Y-W%W', workout_date) AS week,
        COUNT(*) AS workout_count,
        COALESCE(SUM(duration_minutes), 0) AS total_minutes
    FROM workouts
    WHERE user_id = :user_id
    GROUP BY week
    ORDER BY week
""")


def get_workout_consistency(session, user_id: int):
    rows = session.execute(WORKOUT_CONSISTENCY_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# TODAY'S NUTRITION TOTALS vs a target (meal level sum, single day)
# ---------------------------------------------------------------------
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
        "total_carbs_g": 0, "total_fats_g": 0, "meal_count": 0
    }


# ---------------------------------------------------------------------
# TODAY'S WATER TOTAL (water tracked separately from nutrition_logs)
# ---------------------------------------------------------------------
DAILY_WATER_QUERY = text("""
    SELECT COALESCE(SUM(amount_ml), 0) AS total_water_ml
    FROM water_logs
    WHERE user_id = :user_id AND log_date = :log_date
""")


def get_daily_water_total(session, user_id: int, log_date):
    row = session.execute(DAILY_WATER_QUERY, {"user_id": user_id, "log_date": log_date}).mappings().first()
    return row["total_water_ml"] if row else 0


# ---------------------------------------------------------------------
# RECENT FOODS — distinct meal names ordered by most recently logged,
# used to power the "quick add from recent foods" UI. Uses GROUP BY +
# MAX() to find each food's most recent occurrence and its typical
# macros (AVG), so re-selecting "Rice" pre-fills sensible defaults.
# ---------------------------------------------------------------------
RECENT_FOODS_QUERY = text("""
    SELECT
        meal_name,
        MAX(log_date) AS last_logged,
        ROUND(AVG(calories), 0) AS typical_calories,
        ROUND(AVG(protein_g), 1) AS typical_protein_g,
        ROUND(AVG(carbs_g), 1) AS typical_carbs_g,
        ROUND(AVG(fats_g), 1) AS typical_fats_g,
        COUNT(*) AS times_logged
    FROM nutrition_logs
    WHERE user_id = :user_id
    GROUP BY meal_name
    HAVING COUNT(*) >= 1
    ORDER BY last_logged DESC
    LIMIT :limit
""")


def get_recent_foods(session, user_id: int, limit: int = 8):
    rows = session.execute(RECENT_FOODS_QUERY, {"user_id": user_id, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


# =======================================================================
# FINANCE MODULE QUERIES
# =======================================================================

# ---------------------------------------------------------------------
# MONTHLY SPEND — GROUP BY month
# ---------------------------------------------------------------------
MONTHLY_SPEND_QUERY = text("""
    SELECT
        strftime('%Y-%m', expense_date) AS month,
        ROUND(SUM(amount), 2) AS total_spent,
        COUNT(*) AS transaction_count
    FROM expenses
    WHERE user_id = :user_id
    GROUP BY month
    ORDER BY month
""")


def get_monthly_spend(session, user_id: int):
    rows = session.execute(MONTHLY_SPEND_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# TODAY'S SPEND
# ---------------------------------------------------------------------
TODAY_SPEND_QUERY = text("""
    SELECT
        COALESCE(SUM(amount), 0) AS today_spent,
        COUNT(*) AS today_transactions
    FROM expenses
    WHERE user_id = :user_id AND expense_date = :today
""")


def get_today_spend(session, user_id: int, today_date):
    row = session.execute(TODAY_SPEND_QUERY, {"user_id": user_id, "today": today_date}).mappings().first()
    return dict(row) if row else {"today_spent": 0.0, "today_transactions": 0}


# ---------------------------------------------------------------------
# CATEGORY BREAKDOWN — JOIN + GROUP BY, for a given month
# ---------------------------------------------------------------------
CATEGORY_BREAKDOWN_QUERY = text("""
    SELECT
        c.name AS category_name,
        COALESCE(SUM(e.amount), 0) AS total_spent,
        COUNT(e.id) AS transaction_count
    FROM expense_categories c
    LEFT JOIN expenses e
        ON e.category_id = c.id
        AND e.user_id = :user_id
        AND strftime('%Y-%m', e.expense_date) = :month
    WHERE c.user_id = :user_id
    GROUP BY c.id, c.name
    ORDER BY total_spent DESC
""")


def get_category_breakdown(session, user_id: int, month: str):
    rows = session.execute(
        CATEGORY_BREAKDOWN_QUERY, {"user_id": user_id, "month": month}
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# BUDGET REMAINING — CTE joining budgeted amount vs actual spend
# ---------------------------------------------------------------------
BUDGET_REMAINING_QUERY = text("""
    WITH spend AS (
        SELECT
            category_id,
            SUM(amount) AS spent
        FROM expenses
        WHERE user_id = :user_id
          AND strftime('%Y-%m', expense_date) = :month
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
      AND strftime('%Y-%m', b.month) = :month
    ORDER BY remaining ASC
""")


def get_budget_remaining(session, user_id: int, month: str):
    rows = session.execute(
        BUDGET_REMAINING_QUERY, {"user_id": user_id, "month": month}
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# ROLLING 7-DAY SPEND — TRUE calendar-day window (see note above on
# ROWS BETWEEN vs a real date-range window).
# ---------------------------------------------------------------------
ROLLING_SPEND_QUERY = text("""
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
        ROUND((
            SELECT COALESCE(SUM(d2.spent_that_day), 0)
            FROM daily d2
            WHERE d2.expense_date BETWEEN DATE(d.expense_date, '-6 days') AND d.expense_date
        ), 2) AS rolling_7day_spend
    FROM daily d
    ORDER BY d.expense_date
""")


def get_rolling_spend(session, user_id: int):
    rows = session.execute(ROLLING_SPEND_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# =======================================================================
# CROSS-DOMAIN ANALYTICS & SMART INSIGHTS QUERIES
# =======================================================================

# ---------------------------------------------------------------------
# STUDY VS WORKOUT CONSISTENCY BY WEEK — CTE + FULL OUTER JOIN
# ---------------------------------------------------------------------
CROSS_STUDY_WORKOUT_QUERY = text("""
    WITH weekly_study AS (
        SELECT
            strftime('%Y-W%W', session_date) AS week,
            SUM(duration_minutes) / 60.0 AS study_hours
        FROM study_sessions
        WHERE user_id = :user_id
        GROUP BY week
    ),
    weekly_workout AS (
        SELECT
            strftime('%Y-W%W', workout_date) AS week,
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
""")


def get_cross_study_workout(session, user_id: int):
    rows = session.execute(CROSS_STUDY_WORKOUT_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# WEEKLY COMPARISON (THIS WEEK VS LAST WEEK) FOR INSIGHTS GENERATION
# ---------------------------------------------------------------------
WEEKLY_COMPARISON_QUERY = text("""
    WITH study_weeks AS (
        SELECT
            strftime('%Y-W%W', session_date) AS week,
            SUM(duration_minutes) AS total_minutes
        FROM study_sessions
        WHERE user_id = :user_id
        GROUP BY week
    ),
    spend_weeks AS (
        SELECT
            strftime('%Y-W%W', expense_date) AS week,
            SUM(amount) AS total_spend
        FROM expenses
        WHERE user_id = :user_id
        GROUP BY week
    ),
    nutrition_weeks AS (
        SELECT
            strftime('%Y-W%W', log_date) AS week,
            AVG(daily_cal) AS avg_cal,
            AVG(daily_prot) AS avg_prot
        FROM (
            SELECT log_date, SUM(calories) AS daily_cal, SUM(protein_g) AS daily_prot
            FROM nutrition_logs WHERE user_id = :user_id GROUP BY log_date
        )
        GROUP BY week
    )
    SELECT
        w.week,
        COALESCE(s.total_minutes, 0) AS study_minutes,
        COALESCE(e.total_spend, 0) AS total_spend,
        COALESCE(n.avg_cal, 0) AS avg_calories,
        COALESCE(n.avg_prot, 0) AS avg_protein
    FROM (
        SELECT strftime('%Y-W%W', 'now', '-7 days') AS week
        UNION
        SELECT strftime('%Y-W%W', 'now') AS week
    ) w
    LEFT JOIN study_weeks s ON s.week = w.week
    LEFT JOIN spend_weeks e ON e.week = w.week
    LEFT JOIN nutrition_weeks n ON n.week = w.week
    ORDER BY w.week ASC
""")


def get_weekly_comparison(session, user_id: int):
    rows = session.execute(WEEKLY_COMPARISON_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# CATEGORIES OVER BUDGET — JOIN + GROUP BY + HAVING.
# HAVING is used (rather than WHERE) because the filter condition
# (spent > limit) depends on an aggregate (SUM(amount)), which isn't
# available until after grouping.
# ---------------------------------------------------------------------
OVER_BUDGET_CATEGORIES_QUERY = text("""
    SELECT
        c.name AS category_name,
        b.limit_amount AS budget_limit,
        SUM(e.amount) AS spent,
        ROUND(SUM(e.amount) - b.limit_amount, 2) AS overspend
    FROM expenses e
    JOIN expense_categories c ON c.id = e.category_id
    JOIN budgets b ON b.category_id = e.category_id AND b.user_id = e.user_id
    WHERE e.user_id = :user_id
      AND strftime('%Y-%m', e.expense_date) = :month
      AND strftime('%Y-%m', b.month) = :month
    GROUP BY c.id, c.name, b.limit_amount
    HAVING SUM(e.amount) > b.limit_amount
    ORDER BY overspend DESC
""")


def get_over_budget_categories(session, user_id: int, month: str):
    rows = session.execute(
        OVER_BUDGET_CATEGORIES_QUERY, {"user_id": user_id, "month": month}
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# SPENDING BY WEEKDAY — for "your highest spending day was Saturday"
# style insights. Uses strftime('%w', ...) (0=Sunday..6=Saturday).
# ---------------------------------------------------------------------
SPENDING_BY_WEEKDAY_QUERY = text("""
    SELECT
        strftime('%w', expense_date) AS weekday_num,
        CASE strftime('%w', expense_date)
            WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday'
            WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday'
            ELSE 'Saturday' END AS weekday_name,
        SUM(amount) AS total_spent,
        COUNT(*) AS transaction_count
    FROM expenses
    WHERE user_id = :user_id
    GROUP BY weekday_num
    ORDER BY total_spent DESC
""")


def get_spending_by_weekday(session, user_id: int):
    rows = session.execute(SPENDING_BY_WEEKDAY_QUERY, {"user_id": user_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# MONTH-OVER-MONTH CATEGORY CHANGE — self-join comparing this month's
# category spend against last month's, for insights like
# "Food spending increased 18% vs last month."
# ---------------------------------------------------------------------
MONTH_OVER_MONTH_CATEGORY_QUERY = text("""
    WITH this_month AS (
        SELECT category_id, SUM(amount) AS spent
        FROM expenses
        WHERE user_id = :user_id AND strftime('%Y-%m', expense_date) = :this_month
        GROUP BY category_id
    ),
    last_month AS (
        SELECT category_id, SUM(amount) AS spent
        FROM expenses
        WHERE user_id = :user_id AND strftime('%Y-%m', expense_date) = :last_month
        GROUP BY category_id
    )
    SELECT
        c.name AS category_name,
        COALESCE(t.spent, 0) AS this_month_spent,
        COALESCE(l.spent, 0) AS last_month_spent
    FROM expense_categories c
    LEFT JOIN this_month t ON t.category_id = c.id
    LEFT JOIN last_month l ON l.category_id = c.id
    WHERE c.user_id = :user_id AND (t.spent IS NOT NULL OR l.spent IS NOT NULL)
    ORDER BY this_month_spent DESC
""")


def get_month_over_month_category(session, user_id: int, this_month: str, last_month: str):
    rows = session.execute(
        MONTH_OVER_MONTH_CATEGORY_QUERY,
        {"user_id": user_id, "this_month": this_month, "last_month": last_month},
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# LARGEST EXPENSES — simple ORDER BY + LIMIT, for "largest expenses" insight
# ---------------------------------------------------------------------
LARGEST_EXPENSES_QUERY = text("""
    SELECT e.expense_date, e.amount, c.name AS category_name, e.description
    FROM expenses e
    LEFT JOIN expense_categories c ON c.id = e.category_id
    WHERE e.user_id = :user_id
    ORDER BY e.amount DESC
    LIMIT :limit
""")


def get_largest_expenses(session, user_id: int, limit: int = 5):
    rows = session.execute(LARGEST_EXPENSES_QUERY, {"user_id": user_id, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]
