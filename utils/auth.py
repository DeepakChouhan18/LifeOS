"""
utils/auth.py — Secure multi-user authentication for LifeOS.

Responsibilities:
  - Password hashing & verification (bcrypt)
  - User creation (signup) with duplicate-email detection
  - Authentication (login) with timing-safe comparison
  - Session state management (login_user / logout_user)
  - Current user helpers (get_current_user_id, is_authenticated)
  - Legacy data migration: first registered user may claim DEFAULT_USER_ID data

SECURITY:
  - Passwords are NEVER stored in plaintext. Only the bcrypt hash is persisted.
  - The password hash is NEVER stored in Streamlit session_state.
  - Data isolation is enforced at the query level (all CRUD / SQL use user_id).
  - Email addresses are lowercased and stripped before storage/lookup.
"""

import bcrypt
import streamlit as st
from sqlalchemy.orm import Session as OrmSession

from database.models import User, UserProfile
from config import DEFAULT_USER_ID


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """
    Returns a bcrypt hash of the given plaintext password.
    Uses work factor 12 (balances speed vs. brute-force resistance).
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Timing-safe comparison of a plaintext password against a stored bcrypt hash.
    Returns True if they match.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# User creation / signup
# ---------------------------------------------------------------------------

def signup_user(
    session: OrmSession,
    email: str,
    password: str,
    display_name: str,
    claim_legacy_data: bool = False,
) -> tuple[bool, str, "User | None"]:
    """
    Creates a new authenticated user account.

    Args:
        session:            SQLAlchemy session
        email:              User's email address (normalized to lowercase)
        password:           Plaintext password (never stored)
        display_name:       Name shown in UI
        claim_legacy_data:  If True AND DEFAULT_USER_ID row exists without an
                            email/password, claim that row as this new user
                            (preserving all their existing logged data).

    Returns:
        (success: bool, message: str, user: User | None)
    """
    email = email.strip().lower()
    display_name = display_name.strip()

    if not email or "@" not in email:
        return False, "Please enter a valid email address.", None

    if len(password) < 8:
        return False, "Password must be at least 8 characters.", None

    if not display_name:
        return False, "Please enter your name.", None

    # Check for duplicate email
    existing = session.query(User).filter(
        User.email == email
    ).first()
    if existing:
        return False, "An account with this email already exists. Please sign in.", None

    pw_hash = hash_password(password)

    # If claim_legacy_data=True and DEFAULT_USER_ID has no email set, claim it.
    legacy_user = session.get(User, DEFAULT_USER_ID)
    if claim_legacy_data and legacy_user and not legacy_user.email:
        legacy_user.email = email
        legacy_user.display_name = display_name
        legacy_user.password_hash = pw_hash
        legacy_user.is_active = True
        session.commit()
        return True, "Account created. Your existing data has been linked to this account.", legacy_user

    # Create a fresh new user
    new_user = User(
        display_name=display_name,
        email=email,
        password_hash=pw_hash,
        is_active=True,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return True, "Account created successfully.", new_user


# ---------------------------------------------------------------------------
# Authentication / login
# ---------------------------------------------------------------------------

def authenticate_user(
    session: OrmSession,
    email: str,
    password: str,
) -> "User | None":
    """
    Validates credentials. Returns the User object on success, None on failure.
    Uses timing-safe comparison to prevent user-enumeration timing attacks.
    """
    email = email.strip().lower()
    user = session.query(User).filter(
        User.email == email,
        User.is_active == True,  # noqa: E712
    ).first()

    if not user or not user.password_hash:
        # Run a dummy hash comparison to prevent timing-based user enumeration
        bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt(4)))
        return None

    if verify_password(password, user.password_hash):
        return user
    return None


# ---------------------------------------------------------------------------
# Session state management
# ---------------------------------------------------------------------------

def login_user(user: User) -> None:
    """
    Stores authentication state in Streamlit session_state.
    NEVER stores the password hash.
    """
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user.id
    st.session_state["display_name"] = user.display_name or user.email or "User"
    st.session_state["user_email"] = user.email or ""
    # Reset page to Dashboard after login
    st.session_state["page"] = "Dashboard"


def logout_user() -> None:
    """
    Clears all authentication-related state from session.
    After this, the app will redirect to the login screen.
    """
    keys_to_clear = [
        "authenticated", "user_id", "display_name", "user_email", "page",
        "onboarding_choice",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def is_authenticated() -> bool:
    """Returns True if the current session has a valid authenticated user."""
    return bool(st.session_state.get("authenticated") and st.session_state.get("user_id"))


def get_current_user_id() -> int | None:
    """Returns the authenticated user's ID, or None if not authenticated."""
    return st.session_state.get("user_id")


def get_current_user(session: OrmSession) -> "User | None":
    """Returns the full User ORM object for the authenticated session user."""
    uid = get_current_user_id()
    if uid is None:
        return None
    return session.get(User, uid)


def get_current_display_name() -> str:
    """Returns the display name for the authenticated user."""
    return st.session_state.get("display_name", "Friend")


def get_current_email() -> str:
    """Returns the email for the authenticated session user."""
    return st.session_state.get("user_email", "")


def require_login() -> bool:
    """
    Call at the top of any protected page. Returns True if authenticated.
    Use it defensively:
        if not auth.require_login():
            return
    The actual redirect is handled in app.py routing — this is just a guard.
    """
    return is_authenticated()
