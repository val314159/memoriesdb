#!/usr/bin/env python3
"""
Test runner that loads .env before running tests.
"""
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file
load_dotenv()

# Import the test module after setting up the path
from tests import test_memory_graph

if __name__ == "__main__":
    
    # Run the test script
    test_memory_graph.main()
