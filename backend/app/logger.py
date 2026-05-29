import logging
import logging.handlers
import os
from app.config import get_settings


def setup_logging() -> logging.Logger:
    """Configure logging for production."""
    settings = get_settings()
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("enterprise_ka")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Format
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.FileHandler("logs/error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


logger = setup_logging()
