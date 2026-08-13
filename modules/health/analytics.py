"""
Health & Fitness module analytics.

Turns raw DB rows (database/raw_queries.py) and the user's profile
(utils/health_calc.py) into the metrics the Health page shows: today's
totals vs. calculated targets, weight progress, workout consistency,
7-day/30-day averages, and an optional adaptive maintenance estimate.
"""

from datetime import date, timedelta
import pandas as pd

from database import raw_queries as rq
from database.models import BodyMetric, NutritionLog
from utils import health_calc
from modules.settings import crud as settings_crud
from modules.health import crud as health_crud
from config import DEFAULT_CALORIE_TARGET, DEFAULT_PROTEIN_TARGET_G, DEFAULT_WATER_TARGET_ML

MIN_DAYS_FOR_ADAPTIVE_ESTIMATE = 21  # need real history before trusting an observed estimate


def get_user_health_targets(session, user_id: int) -> dict:
    """Retrieves the profile and computes health targets (BMR, TDEE, targets, BMI)."""
    profile = settings_crud.get_user_profile(session, user_id)
    if profile:
        return health_calc.get_full_health_targets(
            age=profile.age, sex=profile.sex, height_cm=profile.height_cm,
            weight_kg=profile.weight_kg, activity_level=profile.activity_level,
            goal=profile.goal, target_weight_kg=profile.target_weight_kg,
            weekly_goal_kg=profile.weekly_goal_kg or 0.5,
        )
    return {
        "bmr": None, "tdee": None, "bmi": None, "bmi_category": None,
        "calorie_target": DEFAULT_CALORIE_TARGET, "protein_target": DEFAULT_PROTEIN_TARGET_G,
        "weight_kg": None, "target_weight_kg": None, "goal": "maintain", "calorie_warning": None,
    }


def get_today_summary(session, user_id: int) -> dict:
    """Today's nutrition/water totals vs. the user's calculated targets."""
    targets = get_user_health_targets(session, user_id)
    totals = rq.get_daily_nutrition_totals(session, user_id, date.today())
    water_ml = rq.get_daily_water_total(session, user_id, date.today())

    calories = totals.get("total_calories") or 0
    protein = totals.get("total_protein_g") or 0
    carbs = totals.get("total_carbs_g") or 0
    fats = totals.get("total_fats_g") or 0

    cal_target = targets["calorie_target"]
    prot_target = targets["protein_target"]

    todays_workout = health_crud.get_todays_workout(session, user_id)

    return {
        "calories": calories, "calorie_target": cal_target,
        "calories_remaining": (cal_target - calories) if cal_target else None,
        "calorie_diff": (calories - cal_target) if cal_target else None,
        "protein_g": protein, "protein_target_g": prot_target,
        "protein_remaining_g": max(0.0, prot_target - protein) if prot_target else None,
        "carbs_g": carbs, "fats_g": fats,
        "water_ml": water_ml, "water_target_ml": DEFAULT_WATER_TARGET_ML,
        "bmr": targets["bmr"], "tdee": targets["tdee"],
        "bmi": targets["bmi"], "bmi_category": targets["bmi_category"],
        "weight_kg": targets["weight_kg"], "target_weight_kg": targets["target_weight_kg"],
        "goal": targets["goal"], "calorie_warning": targets.get("calorie_warning"),
        "workout_completed_today": todays_workout is not None,
    }


def get_weekly_nutrition_df(session, user_id: int) -> pd.DataFrame:
    return pd.DataFrame(rq.get_weekly_nutrition_averages(session, user_id))


def get_weight_trend_df(session, user_id: int) -> pd.DataFrame:
    df = pd.DataFrame(rq.get_weight_trend(session, user_id))
    if not df.empty:
        df["log_date"] = pd.to_datetime(df["log_date"])
    return df


def get_workout_consistency_df(session, user_id: int) -> pd.DataFrame:
    return pd.DataFrame(rq.get_workout_consistency(session, user_id))


def get_weight_progress(session, user_id: int) -> dict:
    """
    Computes starting weight, current weight, target weight, and %
    progress toward the goal. Handles both weight-loss and weight-gain
    goals (progress direction differs).
    """
    profile = settings_crud.get_user_profile(session, user_id)
    starting = health_crud.get_starting_weight(session, user_id)
    current = health_crud.get_latest_weight(session, user_id)
    target = profile.target_weight_kg if profile else None

    if starting is None or current is None or target is None or starting == target:
        return {"starting": starting, "current": current, "target": target,
                "progress_pct": None, "change": None}

    total_needed = target - starting
    achieved = current - starting
    progress_pct = max(0.0, min(100.0, (achieved / total_needed) * 100)) if total_needed != 0 else 0.0

    return {
        "starting": starting, "current": current, "target": target,
        "progress_pct": round(progress_pct, 1),
        "change": round(current - starting, 1),
    }


def get_calorie_history_df(session, user_id: int, days: int = 30) -> pd.DataFrame:
    """Daily calorie/protein totals for the last N days, for averages and charts."""
    since = date.today() - timedelta(days=days)
    rows = (
        session.query(NutritionLog.log_date, NutritionLog.calories, NutritionLog.protein_g)
        .filter(NutritionLog.user_id == user_id, NutritionLog.log_date >= since)
        .all()
    )
    if not rows:
        return pd.DataFrame(columns=["log_date", "calories", "protein_g"])
    df = pd.DataFrame(rows, columns=["log_date", "calories", "protein_g"])
    daily = df.groupby("log_date").sum(numeric_only=True).reset_index()
    daily["log_date"] = pd.to_datetime(daily["log_date"])
    return daily.sort_values("log_date")


def get_calorie_averages(session, user_id: int) -> dict:
    """7-day and 30-day average calorie intake."""
    df30 = get_calorie_history_df(session, user_id, days=30)
    if df30.empty:
        return {"avg_7day": None, "avg_30day": None}

    df7 = df30[df30["log_date"] >= pd.Timestamp(date.today() - timedelta(days=7))]
    return {
        "avg_7day": round(df7["calories"].mean(), 0) if not df7.empty else None,
        "avg_30day": round(df30["calories"].mean(), 0) if not df30.empty else None,
    }


def get_target_consistency(session, user_id: int, days: int = 7) -> dict:
    """
    What fraction of the last N days had calorie intake within 10% of
    the target, and protein intake meeting the target.
    """
    targets = get_user_health_targets(session, user_id)
    cal_target = targets["calorie_target"]
    prot_target = targets["protein_target"]
    df = get_calorie_history_df(session, user_id, days=days)

    if df.empty or not cal_target:
        return {"calorie_consistency_pct": None, "protein_consistency_pct": None, "days_logged": 0}

    within_cal = (df["calories"].sub(cal_target).abs() <= cal_target * 0.10).sum()
    met_protein = (df["protein_g"] >= prot_target).sum() if prot_target else 0

    return {
        "calorie_consistency_pct": round((within_cal / len(df)) * 100, 0),
        "protein_consistency_pct": round((met_protein / len(df)) * 100, 0),
        "days_logged": len(df),
    }


def estimate_observed_maintenance(session, user_id: int) -> dict:
    """
    OPTIONAL / ADVANCED: adaptive maintenance estimate based on actual
    logged calorie intake and observed weight change, instead of just
    the formula-based TDEE.

    Formula: observed_maintenance = avg_daily_calories - (weight_change_kg * 7700 / days)
    (7700 kcal is the commonly cited approximate energy content of 1kg
    of body fat — a widely used but imprecise rule of thumb, not exact.)

    Deliberately requires MIN_DAYS_FOR_ADAPTIVE_ESTIMATE days of BOTH
    calorie and weight data before returning a number — with too little
    data the estimate is noise, not signal, so it explicitly says so
    instead of returning a falsely precise number.
    """
    since = date.today() - timedelta(days=MIN_DAYS_FOR_ADAPTIVE_ESTIMATE)

    weight_rows = (
        session.query(BodyMetric.log_date, BodyMetric.weight_kg)
        .filter(BodyMetric.user_id == user_id, BodyMetric.log_date >= since,
                BodyMetric.weight_kg.isnot(None))
        .order_by(BodyMetric.log_date)
        .all()
    )
    calorie_df = get_calorie_history_df(session, user_id, days=MIN_DAYS_FOR_ADAPTIVE_ESTIMATE)

    if len(weight_rows) < 2 or len(calorie_df) < MIN_DAYS_FOR_ADAPTIVE_ESTIMATE * 0.6:
        return {
            "available": False,
            "message": f"Need at least {MIN_DAYS_FOR_ADAPTIVE_ESTIMATE} days of consistent "
                       "weight AND calorie logging for an observed estimate. Keep logging daily.",
        }

    first_date, first_weight = weight_rows[0]
    last_date, last_weight = weight_rows[-1]
    days_span = (last_date - first_date).days
    if days_span < 7:
        return {"available": False, "message": "Not enough time span between weight entries yet."}

    weight_change_kg = last_weight - first_weight
    avg_daily_calories = calorie_df["calories"].mean()
    observed_maintenance = avg_daily_calories - (weight_change_kg * 7700 / days_span)

    return {
        "available": True,
        "observed_maintenance": round(observed_maintenance),
        "avg_daily_calories": round(avg_daily_calories),
        "weight_change_kg": round(weight_change_kg, 2),
        "days_span": days_span,
    }


def get_full_summary(session, user_id: int) -> dict:
    """One call that returns everything the Overview/dashboard needs."""
    today = get_today_summary(session, user_id)
    weight_progress = get_weight_progress(session, user_id)
    workout_df = get_workout_consistency_df(session, user_id)

    this_week_workouts = 0
    if not workout_df.empty:
        this_week_workouts = int(workout_df.iloc[-1]["workout_count"])

    return {
        "calories_today": today["calories"], "calorie_target": today["calorie_target"],
        "calories_remaining": today["calories_remaining"], "calorie_diff": today["calorie_diff"],
        "protein_today": today["protein_g"], "protein_target_g": today["protein_target_g"],
        "water_today": today["water_ml"], "water_target_ml": today["water_target_ml"],
        "latest_weight": weight_progress["current"], "starting_weight": weight_progress["starting"],
        "target_weight": weight_progress["target"], "weight_progress_pct": weight_progress["progress_pct"],
        "bmi": today["bmi"], "bmi_category": today["bmi_category"],
        "tdee": today["tdee"], "bmr": today["bmr"],
        "workouts_this_week": this_week_workouts,
        "workout_completed_today": today["workout_completed_today"],
        "calorie_warning": today["calorie_warning"],
    }
