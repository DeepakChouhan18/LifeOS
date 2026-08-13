"""
All SQLAlchemy ORM models for LifeOS.

Design decisions worth knowing:
- Money fields use Numeric(10, 2), not Float, to avoid floating-point
  rounding errors in financial totals.
- user_id and date columns are indexed (individually and as composites
  where they're queried together) since almost every query in this app
  filters by user_id + a date range.
- CheckConstraints enforce basic data sanity at the DB level (amounts
  and durations can't be negative) as a second line of defense behind
  the input validation in utils/validation.py.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Numeric, Boolean, Date, DateTime,
    ForeignKey, Index, CheckConstraint, UniqueConstraint, Text
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False)


class UserProfile(Base):
    """
    Persistent onboarding/settings data.

    Calculated targets (BMR, TDEE, calorie target, protein target, BMI)
    are recomputed from these fields on the fly (utils/health_calc.py) —
    never stored — so they're always consistent with the latest profile
    values. Only true preferences (study goal, budget) are stored directly.
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String, nullable=False)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    activity_level = Column(String, nullable=False)
    goal = Column(String, nullable=False)
    target_weight_kg = Column(Float, nullable=True)
    weekly_goal_kg = Column(Float, nullable=True, default=0.5)
    daily_study_goal_minutes = Column(Integer, default=300)
    monthly_budget = Column(Numeric(10, 2), nullable=True)
    score_weight_study = Column(Float, default=0.4)
    score_weight_health = Column(Float, default=0.35)
    score_weight_finance = Column(Float, default=0.25)
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="profile")

    __table_args__ = (
        CheckConstraint("age > 0 AND age < 120", name="ck_profile_age_range"),
        CheckConstraint("height_cm > 0", name="ck_profile_height_positive"),
        CheckConstraint("weight_kg > 0", name="ck_profile_weight_positive"),
    )


# ---------------- Study Module ----------------

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    color = Column(String, default="#4A90D9")

    tasks = relationship("StudyTask", back_populates="subject")
    sessions = relationship("StudySession", back_populates="subject")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_subject_user_name"),
    )


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    title = Column(String, nullable=False)
    priority = Column(String, default="medium")  # low / medium / high
    topic = Column(String, nullable=True)
    is_completed = Column(Boolean, default=False)
    due_date = Column(Date, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    subject = relationship("Subject", back_populates="tasks")

    __table_args__ = (
        Index("ix_study_tasks_user_due", "user_id", "due_date"),
    )


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    session_date = Column(Date, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False)
    topic = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    subject = relationship("Subject", back_populates="sessions")

    __table_args__ = (
        Index("ix_study_sessions_user_date", "user_id", "session_date"),
        CheckConstraint("duration_minutes > 0", name="ck_session_duration_positive"),
    )


# ---------------- Health & Fitness Module ----------------

class NutritionLog(Base):
    __tablename__ = "nutrition_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    logged_at = Column(DateTime, default=_utcnow)
    meal_name = Column(String, nullable=False)
    meal_type = Column(String, nullable=True)
    calories = Column(Integer, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fats_g = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_nutrition_user_date", "user_id", "log_date"),
        CheckConstraint("calories IS NULL OR calories >= 0", name="ck_nutrition_calories_nonneg"),
        CheckConstraint("protein_g IS NULL OR protein_g >= 0", name="ck_nutrition_protein_nonneg"),
    )


class WaterLog(Base):
    """Separate from NutritionLog so multiple water entries/day are easy to sum."""
    __tablename__ = "water_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    amount_ml = Column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_water_user_date", "user_id", "log_date"),
        CheckConstraint("amount_ml > 0", name="ck_water_amount_positive"),
    )


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workout_date = Column(Date, nullable=False, index=True)
    type = Column(String, nullable=True)
    exercise = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_workouts_user_date", "user_id", "workout_date"),
        CheckConstraint("duration_minutes IS NULL OR duration_minutes > 0", name="ck_workout_duration_positive"),
    )


class BodyMetric(Base):
    __tablename__ = "body_metrics"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    weight_kg = Column(Float, nullable=True)
    sleep_hours = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_body_metrics_user_date", "user_id", "log_date"),
        UniqueConstraint("user_id", "log_date", name="uq_body_metric_user_date"),
        CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="ck_weight_positive"),
        CheckConstraint("sleep_hours IS NULL OR (sleep_hours >= 0 AND sleep_hours <= 24)", name="ck_sleep_range"),
    )


# ---------------- Finance Module ----------------

class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)

    expenses = relationship("Expense", back_populates="category")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_category_user_name"),
    )


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    expense_date = Column(Date, nullable=False, index=True)
    description = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    category = relationship("ExpenseCategory", back_populates="expenses")

    __table_args__ = (
        Index("ix_expenses_user_date", "user_id", "expense_date"),
        CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
    )


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    month = Column(Date, nullable=False, index=True)
    limit_amount = Column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", name="uq_budget_user_cat_month"),
        CheckConstraint("limit_amount > 0", name="ck_budget_limit_positive"),
    )


# ---------------- ML Model Metadata ----------------

class MLModelMetadata(Base):
    """
    Tracks each training run: when, what kind of model, how much data,
    and the resulting evaluation metrics. Lets the Insights page show
    "last trained on X" instead of silently retraining every page load.
    """
    __tablename__ = "ml_model_metadata"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    model_type = Column(String, nullable=False)
    algorithm = Column(String, nullable=False)
    trained_at = Column(DateTime, default=_utcnow)
    n_samples = Column(Integer, nullable=True)
    n_features = Column(Integer, nullable=True)
    feature_names = Column(Text, nullable=True)
    data_period_start = Column(Date, nullable=True)
    data_period_end = Column(Date, nullable=True)
    metrics_json = Column(Text, nullable=True)
    status = Column(String, nullable=True)
