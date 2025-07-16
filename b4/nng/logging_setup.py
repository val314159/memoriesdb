#!/usr/bin/env python3
"""
logging_setup.py - Centralized logging configuration for MemoriesDB

Provides consistent logging setup across all modules.
"""

import logging
from config import DEBUG, LOG_FILE

def get_logger(name):
    """
    Configure and return a logger with consistent formatting
    
    Args:
        name: Name of the logger, typically __name__ from the calling module
        
    Returns:
        Configured logger instance
    """
    # Only configure root logger once
    if not logging.getLogger().handlers:
        # Configure basic logging
        log_level = logging.DEBUG if DEBUG else logging.INFO
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Set up console logging
        logging.basicConfig(
            level=log_level,
            format=log_format
        )
        
        # Add file logging if configured
        if LOG_FILE:
            try:
                file_handler = logging.FileHandler(LOG_FILE)
                file_handler.setFormatter(logging.Formatter(log_format))
                file_handler.setLevel(log_level)
                logging.getLogger().addHandler(file_handler)
                logging.info(f"File logging enabled: {LOG_FILE}")
            except Exception as e:
                logging.error(f"Failed to set up file logging: {e}")
    
    return logging.getLogger(name)
