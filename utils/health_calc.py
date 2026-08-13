"""
Health calculation utilities — BMR, TDEE, BMI, calorie/protein targets.

All formulas are well-documented with references.  These are pure
functions with no database dependency, making them easy to unit-test.

DISCLAIMER: These calculations are for informational/educational
purposes only and do not constitute medical advice.  Consult a
healthcare professional before making dietary changes.

References:
- BMR: Mifflin-St Jeor equation (1990)
  Mifflin MD, St Jeor ST, et al. "A new predictive equation for
  resting energy expenditure in healthy individuals."
  Am J Clin Nutr. 1990;51(2):241-247.

- TDEE: Activity multipliers commonly cited in exercise physiology
  literature (Harris-Benedict revision / ACSM guidelines).

- BMI: WHO standard formula (weight_kg / height_m^2).
"""

# Activity multipliers for TDEE = BMR × multiplier
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,        # little or no exercise
    "light": 1.375,          # light exercise 1-3 days/week
    "moderate": 1.55,        # moderate exercise 3-5 days/week
    "active": 1.725,         # hard exercise 6-7 days/week
    "very_active": 1.9,      # very hard exercise, physical job
}

ACTIVITY_LABELS = {
    "sedentary": "Sedentary (little or no exercise)",
    "light": "Lightly Active (1-3 days/week)",
    "moderate": "Moderately Active (3-5 days/week)",
    "active": "Active (6-7 days/week)",
    "very_active": "Very Active (hard exercise, physical job)",
}

# Calorie deficit/surplus per kg of body weight change per week
# ~7700 kcal ≈ 1 kg of body fat
KCAL_PER_KG = 7700


def calculate_bmr(age: int, sex: str, height_cm: float, weight_kg: float) -> float:
    """
    Basal Metabolic Rate using the Mifflin-St Jeor equation.

    Male:   BMR = (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + 5
    Female: BMR = (10 × weight_kg) + (6.25 × height_cm) - (5 × age) - 161

    Returns BMR in kcal/day.
    """
    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        raise ValueError("Weight, height, and age must be positive.")

    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)

    if sex.lower() == "male":
        return round(base + 5, 1)
    elif sex.lower() == "female":
        return round(base - 161, 1)
    else:
        raise ValueError(f"Sex must be 'male' or 'female', got '{sex}'.")


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """
    Total Daily Energy Expenditure = BMR × activity multiplier.

    Returns TDEE in kcal/day.
    """
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level.lower())
    if multiplier is None:
        raise ValueError(
            f"Unknown activity level '{activity_level}'. "
            f"Valid: {list(ACTIVITY_MULTIPLIERS.keys())}"
        )
    return round(bmr * multiplier, 1)


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """
    Body Mass Index = weight_kg / (height_m)^2.

    Returns BMI rounded to 1 decimal place.
    """
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be positive.")
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi: float) -> str:
    """Returns WHO BMI classification."""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25.0:
        return "Normal"
    elif bmi < 30.0:
        return "Overweight"
    else:
        return "Obese"


def calculate_calorie_target(
    tdee: float,
    goal: str,
    weekly_goal_kg: float = 0.5,
) -> int:
    """
    Suggested daily calorie target based on TDEE and goal.

    - lose:     TDEE - (weekly_goal_kg * KCAL_PER_KG / 7)
    - maintain: TDEE
    - gain:     TDEE + (weekly_goal_kg * KCAL_PER_KG / 7)

    Deliberately does NOT floor at a fixed value like 1200 kcal — there is
    no single "safe minimum" that applies to every person (it depends on
    sex, size, activity level, and medical history). Instead, see
    calorie_target_warning() below, which flags aggressive targets so the
    user can make an informed decision rather than hitting a silent,
    inaccurate universal floor.
    """
    daily_change = (weekly_goal_kg * KCAL_PER_KG) / 7.0

    goal_lower = goal.lower()
    if goal_lower == "lose":
        target = tdee - daily_change
    elif goal_lower == "maintain":
        target = tdee
    elif goal_lower == "gain":
        target = tdee + daily_change
    else:
        raise ValueError(f"Goal must be 'lose', 'maintain', or 'gain', got '{goal}'.")

    return round(target)


def calorie_target_warning(calorie_target: int, tdee: float, sex: str) -> str:
    """
    Returns an informational (not medical) warning string if the target
    looks aggressive, or None if it looks reasonable. This is intentionally
    NOT a hard block — the app doesn't diagnose or give medical advice,
    it just flags patterns worth being aware of.

    Thresholds referenced loosely from commonly cited general population
    guidance (e.g., NHS / ACSM commentary that very low intakes are
    harder to sustain and more likely to need medical supervision) —
    this is informational framing, not a personalized medical judgment.
    """
    deficit_pct = (tdee - calorie_target) / tdee if tdee > 0 else 0

    # A rough, commonly-cited floor for general adult populations —
    # presented as a heads-up, not an enforced limit.
    soft_floor = 1500 if sex.lower() == "male" else 1200

    if calorie_target < soft_floor:
        return (
            f"This target ({calorie_target} kcal) is below the commonly cited "
            f"general guidance floor (~{soft_floor} kcal for your profile). "
            "Very low intakes are harder to sustain and are often recommended "
            "only under medical supervision. This is informational, not "
            "medical advice — consider consulting a healthcare professional."
        )
    if deficit_pct > 0.35:
        return (
            f"This target is a {deficit_pct*100:.0f}% deficit from your estimated "
            "maintenance calories, which is considered aggressive. A more "
            "moderate deficit (10-25%) is generally easier to sustain."
        )
    return None


def calculate_protein_target(weight_kg: float, activity_level: str) -> int:
    """
    Suggested daily protein target (grams).

    Uses a range of 1.2–2.0 g/kg depending on activity level:
    - sedentary:   1.2 g/kg
    - light:       1.4 g/kg
    - moderate:    1.6 g/kg
    - active:      1.8 g/kg
    - very_active: 2.0 g/kg

    These are general recommendations for health-conscious individuals,
    not clinical nutrition advice.
    """
    protein_multipliers = {
        "sedentary": 1.2,
        "light": 1.4,
        "moderate": 1.6,
        "active": 1.8,
        "very_active": 2.0,
    }
    multiplier = protein_multipliers.get(activity_level.lower(), 1.6)
    return round(weight_kg * multiplier)


def get_full_health_targets(
    age: int, sex: str, height_cm: float, weight_kg: float,
    activity_level: str, goal: str, target_weight_kg: float = None,
    weekly_goal_kg: float = 0.5,
) -> dict:
    """
    One-call convenience: computes and returns all health metrics.

    Returns dict with: bmr, tdee, bmi, bmi_category, calorie_target,
    protein_target, weight_kg, target_weight_kg, goal.
    """
    bmr = calculate_bmr(age, sex, height_cm, weight_kg)
    tdee = calculate_tdee(bmr, activity_level)
    bmi = calculate_bmi(height_cm, weight_kg)
    cal_target = calculate_calorie_target(tdee, goal, weekly_goal_kg)
    protein = calculate_protein_target(weight_kg, activity_level)
    warning = calorie_target_warning(cal_target, tdee, sex)

    return {
        "bmr": bmr,
        "tdee": tdee,
        "bmi": bmi,
        "bmi_category": bmi_category(bmi),
        "calorie_target": cal_target,
        "protein_target": protein,
        "weight_kg": weight_kg,
        "target_weight_kg": target_weight_kg,
        "goal": goal,
        "calorie_warning": warning,
    }
