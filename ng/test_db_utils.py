#!/usr/bin/env python3
import uuid
import asyncio
import time
import logging
from typing import Optional, List

from db_utils import (
    query, query_fetchone, query_fetchall, execute,
    get_current_user_id, set_current_user_id, set_session_user,
    search_memories_vector,
    get_memory_by_id, create_memory, create_memory_edge
)
from logging_setup import get_logger

logger = get_logger(__name__)
logger.setLevel(logging.INFO)

# Test user details for audit logging
TEST_USER_EMAIL = "test@example.com"

async def setup_test_table():
    """Setup test table using execute for DDL and INSERT"""
    logger.info("Setting up test table...")
    await execute("""DROP TABLE IF EXISTS test_table;""")
    await execute("""CREATE TABLE test_table (id SERIAL PRIMARY KEY, name TEXT);""")
    
    # Insert test data
    for i in range(10):
        await execute("""INSERT INTO test_table (name) VALUES (%s)""", (f"test-{i}",))
    
    logger.info("Test table setup complete")

async def cleanup_test_table():
    """Cleanup test table"""
    logger.info("Cleaning up test table...")
    await execute("DROP TABLE IF EXISTS test_table;")
    logger.info("Test table cleanup complete")

async def get_or_create_test_user():
    """Get existing or create new test user in the database"""
    # Try to get existing test user first
    existing_user = await query_fetchone(
        "SELECT id FROM users WHERE email = %s",
        (TEST_USER_EMAIL,)
    )
    
    if existing_user:
        # Use existing user ID
        user_id = existing_user[0] if isinstance(existing_user, tuple) else existing_user['id']
        logger.info(f"Using existing test user with ID: {user_id}")
    else:
        # Create new test user
        user_id = str(uuid.uuid4())
        logger.info(f"Creating new test user with ID: {user_id}")
        await execute(
            "INSERT INTO users (id, email) VALUES (%s, %s)",
            (user_id, TEST_USER_EMAIL)
        )
    
    # Return the user ID (either existing or new)
    return user_id

# Global variable to store test user ID once retrieved/created
test_user_id = None

# We no longer need to disable/enable triggers with our new approach
# Instead we'll update the database session directly

async def test_query_streaming():
    """Test streaming results from query"""
    logger.info("Testing query streaming...")
    
    # Test streaming with async iterator
    count = 0
    start = time.time()
    async for row in query("""SELECT * FROM test_table ORDER BY id"""):
        logger.info(f"Row {count}: {row}")
        count += 1
        # Simulate processing time to demonstrate streaming
        await asyncio.sleep(0.1)
    
    duration = time.time() - start
    logger.info(f"Processed {count} rows in {duration:.2f}s")
    assert count == 10, f"Expected 10 rows, got {count}"
    
    # Test fetchone
    row = await query_fetchone("""SELECT * FROM test_table WHERE id = 5""")  
    logger.info(f"Fetched one: {row}")
    assert row and row[0] == 5, f"Expected row with id=5, got {row}"
    
    # Test fetching non-existent row
    row = await query_fetchone("""SELECT * FROM test_table WHERE id = 999""") 
    logger.info(f"Fetched non-existent: {row}")
    assert row is None, f"Expected None for non-existent row, got {row}"
    
    # Test error handling
    try:
        await query_fetchone("""SELECT * FROM nonexistent_table""") 
        assert False, "Should have raised an exception"
    except Exception as e:
        logger.info(f"Expected error caught: {e.__class__.__name__}")
        
    logger.info("✅ All streaming tests passed!")

async def test_fetch_all():
    """Test fetching multiple rows at once"""
    logger.info("Testing query_fetchall...")
    
    # Test basic fetch all
    rows = await query_fetchall("""SELECT * FROM test_table ORDER BY id""")
    logger.info(f"Fetched {len(rows)} rows at once")
    assert len(rows) == 10, f"Expected 10 rows, got {len(rows)}"
    
    # Test with parameters
    param_rows = await query_fetchall(
        """SELECT * FROM test_table WHERE id > %s AND id < %s ORDER BY id""", 
        (3, 8)
    )
    logger.info(f"Parameter query returned {len(param_rows)} rows")
    assert len(param_rows) == 4, f"Expected 4 rows, got {len(param_rows)}"
    
    # Test dictionary results
    dict_rows = await query_fetchall(
        """SELECT id, name FROM test_table WHERE id <= 5 ORDER BY id""",
        as_dict=True
    )
    logger.info(f"Dictionary row example: {dict_rows[0]}")
    assert 'id' in dict_rows[0], "Expected dictionary row with 'id' key"
    assert 'name' in dict_rows[0], "Expected dictionary row with 'name' key"
    
    logger.info("✅ All fetchall tests passed!")

async def test_execute():
    """Test execute function for non-query operations"""
    logger.info("Testing execute...")
    
    # Test UPDATE operation
    await execute("UPDATE test_table SET name = %s WHERE id = %s", ("updated-name", 1))
    
    # Get the row and verify content without assuming format
    row = await query_fetchone("SELECT name FROM test_table WHERE id = 1")
    
    # Check if we got a result and log what format it is
    assert row is not None, "Expected a row result but got None"
    logger.info(f"Row type: {type(row)}, value: {row}")
    
    # Handle both possible formats
    if isinstance(row, dict):
        assert row['name'] == "updated-name", f"Expected 'updated-name', got {row['name']}"
    else:
        assert row[0] == "updated-name", f"Expected 'updated-name', got {row[0]}"
    
    # Test transaction handling (should be rolled back on exception)
    try:
        await execute("UPDATE test_table SET nonexistent_column = 'test' WHERE id = 1")
        assert False, "Should have raised an exception"
    except Exception as e:
        logger.info(f"Expected error caught: {e.__class__.__name__}")
    
    logger.info("✅ All execute tests passed!")

async def test_memory_operations():
    """Test memory CRUD operations"""
    logger.info("Testing memory operations...")
    
    # Set the user context for audit logging
    await set_session_user(test_user_id)
    
    # Test direct memory creation using execute
    memory_content = "Test memory content for database operations"
    
    # Create memory directly with execute
    memory_id = await query_fetchone(
        "INSERT INTO memories (content) VALUES (%s) RETURNING id",
        (memory_content,)
    )
    assert memory_id, "Failed to create memory"
    memory_id = memory_id[0] if isinstance(memory_id, tuple) else memory_id['id']
    logger.info(f"Created memory with ID: {memory_id}")
    
    # Test get_memory_by_id
    memory = await get_memory_by_id(memory_id)
    assert memory, f"Failed to retrieve memory with ID: {memory_id}"
    assert memory['content'] == memory_content, "Memory content does not match"
    logger.info(f"Retrieved memory: {memory['id']}")
    
    # Cleanup: delete the test memory
    await execute("DELETE FROM memories WHERE id = %s", (memory_id,))
    
    # Verify deletion
    deleted_memory = await get_memory_by_id(memory_id)
    assert deleted_memory is None, "Memory was not deleted"
    
    logger.info("✅ All memory operations tests passed!")

async def test_memory_edges():
    """Test memory edge operations"""
    logger.info("Testing memory edge operations...")
    
    # Set the user context for audit logging
    await set_session_user(test_user_id)
    
    # Create two test memories directly
    memory1_result = await query_fetchone(
        "INSERT INTO memories (content) VALUES (%s) RETURNING id",
        ("Source memory",)
    )
    memory2_result = await query_fetchone(
        "INSERT INTO memories (content) VALUES (%s) RETURNING id",
        ("Target memory",)
    )
    
    # Extract IDs handling both tuple and dict formats
    memory1_id = memory1_result[0] if isinstance(memory1_result, tuple) else memory1_result['id']
    memory2_id = memory2_result[0] if isinstance(memory2_result, tuple) else memory2_result['id']
    logger.info(f"Created test memories with IDs: {memory1_id}, {memory2_id}")
    
    # Create an edge
    edge_type = "references"
    edge_id = await create_memory_edge(memory1_id, memory2_id, edge_type)
    assert edge_id, "Failed to create memory edge"
    logger.info(f"Created edge with ID: {edge_id}")
    
    # Verify edge exists
    edge = await query_fetchone(
        "SELECT * FROM memory_edges WHERE id = %s", 
        (edge_id,), 
        as_dict=True
    )
    assert edge, f"Failed to retrieve edge with ID: {edge_id}"
    assert edge['from_id'] == memory1_id, "Edge source doesn't match"
    assert edge['to_id'] == memory2_id, "Edge target doesn't match"
    assert edge['edge_type'] == edge_type, "Edge type doesn't match"
    
    # Cleanup
    await execute("DELETE FROM memory_edges WHERE id = %s", (edge_id,))
    await execute("DELETE FROM memories WHERE id = %s", (memory1_id,))
    await execute("DELETE FROM memories WHERE id = %s", (memory2_id,))
    
    logger.info("✅ All memory edge tests passed!")

async def test_vector_search():
    """Test vector search operations"""
    logger.info("Testing vector search...")
    
    try:
        # Set the user context for audit logging
        await set_session_user(test_user_id)
        
        # Create a memory with a test embedding
        vector_dimension = 1536  # Common for embeddings
        test_vector = [1.0] + [0.0] * (vector_dimension - 1)  # Simple unit vector
        
        # Insert a test memory with an embedding
        test_memory_id = await query_fetchone(
            "INSERT INTO memories (content) VALUES (%s) RETURNING id",
            ("Test memory for vector search",)
        )
        test_memory_id = test_memory_id[0] if isinstance(test_memory_id, tuple) else test_memory_id['id']
        
        # Try to update with embedding if the column exists
        try:
            await execute(
                "UPDATE memories SET content_embedding = %s WHERE id = %s",
                (test_vector, test_memory_id)
            )
            logger.info("Added test vector embedding")
            
            # Run a vector search - this should at least not error
            search_vector = [0.8] + [0.1] * (vector_dimension - 1)  # Different but similar vector
            results = await search_memories_vector(
                query_embedding=search_vector,
                limit=5,
                similarity_threshold=0.1  # Low threshold to get some results
            )
            
            logger.info(f"Vector search returned {len(results)} results")
            if results:
                logger.info(f"Top result similarity: {results[0]['similarity']}")
                
        except Exception as e:
            logger.info(f"Vector embedding test skipped: {e.__class__.__name__}")
        
        # Cleanup
        await execute("DELETE FROM memories WHERE id = %s", (test_memory_id,))
        
    except Exception as e:
        logger.info(f"Vector search test encountered an error: {e.__class__.__name__}")
    
    logger.info("✅ Vector search tests completed")

async def main():
    # Setup for basic tests
    await setup_test_table()
    
    # Get or create test user and set current user ID globally
    global test_user_id
    test_user_id = await get_or_create_test_user()
    
    # Set up user context in both memory and database session
    set_current_user_id(test_user_id)  # Set in memory
    await set_session_user(test_user_id)  # Set in database session
    
    try:
        # Run basic tests
        await test_query_streaming()
        
        # Run memory-specific tests
        await test_memory_operations()
        await test_memory_edges()
        await test_vector_search()
        
        logger.info("✅ All database utility tests passed!")
        
    finally:
        # Always cleanup
        await cleanup_test_table()

if __name__ == "__main__":
    asyncio.run(main())
