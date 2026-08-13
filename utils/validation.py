"""
Shared input validation.

Centralized so every form (nutrition, workout, weight, expense, study
session, profile) validates consistently instead of each page re-inventing
its own bounds checks. Each function raises ValueError with a
user-readable message on failure; pages catch this and show st.error().
"""

from datetime import date


class ValidationError(ValueError):
    pass


def validate_positive(value, field_name: str, allow_zero: bool = False):
    if value is None:
        return
    if allow_zero and value < 0:
        raise ValidationError(f"{field_name} cannot be negative.")
    if not allow_zero and value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")


def validate_range(value, field_name: str, min_val, max_val):
    if value is None:
        return
    if not (min_val <= value <= max_val):
        raise ValidationError(f"{field_name} must be between {min_val} and {max_val}.")


def validate_age(age: int):
    validate_range(age, "Age", 5, 119)


def validate_height_cm(height_cm: float):
    validate_range(height_cm, "Height", 50, 272)


def validate_weight_kg(weight_kg: float):
    validate_range(weight_kg, "Weight", 20, 400)


def validate_sleep_hours(sleep_hours: float):
    if sleep_hours is None:
        return
    validate_range(sleep_hours, "Sleep hours", 0, 24)


def validate_calories(calories):
    validate_positive(calories, "Calories", allow_zero=True)


def validate_macro(value, name: str):
    validate_positive(value, name, allow_zero=True)


def validate_expense_amount(amount):
    validate_positive(amount, "Amount", allow_zero=False)


def validate_duration_minutes(minutes, field_name: str = "Duration"):
    validate_positive(minutes, field_name, allow_zero=False)


def validate_not_future_date(d: date, field_name: str = "Date"):
    if d is None:
        return
    if d > date.today():
        raise ValidationError(f"{field_name} cannot be in the future.")


def validate_nonempty_string(value: str, field_name: str):
    if not value or not value.strip():
        raise ValidationError(f"{field_name} cannot be empty.")
