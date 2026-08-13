"""
Data export utilities — CSV export for study, health, finance, and combined data.
"""

import io
import pandas as pd
from sqlalchemy import text


def export_study_csv(session, user_id: int) -> str:
    """Export all study sessions and tasks to CSV."""
    sessions_df = pd.read_sql(
        text("""
            SELECT ss.session_date, s.name AS subject, ss.duration_minutes,
                   ss.topic, ss.notes
            FROM study_sessions ss
            LEFT JOIN subjects s ON s.id = ss.subject_id
            WHERE ss.user_id = :uid
            ORDER BY ss.session_date DESC
        """), session.bind, params={"uid": user_id},
    )

    tasks_df = pd.read_sql(
        text("""
            SELECT st.title, s.name AS subject, st.priority, st.topic,
                   st.due_date, st.is_completed, st.completed_at
            FROM study_tasks st
            LEFT JOIN subjects s ON s.id = st.subject_id
            WHERE st.user_id = :uid
            ORDER BY st.due_date DESC
        """), session.bind, params={"uid": user_id},
    )

    output = io.StringIO()
    output.write("=== STUDY SESSIONS ===\n")
    sessions_df.to_csv(output, index=False)
    output.write("\n=== STUDY TASKS ===\n")
    tasks_df.to_csv(output, index=False)
    return output.getvalue()


def export_health_csv(session, user_id: int) -> str:
    """Export all nutrition, water, workout, and body metric data to CSV."""
    nutrition_df = pd.read_sql(
        text("""
            SELECT log_date, meal_name, meal_type, calories, protein_g, carbs_g, fats_g
            FROM nutrition_logs
            WHERE user_id = :uid
            ORDER BY log_date DESC
        """), session.bind, params={"uid": user_id},
    )

    water_df = pd.read_sql(
        text("""
            SELECT log_date, amount_ml
            FROM water_logs
            WHERE user_id = :uid
            ORDER BY log_date DESC
        """), session.bind, params={"uid": user_id},
    )

    workouts_df = pd.read_sql(
        text("""
            SELECT workout_date, type, exercise, duration_minutes, notes
            FROM workouts
            WHERE user_id = :uid
            ORDER BY workout_date DESC
        """), session.bind, params={"uid": user_id},
    )

    body_df = pd.read_sql(
        text("""
            SELECT log_date, weight_kg, sleep_hours
            FROM body_metrics
            WHERE user_id = :uid
            ORDER BY log_date DESC
        """), session.bind, params={"uid": user_id},
    )

    output = io.StringIO()
    output.write("=== NUTRITION LOGS ===\n")
    nutrition_df.to_csv(output, index=False)
    output.write("\n=== WATER LOGS ===\n")
    water_df.to_csv(output, index=False)
    output.write("\n=== WORKOUTS ===\n")
    workouts_df.to_csv(output, index=False)
    output.write("\n=== BODY METRICS ===\n")
    body_df.to_csv(output, index=False)
    return output.getvalue()


def export_finance_csv(session, user_id: int) -> str:
    """Export all expenses and budgets to CSV."""
    expenses_df = pd.read_sql(
        text("""
            SELECT e.expense_date, e.amount, c.name AS category,
                   e.description, e.payment_method
            FROM expenses e
            LEFT JOIN expense_categories c ON c.id = e.category_id
            WHERE e.user_id = :uid
            ORDER BY e.expense_date DESC
        """), session.bind, params={"uid": user_id},
    )

    budgets_df = pd.read_sql(
        text("""
            SELECT b.month, c.name AS category, b.limit_amount
            FROM budgets b
            LEFT JOIN expense_categories c ON c.id = b.category_id
            WHERE b.user_id = :uid
            ORDER BY b.month DESC
        """), session.bind, params={"uid": user_id},
    )

    output = io.StringIO()
    output.write("=== EXPENSES ===\n")
    expenses_df.to_csv(output, index=False)
    output.write("\n=== BUDGETS ===\n")
    budgets_df.to_csv(output, index=False)
    return output.getvalue()


def export_all_csv(session, user_id: int) -> str:
    """Export combined daily feature data across all modules."""
    daily_df = pd.read_sql(
        text("""
            WITH cte_study AS (
                SELECT session_date AS log_date, SUM(duration_minutes) AS study_minutes
                FROM study_sessions WHERE user_id = :uid GROUP BY session_date
            ),
            cte_nutrition AS (
                SELECT log_date, SUM(calories) AS calories, SUM(protein_g) AS protein_g
                FROM nutrition_logs WHERE user_id = :uid GROUP BY log_date
            ),
            cte_workouts AS (
                SELECT workout_date AS log_date, SUM(duration_minutes) AS workout_minutes
                FROM workouts WHERE user_id = :uid GROUP BY workout_date
            ),
            cte_body AS (
                SELECT log_date, weight_kg, sleep_hours
                FROM body_metrics WHERE user_id = :uid
            ),
            cte_expenses AS (
                SELECT expense_date AS log_date, SUM(amount) AS expense_amount
                FROM expenses WHERE user_id = :uid GROUP BY expense_date
            )
            SELECT COALESCE(s.log_date, n.log_date, w.log_date, b.log_date, e.log_date) AS date,
                   s.study_minutes, n.calories, n.protein_g,
                   w.workout_minutes, b.weight_kg, b.sleep_hours,
                   e.expense_amount
            FROM cte_study s
            LEFT JOIN cte_nutrition n ON s.log_date = n.log_date
            LEFT JOIN cte_workouts w ON COALESCE(s.log_date, n.log_date) = w.log_date
            LEFT JOIN cte_body b ON COALESCE(s.log_date, n.log_date, w.log_date) = b.log_date
            LEFT JOIN cte_expenses e ON COALESCE(s.log_date, n.log_date, w.log_date, b.log_date) = e.log_date
            ORDER BY date DESC
        """), session.bind, params={"uid": user_id},
    )

    output = io.StringIO()
    output.write("=== COMBINED DAILY DATA ===\n")
    daily_df.to_csv(output, index=False)
    return output.getvalue()
