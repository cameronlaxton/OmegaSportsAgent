"""
Database connection management with SQLAlchemy.
Uses Replit's PostgreSQL database via DATABASE_URL environment variable.
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set. Create a PostgreSQL database in Replit.")

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@contextmanager
def get_db():
    """Context manager for database sessions with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection():
    """Verify database connection is working."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection successful")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


def create_all_tables():
    """Create all tables defined in models."""
    from src.db import models
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully")


def drop_all_tables():
    """Drop all tables (use with caution)."""
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped")
