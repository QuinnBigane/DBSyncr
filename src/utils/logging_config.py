"""
Logging configuration for UPS Data Manager
"""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime
from src.config.settings import settings


def setup_logging(
    log_level: str = None,
    log_format: str = None,
    log_dir: str = None
) -> logging.Logger:
    """Set up logging configuration."""
    
    # Use settings defaults if not provided
    log_level = log_level or settings.log_level
    log_format = log_format or settings.log_format
    log_dir = log_dir or settings.logs_dir
    
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("UPSDataManager")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = log_path / f"ups_data_manager_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_log_file = log_path / f"ups_data_manager_errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    if name:
        return logging.getLogger(f"UPSDataManager.{name}")
    return logging.getLogger("UPSDataManager")


# Setup default logger
default_logger = setup_logging()