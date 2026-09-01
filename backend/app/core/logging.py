import logging
import sys
from backend.app.core.config import settings


def setup_logging() -> None:
    """Configures centralized logging for the application."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )
    
    # Set log levels for noisy external libraries if needed
    logging.getLogger("uvicorn.access").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance with the specified name."""
    return logging.getLogger(name)
