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

# check_same_thread=False is required for SQLite when Streamlit accesses the
# connection from a different thread than the one that created it.
# PostgreSQL drivers do NOT accept this argument, so we only pass it for SQLite.
_is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    """Return a new SQLAlchemy session. Caller is responsible for closing it."""
    return SessionLocal()
