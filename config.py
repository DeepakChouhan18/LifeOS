"""
Central config for LifeOS.
Keep DB paths, constants, and settings here so nothing is hardcoded
across modules.

DATABASE_URL priority:
  1. DATABASE_URL environment variable (set this for PostgreSQL in production)
  2. STREAMLIT secrets (st.secrets) — used on Streamlit Cloud
  3. Fallback: SQLite file at data/lifeos.db (local development default)
"""

import os

# Try to load .env for local development (no-op if file absent or dotenv not installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.health_calc import ACTIVITY_LABELS  # noqa: F401 (re-exported for convenience)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "lifeos.db")

# DATABASE_URL: prefer env var (for PostgreSQL in production), else local SQLite
_env_db_url = os.environ.get("DATABASE_URL", "")
if _env_db_url:
    # Heroku / Railway / Render provide "postgres://..." — SQLAlchemy needs "postgresql://..."
    DATABASE_URL = _env_db_url.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

# DEFAULT_USER_ID: the legacy single-user id for backward compatibility.
# This user is created automatically on first launch and can be claimed
# by the first registered account (data migration path).
DEFAULT_USER_ID = 1

# DEMO_USER_ID: dedicated demo data user (separate from DEFAULT_USER_ID in
# multi-user mode so real users don't inherit demo data automatically).
# When running single-user (legacy) mode, DEMO_USER_ID == DEFAULT_USER_ID.
DEMO_USER_ID = DEFAULT_USER_ID

# Secret key for any session-level signing (not currently used for JWT,
# but good practice to have available as an env-configurable constant).
SECRET_KEY = os.environ.get("LIFEOS_SECRET_KEY", "dev-secret-change-in-production")

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
