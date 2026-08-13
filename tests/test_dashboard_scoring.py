"""
Tests for modules/dashboard/aggregator.py scoring functions.
Tests the pure scoring functions directly with known input dicts,
since they don't need a database.
"""

from modules.dashboard import aggregator


def test_study_score_full_marks_for_perfect_completion_and_streak():
    summary = {"completion_pct": 100.0, "current_streak": 10, "longest_streak": 10,
               "total_tasks": 5, "completed_tasks": 5, "total_study_hours": 20}
    score = aggregator._study_score(summary)
    assert score == 100.0


def test_study_score_zero_for_no_activity():
    summary = {"completion_pct": 0.0, "current_streak": 0, "longest_streak": 0,
               "total_tasks": 0, "completed_tasks": 0, "total_study_hours": 0}
    score = aggregator._study_score(summary)
    assert score == 0.0


def test_health_score_full_marks_at_target(): 
    summary = {"calories_today": 2200, "calorie_diff": 0, "protein_today": 130,
               "water_today": 2500, "latest_weight": 70.0, "workouts_this_week": 4}
    score = aggregator._health_score(summary)
    assert score == 100.0


def test_health_score_penalizes_large_calorie_overshoot():
    summary = {"calories_today": 3200, "calorie_diff": 1000, "protein_today": 130,
               "water_today": 2500, "latest_weight": 70.0, "workouts_this_week": 4}
    score = aggregator._health_score(summary)
    # calorie_component should be 0 (overshoot > 1000 kcal), workout component still full
    assert score == 50.0  # 0.5*100 (workout) + 0.5*0 (calories)


def test_finance_score_full_marks_within_budget():
    summary = {"total_spent_this_month": 500, "total_budget_this_month": 1000,
               "budget_remaining": 500, "transaction_count": 3}
    score = aggregator._finance_score(summary)
    assert score == 100.0


def test_finance_score_penalizes_overspend():
    summary = {"total_spent_this_month": 1500, "total_budget_this_month": 1000,
               "budget_remaining": -500, "transaction_count": 5}
    score = aggregator._finance_score(summary)
    assert score == 50.0  # 100 - 50% overspend


def test_finance_score_neutral_when_no_budget_set():
    summary = {"total_spent_this_month": 200, "total_budget_this_month": 0,
               "budget_remaining": 0, "transaction_count": 2}
    score = aggregator._finance_score(summary)
    assert score == 50.0
