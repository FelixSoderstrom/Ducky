from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base


def init_db(database_url: str = "sqlite:///ducky.db"):
    """Initialize the database and create all tables."""
    engine = create_engine(database_url, echo=True)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session factory
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    return engine, SessionLocal


def get_session(SessionLocal):
    """Get a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
