"""
CRUD operations for UserProfile and account-level settings/data management.
"""

from database.models import (
    UserProfile, User, StudySession, StudyTask, Subject,
    NutritionLog, WaterLog, Workout, BodyMetric,
    Expense, Budget, ExpenseCategory, MLModelMetadata,
)
from utils import validation


def get_user_profile(session, user_id: int) -> UserProfile:
    """Returns the UserProfile for user_id, or None if onboarding has not been completed."""
    return session.query(UserProfile).filter_by(user_id=user_id).first()


def save_user_profile(
    session, user_id: int, name: str, age: int, sex: str, height_cm: float,
    weight_kg: float, activity_level: str, goal: str, target_weight_kg: float = None,
    weekly_goal_kg: float = 0.5, daily_study_goal_minutes: int = 300,
    monthly_budget: float = None, is_demo: bool = False,
) -> UserProfile:
    """Creates or updates a user profile. Validates inputs before saving."""
    validation.validate_nonempty_string(name, "Name")
    validation.validate_age(age)
    validation.validate_height_cm(height_cm)
    validation.validate_weight_kg(weight_kg)
    if target_weight_kg is not None:
        validation.validate_weight_kg(target_weight_kg)

    user = session.get(User, user_id)
    if not user:
        user = User(id=user_id, username=f"user_{user_id}")
        session.add(user)
        session.commit()

    profile = session.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id, name=name, age=age, sex=sex,
                               height_cm=height_cm, weight_kg=weight_kg,
                               activity_level=activity_level, goal=goal, is_demo=is_demo)
        session.add(profile)

    profile.name = name
    profile.age = age
    profile.sex = sex
    profile.height_cm = height_cm
    profile.weight_kg = weight_kg
    profile.activity_level = activity_level
    profile.goal = goal
    profile.target_weight_kg = target_weight_kg
    profile.weekly_goal_kg = weekly_goal_kg or 0.5
    profile.daily_study_goal_minutes = daily_study_goal_minutes or 300
    profile.monthly_budget = monthly_budget

    session.commit()
    return profile


def update_score_weights(session, user_id: int, study: float, health: float, finance: float):
    """
    Updates the Personal Consistency Score weights. Must sum to ~1.0 —
    enforced here rather than just in the UI so any caller stays honest.
    """
    total = round(study + health + finance, 3)
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"Weights must sum to 1.0 (got {total}).")

    profile = session.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        raise ValueError("No profile exists yet.")

    profile.score_weight_study = study
    profile.score_weight_health = health
    profile.score_weight_finance = finance
    session.commit()
    return profile


def delete_all_user_data(session, user_id: int):
    """
    Deletes ALL logged data AND the profile for user_id (full reset).
    Used both for "reset demo data" (followed by re-seeding) and could be
    used for a genuine "delete my account" action.
    """
    session.query(StudySession).filter_by(user_id=user_id).delete()
    session.query(StudyTask).filter_by(user_id=user_id).delete()
    session.query(Subject).filter_by(user_id=user_id).delete()
    session.query(NutritionLog).filter_by(user_id=user_id).delete()
    session.query(WaterLog).filter_by(user_id=user_id).delete()
    session.query(Workout).filter_by(user_id=user_id).delete()
    session.query(BodyMetric).filter_by(user_id=user_id).delete()
    session.query(Expense).filter_by(user_id=user_id).delete()
    session.query(Budget).filter_by(user_id=user_id).delete()
    session.query(ExpenseCategory).filter_by(user_id=user_id).delete()
    session.query(MLModelMetadata).filter_by(user_id=user_id).delete()
    session.query(UserProfile).filter_by(user_id=user_id).delete()
    session.commit()


def reset_logged_data_keep_profile(session, user_id: int):
    """
    Clears all logged activity (study/health/finance records) but keeps
    the user's profile and categories/subjects intact. Used for "start
    over with my same profile" from Settings.
    """
    session.query(StudySession).filter_by(user_id=user_id).delete()
    session.query(StudyTask).filter_by(user_id=user_id).delete()
    session.query(NutritionLog).filter_by(user_id=user_id).delete()
    session.query(WaterLog).filter_by(user_id=user_id).delete()
    session.query(Workout).filter_by(user_id=user_id).delete()
    session.query(BodyMetric).filter_by(user_id=user_id).delete()
    session.query(Expense).filter_by(user_id=user_id).delete()
    session.query(MLModelMetadata).filter_by(user_id=user_id).delete()
    session.commit()
