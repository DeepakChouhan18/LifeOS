"""
Tests for the Study module's raw SQL (streaks) and analytics logic.

Uses an isolated in-memory SQLite DB per test so tests never touch
data/lifeos.db and never depend on each other.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, User, Subject, StudySession, StudyTask
from database import raw_queries as rq
from modules.study import analytics


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = User(id=1, username="test_user")
    session.add(user)
    subject = Subject(id=1, user_id=1, name="DSA")
    session.add(subject)
    session.commit()

    yield session
    session.close()


def _log_session(db_session, days_ago, minutes=30):
    db_session.add(StudySession(
        user_id=1, subject_id=1,
        session_date=date.today() - timedelta(days=days_ago),
        duration_minutes=minutes,
    ))
    db_session.commit()


def test_streak_query_groups_consecutive_days_correctly(db_session):
    # Log a 3-day streak (days_ago 4,3,2), a gap, then today (day 0)
    for offset in [4, 3, 2, 0]:
        _log_session(db_session, offset)

    streaks = rq.get_all_streaks(db_session, user_id=1)

    # Expect two islands: the 3-day one (offsets 4,3,2) and a 1-day one (offset 0)
    lengths = sorted(s["streak_length"] for s in streaks)
    assert lengths == [1, 3]


def test_current_streak_is_zero_when_broken(db_session):
    # Only a session 3 days ago -> streak is broken (not today or yesterday)
    _log_session(db_session, days_ago=3)

    summary = analytics.get_streak_summary(db_session, user_id=1)

    assert summary["current_streak"] == 0
    assert summary["longest_streak"] == 1


def test_current_streak_counts_when_active_today(db_session):
    for offset in [2, 1, 0]:
        _log_session(db_session, offset)

    summary = analytics.get_streak_summary(db_session, user_id=1)

    assert summary["current_streak"] == 3
    assert summary["longest_streak"] == 3


def test_completion_percentage_calculation(db_session):
    db_session.add_all([
        StudyTask(user_id=1, subject_id=1, title="t1", is_completed=True),
        StudyTask(user_id=1, subject_id=1, title="t2", is_completed=True),
        StudyTask(user_id=1, subject_id=1, title="t3", is_completed=False),
        StudyTask(user_id=1, subject_id=1, title="t4", is_completed=False),
    ])
    db_session.commit()

    stats = analytics.get_completion_summary(db_session, user_id=1)

    assert stats["total_tasks"] == 4
    assert stats["completed_tasks"] == 2
    assert stats["completion_pct"] == 50.0


def test_completion_percentage_with_no_tasks_is_zero(db_session):
    stats = analytics.get_completion_summary(db_session, user_id=1)
    assert stats["total_tasks"] == 0
    assert stats["completion_pct"] == 0.0


def test_subject_breakdown_sums_minutes_correctly(db_session):
    _log_session(db_session, days_ago=1, minutes=30)
    _log_session(db_session, days_ago=2, minutes=45)

    df = analytics.get_subject_breakdown_df(db_session, user_id=1)

    dsa_row = df[df["subject_name"] == "DSA"].iloc[0]
    assert dsa_row["total_minutes"] == 75
    assert dsa_row["session_count"] == 2
