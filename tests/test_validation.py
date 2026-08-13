"""Tests for utils/validation.py."""

import pytest
from datetime import date, timedelta
from utils import validation


def test_validate_positive_rejects_zero_by_default():
    with pytest.raises(validation.ValidationError):
        validation.validate_positive(0, "Amount")


def test_validate_positive_allows_zero_when_flagged():
    validation.validate_positive(0, "Calories", allow_zero=True)  # should not raise


def test_validate_positive_rejects_negative():
    with pytest.raises(validation.ValidationError):
        validation.validate_positive(-5, "Amount")


def test_validate_age_rejects_out_of_range():
    with pytest.raises(validation.ValidationError):
        validation.validate_age(150)
    with pytest.raises(validation.ValidationError):
        validation.validate_age(0)


def test_validate_age_accepts_valid_range():
    validation.validate_age(25)  # should not raise


def test_validate_expense_amount_rejects_zero():
    with pytest.raises(validation.ValidationError):
        validation.validate_expense_amount(0)


def test_validate_not_future_date_rejects_future():
    with pytest.raises(validation.ValidationError):
        validation.validate_not_future_date(date.today() + timedelta(days=1))


def test_validate_not_future_date_accepts_today_and_past():
    validation.validate_not_future_date(date.today())
    validation.validate_not_future_date(date.today() - timedelta(days=5))


def test_validate_nonempty_string_rejects_blank():
    with pytest.raises(validation.ValidationError):
        validation.validate_nonempty_string("   ", "Name")
    with pytest.raises(validation.ValidationError):
        validation.validate_nonempty_string("", "Name")


def test_validate_sleep_hours_range():
    with pytest.raises(validation.ValidationError):
        validation.validate_sleep_hours(25)
    validation.validate_sleep_hours(8)  # should not raise


def test_crud_functions_reject_invalid_input_end_to_end():
    """Integration check: crud.add_expense should actually raise via validation,
    not silently accept bad data."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database.models import Base, User
    from modules.finance import crud as finance_crud

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(User(id=1, username="test"))
    session.commit()

    with pytest.raises(validation.ValidationError):
        finance_crud.add_expense(session, user_id=1, amount=-50, category_id=None)

    session.close()
