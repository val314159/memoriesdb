#!/usr/bin/env python3
"""
Test script for the MemoryGraph API.
"""
import os
import sys
import uuid
import psycopg2
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from memoriesdb.api.memory_graph import MemoryGraph
from memoriesdb.api import connect

def print_title(title: str):
    """Print a section title."""
    print(f"\n{'='*80}\n{title}\n{'='*80}")

def print_result(label: str, result: Any):
    """Print a result with a label."""
    print(f"\n{label}:")
    if isinstance(result, list):
        for i, item in enumerate(result, 1):
            print(f"{i}. {item}")
    elif isinstance(result, dict):
        for k, v in result.items():
            print(f"- {k}: {v}")
    else:
        print(result)

def test_basic_operations(db):
    """Test basic CRUD operations."""
    print_title("Testing Basic Operations")
    
    # Create a memory
    memory = db.create_memory("Test memory", {"type": "test", "tags": ["test", "example"]})
    print_result("Created memory", memory)
    
    # Get the memory by ID
    fetched = db.get_memory(memory['id'])
    print_result("Fetched memory", fetched)
    
    # Search for the memory
    search_results = db.search_memories("test")
    print_result("Search results", search_results)

def test_session_management(db):
    """Test session creation and messaging."""
    print_title("Testing Session Management")
    
    # Create a session
    session = db.create_session("Test Session", {"description": "A test conversation"})
    print_result("Created session", session)
    
    # Add some messages
    messages = [
        ("system", "You are a helpful assistant."),
        ("user", "Hello, how are you?"),
        ("assistant", "I'm doing well, thank you! How can I help you today?")
    ]
    
    for role, content in messages:
        msg = db.add_message(session['id'], role, content)
        print_result(f"Added {role} message", msg)
    
    # Get all messages in the session
    session_messages = db.get_session_messages(session['id'])
    print_result("Session messages", session_messages)

def test_forking(db):
    """Test session forking."""
    print_title("Testing Session Forking")
    
    # Create an original session with some messages
    original = db.create_session("Original Session")
    db.add_message(original['id'], "user", "Original message")
    
    # Fork the session
    forked = db.fork_session(original['id'], "Forked Session")
    print_result("Forked session", forked)
    
    # Add messages to both sessions
    db.add_message(original['id'], "user", "Continued in original")
    db.add_message(forked['id'], "user", "Continued in fork")
    
    # Show messages in both sessions
    print_result("Original session messages", db.get_session_messages(original['id']))
    print_result("Forked session messages", db.get_session_messages(forked['id']))

def test_semantic_search(db):
    """Test semantic search with vector embeddings."""
    print_title("Testing Semantic Search")
    
    # Create a helper function to generate random 1024-dim vectors
    def random_vector():
        import random
        return [random.uniform(-1, 1) for _ in range(1024)]
    
    # Create some sample memories with 1024-dim embeddings
    samples = [
        ("The sky is blue", random_vector()),
        ("The ocean is deep", random_vector()),
        ("Apples are red", random_vector())
    ]
    
    for content, embedding in samples:
        db.create_memory(content, {}, content_embedding=embedding)
    
    # Use the first sample's embedding as the query (should be most similar to itself)
    query_embedding = samples[0][1]
    results = db.semantic_search(query_embedding, limit=2)
    print_result("Semantic search results", results)

def main():
    """Run all tests."""
    # Connect to the database with explicit credentials
    db = connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        dbname=os.getenv('POSTGRES_DB', 'memories'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'pencil'),
        port=os.getenv('POSTGRES_PORT', '5432')
    )
    
    try:
        test_basic_operations(db)
        test_session_management(db)
        test_forking(db)
        test_semantic_search(db)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\nAll tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
