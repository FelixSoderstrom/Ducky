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
    
    # Reduce SQLAlchemy verbosity (set after basicConfig)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    
    # Reduce HTTP client verbosity
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized - Level: {log_level}")


def setup_code_review_logger():
    """Set up a separate logger specifically for code review pipeline."""
    
    # Create logs directory
    project_root = Path("C:/Users/felix/Desktop/Code/Egna projekt/Ducky")
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create code review logger
    cr_logger = logging.getLogger("code_review")
    cr_logger.setLevel(logging.INFO)
    
    # Prevent propagation to root logger to avoid duplicate entries
    cr_logger.propagate = False
    
    # Check if handler already exists to prevent duplicates
    if cr_logger.handlers:
        return cr_logger
    
    # Create specialized formatter for code review
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create file handler for code review
    handler = logging.handlers.RotatingFileHandler(
        logs_dir / "code_review.log",
        maxBytes=20 * 1024 * 1024,  # 20MB for detailed logs
        backupCount=10,
        encoding='utf-8'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    cr_logger.addHandler(handler)
    
    return cr_logger 