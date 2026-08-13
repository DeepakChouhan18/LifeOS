"""
Central config for LifeOS.
Keep DB paths, constants, and settings here so nothing is hardcoded
across modules.
"""

import os
from utils.health_calc import ACTIVITY_LABELS  # noqa: F401 (re-exported for convenience)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "lifeos.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Default single-user id until multi-user auth is added.
DEFAULT_USER_ID = 1

# Default categories / subjects offered during onboarding & first setup
DEFAULT_EXPENSE_CATEGORIES = [
    "Food", "Travel", "Education", "Shopping",
    "Entertainment", "Bills", "Other",
]
DEFAULT_SUBJECTS = ["DSA", "SQL", "Python", "Machine Learning", "Deep Learning"]

# Fallback health targets ONLY used if a profile somehow doesn't exist yet
# (should not normally happen once onboarding is complete).
DEFAULT_CALORIE_TARGET = 2200
DEFAULT_PROTEIN_TARGET_G = 130
DEFAULT_WATER_TARGET_ML = 2500

# Personal Consistency Score default weights (user-configurable in Settings —
# see UserProfile.score_weight_*). NOT presented as an objective "life score".
DEFAULT_SCORE_WEIGHTS = {"study": 0.4, "health": 0.35, "finance": 0.25}

# ML constants
ML_MODELS_DIR = os.path.join(BASE_DIR, "ml", "models")
WEEKLY_STUDY_GOAL_MINUTES_DEFAULT = 300  # fallback if profile has no goal set
MIN_WEEKS_FOR_SUPERVISED_EVAL = 6   # minimum weeks for a chronological train/test split
MIN_DAYS_FOR_CLUSTERING = 8

# App metadata
APP_NAME = "LifeOS"
APP_TAGLINE = "Personal Productivity, Health & Finance Analytics"
