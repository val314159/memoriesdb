#!/usr/bin/env python3
"""
Test script to verify file logging functionality - improved version
"""

import os
import sys

# Force reload of config after setting env var
os.environ["LOG_FILE"] = "test.log"

# Make sure we're using our modified config
import config
print(f"LOG_FILE config value: {config.LOG_FILE}")

# Now import the logger
from logging_setup import get_logger

# Get a logger after setting the env var
logger = get_logger("test_script")

# Generate some test log messages
logger.info("This is an INFO test message")
logger.debug("This is a DEBUG message - only shows if DEBUG=True")
logger.warning("This is a WARNING test message")
logger.error("This is an ERROR test message")

print("\nLogging test complete. Check for test.log file.")
print(f"Current directory: {os.getcwd()}")
