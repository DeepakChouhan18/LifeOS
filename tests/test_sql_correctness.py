"""
Tests for database/raw_queries.py — verifies JOINs, CTEs, HAVING clauses,
and missing-date behavior produce correct results, not just "doesn't crash".
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base, User, Subject, StudySession, StudyTask,
    ExpenseCategory, Expense, Budget,
)
from database import raw_queries as rq


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(User(id=1, username="test_user"))
    session.commit()
    yield session
    session.close()


# --- JOIN correctness ---

def test_subject_breakdown_left_join_includes_subjects_with_zero_sessions(db_session):
    """LEFT JOIN must include subjects that have no logged sessions at all
    (with 0, not a missing row)."""
    db_session.add_all([
        Subject(id=1, user_id=1, name="SQL"),
        Subject(id=2, user_id=1, name="ML"),  # no sessions logged
    ])
    db_session.add(StudySession(user_id=1, subject_id=1, session_date=date.today(), duration_minutes=60))
    db_session.commit()

    breakdown = rq.get_subject_breakdown(db_session, user_id=1)
    names = {row["subject_name"]: row["total_minutes"] for row in breakdown}

    assert names["SQL"] == 60
    assert names["ML"] == 0  # present with zero, not missing


# --- CTE correctness (streaks) ---

def test_streak_cte_groups_consecutive_days_into_one_island(db_session):
    db_session.add(Subject(id=1, user_id=1, name="DSA"))
    for offset in [2, 1, 0]:
        db_session.add(StudySession(user_id=1, subject_id=1,
                                     session_date=date.today() - timedelta(days=offset),
                                     duration_minutes=30))
    db_session.commit()

    streaks = rq.get_all_streaks(db_session, user_id=1)
    assert len(streaks) == 1
    assert streaks[0]["streak_length"] == 3


def test_streak_cte_separates_non_consecutive_days_into_islands(db_session):
    db_session.add(Subject(id=1, user_id=1, name="DSA"))
    for offset in [5, 0]:  # gap in between
        db_session.add(StudySession(user_id=1, subject_id=1,
                                     session_date=date.today() - timedelta(days=offset),
                                     duration_minutes=30))
    db_session.commit()

    streaks = rq.get_all_streaks(db_session, user_id=1)
    assert len(streaks) == 2
    assert all(s["streak_length"] == 1 for s in streaks)


# --- HAVING clause correctness ---

def test_having_clause_only_returns_categories_over_budget(db_session):
    db_session.add_all([
        ExpenseCategory(id=1, user_id=1, name="Food"),
        ExpenseCategory(id=2, user_id=1, name="Travel"),
    ])
    month_start = date.today().replace(day=1)
    db_session.add_all([
        Budget(user_id=1, category_id=1, month=month_start, limit_amount=500.0),
        Budget(user_id=1, category_id=2, month=month_start, limit_amount=1000.0),
    ])
    # Food: over budget (600 > 500). Travel: under budget (200 < 1000).
    db_session.add(Expense(user_id=1, category_id=1, amount=600.0, expense_date=date.today()))
    db_session.add(Expense(user_id=1, category_id=2, amount=200.0, expense_date=date.today()))
    db_session.commit()

    month = date.today().strftime("%Y-%m")
    over_budget = rq.get_over_budget_categories(db_session, user_id=1, month=month)

    # HAVING should filter out Travel entirely — only Food (which exceeds
    # its budget) should appear in the result.
    assert len(over_budget) == 1
    assert over_budget[0]["category_name"] == "Food"
    assert over_budget[0]["overspend"] == 100.0


def test_having_clause_returns_empty_when_nothing_over_budget(db_session):
    db_session.add(ExpenseCategory(id=1, user_id=1, name="Food"))
    month_start = date.today().replace(day=1)
    db_session.add(Budget(user_id=1, category_id=1, month=month_start, limit_amount=1000.0))
    db_session.add(Expense(user_id=1, category_id=1, amount=200.0, expense_date=date.today()))
    db_session.commit()

    month = date.today().strftime("%Y-%m")
    over_budget = rq.get_over_budget_categories(db_session, user_id=1, month=month)
    assert over_budget == []


# --- Missing-date behavior ---

def test_rolling_spend_missing_days_dont_break_window(db_session):
    """
    If a user logs an expense on day 0 and day 5 but nothing in between,
    the rolling calendar window for day 5 should only include days that
    actually fall within the last 7 calendar days.
    """
    db_session.add(ExpenseCategory(id=1, user_id=1, name="Food"))
    today = date.today()
    db_session.add(Expense(user_id=1, category_id=1, amount=100.0, expense_date=today - timedelta(days=5)))
    db_session.add(Expense(user_id=1, category_id=1, amount=50.0, expense_date=today))
    db_session.commit()

    rolling = rq.get_rolling_spend(db_session, user_id=1)
    assert len(rolling) == 2
    assert rolling[-1]["rolling_7day_spend"] == 150.0


def test_rolling_spend_excludes_entries_outside_calendar_window(db_session):
    db_session.add(ExpenseCategory(id=1, user_id=1, name="Food"))
    today = date.today()
    db_session.add(Expense(user_id=1, category_id=1, amount=100.0, expense_date=today - timedelta(days=10)))
    db_session.add(Expense(user_id=1, category_id=1, amount=50.0, expense_date=today))
    db_session.commit()

    rolling = rq.get_rolling_spend(db_session, user_id=1)
    # 10 days apart -> outside the 7-day window -> should NOT be summed together
    assert rolling[-1]["rolling_7day_spend"] == 50.0


# --- Weekday aggregation correctness ---

def test_spending_by_weekday_aggregates_correctly(db_session):
    db_session.add(ExpenseCategory(id=1, user_id=1, name="Food"))
    monday = date(2026, 8, 3)  # verified Monday
    db_session.add(Expense(user_id=1, category_id=1, amount=100.0, expense_date=monday))
    db_session.add(Expense(user_id=1, category_id=1, amount=50.0, expense_date=monday + timedelta(days=7)))
    db_session.commit()

    weekday_data = rq.get_spending_by_weekday(db_session, user_id=1)
    monday_row = next(r for r in weekday_data if r["weekday_name"] == "Monday")
    assert monday_row["total_spent"] == 150.0
    assert monday_row["transaction_count"] == 2


def test_completion_stats_zero_tasks_returns_zero_not_error(db_session):
    stats = rq.get_completion_stats(db_session, user_id=1)
    assert stats["total_tasks"] == 0
    assert stats["completion_pct"] == 0.0
