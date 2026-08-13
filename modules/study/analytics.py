"""
Study module analytics.

Turns raw DB rows (mostly from database/raw_queries.py) into the metrics
the UI shows: completion %, current streak, longest streak, avg session length,
weekly hours trend, today's summary.
"""

from datetime import date, datetime
import pandas as pd

from database import raw_queries as rq
from modules.settings import crud as settings_crud


def _parse_date(value):
    """SQLite returns dates as strings via raw SQL; normalize to date objects."""
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_streak_summary(session, user_id: int) -> dict:
    """Returns current streak and longest streak (in days)."""
    streaks = rq.get_all_streaks(session, user_id)

    if not streaks:
        return {"current_streak": 0, "longest_streak": 0}

    longest_streak = max(s["streak_length"] for s in streaks)

    # streaks[0] is the most recent island (query orders by streak_end DESC)
    most_recent = streaks[0]
    streak_end = _parse_date(most_recent["streak_end"])
    today = date.today()
    days_since_end = (today - streak_end).days

    # Current streak only counts if the most recent island ends today or yesterday.
    current_streak = most_recent["streak_length"] if days_since_end <= 1 else 0

    return {"current_streak": current_streak, "longest_streak": longest_streak}


def get_completion_summary(session, user_id: int) -> dict:
    return rq.get_completion_stats(session, user_id)


def get_today_summary(session, user_id: int) -> dict:
    """Returns today's study minutes, session count, tasks completed vs due."""
    today_date = date.today()
    study = rq.get_today_study_summary(session, user_id, today_date)
    completion = rq.get_completion_stats(session, user_id, today_date)

    profile = settings_crud.get_user_profile(session, user_id)
    daily_goal_minutes = profile.daily_study_goal_minutes if profile else 300

    return {
        "today_minutes": study["today_minutes"],
        "today_hours": round(study["today_minutes"] / 60.0, 1),
        "session_count": study["session_count"],
        "daily_goal_minutes": daily_goal_minutes,
        "daily_goal_hours": round(daily_goal_minutes / 60.0, 1),
        "goal_pct": round(min(100.0, (study["today_minutes"] / daily_goal_minutes) * 100.0), 1) if daily_goal_minutes > 0 else 0.0,
        "due_today_tasks": completion["due_today_tasks"],
        "completed_tasks": completion["completed_tasks"],
    }


def get_subject_breakdown_df(session, user_id: int) -> pd.DataFrame:
    rows = rq.get_subject_breakdown(session, user_id)
    return pd.DataFrame(rows)


def get_weekly_trend_df(session, user_id: int) -> pd.DataFrame:
    rows = rq.get_rolling_weekly_minutes(session, user_id)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["session_date"] = pd.to_datetime(df["session_date"])
        df["rolling_7day_hours"] = (df["rolling_7day_minutes"] / 60.0).round(2)
    return df


def get_full_summary(session, user_id: int) -> dict:
    """One call that returns everything the dashboard page needs."""
    streaks = get_streak_summary(session, user_id)
    completion = get_completion_summary(session, user_id)
    subject_df = get_subject_breakdown_df(session, user_id)
    today_sum = get_today_summary(session, user_id)

    total_minutes = subject_df["total_minutes"].sum() if not subject_df.empty else 0

    return {
        "current_streak": streaks["current_streak"],
        "longest_streak": streaks["longest_streak"],
        "completion_pct": completion["completion_pct"],
        "total_tasks": completion["total_tasks"],
        "completed_tasks": completion["completed_tasks"],
        "total_study_hours": round(total_minutes / 60.0, 1),
        "today_hours": today_sum["today_hours"],
        "today_minutes": today_sum["today_minutes"],
        "daily_goal_hours": today_sum["daily_goal_hours"],
        "today_goal_pct": today_sum["goal_pct"],
    }
