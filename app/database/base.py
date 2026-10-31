"""
database/base.py

SQLAlchemy engine, session factory, and declarative base.
Uses standard robust SQLAlchemy session management compatible with SQLite and PostgreSQL.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Ensure the data directory exists before the engine connects ───────────────
def _resolve_db_url() -> str:
    """
    Converts DATABASE_URL for standard SQLAlchemy engine.
    Ensures local directory exists for SQLite, falling back to /tmp if read-only (e.g. Vercel).
    """
    import os
    url: str = settings.DATABASE_URL
    if url.startswith("sqlite+aiosqlite:///"):
        url = url.replace("sqlite+aiosqlite:///", "sqlite:///")
    if url.startswith("sqlite:///"):
        db_path_str = url.replace("sqlite:///", "")
        if os.getenv("VERCEL") and not db_path_str.startswith("/tmp"):
            db_path = Path("/tmp") / db_path_str.lstrip("./")
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
                return f"sqlite:///{db_path}"
            except Exception:
                pass
        db_path = Path(db_path_str)
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            db_path = Path("/tmp") / db_path.name
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path}"
        return f"sqlite:///{db_path_str}"
    return url


DATABASE_URL = _resolve_db_url()

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    pass


# ── Dependency for FastAPI DI ─────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a scoped DB session per request.
    Usage in router:
        db: Session = Depends(get_db)
    """
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def init_db() -> None:
    """
    Creates all tables defined in the ORM models and ensures schema migrations.
    Called once at application startup.
    """
    from app.database import models  # noqa: F401
    from sqlalchemy import inspect, text

    Base.metadata.create_all(bind=engine)

    # Lightweight schema migration for existing SQLite / Postgres tables
    try:
        inspector = inspect(engine)
        if "employees" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("employees")]
            with engine.begin() as conn:
                if "routine_work" not in columns:
                    conn.execute(text("ALTER TABLE employees ADD COLUMN routine_work TEXT"))
                    logger.info("Migrated employees table: added routine_work column")
                if "resume_filename" not in columns:
                    conn.execute(text("ALTER TABLE employees ADD COLUMN resume_filename VARCHAR(256)"))
                    logger.info("Migrated employees table: added resume_filename column")
                if "resume_text" not in columns:
                    conn.execute(text("ALTER TABLE employees ADD COLUMN resume_text TEXT"))
                    logger.info("Migrated employees table: added resume_text column")
    except Exception as mig_err:
        logger.warning("Auto-migration check notice: %s", mig_err)

    logger.info("Database tables initialised at: %s", DATABASE_URL)
