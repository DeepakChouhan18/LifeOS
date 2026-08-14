"""
Creates all tables, migrates missing columns, and optionally seeds demo data.

Run directly: `python database/init_db.py` (creates tables + loads demo data)
Also called at app startup (via ensure_tables) to auto-create any
new tables/columns without requiring a manual migration step.

Demo data vs a fresh start are kept strictly separate (see Settings ->
onboarding "Start Fresh" / "Explore Demo Data"): demo-seeded profiles are
flagged is_demo=True so the app can label them and offer a one-click reset,
and a fresh user never has fake personal records inserted automatically.
"""

import os
import sys
import sqlite3
from datetime import date, timedelta, datetime, timezone
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine, get_session
from database.models import (
    Base, User, UserProfile, Subject, StudyTask, StudySession,
    NutritionLog, WaterLog, Workout, BodyMetric,
    ExpenseCategory, Expense, Budget, MLModelMetadata,
)
from config import DEFAULT_USER_ID, DEFAULT_EXPENSE_CATEGORIES, DEFAULT_SUBJECTS, DB_PATH

DEMO_USER_ID = DEFAULT_USER_ID


def create_tables():
    """Create all tables defined in models.py (safe to call repeatedly)."""
    Base.metadata.create_all(engine)
    migrate_columns()


def migrate_columns():
    """
    Auto-migrates new columns onto an existing SQLite database file.
    SQLite's ALTER TABLE ADD COLUMN is safe to attempt repeatedly —
    failures (column already exists) are silently ignored.
    """
    if not os.path.exists(DB_PATH):
        return

    columns_to_add = [
        ("study_tasks", "priority", "TEXT DEFAULT 'medium'"),
        ("study_tasks", "topic", "TEXT"),
        ("study_tasks", "created_at", "TEXT"),
        ("study_sessions", "topic", "TEXT"),
        ("study_sessions", "created_at", "TEXT"),
        ("nutrition_logs", "meal_name", "TEXT"),
        ("nutrition_logs", "meal_type", "TEXT"),
        ("nutrition_logs", "logged_at", "TEXT"),
        ("workouts", "exercise", "TEXT"),
        ("expenses", "payment_method", "TEXT"),
        ("expenses", "created_at", "TEXT"),
        ("user_profiles", "score_weight_study", "REAL DEFAULT 0.4"),
        ("user_profiles", "score_weight_health", "REAL DEFAULT 0.35"),
        ("user_profiles", "score_weight_finance", "REAL DEFAULT 0.25"),
        ("user_profiles", "is_demo", "INTEGER DEFAULT 0"),
        ("user_profiles", "created_at", "TEXT"),
        # Auth fields added for multi-user support
        ("users", "display_name", "TEXT"),
        ("users", "email", "TEXT"),
        ("users", "password_hash", "TEXT"),
        ("users", "is_active", "INTEGER DEFAULT 1"),
        ("users", "updated_at", "TEXT"),
    ]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for table, col, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass
    # Remove old UNIQUE constraint on username if it was blocking (safe to ignore if already gone)
    conn.commit()
    conn.close()


def ensure_tables():
    """Lightweight alias for app startup — creates missing tables/columns."""
    create_tables()


def ensure_default_user(session, user_id: int = DEFAULT_USER_ID, display_name: str = None) -> User:
    """Creates the base User row if missing. Does NOT create a profile —
    onboarding (or demo seeding) is responsible for that."""
    existing = session.get(User, user_id)
    if existing:
        return existing
    user = User(
        id=user_id,
        username=f"user_{user_id}",
        display_name=display_name or f"user_{user_id}",
    )
    session.add(user)
    session.commit()
    return user


def migrate_legacy_user_to_account(session, user_id: int, email: str, display_name: str, password_hash: str):
    """
    Claims the existing legacy user (DEFAULT_USER_ID) for a newly registered account.
    Sets email, display_name, and password_hash on the existing user row.
    Returns the updated User object.
    Called once when the first real account is registered and chooses to claim legacy data.
    """
    user = session.get(User, user_id)
    if not user:
        user = User(id=user_id)
        session.add(user)

    user.email = email
    user.display_name = display_name
    user.password_hash = password_hash
    user.is_active = True
    session.commit()
    return user



def ensure_default_categories_and_subjects(session, user_id: int = DEFAULT_USER_ID):
    """
    Creates the default expense categories and study subjects for a
    FRESH (non-demo) user, without adding any fake transactional data.
    Safe to call multiple times.
    """
    existing_cats = session.query(ExpenseCategory).filter_by(user_id=user_id).first()
    if not existing_cats:
        for name in DEFAULT_EXPENSE_CATEGORIES:
            session.add(ExpenseCategory(user_id=user_id, name=name))

    existing_subjects = session.query(Subject).filter_by(user_id=user_id).first()
    if not existing_subjects:
        colors = ["#6366f1", "#ec4899", "#14b8a6", "#f59e0b", "#8b5cf6"]
        for i, name in enumerate(DEFAULT_SUBJECTS):
            session.add(Subject(user_id=user_id, name=name, color=colors[i % len(colors)]))

    session.commit()


# =======================================================================
# DEMO DATA — clearly separated, flagged, and fully resettable.
# =======================================================================

def seed_demo_profile(session, user_id: int = DEMO_USER_ID) -> UserProfile:
    existing = session.query(UserProfile).filter_by(user_id=user_id).first()
    if existing:
        return existing

    profile = UserProfile(
        user_id=user_id, name="Demo User", age=22, sex="male",
        height_cm=175.0, weight_kg=72.0, activity_level="moderate", goal="lose",
        target_weight_kg=68.0, weekly_goal_kg=0.5,
        daily_study_goal_minutes=300, monthly_budget=15000.0,
        is_demo=True,
    )
    session.add(profile)
    session.commit()
    return profile


def seed_demo_study_data(session, user_id: int = DEMO_USER_ID):
    existing = session.query(StudySession).filter_by(user_id=user_id).first()
    if existing:
        return

    ensure_default_categories_and_subjects(session, user_id)
    subjects = session.query(Subject).filter_by(user_id=user_id).all()

    today = date.today()
    skip_days = {3, 7, 15, 22}
    for offset in range(34, -1, -1):
        if offset in skip_days:
            continue
        session_date = today - timedelta(days=offset)
        subject = random.choice(subjects)
        session.add(StudySession(
            user_id=user_id, subject_id=subject.id, session_date=session_date,
            duration_minutes=random.choice([25, 30, 45, 60, 90, 120]),
            topic=random.choice([None, "Basics", "Practice", "Revision", "Problems"]),
        ))

    task_data = [
        ("Solve 5 array problems", 0, "high", True, 2),
        ("Practice window functions", 1, "high", True, 1),
        ("Finish Streamlit dashboard notes", 2, "medium", False, 0),
        ("Read ML chapter on regularization", 3, "medium", False, 3),
        ("Implement binary search tree", 0, "high", True, 5),
        ("SQL joins practice set", 1, "low", True, 4),
        ("CNN architecture notes", 4, "medium", False, 2),
        ("Python decorators deep dive", 2, "low", False, 1),
    ]
    for title, subj_idx, priority, completed, days_ago in task_data:
        session.add(StudyTask(
            user_id=user_id, subject_id=subjects[subj_idx].id, title=title,
            priority=priority, is_completed=completed,
            due_date=today - timedelta(days=days_ago),
            completed_at=datetime.now(timezone.utc) - timedelta(days=days_ago) if completed else None,
        ))

    session.commit()


def seed_demo_health_data(session, user_id: int = DEMO_USER_ID):
    existing = session.query(NutritionLog).filter_by(user_id=user_id).first()
    if existing:
        return

    today = date.today()
    weight = 72.0
    meal_templates = [
        ("Oatmeal with banana", "Breakfast", 350, 12, 55, 8),
        ("Eggs & toast", "Breakfast", 420, 28, 30, 18),
        ("Chicken rice bowl", "Lunch", 650, 45, 70, 15),
        ("Dal rice", "Lunch", 550, 20, 80, 12),
        ("Paneer curry + roti", "Dinner", 600, 25, 50, 25),
        ("Grilled chicken salad", "Dinner", 450, 40, 15, 18),
        ("Protein shake", "Snack", 200, 30, 10, 5),
        ("Mixed nuts", "Snack", 180, 6, 8, 15),
    ]

    for offset in range(34, -1, -1):
        log_date = today - timedelta(days=offset)
        num_meals = random.randint(2, 4)
        daily_meals = random.sample(meal_templates, min(num_meals, len(meal_templates)))
        for meal_name, meal_type, cal, prot, carbs, fat in daily_meals:
            cal_var = random.randint(-50, 50)
            session.add(NutritionLog(
                user_id=user_id, log_date=log_date, meal_name=meal_name, meal_type=meal_type,
                calories=cal + cal_var,
                protein_g=round(prot + random.uniform(-5, 5), 1),
                carbs_g=round(carbs + random.uniform(-10, 10), 1),
                fats_g=round(fat + random.uniform(-3, 3), 1),
            ))

        session.add(WaterLog(user_id=user_id, log_date=log_date, amount_ml=random.randint(1500, 3000)))

        session.add(BodyMetric(
            user_id=user_id, log_date=log_date,
            weight_kg=round(weight, 1),
            sleep_hours=round(random.uniform(5.5, 8.5), 1),
        ))
        weight += random.uniform(-0.15, 0.1)

        if offset % 2 == 0:
            session.add(Workout(
                user_id=user_id, workout_date=log_date,
                type=random.choice(["Strength", "Cardio", "Yoga", "Sports"]),
                exercise=random.choice(["Bench Press", "5k Run", "Sun Salutations", "Full Body", "Squats"]),
                duration_minutes=random.choice([30, 45, 60]),
                notes=random.choice([None, "Felt great", "Moderate effort", "Tired"]),
            ))

    session.commit()


def seed_demo_finance_data(session, user_id: int = DEMO_USER_ID):
    existing = session.query(Expense).filter_by(user_id=user_id).first()
    if existing:
        return

    ensure_default_categories_and_subjects(session, user_id)
    categories = session.query(ExpenseCategory).filter_by(user_id=user_id).all()

    today = date.today()
    expense_templates = {
        "Food": [("Lunch", 150), ("Dinner", 200), ("Groceries", 500), ("Coffee", 80), ("Snacks", 60)],
        "Travel": [("Auto", 120), ("Metro", 40), ("Uber", 250), ("Bus", 30)],
        "Education": [("Books", 400), ("Course", 1000), ("Stationery", 150)],
        "Shopping": [("Clothes", 800), ("Electronics", 1500), ("Accessories", 300)],
        "Entertainment": [("Movie", 300), ("Games", 200), ("Subscription", 500)],
        "Bills": [("Phone recharge", 399), ("Internet", 600), ("Electricity", 800)],
        "Other": [("Misc", 100), ("Gift", 500)],
    }

    for offset in range(34, -1, -1):
        expense_date = today - timedelta(days=offset)
        for _ in range(random.randint(0, 3)):
            category = random.choice(categories)
            templates = expense_templates.get(category.name, [("Misc", 100)])
            desc, base_amount = random.choice(templates)
            amount = round(base_amount * random.uniform(0.7, 1.3), 2)
            session.add(Expense(
                user_id=user_id, category_id=category.id, amount=amount,
                expense_date=expense_date, description=desc,
                payment_method=random.choice(["UPI", "Cash", "Card", "UPI", "UPI"]),
            ))

    month_start = today.replace(day=1)
    budget_limits = {
        "Food": 6000, "Travel": 3000, "Shopping": 4000,
        "Education": 2000, "Entertainment": 1500, "Bills": 2000, "Other": 1000,
    }
    for category in categories:
        existing_budget = session.query(Budget).filter_by(
            user_id=user_id, category_id=category.id, month=month_start
        ).first()
        if not existing_budget:
            session.add(Budget(
                user_id=user_id, category_id=category.id, month=month_start,
                limit_amount=budget_limits.get(category.name, 2000),
            ))

    session.commit()


def seed_all_demo_data(session, user_id: int = DEMO_USER_ID):
    """Full demo dataset — profile + study + health + finance, all flagged as demo."""
    ensure_default_user(session, user_id)
    seed_demo_profile(session, user_id)
    seed_demo_study_data(session, user_id)
    seed_demo_health_data(session, user_id)
    seed_demo_finance_data(session, user_id)


def reset_demo_data(session, user_id: int = DEMO_USER_ID):
    """Wipes all logged data + profile for the demo user, then re-seeds fresh demo data."""
    from modules.settings import crud as settings_crud
    settings_crud.delete_all_user_data(session, user_id)
    seed_all_demo_data(session, user_id)


if __name__ == "__main__":
    create_tables()
    db = get_session()
    try:
        seed_all_demo_data(db)
        print("Demo data ready.")
    finally:
        db.close()
