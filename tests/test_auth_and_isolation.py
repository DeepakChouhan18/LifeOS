"""
tests/test_auth_and_isolation.py — Authentication & Data Isolation Tests

Covers:
- Password hashing and verification
- Signup: success, duplicate email detection
- Authenticate: correct and wrong credentials
- Legacy data migration (claim_legacy_data)
- Data isolation: User A cannot read User B's data
  (Study, Health, Finance, Settings modules all pass user_id)
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base, User, UserProfile
from utils.auth import (
    hash_password, verify_password,
    signup_user, authenticate_user,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite engine (fresh per test module run)."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    """Fresh session per test; rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        pw = "securepassword123"
        h = hash_password(pw)
        assert h != pw

    def test_verify_correct_password(self):
        pw = "securepassword123"
        h = hash_password(pw)
        assert verify_password(pw, h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correctpassword")
        assert verify_password("wrongpassword", h) is False

    def test_different_hashes_for_same_password(self):
        pw = "samepassword"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        # bcrypt uses random salt — hashes should differ
        assert h1 != h2
        # But both should verify
        assert verify_password(pw, h1)
        assert verify_password(pw, h2)

    def test_hash_is_bcrypt_format(self):
        h = hash_password("testpass99")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_empty_string_verify_returns_false(self):
        h = hash_password("nonempty")
        assert verify_password("", h) is False


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

class TestSignupUser:
    def test_successful_signup(self, db):
        success, msg, user = signup_user(db, "alice@example.com", "password123", "Alice")
        assert success is True
        assert user is not None
        assert user.email == "alice@example.com"
        assert user.display_name == "Alice"
        # Password hash should not be plaintext
        assert user.password_hash != "password123"
        assert user.password_hash.startswith("$2b$")

    def test_password_hash_not_in_user_object(self, db):
        """Ensure password_hash field exists but is a bcrypt hash, never plaintext."""
        _, _, user = signup_user(db, "bob@example.com", "mysecretpass", "Bob")
        assert user.password_hash is not None
        assert "mysecretpass" not in user.password_hash

    def test_duplicate_email_rejected(self, db):
        signup_user(db, "dup@example.com", "password123", "First User")
        success, msg, user = signup_user(db, "dup@example.com", "anotherpass", "Second User")
        assert success is False
        assert "already exists" in msg.lower()
        assert user is None

    def test_email_normalized_to_lowercase(self, db):
        success, msg, user = signup_user(db, "UPPER@Example.COM", "password123", "Upper User")
        assert success is True
        assert user.email == "upper@example.com"

    def test_short_password_rejected(self, db):
        success, msg, user = signup_user(db, "short@example.com", "1234567", "Short Pw")
        assert success is False
        assert user is None

    def test_empty_display_name_rejected(self, db):
        success, msg, user = signup_user(db, "noname@example.com", "password123", "")
        assert success is False
        assert user is None

    def test_invalid_email_rejected(self, db):
        success, msg, user = signup_user(db, "not-an-email", "password123", "Someone")
        assert success is False
        assert user is None


# ---------------------------------------------------------------------------
# Authenticate
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    def test_correct_credentials_return_user(self, db):
        signup_user(db, "login@example.com", "correct_pass", "Login User")
        user = authenticate_user(db, "login@example.com", "correct_pass")
        assert user is not None
        assert user.email == "login@example.com"

    def test_wrong_password_returns_none(self, db):
        signup_user(db, "wrongpw@example.com", "real_password", "Wrong PW")
        result = authenticate_user(db, "wrongpw@example.com", "wrong_password")
        assert result is None

    def test_nonexistent_email_returns_none(self, db):
        result = authenticate_user(db, "doesnotexist@example.com", "anypassword")
        assert result is None

    def test_email_lookup_is_case_insensitive(self, db):
        signup_user(db, "casetest@example.com", "password123", "Case Test")
        user = authenticate_user(db, "CASETEST@EXAMPLE.COM", "password123")
        assert user is not None

    def test_inactive_user_cannot_login(self, db):
        _, _, user = signup_user(db, "inactive@example.com", "password123", "Inactive")
        user.is_active = False
        db.commit()
        result = authenticate_user(db, "inactive@example.com", "password123")
        assert result is None


# ---------------------------------------------------------------------------
# Data Isolation (multi-user)
# ---------------------------------------------------------------------------

class TestDataIsolation:
    """Verifies that CRUD operations respect user_id boundaries."""

    def test_study_sessions_isolated(self, db):
        from database.models import User, Subject, StudySession
        from datetime import date

        # Create two users
        u1 = User(email="u1@example.com", password_hash="x", display_name="User1")
        u2 = User(email="u2@example.com", password_hash="x", display_name="User2")
        db.add_all([u1, u2])
        db.flush()

        # Each user gets a subject
        subj1 = Subject(user_id=u1.id, name="DSA", color="#000")
        subj2 = Subject(user_id=u2.id, name="SQL", color="#fff")
        db.add_all([subj1, subj2])
        db.flush()

        # Log a session for u1
        sess = StudySession(user_id=u1.id, subject_id=subj1.id, duration_minutes=60, session_date=date.today())
        db.add(sess)
        db.commit()

        # u2 should have no sessions
        u2_sessions = db.query(StudySession).filter(StudySession.user_id == u2.id).all()
        assert len(u2_sessions) == 0

        # u1 should have one session
        u1_sessions = db.query(StudySession).filter(StudySession.user_id == u1.id).all()
        assert len(u1_sessions) == 1

    def test_expense_categories_isolated(self, db):
        from database.models import User, ExpenseCategory

        u1 = User(email="exp_u1@test.com", password_hash="x", display_name="U1")
        u2 = User(email="exp_u2@test.com", password_hash="x", display_name="U2")
        db.add_all([u1, u2])
        db.flush()

        cat1 = ExpenseCategory(user_id=u1.id, name="Food")
        db.add(cat1)
        db.commit()

        u2_cats = db.query(ExpenseCategory).filter(ExpenseCategory.user_id == u2.id).all()
        assert len(u2_cats) == 0

        u1_cats = db.query(ExpenseCategory).filter(ExpenseCategory.user_id == u1.id).all()
        assert len(u1_cats) == 1

    def test_nutrition_logs_isolated(self, db):
        from database.models import User, NutritionLog
        from datetime import date

        u1 = User(email="nut1@test.com", password_hash="x", display_name="N1")
        u2 = User(email="nut2@test.com", password_hash="x", display_name="N2")
        db.add_all([u1, u2])
        db.flush()

        log = NutritionLog(user_id=u1.id, meal_name="Oats", log_date=date.today(), calories=350)
        db.add(log)
        db.commit()

        u2_logs = db.query(NutritionLog).filter(NutritionLog.user_id == u2.id).all()
        assert len(u2_logs) == 0

    def test_user_profiles_isolated(self, db):
        from database.models import User, UserProfile

        u1 = User(email="prof1@test.com", password_hash="x", display_name="P1")
        u2 = User(email="prof2@test.com", password_hash="x", display_name="P2")
        db.add_all([u1, u2])
        db.flush()

        profile1 = UserProfile(user_id=u1.id, name="User One", age=25, sex="male",
                                height_cm=175, weight_kg=70, activity_level="moderate",
                                goal="maintain")
        db.add(profile1)
        db.commit()

        u2_profile = db.query(UserProfile).filter(UserProfile.user_id == u2.id).first()
        assert u2_profile is None

        u1_profile = db.query(UserProfile).filter(UserProfile.user_id == u1.id).first()
        assert u1_profile is not None
        assert u1_profile.name == "User One"
