"""
Unit tests for utils/health_calc.py.

Tests BMR (Mifflin-St Jeor equation), TDEE, BMI, calorie targets, and protein targets,
including male/female differences and edge cases.
"""

import pytest
from utils import health_calc


def test_bmr_male_calculation():
    # 25 yr old male, 180 cm, 75 kg
    # BMR = (10 * 75) + (6.25 * 180) - (5 * 25) + 5
    # BMR = 750 + 1125 - 125 + 5 = 1755.0
    bmr = health_calc.calculate_bmr(age=25, sex="male", height_cm=180, weight_kg=75)
    assert bmr == 1755.0


def test_bmr_female_calculation():
    # 25 yr old female, 165 cm, 60 kg
    # BMR = (10 * 60) + (6.25 * 165) - (5 * 25) - 161
    # BMR = 600 + 1031.25 - 125 - 161 = 1345.25 -> 1345.2
    bmr = health_calc.calculate_bmr(age=25, sex="female", height_cm=165, weight_kg=60)
    assert bmr == 1345.2


def test_tdee_calculation():
    bmr = 1600.0
    # Sedentary (1.2)
    assert health_calc.calculate_tdee(bmr, "sedentary") == 1920.0
    # Moderate (1.55)
    assert health_calc.calculate_tdee(bmr, "moderate") == 2480.0


def test_bmi_calculation():
    # 70 kg, 175 cm (1.75m)
    # BMI = 70 / (1.75^2) = 70 / 3.0625 = 22.857... -> 22.9
    bmi = health_calc.calculate_bmi(height_cm=175, weight_kg=70)
    assert bmi == 22.9
    assert health_calc.bmi_category(bmi) == "Normal"


def test_calorie_target_adjustments():
    tdee = 2400.0
    # Weight loss (0.5 kg/week deficit = 550 kcal/day) -> 1850 kcal
    loss_target = health_calc.calculate_calorie_target(tdee, goal="lose", weekly_goal_kg=0.5)
    assert loss_target == 1850

    # Maintain -> 2400 kcal
    maint_target = health_calc.calculate_calorie_target(tdee, goal="maintain")
    assert maint_target == 2400

    # Weight gain (0.5 kg/week surplus = 550 kcal/day) -> 2950 kcal
    gain_target = health_calc.calculate_calorie_target(tdee, goal="gain", weekly_goal_kg=0.5)
    assert gain_target == 2950


def test_protein_target_calculation():
    # 70 kg, moderate activity (1.6 g/kg) -> 112 g
    protein = health_calc.calculate_protein_target(weight_kg=70, activity_level="moderate")
    assert protein == 112


def test_invalid_health_inputs_raise_error():
    with pytest.raises(ValueError):
        health_calc.calculate_bmr(age=-5, sex="male", height_cm=170, weight_kg=70)

    with pytest.raises(ValueError):
        health_calc.calculate_tdee(bmr=1500, activity_level="invalid_activity")
