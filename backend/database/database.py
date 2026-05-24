"""SQLite database engine, session factory, and lifecycle helpers."""
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import settings
from backend.logger import setup_logger

logger = setup_logger(__name__)

_db_path = Path(settings.db_path)
_db_path.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{_db_path.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after use.

    Yields:
        A SQLAlchemy Session bound to the configured engine.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all database tables defined on Base.metadata.

    This function is idempotent — existing tables are left untouched.
    """
    from backend.database import models  # noqa: F401  (register models on Base)

    logger.info("Initializing database at %s", DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialization complete")
