"""Centralized logging configuration for the Zomato RAG Chatbot."""

import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logger(
    name: str, 
    log_file: Optional[str] = None, 
    level: int = logging.INFO,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> logging.Logger:
    """Set up and return a logger with the given name and configuration.
    
    Args:
        name: Name for the logger
        log_file: Path to log file (if None, logs only to console)
        level: Logging level
        log_format: Log message format
    
    Returns:
        Configured logger object
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Create the default application logger
app_logger = setup_logger(
    "zomato_bot", 
    log_file="logs/application.log"
)
