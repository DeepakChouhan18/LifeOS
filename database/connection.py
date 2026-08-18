"""
SQLAlchemy engine + session management.

This is the single place the rest of the app gets a DB connection from.
Modules should import `get_session` or `engine` from here, never create
their own engine.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL, DATA_DIR

# Make sure the data/ folder exists before SQLite tries to create the file
os.makedirs(DATA_DIR, exist_ok=True)

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # check_same_thread=False is required for SQLite when Streamlit accesses
    # the connection from a different thread than the one that created it.
    _connect_args = {"check_same_thread": False}
else:
    # prepare_threshold=0 disables psycopg2's server-side prepared statement
    # cache.  Neon (and any PgBouncer pooler in transaction mode) does NOT
    # support session-persistent prepared statements — without this setting
    # every connection attempt raises OperationalError / "prepared statement
    # already exists".
    _connect_args = {"prepare_threshold": 0}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    # pool_pre_ping=True tests each pooled connection with a cheap SELECT 1
    # before handing it to the app.  This is essential for Neon's free tier
    # which scales to zero — a recycled connection may be stale after a cold
    # start, and pre-ping silently replaces it instead of crashing.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    """Return a new SQLAlchemy session. Caller is responsible for closing it."""
    return SessionLocal()
