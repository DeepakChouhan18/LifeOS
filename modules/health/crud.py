"""
ORM-based CRUD operations for the Health & Fitness module.
Nutrition, water, workouts, body metrics — all with edit/delete and
input validation via utils/validation.py.
"""

from datetime import date
from database.models import NutritionLog, WaterLog, Workout, BodyMetric
from database import raw_queries as rq
from utils import validation


# --- Nutrition ---

def log_nutrition(
    session, user_id: int, meal_name: str, log_date: date = None,
    meal_type: str = None, calories: int = None, protein_g: float = None,
    carbs_g: float = None, fats_g: float = None,
) -> NutritionLog:
    validation.validate_nonempty_string(meal_name, "Food name")
    validation.validate_not_future_date(log_date, "Date")
    validation.validate_calories(calories)
    validation.validate_macro(protein_g, "Protein")
    validation.validate_macro(carbs_g, "Carbs")
    validation.validate_macro(fats_g, "Fats")

    entry = NutritionLog(
        user_id=user_id, log_date=log_date or date.today(),
        meal_name=meal_name.strip(), meal_type=meal_type or "Meal",
        calories=calories, protein_g=protein_g, carbs_g=carbs_g, fats_g=fats_g,
    )
    session.add(entry)
    session.commit()
    return entry


def duplicate_nutrition_log(session, log_id: int, new_log_date: date = None) -> NutritionLog:
    """Quickly re-logs a past food entry (e.g. yesterday's breakfast, today)."""
    original = session.get(NutritionLog, log_id)
    if not original:
        return None
    return log_nutrition(
        session, original.user_id, original.meal_name,
        new_log_date or date.today(), original.meal_type,
        original.calories, original.protein_g, original.carbs_g, original.fats_g,
    )


def update_nutrition_log(session, log_id: int, **kwargs) -> NutritionLog:
    entry = session.get(NutritionLog, log_id)
    if not entry:
        return None
    if "calories" in kwargs:
        validation.validate_calories(kwargs["calories"])
    if "protein_g" in kwargs:
        validation.validate_macro(kwargs["protein_g"], "Protein")
    for field in ("meal_name", "meal_type", "calories", "protein_g", "carbs_g", "fats_g", "log_date"):
        if field in kwargs and kwargs[field] is not None:
            setattr(entry, field, kwargs[field])
    session.commit()
    return entry


def delete_nutrition_log(session, log_id: int) -> bool:
    entry = session.get(NutritionLog, log_id)
    if entry:
        session.delete(entry)
        session.commit()
        return True
    return False


def list_nutrition_logs(session, user_id: int, log_date: date = None, limit: int = 200):
    query = session.query(NutritionLog).filter_by(user_id=user_id)
    if log_date:
        query = query.filter_by(log_date=log_date)
    return query.order_by(NutritionLog.log_date.desc(), NutritionLog.id.desc()).limit(limit).all()


def get_recent_foods(session, user_id: int, limit: int = 8):
    """Powers the 'Recent Foods' quick-add UI. See raw_queries.get_recent_foods."""
    return rq.get_recent_foods(session, user_id, limit)


# --- Water ---

def log_water(session, user_id: int, amount_ml: int, log_date: date = None) -> WaterLog:
    validation.validate_positive(amount_ml, "Water amount")
    validation.validate_not_future_date(log_date, "Date")
    entry = WaterLog(user_id=user_id, log_date=log_date or date.today(), amount_ml=amount_ml)
    session.add(entry)
    session.commit()
    return entry


def delete_water_log(session, log_id: int) -> bool:
    entry = session.get(WaterLog, log_id)
    if entry:
        session.delete(entry)
        session.commit()
        return True
    return False


def list_water_logs(session, user_id: int, log_date: date = None):
    query = session.query(WaterLog).filter_by(user_id=user_id)
    if log_date:
        query = query.filter_by(log_date=log_date)
    return query.order_by(WaterLog.log_date.desc()).all()


# --- Workouts ---

def log_workout(
    session, user_id: int, workout_date: date = None, type: str = None,
    exercise: str = None, duration_minutes: int = None, notes: str = None,
) -> Workout:
    validation.validate_not_future_date(workout_date, "Date")
    validation.validate_duration_minutes(duration_minutes, "Duration") if duration_minutes else None

    entry = Workout(
        user_id=user_id, workout_date=workout_date or date.today(),
        type=type, exercise=exercise, duration_minutes=duration_minutes, notes=notes,
    )
    session.add(entry)
    session.commit()
    return entry


def update_workout(session, workout_id: int, **kwargs) -> Workout:
    entry = session.get(Workout, workout_id)
    if not entry:
        return None
    for field in ("workout_date", "type", "exercise", "duration_minutes", "notes"):
        if field in kwargs and kwargs[field] is not None:
            setattr(entry, field, kwargs[field])
    session.commit()
    return entry


def delete_workout(session, workout_id: int) -> bool:
    entry = session.get(Workout, workout_id)
    if entry:
        session.delete(entry)
        session.commit()
        return True
    return False


def list_workouts(session, user_id: int, limit: int = 100):
    return (
        session.query(Workout).filter_by(user_id=user_id)
        .order_by(Workout.workout_date.desc()).limit(limit).all()
    )


def get_todays_workout(session, user_id: int, today: date = None):
    today = today or date.today()
    return session.query(Workout).filter_by(user_id=user_id, workout_date=today).first()


# --- Body Metrics ---

def log_body_metric(
    session, user_id: int, log_date: date = None,
    weight_kg: float = None, sleep_hours: float = None,
) -> BodyMetric:
    if weight_kg is not None:
        validation.validate_weight_kg(weight_kg)
    validation.validate_sleep_hours(sleep_hours)
    validation.validate_not_future_date(log_date, "Date")

    # If a metric for this date already exists, update it (unique constraint
    # on user_id+log_date) rather than raising an integrity error.
    entry = (
        session.query(BodyMetric)
        .filter_by(user_id=user_id, log_date=log_date or date.today())
        .first()
    )
    if entry:
        if weight_kg is not None:
            entry.weight_kg = weight_kg
        if sleep_hours is not None:
            entry.sleep_hours = sleep_hours
        session.commit()
        return entry

    entry = BodyMetric(
        user_id=user_id, log_date=log_date or date.today(),
        weight_kg=weight_kg, sleep_hours=sleep_hours,
    )
    session.add(entry)
    session.commit()
    return entry


def update_body_metric(session, metric_id: int, **kwargs) -> BodyMetric:
    entry = session.get(BodyMetric, metric_id)
    if not entry:
        return None
    if "weight_kg" in kwargs and kwargs["weight_kg"] is not None:
        validation.validate_weight_kg(kwargs["weight_kg"])
    for field in ("weight_kg", "sleep_hours", "log_date"):
        if field in kwargs and kwargs[field] is not None:
            setattr(entry, field, kwargs[field])
    session.commit()
    return entry


def delete_body_metric(session, metric_id: int) -> bool:
    entry = session.get(BodyMetric, metric_id)
    if entry:
        session.delete(entry)
        session.commit()
        return True
    return False


def list_body_metrics(session, user_id: int, limit: int = 200):
    return (
        session.query(BodyMetric).filter_by(user_id=user_id)
        .order_by(BodyMetric.log_date.desc()).limit(limit).all()
    )


def get_latest_weight(session, user_id: int):
    entry = (
        session.query(BodyMetric)
        .filter(BodyMetric.user_id == user_id, BodyMetric.weight_kg.isnot(None))
        .order_by(BodyMetric.log_date.desc())
        .first()
    )
    return entry.weight_kg if entry else None


def get_starting_weight(session, user_id: int):
    entry = (
        session.query(BodyMetric)
        .filter(BodyMetric.user_id == user_id, BodyMetric.weight_kg.isnot(None))
        .order_by(BodyMetric.log_date.asc())
        .first()
    )
    return entry.weight_kg if entry else None
