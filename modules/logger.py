import logging
import sys
from typing import Optional


def get_logger(name: str = "APP", level: int = logging.DEBUG) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name (str): Logger name
        level (int): Logging level

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger


class UvicornFilter(logging.Filter):
    """Filter to suppress uvicorn access logs for health checks."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        # Filter out ping/health check requests
        if "/ping" in message or "/health" in message:
            return False
        return True


def configure_uvicorn_filter():
    """Configure uvicorn logging filters."""
    # Get uvicorn loggers
    access_logger = logging.getLogger("uvicorn.access")
    error_logger = logging.getLogger("uvicorn.error")

    # Add filter to suppress health check logs
    health_filter = UvicornFilter()
    access_logger.addFilter(health_filter)

    return access_logger, error_logger
