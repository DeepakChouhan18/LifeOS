"""
Tests for the Health module's raw SQL and analytics logic.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, User, UserProfile, NutritionLog, WaterLog, Workout, BodyMetric
from database import raw_queries as rq
from modules.health import analytics


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add(User(id=1, username="test_user"))
    session.add(UserProfile(
        user_id=1, name="Test", age=25, sex="male", height_cm=175, weight_kg=70,
        activity_level="moderate", goal="maintain", target_weight_kg=70,
    ))
    session.commit()

    yield session
    session.close()


def test_daily_nutrition_totals_sum_multiple_entries(db_session):
    today = date.today()
    db_session.add_all([
        NutritionLog(user_id=1, log_date=today, meal_name="Breakfast", calories=500, protein_g=30, carbs_g=60, fats_g=15),
        NutritionLog(user_id=1, log_date=today, meal_name="Lunch", calories=700, protein_g=40, carbs_g=80, fats_g=20),
    ])
    db_session.commit()

    totals = rq.get_daily_nutrition_totals(db_session, user_id=1, log_date=today)

    assert totals["total_calories"] == 1200
    assert totals["total_protein_g"] == 70


def test_water_tracked_separately_and_sums_correctly(db_session):
    today = date.today()
    db_session.add_all([
        WaterLog(user_id=1, log_date=today, amount_ml=500),
        WaterLog(user_id=1, log_date=today, amount_ml=750),
    ])
    db_session.commit()

    total = rq.get_daily_water_total(db_session, user_id=1, log_date=today)
    assert total == 1250


def test_today_summary_uses_calculated_profile_targets(db_session):
    """Calorie target should come from BMR/TDEE calc, not a hardcoded default,
    once a profile exists."""
    today = date.today()
    db_session.add(NutritionLog(user_id=1, log_date=today, meal_name="Meal",
                                 calories=2000, protein_g=100, carbs_g=200, fats_g=60))
    db_session.commit()

    summary = analytics.get_today_summary(db_session, user_id=1)

    assert summary["calories"] == 2000
    # target should be a real calculated number, not the DEFAULT_CALORIE_TARGET fallback
    from utils import health_calc
    expected_targets = health_calc.get_full_health_targets(
        age=25, sex="male", height_cm=175, weight_kg=70,
        activity_level="moderate", goal="maintain", target_weight_kg=70, weekly_goal_kg=0.5,
    )
    assert summary["calorie_target"] == expected_targets["calorie_target"]
    assert summary["calorie_diff"] == 2000 - expected_targets["calorie_target"]


def test_weight_rolling_average_true_calendar_window(db_session):
    """
    Verifies the rolling average is a TRUE calendar-day window, not a
    row-based one: logging on non-consecutive days should NOT be averaged
    together if they fall outside the 7-calendar-day range.
    """
    today = date.today()
    # Day 0 and day 10 (10 days apart) — should NOT be in each other's window
    db_session.add(BodyMetric(user_id=1, log_date=today - timedelta(days=10), weight_kg=80.0))
    db_session.add(BodyMetric(user_id=1, log_date=today, weight_kg=70.0))
    db_session.commit()

    trend = rq.get_weight_trend(db_session, user_id=1)
    assert len(trend) == 2
    # Each entry's rolling average should just be itself, since they are
    # 10 calendar days apart (outside the 7-day window) even though they
    # are only 2 ROWS apart.
    assert trend[0]["rolling_avg_weight"] == 80.0
    assert trend[1]["rolling_avg_weight"] == 70.0


def test_weight_rolling_average_averages_within_calendar_window(db_session):
    today = date.today()
    weights = [70.0, 72.0, 74.0]
    for i, w in enumerate(weights):
        db_session.add(BodyMetric(user_id=1, log_date=today - timedelta(days=2 - i), weight_kg=w))
    db_session.commit()

    trend = rq.get_weight_trend(db_session, user_id=1)
    assert len(trend) == 3
    assert trend[-1]["rolling_avg_weight"] == 72.0
    assert trend[0]["rolling_avg_weight"] == 70.0


def test_workout_consistency_counts_per_week(db_session):
    monday = date.today() - timedelta(days=date.today().weekday())
    for i in range(3):
        db_session.add(Workout(user_id=1, workout_date=monday + timedelta(days=i),
                                type="Strength", duration_minutes=30))
    db_session.commit()

    consistency = rq.get_workout_consistency(db_session, user_id=1)
    assert len(consistency) == 1
    assert consistency[0]["workout_count"] == 3
    assert consistency[0]["total_minutes"] == 90


def test_full_summary_handles_empty_data_gracefully(db_session):
    summary = analytics.get_full_summary(db_session, user_id=1)
    assert summary["calories_today"] == 0
    assert summary["latest_weight"] is None
    assert summary["workouts_this_week"] == 0


def test_weight_progress_percent_for_loss_goal(db_session):
    """Starting 80kg, target 70kg, current 75kg -> 50% progress."""
    today = date.today()
    profile = db_session.query(UserProfile).filter_by(user_id=1).first()
    profile.target_weight_kg = 70.0
    db_session.add(BodyMetric(user_id=1, log_date=today - timedelta(days=10), weight_kg=80.0))
    db_session.add(BodyMetric(user_id=1, log_date=today, weight_kg=75.0))
    db_session.commit()

    progress = analytics.get_weight_progress(db_session, user_id=1)
    assert progress["progress_pct"] == 50.0


def test_adaptive_maintenance_estimate_requires_enough_data(db_session):
    """With too little history, the adaptive estimate must say so, not fabricate a number."""
    result = analytics.estimate_observed_maintenance(db_session, user_id=1)
    assert result["available"] is False
    assert "message" in result


def test_calorie_target_no_universal_1200_floor():
    """
    Regression test for the spec requirement: no universal 1200 kcal
    floor should be silently applied. An aggressive deficit should be
    allowed through with a warning, not clamped to exactly 1200.
    """
    from utils import health_calc
    # A small, low-activity female with an aggressive weekly loss goal
    target = health_calc.calculate_calorie_target(tdee=1400, goal="lose", weekly_goal_kg=1.0)
    # 1400 - (1*7700/7) = 1400 - 1100 = 300 (deliberately not floored at 1200)
    assert target == 300
    warning = health_calc.calorie_target_warning(target, tdee=1400, sex="female")
    assert warning is not None
