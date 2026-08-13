"""
ML preprocessing.

Builds two feature sets from the user's own logged data:
1. Daily features (for clustering "day types") — joins study, health,
   and finance data by date.
2. Weekly features (for predicting whether a weekly study goal was hit)
   — aggregates daily features into weeks and labels each week.

Kept separate from analytics.py: analytics.py serves the dashboards,
this module serves the ML models and has different needs (numeric
arrays, no NaNs, consistent shape).
"""

import pandas as pd
import numpy as np
from sqlalchemy import text
from config import WEEKLY_STUDY_GOAL_MINUTES_DEFAULT


def build_daily_features_df(session, user_id: int) -> pd.DataFrame:
    """
    One row per date the user has ANY activity logged, with columns:
    study_minutes, calories, workout_minutes, sleep_hours, weight_kg, expense_amount.
    Missing values are filled with sensible defaults (0 for activity/spend,
    forward-filled for weight) rather than dropped, so we don't lose days
    where only some modules were logged.
    """
    study_df = pd.read_sql(
        text("""
            SELECT session_date AS log_date, SUM(duration_minutes) AS study_minutes
            FROM study_sessions WHERE user_id = :uid GROUP BY session_date
        """), session.bind, params={"uid": user_id},
    )

    nutrition_df = pd.read_sql(
        text("""
            SELECT log_date, SUM(calories) AS calories
            FROM nutrition_logs WHERE user_id = :uid GROUP BY log_date
        """), session.bind, params={"uid": user_id},
    )

    workout_df = pd.read_sql(
        text("""
            SELECT workout_date AS log_date, SUM(duration_minutes) AS workout_minutes
            FROM workouts WHERE user_id = :uid GROUP BY workout_date
        """), session.bind, params={"uid": user_id},
    )

    body_df = pd.read_sql(
        text("""
            SELECT log_date, weight_kg, sleep_hours
            FROM body_metrics WHERE user_id = :uid
        """), session.bind, params={"uid": user_id},
    )

    expense_df = pd.read_sql(
        text("""
            SELECT expense_date AS log_date, SUM(amount) AS expense_amount
            FROM expenses WHERE user_id = :uid GROUP BY expense_date
        """), session.bind, params={"uid": user_id},
    )

    for df in [study_df, nutrition_df, workout_df, body_df, expense_df]:
        if not df.empty:
            df["log_date"] = pd.to_datetime(df["log_date"])

    frames = [study_df, nutrition_df, workout_df, body_df, expense_df]
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=[
            "log_date", "study_minutes", "calories", "workout_minutes",
            "sleep_hours", "weight_kg", "expense_amount",
        ])

    merged = non_empty[0]
    for f in non_empty[1:]:
        merged = merged.merge(f, on="log_date", how="outer")

    merged = merged.sort_values("log_date").reset_index(drop=True)

    for col in ["study_minutes", "calories", "workout_minutes", "expense_amount"]:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0)

    for col in ["weight_kg", "sleep_hours"]:
        if col in merged.columns:
            merged[col] = merged[col].ffill().bfill()
            merged[col] = merged[col].fillna(0)

    return merged


def build_weekly_features_df(session, user_id: int, weekly_goal_minutes: int = None) -> pd.DataFrame:
    """
    Aggregates daily features into weekly rows and labels each week
    1 (hit weekly study goal) or 0 (missed it), for the supervised model.

    weekly_goal_minutes defaults to WEEKLY_STUDY_GOAL_MINUTES_DEFAULT but
    should normally be passed as 7 * the user's actual daily_study_goal_minutes
    from their profile, so the label reflects THEIR goal, not a generic one.

    LEAKAGE AVOIDANCE: features used to predict week N's label are
    deliberately taken from week N-1 (shift(1)) — never from week N
    itself. Predicting week N's outcome from week N's own study minutes
    would be circular (the model would just be reading the answer).
    Also includes previous week's task completion rate and previous
    week's study streak length as additional predictive features.
    """
    goal_minutes = weekly_goal_minutes or WEEKLY_STUDY_GOAL_MINUTES_DEFAULT
    daily = build_daily_features_df(session, user_id)
    if daily.empty:
        return pd.DataFrame()

    daily["week"] = daily["log_date"].dt.strftime("%Y-%W")

    weekly = daily.groupby("week").agg(
        study_minutes=("study_minutes", "sum"),
        avg_calories=("calories", "mean"),
        workout_minutes=("workout_minutes", "sum"),
        avg_sleep_hours=("sleep_hours", "mean"),
        total_expense=("expense_amount", "sum"),
    ).reset_index()

    # Task completion rate and streak length per week (additional signal)
    task_df = pd.read_sql(
        text("""
            SELECT due_date AS log_date, is_completed
            FROM study_tasks WHERE user_id = :uid AND due_date IS NOT NULL
        """), session.bind, params={"uid": user_id},
    )
    if not task_df.empty:
        task_df["log_date"] = pd.to_datetime(task_df["log_date"])
        task_df["week"] = task_df["log_date"].dt.strftime("%Y-%W")
        completion_by_week = task_df.groupby("week")["is_completed"].mean().reset_index()
        completion_by_week.columns = ["week", "task_completion_rate"]
        weekly = weekly.merge(completion_by_week, on="week", how="left")
    else:
        weekly["task_completion_rate"] = np.nan
    weekly["task_completion_rate"] = weekly["task_completion_rate"].fillna(0)

    weekly["goal_hit"] = (weekly["study_minutes"] >= goal_minutes).astype(int)

    feature_cols = ["study_minutes", "avg_calories", "workout_minutes",
                     "avg_sleep_hours", "total_expense", "task_completion_rate"]
    shifted = weekly[feature_cols].shift(1)
    shifted.columns = [f"prev_{c}" for c in feature_cols]

    result = pd.concat([weekly[["week", "goal_hit"]], shifted], axis=1)
    result = result.dropna().reset_index(drop=True)

    return result
