"""SQLAlchemy database session lifecycle and connection pool management."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.database.base import Base

logger = get_logger(__name__)

# Connection pool configuration for PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency and context manager yielding a clean database session.
    Automatically rolls back uncommitted transactions on exception and closes session.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def create_tables_if_not_exist():
    """Initializes all registered SQLAlchemy tables in the database."""
    import backend.app.database.models  # Ensure all models are loaded
    Base.metadata.create_all(bind=engine)
