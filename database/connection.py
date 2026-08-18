"""
SQLAlchemy engine + session management.

This is the single place the rest of the app gets a DB connection from.
Modules should import `get_session` or `engine` from here, never create
their own engine.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL, DATA_DIR

# Make sure the data/ folder exists before SQLite tries to create the file
os.makedirs(DATA_DIR, exist_ok=True)

_is_sqlite = DATABASE_URL.startswith("sqlite")

# check_same_thread=False is required for SQLite only (Streamlit multi-thread).
# PostgreSQL drivers do NOT accept this argument.
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    # pool_pre_ping sends a lightweight "SELECT 1" before handing a connection
    # to the app, silently replacing stale ones.  Essential for Neon's free
    # tier which scales to zero between requests.
    pool_pre_ping=True,
)

# ── Neon / PgBouncer prepared-statement fix ───────────────────────────────────
# psycopg2 >= 2.9 caches server-side prepared statements by default
# (prepare_threshold = 5).  Neon's connection pooler (PgBouncer in transaction
# mode) does NOT persist prepared statements across transactions, which causes:
#   "ERROR: prepared statement '...' already exists" / OperationalError
#
# The correct fix is to set prepare_threshold = None (disable prepared
# statements) on each fresh connection via an event listener.
# IMPORTANT: this CANNOT be passed via connect_args — psycopg2 rejects
# unknown keys in make_dsn() / parse_dsn() with ProgrammingError.
if not _is_sqlite:
    @event.listens_for(engine, "connect")
    def _disable_prepared_statements(dbapi_connection, connection_record):
        try:
            # None = never prepare; 0 = prepare immediately (not what we want)
            dbapi_connection.prepare_threshold = None
        except AttributeError:
            pass  # psycopg2 < 2.9 — no prepared statement management needed


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    """Return a new SQLAlchemy session. Caller is responsible for closing it."""
    return SessionLocal()
