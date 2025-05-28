import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_level: str = "INFO"):
    """Set up logging configuration for Ducky application."""
    
    # Create logs directory
    project_root = Path("C:/Users/felix/Desktop/Code/Egna projekt/Ducky")
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler with rotation
            logging.handlers.RotatingFileHandler(
                logs_dir / "ducky.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            ),
            # Error-only file handler
            logging.handlers.RotatingFileHandler(
                logs_dir / "errors.log",
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3,
                encoding='utf-8'
            )
        ]
    )
    
    # Set error handler to only log errors
    error_handler = logging.getLogger().handlers[-1]
    error_handler.setLevel(logging.ERROR)
    
    # Reduce SQLAlchemy verbosity
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized - Level: {log_level}") 