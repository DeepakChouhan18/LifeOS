"""
tests/test_config.py — DATABASE_URL resolution priority tests

Verifies that config._resolve_database_url() checks sources in the correct
order:
  1. DATABASE_URL environment variable   (highest priority)
  2. st.secrets["DATABASE_URL"]          (Streamlit Cloud secrets manager)
  3. SQLite fallback at data/lifeos.db   (local development only)

Also verifies "postgres://" → "postgresql://" normalisation for SQLAlchemy
compatibility in both the env-var and st.secrets paths.
"""

import os
import sys
import importlib
import types

import pytest

# Ensure the project root is on sys.path so we can import config directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_resolve(monkeypatch, env_url=None, secrets_url=None):
    """
    Call config._resolve_database_url() in isolation by:
    - Patching os.environ["DATABASE_URL"] (or removing it).
    - Injecting a fake `streamlit` module whose st.secrets.get() returns
      secrets_url (or "" if None).

    Returns the resolved DATABASE_URL string.
    """
    # --- environment variable ---
    if env_url is not None:
        monkeypatch.setenv("DATABASE_URL", env_url)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)

    # --- fake streamlit module ---
    fake_st = types.SimpleNamespace()
    fake_st.secrets = types.SimpleNamespace()
    fake_st.secrets.get = lambda key, default="": secrets_url if secrets_url else default

    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    # Re-import config fresh so _resolve_database_url sees the patched env.
    import config  # noqa: PLC0415
    importlib.reload(config)
    return config._resolve_database_url()


# ---------------------------------------------------------------------------
# Priority 1 — environment variable wins
# ---------------------------------------------------------------------------

class TestEnvVarPriority:
    def test_env_var_used_when_set(self, monkeypatch):
        url = _fresh_resolve(monkeypatch, env_url="postgresql://env-host/db")
        assert url == "postgresql://env-host/db"

    def test_env_var_beats_secrets(self, monkeypatch):
        """env var must win even when st.secrets also has a value."""
        url = _fresh_resolve(
            monkeypatch,
            env_url="postgresql://env-host/db",
            secrets_url="postgresql://secrets-host/db",
        )
        assert url == "postgresql://env-host/db"

    def test_postgres_scheme_normalised_in_env_var(self, monkeypatch):
        """'postgres://' from Heroku/Railway/Render must become 'postgresql://'."""
        url = _fresh_resolve(monkeypatch, env_url="postgres://user:pw@host:5432/db")
        assert url.startswith("postgresql://")
        assert "postgres://" not in url  # original scheme gone

    def test_postgresql_scheme_unchanged_in_env_var(self, monkeypatch):
        url = _fresh_resolve(monkeypatch, env_url="postgresql://user:pw@host/db")
        assert url == "postgresql://user:pw@host/db"


# ---------------------------------------------------------------------------
# Priority 2 — st.secrets (when no env var)
# ---------------------------------------------------------------------------

class TestSecretsPriority:
    def test_secrets_used_when_no_env_var(self, monkeypatch):
        url = _fresh_resolve(
            monkeypatch,
            env_url=None,
            secrets_url="postgresql://secrets-host/db",
        )
        assert url == "postgresql://secrets-host/db"

    def test_postgres_scheme_normalised_in_secrets(self, monkeypatch):
        url = _fresh_resolve(
            monkeypatch,
            env_url=None,
            secrets_url="postgres://user:pw@host:5432/db",
        )
        assert url.startswith("postgresql://")

    def test_secrets_beats_sqlite_fallback(self, monkeypatch):
        url = _fresh_resolve(
            monkeypatch,
            env_url=None,
            secrets_url="postgresql://secrets-host/db",
        )
        assert "sqlite" not in url


# ---------------------------------------------------------------------------
# Priority 3 — SQLite fallback
# ---------------------------------------------------------------------------

class TestSQLiteFallback:
    def test_sqlite_fallback_when_nothing_set(self, monkeypatch):
        url = _fresh_resolve(monkeypatch, env_url=None, secrets_url=None)
        assert url.startswith("sqlite:///")
        assert "lifeos.db" in url

    def test_sqlite_fallback_not_used_when_env_set(self, monkeypatch):
        url = _fresh_resolve(monkeypatch, env_url="postgresql://x/y")
        assert "sqlite" not in url

    def test_sqlite_fallback_not_used_when_secrets_set(self, monkeypatch):
        url = _fresh_resolve(monkeypatch, env_url=None, secrets_url="postgresql://x/y")
        assert "sqlite" not in url


# ---------------------------------------------------------------------------
# Resilience: broken st.secrets should not crash the app
# ---------------------------------------------------------------------------

class TestSecretsErrorHandling:
    def test_streamlit_import_error_falls_back_to_sqlite(self, monkeypatch):
        """If streamlit is not installed, we should gracefully fall back."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # Remove the fake streamlit so the import fails
        monkeypatch.delitem(sys.modules, "streamlit", raising=False)

        import config
        importlib.reload(config)
        url = config._resolve_database_url()
        # Without env var and without streamlit, must use SQLite
        assert url.startswith("sqlite:///")

    def test_secrets_exception_falls_back_to_sqlite(self, monkeypatch):
        """If st.secrets.get() raises, we should not crash — fall back to SQLite."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # Fake st whose .secrets.get() raises
        def _bad_get(key, default=""):
            raise RuntimeError("secrets file not found")

        fake_st = types.SimpleNamespace()
        fake_st.secrets = types.SimpleNamespace()
        fake_st.secrets.get = _bad_get
        monkeypatch.setitem(sys.modules, "streamlit", fake_st)

        import config
        importlib.reload(config)
        url = config._resolve_database_url()
        assert url.startswith("sqlite:///")
