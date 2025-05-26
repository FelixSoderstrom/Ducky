from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from .models import Base, NotificationType


def init_notification_types(session):
    """Initialize the notification types table with default values."""
    notification_types = ["Voice", "Text", "Badge"]
    
    for type_name in notification_types:
        # Check if type already exists using SQLAlchemy 2.0 style
        stmt = select(NotificationType).where(NotificationType.name == type_name)
        existing = session.execute(stmt).scalar_one_or_none()
        
        if not existing:
            notification_type = NotificationType(name=type_name)
            session.add(notification_type)
    
    session.commit()


def init_db(database_url: str = "sqlite:///ducky.db"):
    """Initialize the database and create all tables."""
    engine = create_engine(database_url, echo=True)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session factory
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    # Initialize notification types
    session = SessionLocal()
    try:
        init_notification_types(session)
    finally:
        session.close()

    return engine, SessionLocal


def get_session(SessionLocal):
    """Get a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
