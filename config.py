"""
Central config for LifeOS.
Keep DB paths, constants, and settings here so nothing is hardcoded
across modules.

DATABASE_URL priority (checked in order):
  1. DATABASE_URL environment variable  — highest priority; set for PostgreSQL in production.
  2. st.secrets["DATABASE_URL"]         — Streamlit Community Cloud secrets manager.
  3. SQLite fallback at data/lifeos.db  — local development ONLY; NOT safe for production.
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


def _resolve_database_url() -> str:
    """
    Resolve DATABASE_URL in priority order:

    1. DATABASE_URL environment variable (highest priority)
    2. st.secrets["DATABASE_URL"] — Streamlit Community Cloud secrets manager
    3. SQLite file fallback (local development only)

    "postgres://" is normalised to "postgresql://" for SQLAlchemy compatibility
    in both env-var and st.secrets paths.
    """
    # --- Priority 1: environment variable ---
    env_url = os.environ.get("DATABASE_URL", "").strip()
    if env_url:
        return env_url.replace("postgres://", "postgresql://", 1)

    # --- Priority 2: Streamlit secrets ---
    # st.secrets raises FileNotFoundError (or KeyError) when no secrets file
    # exists (e.g. during local development / pytest), so wrap defensively.
    try:
        import streamlit as st
        secrets_url = st.secrets.get("DATABASE_URL", "")
        if secrets_url:
            return secrets_url.replace("postgres://", "postgresql://", 1)
    except Exception:
        # Streamlit not installed, no secrets file present, or running outside
        # a Streamlit context — silently continue to the SQLite fallback.
        pass

    # --- Priority 3: SQLite fallback (LOCAL DEVELOPMENT ONLY) ---
    # ⚠️  WARNING: Streamlit Community Cloud's filesystem is EPHEMERAL.
    # Every app restart / redeploy / sleep cycle wipes the container disk,
    # which deletes data/lifeos.db and all user accounts stored in it.
    # Do NOT rely on this fallback in production.  Set DATABASE_URL to a
    # persistent PostgreSQL instance (e.g. Supabase, Neon, Railway) via
    # Streamlit Cloud's "Secrets" settings panel before going live.
    return f"sqlite:///{DB_PATH}"


DATABASE_URL = _resolve_database_url()

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
