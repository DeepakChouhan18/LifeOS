"""
Tests for the Finance module's raw SQL and analytics logic.
Mirrors tests/test_study_analytics.py and tests/test_health_analytics.py.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, User, ExpenseCategory, Expense, Budget
from database import raw_queries as rq
from modules.finance import analytics


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = User(id=1, username="test_user")
    session.add(user)
    food = ExpenseCategory(id=1, user_id=1, name="Food")
    travel = ExpenseCategory(id=2, user_id=1, name="Travel")
    session.add_all([food, travel])
    session.commit()

    yield session
    session.close()


def test_monthly_spend_sums_correctly(db_session):
    today = date.today()
    db_session.add_all([
        Expense(user_id=1, category_id=1, amount=100.0, expense_date=today),
        Expense(user_id=1, category_id=2, amount=250.5, expense_date=today),
    ])
    db_session.commit()

    monthly = rq.get_monthly_spend(db_session, user_id=1)

    this_month = today.strftime("%Y-%m")
    row = next(m for m in monthly if m["month"] == this_month)
    assert row["total_spent"] == 350.5
    assert row["transaction_count"] == 2


def test_category_breakdown_includes_zero_spend_categories(db_session):
    today = date.today()
    db_session.add(Expense(user_id=1, category_id=1, amount=100.0, expense_date=today))
    db_session.commit()

    month = today.strftime("%Y-%m")
    breakdown = rq.get_category_breakdown(db_session, user_id=1, month=month)

    # Travel has no expenses but should still appear with 0 spend
    names = {row["category_name"]: row["total_spent"] for row in breakdown}
    assert names["Food"] == 100.0
    assert names["Travel"] == 0


def test_budget_remaining_calculation(db_session):
    today = date.today()
    month_start = today.replace(day=1)

    db_session.add(Budget(user_id=1, category_id=1, month=month_start, limit_amount=1000.0))
    db_session.add(Expense(user_id=1, category_id=1, amount=350.0, expense_date=today))
    db_session.commit()

    month = today.strftime("%Y-%m")
    remaining = rq.get_budget_remaining(db_session, user_id=1, month=month)

    assert len(remaining) == 1
    assert remaining[0]["spent"] == 350.0
    assert remaining[0]["remaining"] == 650.0


def test_budget_remaining_can_go_negative_when_overspent(db_session):
    today = date.today()
    month_start = today.replace(day=1)

    db_session.add(Budget(user_id=1, category_id=1, month=month_start, limit_amount=200.0))
    db_session.add(Expense(user_id=1, category_id=1, amount=500.0, expense_date=today))
    db_session.commit()

    month = today.strftime("%Y-%m")
    remaining = rq.get_budget_remaining(db_session, user_id=1, month=month)

    assert remaining[0]["remaining"] == -300.0


def test_full_summary_with_no_data_is_zero(db_session):
    summary = analytics.get_full_summary(db_session, user_id=1)

    assert summary["total_spent_this_month"] == 0
    assert summary["transaction_count"] == 0
    assert summary["budget_remaining"] == 0


def test_monthly_budget_fallback_decimal_float_arithmetic_does_not_crash(db_session):
    """
    Regression test: UserProfile.monthly_budget is a Numeric(10,2) column,
    read via the ORM as a Decimal. total_spent/total_remaining come from
    raw SQL as plain floats. Mixing Decimal and float in a subtraction
    raises TypeError in Python — this happened in production when a user
    had a profile-level monthly_budget set but no category-level budgets,
    triggering the fallback path. Verifies that path no longer crashes.
    """
    from database.models import UserProfile

    db_session.add(UserProfile(
        user_id=1, name="Test", age=25, sex="male", height_cm=175, weight_kg=70,
        activity_level="moderate", goal="maintain", monthly_budget=15000.0,
    ))
    db_session.add(Expense(user_id=1, category_id=1, amount=500.0, expense_date=date.today()))
    db_session.commit()

    # Must not raise TypeError: unsupported operand type(s) for -: 'Decimal' and 'float'
    summary = analytics.get_current_month_summary(db_session, user_id=1)

    assert summary["total_budget"] == 15000.0
    assert summary["total_remaining"] == 14500.0
    assert isinstance(summary["total_remaining"], float)
