from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session

from .init_db import init_db

# Initialize database and get session factory
engine, SessionLocal = init_db()

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get a database session using a context manager.
    
    Yields:
        Session: SQLAlchemy session instance
        
    Example:
        with get_db() as session:
            project = get_project_by_path(session, project_path)
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close() 